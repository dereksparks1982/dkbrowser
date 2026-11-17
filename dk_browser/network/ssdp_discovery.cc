// Copyright 2026 DK Softworks.
// Native SSDP discovery used only after a DK NetNav user action.
// LAN responses are untrusted; do not fetch LOCATION URLs in this phase.
#include "dk_browser/network/ssdp_discovery.h"

#include <arpa/inet.h>
#include <poll.h>
#include <sys/socket.h>
#include <unistd.h>

#include <algorithm>
#include <array>
#include <chrono>
#include <cctype>
#include <cstdint>
#include <cstring>
#include <map>
#include <set>
#include <string>
#include <string_view>
#include <utility>
#include <vector>

namespace dk_browser::network {
namespace {

constexpr char kMulticastAddress[] = "239.255.255.250";
constexpr int kSsdpPort = 1900;
constexpr auto kScanWindow = std::chrono::seconds(3);
constexpr size_t kMaxDatagram = 8192;
constexpr size_t kMaxResponses = 128;
constexpr size_t kMaxDevices = 32;

bool IsLocalIPv4(in_addr address) {
  const uint32_t ip = ntohl(address.s_addr);
  return (ip & 0xff000000) == 0x0a000000 ||    // 10/8
         (ip & 0xfff00000) == 0xac100000 ||    // 172.16/12
         (ip & 0xffff0000) == 0xc0a80000 ||    // 192.168/16
         (ip & 0xffff0000) == 0xa9fe0000;     // link local
}

std::string Trim(std::string_view value) {
  while (!value.empty() && (value.front() == ' ' || value.front() == '\t'))
    value.remove_prefix(1);
  while (!value.empty() &&
         (value.back() == ' ' || value.back() == '\t' ||
          value.back() == '\r'))
    value.remove_suffix(1);
  return std::string(value);
}

std::string Lower(std::string_view input) {
  std::string output(input);
  for (char& ch : output)
    ch = static_cast<char>(std::tolower(static_cast<unsigned char>(ch)));
  return output;
}

bool PrintableHeader(std::string_view value) {
  if (value.empty() || value.size() > 200)
    return false;
  for (unsigned char ch : value) {
    if (ch < 0x20 || ch > 0x7e)
      return false;
  }
  return true;
}

// Never trust an arbitrary URL found in a multicast response. For this first
// milestone, accept only an HTTP URL with a literal private IPv4 address
// matching the actual datagram sender, with a valid explicit/implicit port.
// A later description-fetch phase needs further URL/redirect restrictions.
bool LocationMatchesSender(std::string_view url, in_addr sender) {
  if (url.size() > 512 || url.substr(0, 7) != "http://")
    return false;
  url.remove_prefix(7);
  const size_t slash = url.find_first_of("/?#");
  const std::string_view authority = url.substr(0, slash);
  if (authority.empty() || authority.find('@') != std::string_view::npos)
    return false;
  const size_t colon = authority.find(':');
  const std::string host(authority.substr(0, colon));
  in_addr location_ip{};
  if (inet_pton(AF_INET, host.c_str(), &location_ip) != 1 ||
      location_ip.s_addr != sender.s_addr || !IsLocalIPv4(location_ip)) {
    return false;
  }
  if (colon != std::string_view::npos) {
    const std::string_view port = authority.substr(colon + 1);
    if (port.empty() || port.size() > 5)
      return false;
    int number = 0;
    for (char ch : port) {
      if (ch < '0' || ch > '9')
        return false;
      number = number * 10 + (ch - '0');
    }
    if (number < 1 || number > 65535)
      return false;
  }
  return true;
}

bool ParseResponse(std::string_view text, const sockaddr_in& from,
                   MediaDevice* device) {
  if (!IsLocalIPv4(from.sin_addr) || text.size() > kMaxDatagram ||
      (text.substr(0, 12) != "HTTP/1.1 200" &&
       text.substr(0, 12) != "HTTP/1.0 200")) {
    return false;
  }

  std::map<std::string, std::string> headers;
  size_t start = text.find('\n');
  if (start == std::string_view::npos)
    return false;
  ++start;
  for (size_t count = 0; start < text.size() && count < 40; ++count) {
    const size_t end = text.find('\n', start);
    if (end == std::string_view::npos)
      break;
    const std::string_view line = text.substr(start, end - start);
    start = end + 1;
    if (line == "\r" || line.empty())
      break;
    const size_t colon = line.find(':');
    if (colon == std::string_view::npos)
      return false;
    const std::string key = Lower(Trim(line.substr(0, colon)));
    const std::string value = Trim(line.substr(colon + 1));
    if (key.empty() || key.size() > 40 || !PrintableHeader(value))
      return false;
    headers.emplace(key, value);
  }

  const auto st = headers.find("st");
  const auto usn = headers.find("usn");
  const auto location = headers.find("location");
  if (st == headers.end() || usn == headers.end() ||
      location == headers.end() || usn->second.size() > 160 ||
      Lower(usn->second).find("uuid:") == std::string::npos ||
      !LocationMatchesSender(location->second, from.sin_addr)) {
    return false;
  }

  const std::string target = Lower(st->second);
  if (target.find("urn:schemas-upnp-org:device:mediaserver:") == 0) {
    device->kind = "server";
  } else if (target.find("urn:schemas-upnp-org:device:mediarenderer:") == 0) {
    device->kind = "renderer";
  } else {
    return false;
  }
  // No unsolicited network device data is exposed to renderer pages.
  std::array<char, INET_ADDRSTRLEN> address{};
  if (!inet_ntop(AF_INET, &from.sin_addr, address.data(), address.size()))
    return false;
  device->address = address.data();
  device->usn = usn->second;
  device->description_url = location->second;
  const auto server = headers.find("server");
  device->server_header = server == headers.end() ? "" :
                          server->second.substr(0, 100);
  return true;
}

void SendSearch(int fd, const sockaddr_in& destination,
                std::string_view device_type) {
  std::string request =
      "M-SEARCH * HTTP/1.1\r\n"
      "HOST: 239.255.255.250:1900\r\n"
      "MAN: \"ssdp:discover\"\r\n"
      "MX: 2\r\n"
      "ST: " + std::string(device_type) + "\r\n\r\n";
  sendto(fd, request.data(), request.size(), 0,
         reinterpret_cast<const sockaddr*>(&destination),
         sizeof(destination));
}

}  // namespace

std::vector<MediaDevice> DiscoverLocalMediaDevices() {
  std::vector<MediaDevice> devices;
  const int fd = socket(AF_INET, SOCK_DGRAM | SOCK_CLOEXEC, 0);
  if (fd < 0)
    return devices;

  sockaddr_in local{};
  local.sin_family = AF_INET;
  local.sin_port = 0;
  local.sin_addr.s_addr = htonl(INADDR_ANY);
  if (bind(fd, reinterpret_cast<sockaddr*>(&local), sizeof(local)) != 0) {
    close(fd);
    return devices;
  }
  sockaddr_in destination{};
  destination.sin_family = AF_INET;
  destination.sin_port = htons(kSsdpPort);
  if (inet_pton(AF_INET, kMulticastAddress, &destination.sin_addr) != 1) {
    close(fd);
    return devices;
  }
  SendSearch(fd, destination, "urn:schemas-upnp-org:device:MediaServer:1");
  SendSearch(fd, destination, "urn:schemas-upnp-org:device:MediaRenderer:1");

  const auto deadline = std::chrono::steady_clock::now() + kScanWindow;
  std::set<std::string> seen;
  size_t received = 0;
  while (received < kMaxResponses && devices.size() < kMaxDevices) {
    auto remaining = std::chrono::duration_cast<std::chrono::milliseconds>(
        deadline - std::chrono::steady_clock::now());
    if (remaining.count() <= 0)
      break;
    pollfd descriptor{fd, POLLIN, 0};
    const int wait = std::min<int>(remaining.count(), 350);
    const int ready = poll(&descriptor, 1, wait);
    if (ready < 0)
      break;
    if (ready == 0 || !(descriptor.revents & POLLIN))
      continue;
    sockaddr_in from{};
    socklen_t from_length = sizeof(from);
    std::array<char, kMaxDatagram + 1> buffer{};
    const ssize_t count = recvfrom(
        fd, buffer.data(), buffer.size(), 0,
        reinterpret_cast<sockaddr*>(&from), &from_length);
    ++received;
    if (count <= 0 || count > static_cast<ssize_t>(kMaxDatagram) ||
        from_length != sizeof(from) || from.sin_family != AF_INET) {
      continue;
    }
    MediaDevice item;
    if (ParseResponse(std::string_view(buffer.data(), count), from, &item) &&
        seen.insert(item.usn).second) {
      devices.push_back(std::move(item));
    }
  }
  close(fd);
  return devices;
}

}  // namespace dk_browser::network

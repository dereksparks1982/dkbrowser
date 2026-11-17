// Copyright 2026 DK Softworks.
#include "dk_browser/network/content_directory.h"

#include <arpa/inet.h>
#include <fcntl.h>
#include <poll.h>
#include <sys/socket.h>
#include <unistd.h>

#include <algorithm>
#include <array>
#include <chrono>
#include <cctype>
#include <cstdint>
#include <cstdlib>
#include <iterator>
#include <limits>
#include <optional>
#include <string>
#include <string_view>
#include <utility>
#include <vector>

namespace dk_browser::network {
namespace {

constexpr size_t kMaxResponse = 384 * 1024;
constexpr size_t kMaxXml = 256 * 1024;
constexpr size_t kMaxEntries = kMediaLibraryPageSize;
constexpr int kRequestTimeoutMs = 1800;
constexpr size_t kMaxHeader = 8192;

struct Url {
  std::string host;
  std::string path;
  uint16_t port = 80;
  in_addr address{};
};

bool IsLocal(in_addr addr) {
  const uint32_t ip = ntohl(addr.s_addr);
  return (ip & 0xff000000) == 0x0a000000 ||
         (ip & 0xfff00000) == 0xac100000 ||
         (ip & 0xffff0000) == 0xc0a80000 ||
         (ip & 0xffff0000) == 0xa9fe0000;
}

std::string Lower(std::string_view s) {
  std::string out(s);
  for (char& c : out)
    c = static_cast<char>(std::tolower(static_cast<unsigned char>(c)));
  return out;
}

std::string Trim(std::string_view s) {
  while (!s.empty() && std::isspace(static_cast<unsigned char>(s.front())))
    s.remove_prefix(1);
  while (!s.empty() && std::isspace(static_cast<unsigned char>(s.back())))
    s.remove_suffix(1);
  return std::string(s);
}

bool ParseUrl(std::string_view raw, std::string_view expected_host, Url* out) {
  if (raw.size() > 1024 || raw.substr(0, 7) != "http://")
    return false;
  raw.remove_prefix(7);
  const size_t slash = raw.find_first_of("/?#");
  const auto authority = raw.substr(0, slash);
  const size_t colon = authority.find(':');
  const std::string host(authority.substr(0, colon));
  if (host != expected_host || host.empty() || authority.find('@') != authority.npos ||
      authority.find('[') != authority.npos)
    return false;
  in_addr addr{};
  if (inet_pton(AF_INET, host.c_str(), &addr) != 1 || !IsLocal(addr))
    return false;
  int port = 80;
  if (colon != authority.npos) {
    auto digits = authority.substr(colon + 1);
    if (digits.empty() || digits.size() > 5)
      return false;
    port = 0;
    for (char c : digits) {
      if (c < '0' || c > '9')
        return false;
      port = port * 10 + (c - '0');
    }
    if (port < 1 || port > 65535)
      return false;
  }
  auto rest = slash == raw.npos ? std::string_view("/") : raw.substr(slash);
  if (rest.empty() || rest.front() != '/' || rest.find('#') != rest.npos ||
      rest.find('\\') != rest.npos || rest.size() > 768)
    return false;
  for (unsigned char ch : rest) {
    if (ch < 32 || ch > 126)
      return false;
  }
  out->host = host;
  out->address = addr;
  out->port = static_cast<uint16_t>(port);
  out->path = std::string(rest);
  return true;
}

// Only expose media types that Chromium's native playback path may handle.
// Real support depends on the server's headers and available decoders.
bool SupportedStreamType(std::string_view mime) {
  constexpr std::string_view kSupportedTypes[] = {
      "audio/mpeg", "audio/mp4", "audio/aac", "audio/ogg",
      "audio/wav", "audio/x-wav", "audio/flac", "audio/webm",
      "video/mp4", "video/webm", "video/ogg", "video/mpeg",
      "video/mp2t", "video/x-matroska",
  };
  return std::find(std::begin(kSupportedTypes), std::end(kSupportedTypes),
                   mime) != std::end(kSupportedTypes);
}

// Extract the MIME component from DLNA protocolInfo. Refuse unadvertised
// protocols, schemes and opaque binary resources rather than forwarding
// arbitrary links to the browser.
std::string MediaMime(std::string_view protocol_info) {
  const auto first = protocol_info.find(':');
  if (first == protocol_info.npos ||
      Lower(Trim(protocol_info.substr(0, first))) != "http-get")
    return "";
  const auto second = protocol_info.find(':', first + 1);
  if (second == protocol_info.npos)
    return "";
  const auto third = protocol_info.find(':', second + 1);
  if (third == protocol_info.npos)
    return "";
  const std::string mime = Lower(Trim(
      protocol_info.substr(second + 1, third - second - 1)));
  return SupportedStreamType(mime) ? mime : "";
}

// A device's ControlURL may be absolute or relative to its description URL.
// Never allow it to choose a new IP address, network segment or port.
bool ControlUrl(std::string_view control, const Url& description, Url* out) {
  if (control.empty() || control.size() > 768 ||
      control.find('#') != control.npos || control.find('\\') != control.npos)
    return false;
  if (control.substr(0, 7) == "http://") {
    if (!ParseUrl(control, description.host, out))
      return false;
    return out->port == description.port;
  }
  if (control.find("://") != control.npos || control.substr(0, 2) == "//")
    return false;
  std::string path;
  if (control.front() == '/') {
    path = std::string(control);
  } else {
    size_t dir = description.path.find_last_of('/');
    path = description.path.substr(0, dir == std::string::npos ? 0 : dir + 1);
    path += control;
  }
  if (path.size() > 768)
    return false;
  for (unsigned char ch : path) {
    if (ch < 32 || ch > 126)
      return false;
  }
  *out = description;
  out->path = path;
  return true;
}

bool WaitReady(int fd, short events,
               std::chrono::steady_clock::time_point deadline) {
  for (;;) {
    const auto ms = std::chrono::duration_cast<std::chrono::milliseconds>(
        deadline - std::chrono::steady_clock::now()).count();
    if (ms <= 0)
      return false;
    pollfd p{fd, events, 0};
    int ready = poll(&p, 1, static_cast<int>(ms));
    if (ready == 0)
      return false;
    if (ready < 0)
      continue;
    return (p.revents & events) != 0 && !(p.revents & (POLLERR | POLLNVAL));
  }
}

std::optional<std::string> Fetch(const Url& url, std::string_view method,
                                 std::string_view body,
                                 std::string_view soap_action) {
  const int fd = socket(AF_INET, SOCK_STREAM | SOCK_NONBLOCK | SOCK_CLOEXEC, 0);
  if (fd < 0)
    return std::nullopt;
  const auto deadline = std::chrono::steady_clock::now() +
                        std::chrono::milliseconds(kRequestTimeoutMs);
  sockaddr_in target{};
  target.sin_family = AF_INET;
  target.sin_port = htons(url.port);
  target.sin_addr = url.address;
  if (connect(fd, reinterpret_cast<sockaddr*>(&target), sizeof(target)) < 0) {
    if (!WaitReady(fd, POLLOUT, deadline)) {
      close(fd);
      return std::nullopt;
    }
    int error = 0;
    socklen_t error_size = sizeof(error);
    if (getsockopt(fd, SOL_SOCKET, SO_ERROR, &error, &error_size) != 0 ||
        error != 0) {
      close(fd);
      return std::nullopt;
    }
  }
  std::string request = std::string(method) + " " + url.path + " HTTP/1.1\r\n" +
      "Host: " + url.host + ":" + std::to_string(url.port) + "\r\n"
      "Connection: close\r\n"
      "Accept: text/xml, application/xml\r\n"
      "User-Agent: DKNetNav/1.0 UPnP/1.1\r\n";
  if (method == "POST") {
    request += "Content-Type: text/xml; charset=\"utf-8\"\r\n";
    request += "SOAPACTION: \"" + std::string(soap_action) + "\"\r\n";
    request += "Content-Length: " + std::to_string(body.size()) + "\r\n";
  }
  request += "\r\n";
  request += body;
  size_t sent = 0;
  while (sent < request.size()) {
    if (!WaitReady(fd, POLLOUT, deadline)) {
      close(fd);
      return std::nullopt;
    }
    const ssize_t n = send(fd, request.data() + sent,
                           request.size() - sent, MSG_NOSIGNAL);
    if (n <= 0) {
      close(fd);
      return std::nullopt;
    }
    sent += static_cast<size_t>(n);
  }
  std::string raw;
  while (raw.size() <= kMaxResponse) {
    if (!WaitReady(fd, POLLIN, deadline))
      break;
    std::array<char, 8192> buf{};
    const ssize_t n = recv(fd, buf.data(), buf.size(), 0);
    if (n <= 0)
      break;
    raw.append(buf.data(), n);
  }
  close(fd);
  const size_t headers_end = raw.find("\r\n\r\n");
  if (raw.size() > kMaxResponse || headers_end == std::string::npos ||
      headers_end > kMaxHeader || raw.substr(0, 12) != "HTTP/1.1 200" &&
      raw.substr(0, 12) != "HTTP/1.0 200") {
    return std::nullopt;
  }
  const std::string headers = Lower(std::string_view(raw).substr(0, headers_end));
  std::string data = raw.substr(headers_end + 4);
  if (headers.find("\ntransfer-encoding: chunked") != std::string::npos) {
    std::string output;
    size_t at = 0;
    for (;;) {
      const size_t end = data.find("\r\n", at);
      if (end == data.npos || end - at > 20)
        return std::nullopt;
      const std::string hex = data.substr(at, end - at);
      if (hex.empty() || hex.find_first_not_of("0123456789abcdefABCDEF") != hex.npos)
        return std::nullopt;
      unsigned long chunk = std::strtoul(hex.c_str(), nullptr, 16);
      if (chunk > kMaxXml || output.size() + chunk > kMaxXml)
        return std::nullopt;
      at = end + 2;
      if (chunk == 0)
        return output;
      if (at + chunk + 2 > data.size() ||
          data.substr(at + chunk, 2) != "\r\n")
        return std::nullopt;
      output.append(data, at, chunk);
      at += chunk + 2;
    }
  }
  const size_t length_at = headers.find("\ncontent-length:");
  if (length_at != headers.npos) {
    const size_t start = length_at + std::string("\ncontent-length:").size();
    const size_t end = headers.find("\r\n", start);
    if (end == headers.npos)
      return std::nullopt;
    const std::string count = Trim(std::string_view(headers).substr(start, end-start));
    if (count.empty() || count.size() > 8 ||
        count.find_first_not_of("0123456789") != count.npos)
      return std::nullopt;
    size_t needed = std::strtoul(count.c_str(), nullptr, 10);
    if (needed > kMaxXml || data.size() < needed)
      return std::nullopt;
    data.resize(needed);
  }
  if (data.size() > kMaxXml)
    return std::nullopt;
  return data;
}

bool AllowedXml(std::string_view xml) {
  if (xml.empty() || xml.size() > kMaxXml)
    return false;
  std::string lower = Lower(xml);
  return lower.find("<!doctype") == lower.npos &&
         lower.find("<!entity") == lower.npos &&
         lower.find("<![cdata") == lower.npos &&
         lower.find("<!include") == lower.npos;
}

struct Element {
  std::string opening;
  std::string inner;
  size_t next = 0;
};

// Bounded tag scanner: handles namespace prefixes and quoted attributes.
// It does not use XML DTDs, external entities or network parsers.
std::optional<Element> FindElement(std::string_view xml,
                                   std::string_view local_name,
                                   size_t from = 0) {
  size_t cursor = from;
  size_t count = 0;
  while (cursor < xml.size() && ++count < 12000) {
    size_t start = xml.find('<', cursor);
    if (start == xml.npos)
      break;
    size_t close = start + 1;
    if (close >= xml.size())
      break;
    if (xml[close] == '?' || xml[close] == '!') {
      size_t end = xml.find('>', close);
      if (end == xml.npos)
        break;
      cursor = end + 1;
      continue;
    }
    if (xml[close] == '/') {
      cursor = close + 1;
      continue;
    }
    size_t name_end = close;
    while (name_end < xml.size() &&
           !std::isspace(static_cast<unsigned char>(xml[name_end])) &&
           xml[name_end] != '>' && xml[name_end] != '/')
      ++name_end;
    auto name = xml.substr(close, name_end - close);
    auto colon = name.rfind(':');
    auto local = name.substr(colon == name.npos ? 0 : colon + 1);
    size_t end = name_end;
    char quote = 0;
    for (; end < xml.size(); ++end) {
      char c = xml[end];
      if (quote) {
        if (c == quote)
          quote = 0;
      } else if (c == '"' || c == '\'') {
        quote = c;
      } else if (c == '>') {
        break;
      }
    }
    if (end == xml.size())
      break;
    cursor = end + 1;
    if (local != local_name || (end > start && xml[end-1] == '/'))
      continue;
    std::string terminator = "</" + std::string(name) + ">";
    size_t stop = xml.find(terminator, cursor);
    if (stop == xml.npos)
      return std::nullopt;
    return Element{std::string(xml.substr(start, end - start + 1)),
                   std::string(xml.substr(cursor, stop-cursor)),
                   stop + terminator.size()};
  }
  return std::nullopt;
}

std::string Unescape(std::string_view input) {
  std::string text;
  text.reserve(std::min<size_t>(input.size(), kMaxXml));
  for (size_t i = 0; i < input.size() && text.size() < kMaxXml; ++i) {
    if (input[i] != '&') {
      text.push_back(input[i]);
      continue;
    }
    const size_t end = input.find(';', i + 1);
    if (end == input.npos || end-i > 12) {
      text.push_back('&');
      continue;
    }
    const auto ref = input.substr(i + 1, end - i - 1);
    char replacement = 0;
    if (ref == "lt") replacement = '<';
    if (ref == "gt") replacement = '>';
    if (ref == "amp") replacement = '&';
    if (ref == "quot") replacement = '"';
    if (ref == "apos") replacement = '\'';
    if (replacement) {
      text.push_back(replacement);
      i = end;
    } else {
      text.push_back('&');
    }
  }
  return text;
}

std::string Escape(std::string_view input) {
  std::string out;
  for (unsigned char c : input) {
    if (c < 0x20 || c == 0x7f)
      continue;
    switch (c) {
      case '&': out += "&amp;"; break;
      case '<': out += "&lt;"; break;
      case '>': out += "&gt;"; break;
      case '"': out += "&quot;"; break;
      case '\'': out += "&apos;"; break;
      default: out.push_back(c);
    }
  }
  return out;
}

std::string Field(std::string_view xml, std::string_view name) {
  const auto found = FindElement(xml, name);
  return found ? Trim(Unescape(found->inner)) : "";
}

std::optional<uint32_t> ParseCount(std::string_view input) {
  // Reject negative, malformed, excessively long and overflowing counters.
  if (input.empty() || input.size() > 10)
    return std::nullopt;
  uint64_t value = 0;
  for (char digit : input) {
    if (digit < '0' || digit > '9')
      return std::nullopt;
    value = value * 10 + static_cast<unsigned>(digit - '0');
    if (value > std::numeric_limits<uint32_t>::max())
      return std::nullopt;
  }
  return static_cast<uint32_t>(value);
}

std::string Attr(std::string_view tag, std::string_view name) {
  // Match exact attribute boundary, never 'parentid' for 'id'.
  for (size_t at = 0; at < tag.size();) {
    at = tag.find(name, at);
    if (at == tag.npos)
      return "";
    if (at > 0 && !std::isspace(static_cast<unsigned char>(tag[at-1]))) {
      at += name.size();
      continue;
    }
    size_t after = at + name.size();
    while (after < tag.size() &&
           std::isspace(static_cast<unsigned char>(tag[after])))
      ++after;
    if (after >= tag.size() || tag[after] != '=') {
      at += name.size();
      continue;
    }
    ++after;
    while (after < tag.size() &&
           std::isspace(static_cast<unsigned char>(tag[after])))
      ++after;
    if (after >= tag.size() || (tag[after] != '"' && tag[after] != '\''))
      return "";
    const char quote = tag[after++];
    const size_t end = tag.find(quote, after);
    if (end == tag.npos)
      return "";
    return Unescape(tag.substr(after, end-after));
  }
  return "";
}

}  // namespace

LibraryPage BrowseMediaFolder(const MediaDevice& device,
                              const std::string& object_id,
                              uint32_t starting_index) {
  LibraryPage page;
  page.address = device.address;
  page.device_name = device.address;
  page.first_index = starting_index;
  if (object_id.size() > 256 || device.address.empty() ||
      starting_index > kMaxMediaLibraryIndex) {
    page.error = "Invalid folder identifier.";
    return page;
  }
  Url description{};
  if (!ParseUrl(device.description_url, device.address, &description)) {
    page.error = "Device description URL is not a safe local address.";
    return page;
  }
  auto description_xml = Fetch(description, "GET", "", "");
  if (!description_xml || !AllowedXml(*description_xml)) {
    page.error = "Cannot read a valid local device description.";
    return page;
  }
  const auto root_device = FindElement(*description_xml, "device");
  if (!root_device) {
    page.error = "Missing UPnP device information.";
    return page;
  }
  const std::string name = Field(root_device->inner, "friendlyName");
  if (!name.empty())
    page.device_name = name.substr(0, 100);
  if (device.kind == "renderer") {
    page.is_renderer = true;
    return page;
  }

  std::string control;
  std::string service_type;
  size_t pos = 0;
  for (size_t n = 0; n < 64; ++n) {
    auto service = FindElement(root_device->inner, "service", pos);
    if (!service)
      break;
    pos = service->next;
    std::string type = Field(service->inner, "serviceType");
    if (type == "urn:schemas-upnp-org:service:ContentDirectory:1" ||
        type == "urn:schemas-upnp-org:service:ContentDirectory:2" ||
        type == "urn:schemas-upnp-org:service:ContentDirectory:3" ||
        type == "urn:schemas-upnp-org:service:ContentDirectory:4") {
      service_type = std::move(type);
      control = Field(service->inner, "controlURL");
      break;
    }
  }
  Url endpoint{};
  if (service_type.empty() || !ControlUrl(control, description, &endpoint)) {
    page.error = "This device has no supported local ContentDirectory service.";
    return page;
  }

  std::string request =
      "<?xml version=\"1.0\" encoding=\"utf-8\"?>"
      "<s:Envelope xmlns:s=\"http://schemas.xmlsoap.org/soap/envelope/\" "
      "s:encodingStyle=\"http://schemas.xmlsoap.org/soap/encoding/\">"
      "<s:Body><u:Browse xmlns:u=\"" + service_type + "\">"
      "<ObjectID>" + Escape(object_id) + "</ObjectID>"
      "<BrowseFlag>BrowseDirectChildren</BrowseFlag>"
      "<Filter>*</Filter><StartingIndex>" +
      std::to_string(starting_index) + "</StartingIndex>"
      "<RequestedCount>" + std::to_string(kMediaLibraryPageSize) +
      "</RequestedCount><SortCriteria/>"
      "</u:Browse></s:Body></s:Envelope>";
  const std::string action = service_type + "#Browse";
  auto response = Fetch(endpoint, "POST", request, action);
  if (!response || !AllowedXml(*response)) {
    page.error = "Unable to browse this device's shared folders.";
    return page;
  }
  const auto result_element = FindElement(*response, "Result");
  if (!result_element) {
    page.error = "Device did not return a ContentDirectory result.";
    return page;
  }
  // Empty Result is valid for an empty folder or terminal page.
  const std::string result = Trim(Unescape(result_element->inner));
  if (!result.empty() && !AllowedXml(result)) {
    page.error = "Device returned invalid ContentDirectory XML.";
    return page;
  }
  // Count parsed DIDL records even when a record has no usable title.
  uint32_t records_seen = 0;
  for (size_t pos = 0; pos < result.size() &&
                       records_seen < kMaxEntries;) {
    size_t next_container = result.find("<container", pos);
    size_t next_item = result.find("<item", pos);
    size_t at = std::min(next_container, next_item);
    if (at == std::string::npos)
      break;
    const bool folder = at == next_container;
    const auto entry = FindElement(result, folder ? "container" : "item", at);
    if (!entry) {
      pos = at + 2;
      continue;
    }
    pos = entry->next;
    ++records_seen;
    std::string id = Attr(entry->opening, "id");
    std::string title = Field(entry->inner, "title");
    if (id.empty() || id.size() > 256 || title.empty())
      continue;
    LibraryEntry item;
    item.id = std::move(id);
    item.title = title.substr(0, 180);
    item.is_folder = folder;
    if (!folder) {
      // ContentDirectory items may advertise many <res> endpoints. Check
      // only a bounded number and choose the first compatible HTTP GET
      // resource on the same private IPv4 host as the SSDP responder.
      size_t resource_cursor = 0;
      for (size_t resource_count = 0; resource_count < 12;
           ++resource_count) {
        const auto resource =
            FindElement(entry->inner, "res", resource_cursor);
        if (!resource)
          break;
        resource_cursor = resource->next;
        const std::string media_type =
            MediaMime(Attr(resource->opening, "protocolInfo"));
        if (media_type.empty())
          continue;
        const std::string candidate = Trim(Unescape(resource->inner));
        Url resolved{};
        if (!ParseUrl(candidate, device.address, &resolved))
          continue;
        // Browsing XML never contacts media URLs. The selected URL is
        // handed to Chromium only after an explicit Play click.
        item.media_type = media_type;
        item.resource_url = candidate;
        break;
      }
    }
    page.entries.push_back(std::move(item));
  }
  const auto reported = ParseCount(Field(*response, "NumberReturned"));
  // Some devices omit NumberReturned; others report a larger count than
  // the requested page. Never advance by more than the bounded page size.
  uint32_t advanced = records_seen;
  if (reported && *reported > 0 && *reported <= kMediaLibraryPageSize)
    advanced = std::max(advanced, *reported);
  const auto total = ParseCount(Field(*response, "TotalMatches"));
  // Some servers incorrectly report zero even when they supplied results.
  page.total_matches_known = total.has_value() &&
                             (*total != 0 || advanced == 0);
  if (page.total_matches_known)
    page.total_matches = *total;
  if (advanced > 0 &&
      starting_index <= kMaxMediaLibraryIndex - advanced) {
    page.next_index = starting_index + advanced;
    page.more_entries =
        (page.total_matches_known && page.next_index < page.total_matches) ||
        (!page.total_matches_known && advanced == kMediaLibraryPageSize);
  }
  return page;
}

}  // namespace dk_browser::network

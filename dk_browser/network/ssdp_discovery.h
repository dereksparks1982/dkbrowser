// Copyright 2026 DK Softworks.
// Built-in, opt-in LAN device discovery for DK NetNav.
#ifndef DK_BROWSER_NETWORK_SSDP_DISCOVERY_H_
#define DK_BROWSER_NETWORK_SSDP_DISCOVERY_H_

#include <string>
#include <vector>

namespace dk_browser::network {

struct MediaDevice {
  std::string address;
  std::string description_url;
  std::string usn;
  std::string server_header;
  // Either "server" (shared media) or "renderer" (playback equipment).
  std::string kind;
};

// Linux-only, synchronous worker function. Always call this from a blocking
// task, never on Chromium's UI thread. Makes two bounded SSDP M-SEARCH
// requests; no background listener, device fetching, or persistent state.
std::vector<MediaDevice> DiscoverLocalMediaDevices();

}  // namespace dk_browser::network

#endif  // DK_BROWSER_NETWORK_SSDP_DISCOVERY_H_

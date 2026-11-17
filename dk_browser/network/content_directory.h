// Copyright 2026 DK Softworks.
// On-demand local UPnP device descriptions and ContentDirectory browsing.
#ifndef DK_BROWSER_NETWORK_CONTENT_DIRECTORY_H_
#define DK_BROWSER_NETWORK_CONTENT_DIRECTORY_H_

#include <cstdint>
#include <string>
#include <vector>

#include "dk_browser/network/ssdp_discovery.h"

namespace dk_browser::network {

// Keep each page small enough for the native Devices panel.
inline constexpr uint32_t kMediaLibraryPageSize = 20;
inline constexpr uint32_t kMaxMediaLibraryIndex = 1000000;

struct LibraryEntry {
  std::string id;
  std::string title;
  bool is_folder = false;
  // Empty unless the device advertised a compatible HTTP media resource on
  // its own private IPv4 address. No URL is opened until the user clicks Play.
  std::string resource_url;
  std::string media_type;
};

struct LibraryPage {
  std::string device_name;
  std::string address;
  std::string error;
  std::vector<LibraryEntry> entries;
  bool is_renderer = false;
  bool more_entries = false;
  uint32_t first_index = 0;
  uint32_t next_index = 0;
  uint32_t total_matches = 0;
  bool total_matches_known = false;
};

// Runs only on a blocking worker following a user click. The initial folder
// ID is "0". Does not access the Internet or expose the LAN to web pages.
// All URLs must remain on the exact private IPv4 host that sent the SSDP
// response; no redirects, external entities, cookies or credentials.
LibraryPage BrowseMediaFolder(const MediaDevice& device,
                              const std::string& object_id,
                              uint32_t starting_index);

}  // namespace dk_browser::network

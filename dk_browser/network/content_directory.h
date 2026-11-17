// Copyright 2026 DK Softworks.
// On-demand local UPnP device descriptions and ContentDirectory browsing.
#ifndef DK_BROWSER_NETWORK_CONTENT_DIRECTORY_H_
#define DK_BROWSER_NETWORK_CONTENT_DIRECTORY_H_

#include <string>
#include <vector>

#include "dk_browser/network/ssdp_discovery.h"

namespace dk_browser::network {

struct LibraryEntry {
  std::string id;
  std::string title;
  bool is_folder = false;
};

struct LibraryPage {
  std::string device_name;
  std::string address;
  std::string error;
  std::vector<LibraryEntry> entries;
  bool is_renderer = false;
  bool more_entries = false;
};

// Runs only on a blocking worker following a user click. The initial folder
// ID is "0". Does not access the Internet or expose the LAN to web pages.
// All URLs must remain on the exact private IPv4 host that sent the SSDP
// response; no redirects, external entities, cookies or credentials.
LibraryPage BrowseMediaFolder(const MediaDevice& device,
                              const std::string& object_id);

}  // namespace dk_browser::network

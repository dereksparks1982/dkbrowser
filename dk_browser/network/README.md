# DK NetNav built-in UPnP/DLNA

DK NetNav's native Linux **Devices / Устройства** toolbar action searches
the local network for MediaServers and MediaRenderers using SSDP M-SEARCH.
It is entirely browser-owned and needs no separate helper or installed server
on the browser side.

## Device browsing

Selecting a responding server requests its UPnP XML device description over
HTTP and identifies a supported ContentDirectory service. Its friendly name
appears above a browseable list of folders and media titles. The **Back /
Назад** button navigates toward the server list. Renderer devices are
identified but do not expose media folders. The native browser never grants
this functionality to visited websites.

The first ContentDirectory page returns up to 100 items; the panel displays
up to 30 entries and notes if more exist. Folder navigation works but
pagination, artwork, searching, media playback, remote control and protocol
extensions remain separate development tasks.

## Network boundaries

- Discovery is started only after an explicit Devices click.
- Media descriptions and SOAP browse requests are made only after selecting a
  device or folder. They run on Chromium blocking worker threads.
- A description URL must use unencrypted HTTP and a *literal local IPv4*
  address identical to the SSDP datagram sender. SOAP control URLs must
  resolve to that same IP and port.
- No HTTP redirects, automatic cookies or credentials, remote hostnames,
  external XML entities, DTDs, or cross-site page APIs.
- SSDP, XML and HTTP responses are size-bounded, requests have deadlines,
  and the content displayed in the native interface is treated as text.
- Device names, titles, and object IDs are never trusted as executable data.

This stage does not perform background discovery, start a listening service,
fetch media resources, or open ports for inbound traffic. No release has yet
been produced. Some devices require additional ContentDirectory protocol
versions, pagination or HTTP behaviors beyond this initial implementation.

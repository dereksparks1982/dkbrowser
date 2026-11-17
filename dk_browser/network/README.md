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

ContentDirectory now requests **20 items per page**. Both **Next / Следующая
страница** and **Previous / Предыдущая страница** move through a shared folder
using the device's reported `NumberReturned` and `TotalMatches`, with a
bounded fallback for servers that omit those counters. The panel shows a page
number and item range. Returning from a subfolder restores the parent's
previously visited page. Response counts, offsets, list sizes and folder
navigation depth are bounded.

## Direct playback

Shared audio and video entries with a compatible DLNA `http-get`
`protocolInfo` resource now display a **Play / Воспроизвести** action. The
native ContentDirectory reader selects a resource only when its HTTP URL
uses the literal private IPv4 address of the device discovered by SSDP.
A click opens that resource directly in a new DK NetNav tab using Chromium's
native media handling. Where supported, Chromium and the media server can
stream or request byte ranges instead of first saving the entire file.

Entries without a compatible resource remain visible as text, not dead Play
buttons. The browser does not run a proxy, add a background downloader, or
grant media access to ordinary websites. The stream uses the browser's
existing network stack, so subsequent HTTP redirects and cookies follow its
normal navigation policies rather than the stricter description-fetch rules.
Actual codec and container compatibility remains limited to what the browser
and server support.

Artwork, search, renderer control and wider protocol interoperability remain
separate development milestones.

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
- A user must explicitly select a shared media item before its HTTP stream
  URL is opened. Resources are restricted to the SSDP responder's private
  IPv4 address; ordinary browser navigation rules apply after the click.

This stage does not perform background discovery, start a listening service,
automatically fetch media resources, or open ports for inbound traffic. No release has yet
been produced. Some devices require additional ContentDirectory protocol
versions or HTTP behaviors beyond this initial implementation.

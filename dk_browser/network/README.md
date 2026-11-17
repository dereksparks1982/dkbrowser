# DK NetNav native UPnP/DLNA discovery (first milestone)

This source set implements **browser-owned, user-triggered** SSDP M-SEARCH on
Linux, without an externally installed helper, service, extension, or account.
It searches for UPnP MediaServer and MediaRenderer devices on the local IPv4
network, caps the scan at three seconds, and returns at most 32 unique devices.
The Chromium toolbar's **Devices / Устройства** button opens an English/Russian
list and starts discovery on a blocking worker thread.

Security boundaries: no passive background probing; no website API; no inbound
listener; no XML, SOAP or UPnP description fetch. UDP responses are bounded,
require private/link-local IPv4 senders and HTTP location URLs on the same
literal IP, and are displayed as text rather than markup. Discovery must remain
a direct user action. A device's claims are untrusted and its location is not
automatically fetched.

**Incomplete:** This milestone only discovers SSDP responders and displays
their type, network address and reported server identifier. Device-description
parsing, friendly names, ContentDirectory browsing, media streaming, renderer
control, additional network ranges/IPv6, and permission persistence/revocation
remain future milestones. The native browser is not compiled or tested yet.

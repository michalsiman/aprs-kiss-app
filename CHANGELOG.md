# Changelog

## 0.1.5 – 2026-11-17

- Own Flatpak repository with automatic updates:
  [michalsiman.github.io/aprs-kiss-app](https://michalsiman.github.io/aprs-kiss-app/). The `.flatpak`
  file from a release now also takes its updates from there.
- Right-click the map (long press on a touch screen): *Set as my position* or copy the coordinates,
  so you no longer need to type them in.
- Settings are more compact: smaller text and input boxes.

## 0.1.4 – 2026-11-17

- Tells you when a new version is out: once a day at most it asks GitHub for the latest release
  (nothing about you is sent). A button in the top bar opens the download page; a short notice is
  shown once per version. The About window shows the last check and can check now; Settings can
  switch it off.

## 0.1.3 – 2026-11-17

- Closing the window asks first and says what would stop (receiving, the beacon, the iGate,
  connected sessions); it can also just minimise the window.
- README links to the F4HWN firmware and its KISS TNC app.

## 0.1.2 – 2026-11-17

- Legend for the map and the station list: what the callsign colours mean (heard by the radio,
  internet only, tracked, you) and which symbols are shown, with their names.
- The whole APRS symbol set with names in English and Czech, including LoRa iGates and
  digipeaters; 📍 is left only for symbols that are not in the table.
- "Stations from the internet" on the map and in the station list (one shared, saved choice).
- The station list says "radio" / "internet" and the symbol's name; the station window shows the
  symbol's name and code.

## 0.1.1 – 2026-11-17

- Install with one click: a Flatpak and a `.deb` with every release, besides the tarball.
- App icon, desktop entry and AppStream metainfo (app id `io.github.michalsiman.aprs_kiss_app`).
- About window (ⓘ in the top bar, or Settings): what the app does, version, links to the source,
  issues, new versions, the F4HWN firmware and its KISS TNC app, the author.

## 0.1.0 – 2026-11-17

First standalone version, for Linux.

- The radio core of the Home Assistant integration 0.3.4 (KISS, AX.25, APRS, APRS-IS, iGate,
  sessions) without Home Assistant; `Engine` replaces the integration's hub and announces events
  to listeners.
- TNC transports are pluggable (TCP and serial built in), ready for Android USB and Bluetooth.
- Settings and message history saved as JSON in the user's data folder.
- Flet desktop app: map, messages, stations, terminal, chat, monitor, settings; English and Czech.
- Tests of the core and of the engine against the simulated TNC; CI and a Linux build workflow.
- Light and dark mode following the system; screenshots in the README.
- The simulated TNC has more stations and `--message-every` (0 = no messages).

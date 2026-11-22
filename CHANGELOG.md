# Changelog

## 0.1.14 – 2026-11-22

- **BBS SERVER guide** in English and Czech ([docs/BBS.md](docs/BBS.md), [docs/BBS.cs.md](docs/BBS.cs.md)):
  switching it on, the settings, where the files are, every option in bbs.toml, the placeholders in the
  texts, users.toml, the message files and the user commands, with screenshots. The BBS SERVER section
  has a *Guide* button that opens it.
- **README in Czech** ([README.cs.md](README.cs.md)) with Czech screenshots; both READMEs link to each other.
- New screenshots in English and Czech, light and dark, now with BBS SERVER.
- The BBS folder is shown with ~ for your home folder.

## 0.1.13 – 2026-11-22

- **BBS SERVER**: the app can run its own packet BBS on your callsign with its own SSID. Users get the
  classic W0RLI / MBL / FBB commands (L, LM, LB, R, RM, S, SP, SB, K, KM, N, NQ, NH, I, H, J, B), personal
  messages and bulletins. Everything lives in files in the BBS folder: bbs.toml (with comments),
  welcome.txt, help.txt, info.txt, users.toml, and one text file per message. The BBS SERVER section shows
  who is connected, the messages (read, delete) and a log.
- Switching BBS SERVER on takes a typed sentence ("BBS SERVER must have another frequency than APRS"),
  and while it runs everything else is off: APRS, APRS-IS, iGate, beacon, messages, APRS Thursday,
  terminal and chat. The monitor stays.
- Settings › BBS SERVER: SSID, clients at the same time, inactivity timeout (seconds), maximum TX time per
  connection, maximum stored messages and the welcome message (ASCII art welcome), written to the BBS files.
- Terminal: while connecting, the attempts are shown with their times ("attempt 3/9"), and the Disconnect
  button becomes *Stop connecting*, which stops the attempts at once.

## 0.1.12 – 2026-11-22

- **APRS Thursday**: a new section for the weekly #APRSThursday net. Shows whether the net is on
  (Thursday, UTC) or when the next one starts, and whether you are in the HOTG group. Check in with
  one button ("CQ HOTG …" to ANSRVR, by radio or over the internet, with the delivery state), read
  the group's messages in their own feed (they no longer fill your inbox), leave the group
  ("U HOTG"), open the map of check-ins on aprs.to. ANSRVR's one message per 30 minutes is shown.
- Terminal: a list of **saved BBSes and nodes** (callsign and digipeater path): save the station
  you typed, pick one from the list to fill in the fields, remove it again.
- New screenshots; README describes the new features and the Windows install.

## 0.1.11 – 2026-11-22

- Map: callsign labels have a thin dark frame, so they stand out on a colourful map.
- Map: a *Muted map* button fades the map tiles; the stations keep their colours. The choice is saved.

## 0.1.10 – 2026-11-22

- Polish: 16 languages in all.
- Chat shows only text meant for people: frames to CQ, QST, ALL or your own callsign. Automatic
  frames, such as a digipeater's "DX de …" report of the farthest station it heard or station IDs,
  stay in the monitor.

## 0.1.9 – 2026-11-22

- Third-party packets (`}`), which an iGate uses to put an internet station on the air, are now
  unpacked: the station inside shows on the map at its position, marked *iGate OK0XYZ* in the
  station list until your radio hears it directly.
- Messages for you that an iGate relays from the internet by radio are now received and
  acknowledged (the ack goes back by radio for the iGate to pass on). Before, they were dropped
  unless the app was also connected to APRS-IS.

## 0.1.8 – 2026-11-22

- Monitor: a *Stations from the internet* switch hides the APRS-IS lines (`[IS]`) and leaves only
  what the radio heard and sent. The choice is saved. The radio's frames are kept apart, so a busy
  APRS-IS feed no longer pushes them out of the monitor history.
- Windows: an installer and a zip are built with every release; serial ports are listed as
  "COM5 – USB-SERIAL CH340" instead of repeating the port.

## 0.1.7 – 2026-11-17

- 13 more languages, 15 in all: Brazilian Portuguese, Croatian, Czech, Danish, English, French, German, Italian, Norwegian (Bokmål), Serbian (Cyrillic), Slovak, Slovenian, Spanish, Swedish and Ukrainian. The app picks the system language,
  Settings › App › Language picks another. APRS symbol names stay in English outside Czech.
- The APRS-IS licence statement can be typed in any of these languages.

## 0.1.6 – 2026-11-17

- Settings › App › Appearance: as the system, light or dark.
- "As the system" now also sees a dark desktop that only says so through its theme (Linux Mint's
  dark themes and the like leave the light/dark preference unset), and follows changes within 30 s.

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

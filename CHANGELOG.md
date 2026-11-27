# Changelog

Stable versions are 1.0.0, 1.1.0, 1.2.0 …; between them come **betas** (1.0.1, 1.0.2 …, tagged
`vX.Y.Z-beta`, pre-releases on GitHub) for testers. The app tells about a new beta only when
*Also offer beta versions* is ticked in Settings; Flatpak and Linux Mint's update manager get stable ones only.

## Unreleased

- **Winlink e-mail over APRS (APRSLink, WLNK-1)** – in Messages › Services or a conversation with WLNK-1: *Log in*
  answers the gateway's challenge by itself (only three characters of your Winlink password go on air, with three
  random ones; the password is kept in Settings › Station), then buttons for the list, read, reply, forward,
  delete, a new e-mail (each further message a line, *Send e-mail* = /EX), a short one, play back and help. Lines
  to WLNK-1 are not numbered "1/3" (they would end up in the e-mail). Needs a Winlink account (Winlink Express, Pat).
- **Topographic map (OpenTopoMap)** as another online map in the map menu: contour lines and hill shading, to
  zoom 17 (also on the TAK map).
- **Stations in order**: last heard first, nearest first or by callsign – the sort button above the list,
  remembered.
- **"Road incidents" are now "Warnings"** (map filter, tracker alerts, sounds): besides crashes and road works
  they are fires, floods and fog too, and not only in Czechia – the same objects come from the US, Australia
  or Portugal.
- **Navigate here / Share this place** – in a station's details and in the map's long-press menu: on a phone
  the place opens in a navigation or map app (Android asks which: Google Maps, Mapy.com, Waze, OsmAnd…; an
  iPhone opens Apple Maps) or goes to another app through the share sheet (name, coordinates, locator, a map
  link); on a computer it opens on a web map, and sharing copies the text.

## 1.7.0 – 2026-11-27

- **Station details** say altitude, speed and course in your language and units (they said `speed: 89`).
- **Callbooks in the station's details**: besides QRZ.com also HamQTH and QRZCQ (the operator), and aprs.fi
  (this station's track and packets) – one *Callbooks* menu.
- **Web links in messages, APRS Thursday and the chat are clickable** – a tap first shows where the link leads and
  warns that nobody vouches for the page (it may be harmful); then *Open* or *Cancel*.
- **The menu in sections**: APRS (map, messages, APRS Thursday, stations), packet radio (terminal, chat, files,
  monitor, BBS, TAK), then the settings – headings on a phone, gaps on a computer.
- **Stations a message mentions** (e.g. OK6DJ-6 in a WXNOW answer): a small button at the message lists those
  heard with a position, with how far and which way; a tap shows one on the map.
- **A tap on "On the map: 18"**: how many points, how many different callsigns (and without the SSID), the
  nearest and the furthest one (a tap opens it). *Number of points on the map* in the map menu hides the line.
- **Map: the grey lines no longer cross** – where two would, the two markers swap places.
- **Map: the grey dot no longer sits inside another station's symbol.** Two stations a little apart (not at
  one place, e.g. OK1KUN-1 and OK1KUN-2) – one stayed, and the other one's dot (where it really is) fell on the
  first one's symbol. Now both move aside, as stations at one place do.
- **A tap on the temperature around you** lists the weather stations it is the average of – nearest first, each
  with its temperature, humidity and pressure, how far and in which direction, how old; a tap on one opens it.

## 1.6.0 – 2026-11-27

- **Kilometres or miles, °C or °F, hPa or inHg** – Settings › App; by default as the phone or computer is set
  (miles in the US and the UK, Fahrenheit and inches of mercury in the US). Distances everywhere, the map scale,
  the filter's how-far (10 / 30 / 60 mi), the APRS-IS radius, the look-ahead of road alerts, speeds, altitudes,
  temperatures and pressure follow it.
- **Temperature around you on the map** – top right corner: the average of the weather stations within 20 km
  (reports at most 2 hours old), humidity and pressure too when sent; every 5 minutes; under the map buttons
  while they are open; *Temperature around me* in the map menu switches it off.
- **Phone: IS and GPS lamps together exactly as wide as TNC below them.**

## 1.5.2 beta – 2026-11-27

- **Messages: All / Unread count conversations** – the lines of the list – not every message sent and received
  (it said 61 with 17 conversations on screen).

## 1.5.1 beta – 2026-11-27

- **Messages, APRS Thursday, Monitor, chat, terminal and BBS open straight on the last line** – no more slow
  scrolling down through the whole history.
- **The bars at the bottom** (sent, TNC not connected, new message, hazard on the road) have the same thin grey
  frame and shadow as the menus and dialogs.
- **"You seem to be driving"** comes at most once an hour (stops on the way do not bring it back sooner), and has a
  new **Not today** button. It also says where to switch the offer off for good (Settings › Tracker).
- **Map filter: how far.** Internet stations up to 20, 50 or 100 km – the APRS-IS server is asked for the new
  area at once (the same setting as in Settings › APRS-IS) – and radio stations up to 20, 50, 100 km or with
  no limit (the default).
- **"On the map: 17"** – a small line under the map buttons: how many stations are in the part of the map on
  screen; it follows the panning, zooming and filters.
- **What is new**: after an update to a new stable version, the first start shows the changes since the
  version used before (once; a Close button). Betas do not; the next stable version lists their changes too.
- **The handheld radio icon** wherever the radio is meant (map filter, VARA FM, the first-start warning, About).
- **About**: the thanks now say what for – support in amateur radio – and include the OK1RPL radio club.

## 1.5.0 – 2026-11-26

- **Phone: back on the same screen** after Android restarts the app's screen part in the background (it did
  that after a few minutes away; the app came back on the map).

## 1.4.0 – 2026-11-26

- **Radio frequency from the app** for radios with a built-in KISS TNC over Bluetooth (VGC VR-N76, BTECH
  UV-PRO, Radioddity GA-5WB, firmware 0.7.11+): *Settings › TNC connection*, *Tune* and *Its own* (KISS
  SetHardware). The power cannot be set this way.
- **QRZ.com** in a station's details (the base callsign, without SSID or /P).
- **The profile's symbol** next to the callsign in the top bar.
- **Menus stay open** after a choice (the map, Show all stations, the tracker's send and start/stop); back or a
  tap outside closes them.
- APRS Thursday back in the main menu.

## 1.3.0 – 2026-11-26

The betas 1.2.1–1.2.4 as a stable version:

- **Messages look and work better**: a coloured circle with a letter for each conversation and its count of
  unread messages; *All / Unread* filter with counts and a full-text search; *⋮ › Mark all as read*;
  unread messages stay unread after a restart or an update; the new-message form shows at once.
- **Radio and internet** as two remembered icons (a walkie-talkie and a globe) in Messages and APRS Thursday.
- **Notifications** say how many messages are unread in all.
- **APRS Thursday**: ANSRVR's relays ("N:HOTG …") go to its screen, not to Messages.
- **Menus**: boxes and round marks with an empty frame, ticking keeps the menu open, long texts in other
  languages wrap; dialogs framed like the menus.
- **Map**: the offline map is light in the dark mode too.
- **Stations** say why the list is empty; the TAK explanation is shown whole.
- **Reliability**: a log (*About › Copy log*) with a watchdog that records what blocks the app; on a phone,
  when Android restarts the screen part, the old session is stopped before the new one starts.

## 1.2.4 beta – 2026-11-26

- **Messages: All / Unread** filter, each with its count of messages in a circle, and a **search** field
  next to them: only conversations whose callsign or messages have the text (case and accents ignored),
  with the message found shown under the callsign.
- **APRS Thursday moved to Messages › Services** (first there), out of the menu; its radio/internet choice
  is the same two remembered icons as in Messages. (Back in the menu in 1.3.0.)
- **ANSRVR's relays ("N:HOTG …") go to APRS Thursday**, not to Messages as one conversation per station;
  the ones already in Messages are moved there.
- **Radio is a walkie-talkie icon** (our own drawing) in the radio/internet choice.
- **The offline map is light in the dark mode too**, like the OSM and imported maps.
- **Menus**: the map choice has round marks (an empty ring when not chosen); long texts in other languages
  (French, Slovenian, …) wrap instead of running out of the menu.

## 1.2.3 beta – 2026-11-26

- **Messages: radio and internet as two icons** (an antenna and a globe) instead of a drop-down: one or
  both on, remembered until changed; the last one on cannot be switched off.
- **The new-message form shows at once** after a tap on +, then the cursor goes to To (before, the screen
  changed only after the keyboard came up, so a tap looked missed).
- **On/off lines in menus are boxes** (map filters, Muted map, the tracker's alerts): an empty faint frame
  when off, and ticking one keeps the menu open; back or a tap outside closes it.
- **Dialogs and bottom sheets have the same thin grey frame** and shadow as the menus.
- **A log for finding faults**: the app writes a small log file (lifecycle, back, errors, and what blocks
  the app when it stops answering for 10 s); *About › Copy log* puts its end in the clipboard. The app's
  clock no longer stops after an error, and the screen is sent again when the app comes back on screen.

## 1.2.2 beta – 2026-11-26

- **Stations: why the list is empty** – "No station matches the filter", or "All 13 stations were heard only
  on the internet (APRS-IS); the globe button shows them" instead of "No stations heard yet". The count
  (shown / all heard) has a tooltip.
- **TAK switched off**: the whole explanation is shown, wrapped, not cut off.

## 1.2.1 beta – 2026-11-26

- **Messages look nicer**: each conversation has a coloured circle with a letter – the suffix's first
  (OK1TNT → T; the prefix is the same for a whole country), the first one for a service (REPEAT → R); the same
  letter always the same colour. An unread conversation shows how many messages are unread in a red count on
  the circle, its callsign and text in bold. On a computer the list is wider so callsigns don't break.
- **The total in a notification**: a message notification says how many messages are unread in all
  (Android in the notification's header, with the number on the app's icon where the launcher shows it).
  The count on Messages and ☰ is now messages, not conversations.
- **A ⋮ menu in Messages** with *Mark all as read*.
- **Unread stays unread** after a restart or an update (it was kept only in memory before).

## 1.2.0 – 2026-11-26

The betas 1.1.1–1.1.3 as a stable version:

- **Notifications of new messages and chat lines**: Android while the app is in the background (a tap opens
  the conversation), Linux, Windows and macOS while the window is not in front.
- **Messages**: back from an open conversation goes to the list first; a round + for a new message; unread
  conversations marked with a red dot and counted until read; the REPEAT service works; accented letters
  read right.
- **Profiles**: each with its own position comment and tracker way (fixed interval or SmartBeaconing).
- **Menus stand out** with a frame and a shadow; serial TNC errors said plainly.

## 1.1.3 beta – 2026-11-26

- **A notification for a new message or chat line** when you are not looking at the app: on Android while
  it is in the background (silent, the app beeps itself; a tap opens that conversation or the chat; Android
  13+ asks once for the permission), on a computer while its window is not in front – Linux (also the
  Flatpak, through the notification portal), Windows (a toast, shown under Windows PowerShell) and macOS.
  An incoming file is announced the same way. Not on iPhone: iOS stops the app in the background.
- **Back from a conversation on a phone**: the back gesture in an open conversation goes to the list of
  conversations first; only the next one goes to the previous screen.
- **Services › REPEAT works**: it wants `n 3 2m`, `n 3 70cm` (how many, which band), not "nearest", which it
  answered with "Unknown command!".
- **Messages: one line on top** – a round **+** for a new message, then Spot and Services.
- **Letters with accents read right**: UTF-8 heard over the radio is read as UTF-8 (it was Latin-1), and text
  broken on the way ("TURKÄ°YE") is put right ("TURKİYE").
- A reject or ack with a garbled message number (e.g. "rejÊ") is no longer shown as a message.

## 1.1.2 beta – 2026-11-25

- **Each profile has its own position comment** (Settings › Station, under its SSID and icon); switching the
  profile in the top bar switches the comment too. Profiles saved before start with the comment used so far.
- **Each profile has its own tracker way**: a fixed interval, or SmartBeaconing and how you move (on foot,
  by bike, by car) – a car profile can beacon smartly, a handheld one every few minutes. The interval when
  standing still stays one for all (Settings › Tracker).
- **"Active profile"** is written next to the number of the profile in use.
- **Menus stand out**: pop-up menus (map tools, filters, ⋮) and drop-down lists have a lighter background, a
  thin grey frame and a shadow, so they no longer blend with the bar or the map under them.

## 1.1.1 beta – 2026-11-25

- **Unread messages stay counted while Messages is open**: the red number in the menu (and on the
  selected Messages item) goes away only when the messages are read, not as soon as the screen opens.
- **A red dot on the envelope of an unread conversation** (on the left), besides the bold callsign.
- **A serial TNC that is not there is said plainly**: instead of "Could not configure port: (5, …)" the app
  says the port does not answer (probably not the radio's), is not there, is not allowed (the dialout group)
  or is not chosen – in the app's language, with what to do. The Linux ports ttyS0…ttyS31 with nothing
  behind them are no longer offered.

## 1.1.0 – 2026-11-24

The betas 1.0.1–1.0.3 as a stable version:

- **TNC over Bluetooth LE** (KISS over BLE) on every platform, iPhone included: a LoRa APRS tracker,
  Mobilinkd TNC4, PicoAPRS, B.B. Link and others, found by a scan in Settings › Connection.
- **Spotting an activation** (Messages › Spot): SOTA, POTA, WWFF, SIOTA, GMA, WCA castles, IOTA and
  lighthouses, by radio through APRS2SOTA, Camilla or APSPOT.
- **Services on APRS** (Messages › Services): FIND, REPEAT, WXNOW, UTC, satellite passes (9M2PJU-4) and
  e-mail (MAILMY), one tap each.
- **Android**: a radio plugged in opens the app; the map edge to edge; the notification's own icon; the
  Files screen fitted to a phone.

## 1.0.3 beta – 2026-11-24

- **TNC over Bluetooth LE** (KISS over BLE, the standard of aprs.fi, Mobilinkd and others): Settings ›
  Connection › *TNC over Bluetooth LE* finds the devices around (those offering KISS first) and connects to
  the one picked, with reconnecting as for the other connections. For the CA2RXU LoRa APRS Tracker (Bluetooth
  set to KISS), Mobilinkd TNC3/TNC4, PicoAPRS, B.B. Link, Vero VR-N76, BTECH UV-Pro and the like; on Android,
  iPhone (its only Bluetooth for a TNC), Linux, Windows and macOS. Made with universal_ble (a Flet extension of
  the app's own, packages/flet-ble-kiss).

## 1.0.2 beta – 2026-11-24

- **Services on APRS**: Messages › Services lists the services that answer a message – FIND (where a
  station was last heard), REPEAT (the nearest repeaters), WXNOW (the nearest weather), UTC (the time),
  9M2PJU-4 (satellite passes, sunrise and sunset) and MAILMY (e-mail from the radio). A tap on a command
  puts it in a new message to the service, ready to send; the answer comes in that conversation.
- **Android**: the map goes edge to edge (no frame around it); the "Running" notification has its own icon
  instead of a white square; the "Accept files" switch on Files wraps its label on a phone, and the "Open the folder"
  button (which cannot open the app's private folder on a phone) is gone: a received file has its own
  "save a copy" button.
- **Spotting an activation (SOTA, POTA, WWFF, SIOTA, GMA, WCA castles, IOTA, lighthouses)**: Messages ›
  Spot sends a self-spot by radio as an APRS message to a gateway – APRS2SOTA (SOTAwatch; the callsign is
  registered with its operator first), Camilla DL0QW-12 (GMA, and SOTAwatch for a SOTA summit; registered
  GMA users) or APSPOT (pota.app, SOTAwatch, ParksnPeaks; an account there). The reference is checked, kHz is turned
  into MHz, the comment is shortened to fit one message, a test spot can be sent; the dialog shows the
  message before it goes and the gateway's answer comes in its conversation. The last spot is remembered.

## 1.0.1 beta – 2026-11-24

- **Android: a radio plugged in opens the app.** When a TNC is plugged into the phone (the Quansheng with
  the F4HWN KISS TNC, other USB CDC TNCs, FTDI / CP210x / CH340 / PL2303 cables), Android offers
  "Open APRS & Packet to handle …"; with *always* ticked the app opens by itself and gets the USB access.

## 1.0.0 – 2026-11-24

- **The first stable version** – the same as 0.1.55, plus:
- **A radio plugged in is connected by itself**: a TNC on USB, Bluetooth or a serial port is looked for every
  3 seconds (it was up to a minute), and at once when the app comes back to the screen – no need to
  save the settings again.
- **Beta versions for testers**: Settings › App › *Also offer beta versions*. From now on new features come
  as betas first and now and then as a new stable version.

## 0.1.55 – 2026-11-24

- **Positions in the chat and in messages**:
  - send yours to the chat (a button by the text), or put it into a message being written;
  - on the map, a long press (right click) on any place: send that position to the chat or in a message,
    as coordinates ("QTH 49.74750, 13.37760") or as a locator ("LOC JN69QR");
  - the map's menu shows the place's Maidenhead locator (a tap copies it);
  - a position written in a message or a chat line gets a map button: the map shows it with a red pin and
    the sender's callsign. Understood are decimal degrees, degrees and minutes (or seconds) with N/E,
    APRS's own "4944.85N/01322.66E" and six-character locators.

## 0.1.54 – 2026-11-24

- **Files** (new section): send a file to another station over packet radio and receive files – YAPP, the
  packet radio standard (BPQ, WinPack, Paxon), over a connected AX.25 link that acknowledges and repeats
  frames. Before sending, an estimate of the time (in excellent conditions, longer through digipeaters);
  while it runs the progress, the speed, the bytes and time still to go; it can be cancelled. Receiving is
  switched on in the section, every file is offered first (a dialog on any screen, a notification in the
  background). An interrupted transfer goes on from where it stopped when the same file is sent again.
- **Messages**:
  - a longer text goes as several messages numbered 1/2, 2/2 … (up to five); the counter says how many;
  - the conversation shows the station's distance and direction now and a button to see it on the map;
    each received message keeps how far the sender was when it came;
  - a conversation can be deleted (⋮ in the list);
  - long messages wrap in their bubble; the radio / internet choice fits on a phone;
  - the "new message" bar goes away by itself (it stayed on Android) and as soon as its conversation is open.

## 0.1.53 – 2026-11-24

- **Phone: "You seem to be driving – switch the tracker on?"** When the app sees from the phone's GPS that
  you are on the move with the tracker off, it asks (in the background with a notification; a tap opens
  the app and asks). Once per trip; again only after standing still for a quarter of an hour or after two
  hours. Needs running in the background; can be switched off in Settings › Tracker. Not on computers.
- **Weather stations show their temperature** on the map, in the second line of their tag (like a
  repeater's frequency).
- New screenshots (`tools/screenshots.py` takes them all, `tests/fake_tnc.py --scene` plays a busy area).

## 0.1.52 – 2026-11-24

- **Phone top bar**: the text in the small TNC and IS lamps sits in the middle of its frame.

## 0.1.51 – 2026-11-24

- **Computer top bar** (Linux, Windows, macOS): the same lamps as on a phone – TNC, IS, GPS, the position /
  tracker button and TX – larger, side by side on the right; the callsign stays on the left. Hovering a
  lamp tells its state (TNC error, APRS-IS server, GPS satellites); a click on TX switches transmitting.
- **"Back to me"** (the map follows you while the tracker runs): the button with its countdown is now in
  the bottom left corner, above the scale.

## 0.1.50 – 2026-11-24

- **Phone top bar**: TNC, IS and GPS share one small block (IS and GPS above, TNC below), so the whole
  callsign with its SSID fits again (since 0.1.49 the SSID was cut off).
- **Map filter menu**: one line per filter, nothing cut off on a phone.
- **TNC errors in your language**: USB and Bluetooth TNC messages (no TNC plugged in, permission,
  Bluetooth off, not paired, …) are shown translated instead of in English.

## 0.1.49 – 2026-11-24

- **Station profiles**: one callsign, up to three SSIDs, each with its own symbol (Settings › Station).
  A tap on the callsign in the top bar picks one; from then on everything (position, tracker, messages,
  terminal, chat, APRS-IS) goes out under it.
- **Map**: the grey line to a moved station's real place now starts in the middle of its symbol's disc.

## 0.1.48 – 2026-11-24

- **Map filters** (funnel button): only weather stations, only moving stations (moved in the last 10
  minutes; a station just heard stays until it is clear it stands still), only repeaters, only road
  incidents (crash, emergency, work zone, flooding, fog, snow) – any mix; remembered.
- **Repeaters show their frequency** in their map tag, with the band (2 m green, 70 cm magenta) and the
  digital mode when the comment says it (DMR, D-Star, C4FM, NXDN, TETRA).
- **The map follows you while the tracker runs**, at zoom 13, like a navigation. Moved or zoomed by hand,
  a **"Back to me"** button counts down 15 s and the map then comes back by itself (or at once on a tap).
- **Warnings ahead while the tracker runs** (off until switched on in the position menu or Settings ›
  Tracker): road incidents, and other moving stations (going your way, coming towards you or crossing)
  in a lobe ahead of you – long and narrow when fast, wide in town, never behind; a bubble and a sound
  (each sound can be switched off).

## 0.1.47 – 2026-11-23

- **One switch for the internet** (Settings › APRS-IS): "Send over the internet too: my position (now,
  regular, tracker) and messages". It now also governs *Send my position now* (before, that always went
  to APRS-IS) and sets the default way for messages (radio and internet, or radio only; each message can
  still choose). Transmit (TX) stays the radio's switch: with TX off and this on, everything goes over the
  internet only – the app works with APRS-IS alone.
- **The IS lamp turns red for a second** when something goes out over APRS-IS, like TX on air.
- **Stations sharing one place** (a digipeater, an iGate and their objects on one mast): all of them now
  move off the place, which stays free for its grey dot; before, the first marker covered it and you could
  not tell where the group really is. The dots are drawn on top.

## 0.1.46 – 2026-11-23

- **Fix: the .flatpak file from the release could not be installed** ("GPG verification enabled, but no
  signatures found"): it carries our repository's key, so Flatpak wants a signed build, and the build was
  not signed. It is now signed with the repository key when it is built, and installs both on its own and
  over an installation from our repository.
- **Settings in a wide window**: an open block's fields are on the left, no longer centred.

## 0.1.45 – 2026-11-23

- **Fix: the map was not redrawn after zooming with the fingers**: the new zoom was asked for only once,
  just after the fingers lifted; a fling going on (or a question still pending) left the markers, the
  lines and the scale as they were (grey lines over half of Europe, "10 km" at continent size). While the
  map is on screen it is now asked every second where it looks, and redrawn when that changed.

## 0.1.44 – 2026-11-23

- **Your own trail**: with trails on, your station gets one too, from the GPS (the last half hour, in
  memory only).
- **Trails** red and a pixel thicker than the grey lines to moved markers.
- **Fix: long lines across the map**: APRS objects (repeaters, events…) are now places of their own under
  their names ("object of DB0YC" in the details); before, they moved the sending station between all its
  objects and the trail joined them across the country. A killed object goes away; a jump no vehicle can
  make starts a trail again.
- **Fix: stray lines and lost markers**: two moved stations at one place shared one dot, which confused the
  map (old lines stayed, markers – even your own – disappeared).
- Zoomed far out (a whole region on screen) the markers are no longer spread: it made a web of lines.

## 0.1.43 – 2026-11-23

- **Measure a distance on the map**: long press › *Measure distance from here* and tap the other point (or
  *Distance from my position*): a dashed line and the distance with the direction in degrees from north
  (handy for pointing an antenna). Another tap moves the far end, ✕ ends it.
- **Station symbols on a small light disc** with a soft shadow: they no longer melt into green forests or
  brown hills.
- **A grey dot** at the end of the line from a moved marker: where the station really is.

## 0.1.42 – 2026-11-23

- **Android back gesture**: closes the open menu, otherwise goes back to the screen shown before (Settings
  → Messages → Map …) and only from the first one leaves the app (to the background; receiving goes on).
- **Unsaved changes in Settings**: leaving them with something changed and not saved asks: Save or Discard.
- **Station labels**: always light tags with deeper colours and a soft shadow, also in the dark theme
  (the map itself is light); the same in TAK and in the legend.
- **Fix: markers jumped by kilometres when zooming**: overlapping markers now move only a little around
  their own place (a chain of nearby stations no longer becomes one big group); the line to the real
  place is clearer.

## 0.1.41 – 2026-11-23

- **Fix: APRS-IS went quiet after saving the settings** (e.g. a new SSID or symbol): the app logged in
  again without the area around your position, and the server sends nothing without one; only a restart
  helped. The GPS position now carries over and the area is always set by the first fix. The stations
  heard also stay on the map after saving.
- **Overlapping markers spread out**: stations at the same or nearly the same place (a digipeater and
  an iGate on one mast) are laid out in a small circle, each with a thin line to where it really is; your
  own station stays in place. Zooming in they return to their places.
- **Map menu**: long names (Online map / OpenStreetMap) on two lines, so they stay inside the menu.

## 0.1.40 – 2026-11-23

- **Tracker**: the position button in the top bar now opens a menu: send the position now, or start the
  tracker (▶) – the GPS position then goes out by itself, by radio while TX is on (and over the internet
  when chosen). Green ▶ while it sends, amber while it waits for the GPS or for TX; ⏸ stops it. Kept
  across restarts.
- **Settings › Tracker**: a fixed interval (1–30 min), or **smart (SmartBeaconing)** like the APRS and LoRa
  APRS trackers: standing still once in 10–60 min (60 by default), moving more often the faster you go,
  at once on a turn; profiles on foot, bike and car. Positions carry course and speed.
- **Fix: APRS-IS could not be switched on**: the field for the licence sentence never appeared, so the
  sentence could not be typed. The sentence is now also written out above the field (and can be copied).
- **Fix: "no internet" after the background**: phones that cut an app off the network for a while in the
  background (Xiaomi) made the map flip to the offline map and back. The app no longer checks while in
  the background or just after it returns, and goes offline only after three failed checks in a row.
- **Map bar fits on a phone**: the muted map and the legend moved into the map menu.

## 0.1.39 – 2026-11-23

- **Your own offline maps** (Settings › Offline maps): import a better map, e.g. a topographic one, from
  wherever you get it: raster tile maps in MBTiles, PMTiles (v3), SQLiteDB (OsmAnd, Locus), a ZIP of
  z/x/y tiles (osmdroid/MOBAC), or a ZIP/7z with such files inside (7z on a computer with 7-Zip).
  Several files at once; on a computer the map is used where it lies, on a phone it moves into the app.
  Vector maps (Mapsforge, vector MBTiles) are not supported and are refused with a reason.
- **Map menu**: the map button now chooses between the online map (OpenStreetMap), the imported map and
  the basic offline map, on the APRS map and on the TAK map; without internet the imported map is used
  when there is one. Where the imported map has no tiles the basic map shows under it; past its most
  detailed zoom its tiles are enlarged.
- **Station trails** (map, the line icon): where each moving station went in the last half hour, a red
  line like on aprs.fi; off by default, kept in memory only.
- **Foldable map toolbar**: the bar folds into a gear button and stays folded next time.
- **APRS Thursday**: one short line ("next one in …"), the rest behind an ⓘ button.
- **Messages**: the To field and the text each on their own full-width line, the character count by Send.
- The walking person is back for the `/[` symbol.

## 0.1.38 – 2026-11-23

- **APRS-IS with the phone's GPS**: the area the server sends stations from ("within 50 km of my position")
  now comes from the GPS, not only from a position typed in; with only the phone's GPS nothing came
  before. When you move by more than a tenth of the radius, the server gets the new area.
- **Phone top bar**: all lamps in the same frame and spacing, a satellite icon instead of "GPS", the
  "send my position" button framed too, and the TX lamp a little away from the edge.

## 0.1.37 – 2026-11-23

- **APRS digipeater** (Settings › Digipeater): fill-in (WIDE1-1, for a home station) or full (WIDEn-N
  with a hop limit, 2 by default), frames addressed to your callsign or aliases (e.g. RELAY) too; the
  same packet only once in 30 seconds, never your own; only while transmitting is on.
- **Android: a TNC over Bluetooth** (Settings › Connection › TNC over Bluetooth): a paired TNC or radio
  with the serial port profile (SPP), e.g. Mobilinkd TNC3 or a handheld with a Bluetooth KISS TNC.
  Android asks once for "Nearby devices". Bluetooth Low Energy-only TNCs are not supported.
- README: verified also with the VGC VR-N76 and AnyTone UV890 handhelds.

## 0.1.36 – 2026-11-23

- **Offline map with roads and more places** (Europe): motorways (from the whole country's view) and main
  roads (closer up) from Natural Earth; places of 1,000 people and more (one level smaller than before,
  shown close up) and each country's 30 highest peaks (before 15). About 0.9 MB more in the packages.
- SSID 0 is labelled "no SSID" too (on air it is the same).
- README with new screenshots from the computer and the phone, and all the features described again;
  macOS and iOS are built but untested: testers wanted.

## 0.1.35 – 2026-11-23

- **Android: keeps running in the background** (Settings › Background and screen): receiving, beacons,
  messages and TAK go on when the app is not on screen or the phone is locked, with a notification
  ("Running: receiving and transmitting go on") and a wake lock. Needs the location permission (Android
  allows this kind of service only so). Uses more battery; off by default.
- **Keep the screen on**: never, while TAK runs, or always while the app is open; on phones and computers.

## 0.1.34 – 2026-11-23

- **The callsign is required**: until one is saved, its field in Settings is framed red and has the
  cursor, and the app stays in Settings (another screen brings you back to the field with a message).
- **Offline map with more detail** (Europe): some 17,000 towns of 5,000 people and more and each
  country's highest peaks (▲ with the height), from GeoNames (CC BY 4.0); more appear as you zoom in.
  Names are drawn only around what is on screen, so phones stay quick. About 275 kB more in the packages.
- **A scale bar** in the lower left corner of the maps ("5 km", "200 m").
- **The map turns less easily**: two fingers either zoom or turn it, and turning needs a clear twist
  (60° instead of 20°).
- **TX lamp**: a red frame and red text while transmitting is on, all red only while a frame goes out
  on air (estimated from its length at 1200 Bd).
- Settings: the first field's label in each block is no longer cut off; shorter GPS choices on phones.
- Android backs up the app's settings again (switched off in 0.1.33 for a clean first-start test).

## 0.1.33 – 2026-11-23

- **Confirmation sentences only once**: the sentences typed to switch on TAK, BBS SERVER and APRS-IS
  (the licence) are asked for the first time only; afterwards, and after updates, switching on just works.
- **Phone GPS by default**: on a phone with no position typed in, the app uses the phone's GPS.
- **Settings show the GPS position**: with the phone's (or a USB) GPS chosen, the latitude and longitude
  fields are greyed out and the position from the GPS (with its accuracy) is shown under them.
- **Android keeps no backup of the app's settings**: an uninstall really starts afresh (a restored old
  settings file had skipped the language question and the licence warning).
- **TAK on a phone**: who you are, the team and the number of stations are on their own line, whole.
- **Handheld radio** in the APRS symbols: "/[" is the person / handheld (HT) symbol, now shown as 📻.

## 0.1.32 – 2026-11-23

- **The phone's language is recognised**: the app asks the device for its languages (Android and iOS do
  not tell them the way computers do), so a phone set to Czech starts in Czech.
- **The very first start asks for the language**: the one the device uses is offered ("System"), any other
  can be picked; then the licence warning comes in that language. Asked once.
- **Settings are folded up in blocks** (TNC, Station, GPS, APRS-IS, VARA FM, TAK, Sounds, App); a tap on
  a block opens it. The first time, the blocks that must be filled in are open.
- **Sounds**: a short beep when the radio transmits, and sounds for a new APRS message, packet chat line
  and TAK GeoChat message; each can be switched on or off in Settings › Sounds, with a button to hear
  them. On phones and computers.
- The map no longer logs errors every few seconds after the browser of the web version went away.

## 0.1.31 – 2026-11-23

- **TAK takes less room**: while TAK runs, its header is one slim line – who you are, the team and the
  number of stations, a warning icon when transmitting is off, "send my position" and a small switch.
- **TAK on a phone: the map and GeoChat are two screens**, switched by two icons in that line. On the map
  a number on the GeoChat icon and a short message tell about new messages.
- **The team's moves in GeoChat**: who appeared on the map and who moved how far (at least 200 m, at
  most every 2 minutes per station), between the messages.
- TAK frames are at most 220 bytes, so they also fit LoRa KISS modems (MeshCore's "KISS Radio Modem").

## 0.1.30 – 2026-11-23

- **Phone top bar as a dashboard**: TNC, IS, GPS and TX are small lamps – green when working, grey when
  not, TX red while transmitting is on; a tap on TX switches transmitting, a tap on TNC or GPS tells
  their state. A long callsign is shortened instead of pushing the switch off the screen.
- **The same on/off icons on every screen**: Monitor (stations from the internet, pause, clear) and
  Stations now use the lit / crossed-out icons of the map.
- **Terminal**: just the list of saved BBSes and the connect / disconnect icons; "New station…" in the
  list opens the fields for a callsign and path (and saving it).
- **TAK on a phone**: while typing a GeoChat message the map and the station list step aside, so the
  keyboard does not cover the text.
- The Android .apk is now signed with the project's permanent key (uninstall the old app once; from
  now on new versions install over it), and the release has the .aab for Google Play.

## 0.1.29 – 2026-11-23

- **A warning at the first start**, to be accepted before the app can be used: the app makes a radio
  transmit, transmitting needs an amateur radio licence, wrong use can interfere with other services
  (also emergency ones) and put people at risk, you are responsible for what you transmit. Shown once.
  The checks inside the app (the Transmit switch, the licence sentence for APRS-IS…) stay as they were.
- **Ready for Google Play** (not published yet): each release also has a signed `.aab` for Google Play
  (once the signing key is in the GitHub secrets), without the app's own update check, which Google
  Play does not allow; growing build numbers, Android 16 as the target, a privacy policy page and the
  store texts and pictures in `packaging/play`.
- Serbian texts added in the last versions are in Cyrillic like the rest.

## 0.1.28 – 2026-11-23

- **New versions on phones too**: the check once a day now works on Android and iOS (it could not
  verify GitHub's HTTPS certificate there). On Android "Download" fetches the new .apk straight away;
  open it to install. A small icon in the top bar shows a new version.
- **Phone: About is in the ☰ menu** (with "New version …" when there is one, and "Check now" inside),
  so the top bar has room.

## 0.1.27 – 2026-11-23

- **Map: zoom buttons and a compass** in the lower right corner, small so they take little of the map
  (on the APRS and the TAK map, on phones and computers). The compass needle shows where north is when
  the map has been turned; a tap turns it north up again.
- **Android: the app icon is blue to the edges**, with no white margin around it; the launcher shapes
  it (circle, rounded square…) like the other icons.

## 0.1.25 – 2026-11-23

- **Phone: the screens are in a menu again**, sliding in from the left with the ☰ button in the top bar
  and hiding when a screen is picked, so the whole screen below the top bar is for the content. Unread
  messages show on the ☰ button.

## 0.1.24 – 2026-11-23

- **A much faster map, above all on phones**:
  - the offline map sends only the area around what is on screen (at least ~300 km each way), thinned
    out to what the zoom can show, instead of the whole world (hundreds to a few thousand points
    instead of ~50,000); it is refilled when the map is moved far or zoomed;
  - only the stations in that area are drawn (at most 150 on a phone), and a station that did not
    change keeps its marker, so nothing is sent again for it;
  - the map no longer reports every frame of a pan or zoom to the app; where it looks is asked for
    after a gesture;
  - switching to another screen and back no longer throws the map away and builds it again.

## 0.1.23 – 2026-11-23

- **The phone's own GPS** (Settings › GPS: The phone's GPS): the map and the beacon use the phone's
  location; Android asks for the permission once. A tap on "GPS" in the top bar tells its state.
- **Map**: the "Stations from the internet" and "Last 2 hours" filters are icons next to the map buttons
  (lit when on), so the bar takes one line; the OpenStreetMap credit is a small line in the corner.
- **Switching between the offline and the online map is immediate**: the offline map is sent to the
  screen once and then only shown or hidden.
- **"Centre on my position" with no position** now says how to set one instead of doing nothing.

## 0.1.22 – 2026-11-23

- **Android: a TNC on the phone's USB port** (Settings › Connection: TNC on USB, through an OTG cable):
  CDC-ACM devices such as the Quansheng with the F4HWN KISS firmware, CP210x and FTDI cables. Android
  asks to allow the app to use the device.
- **Phone layout fixed**: smaller type and denser fields (fit also with a large system font), dialogs and
  fields no wider than the screen, long checkbox and field labels wrap instead of running off the screen,
  the APRS Thursday, Stations and map bars fit. A tap on "TNC" in the top bar tells its state or error.
- **Callsigns are always capitals**, whatever the phone keyboard types.

## 0.1.21 – 2026-11-23

- **Phone: the screens are in a bar along the bottom** instead of a side menu that covered half of the
  screen. The bar scrolls sideways when the screens do not fit, and the open one stays in sight.

## 0.1.20 – 2026-11-23

- **New platforms**: every release now also has
  - **Android** (`…-android.apk`), tried in the Android 17 emulator: connects to the TNC over the network
    (KISS over TCP);
  - **macOS** (`…-macos.dmg` and `.zip`, not signed by Apple: the first time right-click › Open);
  - **iOS** as an unsigned `.ipa` for sideloading (AltStore, Sideloadly).
  The macOS and iOS builds are made on GitHub and not tried on Apple hardware yet.
- **Phone layout**: on a narrow screen a menu replaces the side bar, the top bar is slimmer, Messages show the
  list or one conversation with a back button, TAK puts its map above the stations and GeoChat, and the map and
  monitor toolbars fit. BBS SERVER, the serial port and USB GPS are left out on phones.
- **Switching TAK or BBS SERVER on and off is fast again**: the screens are now built the first time they are
  opened instead of all at once (this also makes the app start faster).
- Back to the desktop layout when a narrow window is made wide again.

## 0.1.19 – 2026-11-22

- Fix: outside TAK mode, TAK frames heard on the radio (binary, to `TAK`) were read as APRS and could
  add a bogus station to the map and the station list. They are now left to TAK mode (the monitor still
  shows them decoded).
- The VARA FM hint in Settings names the terminal's *Connection* choice.
- The simulated TNC can send TAK stations and GeoChat (`tests/fake_tnc.py --tak`).
- README: all features described, new screenshots (offline map, terminal over VARA FM, TAK, more settings).

## 0.1.18 – 2026-11-22

- **Terminal over VARA FM**: with VARA FM's address set in Settings › VARA FM, the terminal offers
  *Connection: Packet (AX.25) / VARA FM*. Over VARA it connects to BBSes and nodes that take VARA FM
  (BPQ, RMS gateways…), through VARA's TCP interface (command port 8300, data 8301 by default), with
  digipeaters if given. The state line shows VARA's progress, PTT and the transmit buffer; *Stop
  connecting* aborts a connect at once. VARA runs on its own (Windows, or Wine on Linux) with the radio
  on a sound card, e.g. an AIOC cable. A pretend VARA for trying it without a radio: `tests/fake_vara.py`.
- Tests: the offline map test also runs where Flet is not installed.

## 0.1.17 – 2026-11-22

- **Offline map** bundled with the app: country borders, coastlines and about 1,000 bigger cities
  (Natural Earth, public domain), for the APRS map and for TAK. More and smaller cities appear as you
  zoom in. A button on the map switches to it; **with no internet the map switches to it by itself**
  and says so, and back to OpenStreetMap when the internet returns.
- The map can no longer be zoomed out so far that the world repeats.

## 0.1.16 – 2026-11-22

- **USB GPS module** as the source of your position (Settings › GPS): NMEA from u-blox, VK-172 and
  similar modules, the speed found automatically, reconnecting when unplugged. With a fix the map,
  the station list, the beacon (with the APRS altitude extension) and TAK use the GPS position; without
  one, the position typed in Settings. The top bar shows the GPS state; the map centres on the first fix.
- **TAK**: a new section that turns the app into a TAK station over the radio – positions (PLI) and
  GeoChat in TAK Protocol v1 (protobuf) in AX.25 UI frames, compatible with ATAK, WinTAK and iTAK.
  The TAK stations on the map, coloured by team and faded when stale; a station list; GeoChat to
  everybody or to one station; your position every N minutes and with a button. Callsign, team, role
  and interval in Settings › TAK. Switching it on takes a typed sentence ("TAK must have another
  frequency than APRS") and, like BBS SERVER, turns everything else off. The monitor shows TAK frames
  decoded. [Specification](docs/TAK.md).

## 0.1.15 – 2026-11-22

- Chat: a message that starts with a character APRS uses (`?`, `:`, `>`, `!`, `@`…, e.g. a smiley
  `:-)`) gets a leading space on the air, so other stations no longer take it for APRS and drop it.
- Chat: a message longer than 256 bytes is sent as several frames, split between words, instead of
  one frame some TNCs would drop.
- [Packet chat specification](docs/CHAT.md) (also [in Czech](docs/CHAT.cs.md)), for using the chat
  from other software.

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

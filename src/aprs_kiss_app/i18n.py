"""User interface texts. English and Czech here; other languages in lang/<code>.py
(TEXTS, SSIDS, NAME), each falling back to English for anything missing."""

from __future__ import annotations

import importlib
import locale
import os

TEXTS: dict[str, dict[str, str]] = {
    "en": {
        "app_title": "APRS & Packet",
        "map": "Map", "messages": "Messages", "stations": "Stations", "terminal": "Terminal",
        "chat": "Chat", "monitor": "Monitor", "settings": "Settings",
        "tnc": "TNC", "connected": "connected", "disconnected": "not connected",
        "transmit": "Transmit", "tx_on": "Transmitting is ON", "tx_off": "Transmitting is off (receive only)",
        "tx_refused": "Not sent: transmitting is switched off",
        "not_sent": "Not sent", "send": "Send", "to": "To", "text": "Text", "via": "Via",
        "via_radio": "Radio", "via_internet": "Internet", "via_both": "Radio + internet",
        "new_message": "New message", "message_from": "Message from {call}",
        "state_pending": "waiting for ack", "state_acked": "delivered", "state_rejected": "rejected",
        "state_failed": "not delivered",
        "no_messages": "No messages yet.", "pick_conversation": "Pick a conversation or start a new one.",
        "no_stations": "No stations heard yet.", "filter": "Filter", "last_heard": "heard", "ago": "{t} ago",
        "show_on_map": "Show on map", "send_message": "Send a message", "close": "Close",
        "my_position": "My position", "centre_me": "Centre on my position",
        "remote": "Station", "path": "Via digipeaters", "connect": "Connect",
        "disconnect": "Disconnect", "session": "Session", "type_here": "Type and press Enter",
        "not_connected_session": "Not connected to any station.",
        "chat_hint": "Packet chat: plain text to CQ, heard by everyone on the frequency.",
        "monitor_hint": "Every frame received and sent, TNC style.", "clear": "Clear",
        "pause": "Pause", "resume": "Resume",
        "beacon_now": "Send position now", "position_sent": "Position sent",
        # settings
        "tnc_section": "TNC connection", "connection": "Connection", "conn_tcp": "KISS over TCP (network)",
        "conn_serial": "Serial port (USB)", "conn_usb": "TNC on USB (OTG cable)", "host": "Host", "port": "Port", "device": "Serial port",
        "th_starts_in": "Next one in {t}",
        "map_trails": "Trails (where stations went in the last half hour)",
        "map_tools_hide": "Hide the map buttons", "map_tools_show": "Map buttons",
        "filter": "Filter stations", "filter_on": "Shown only: {what}", "filter_all": "Show all stations", "filter_weather": "Weather stations only", "filter_moving": "Moving only (moved in the last 10 min)", "filter_road": "Road incidents only (crashes, work zones, floods…)", "filter_weather_short": "weather", "filter_moving_short": "moving", "filter_road_short": "road incidents",
        "filter_repeater": "Repeaters only (with their frequency)", "filter_repeater_short": "repeaters",
        "map_following": "Following my position (tracker); tap to come back at once after moving the map",
        "follow_back": "Back to me · {s} s", "follow_back_tip": "Back to my position now (it goes back by itself when the time is up)",
        "road_alerts": "Warn about road incidents ahead (while the tracker runs)", "road_alert_km": "Look ahead", "road_alerts_hint": "Crashes, work zones and other traffic reports on the map in a lobe ahead of you: the chosen distance straight ahead, less to the sides, never behind. Slowly (in town) the lobe is wide, fast (main roads) long and narrow. A bubble and a sound, once for each.", "road_ahead": "Road incident {d} ahead", "road_left": "to the left", "road_right": "to the right", "road_more": "and {n} more ahead", "road_show": "Show", "sound_road": "Road incident ahead (tracker)",
        "about_thanks": "Thanks to the OK1OMG radio club and to Martin OK1MDX for their help and support.",
        "update_beta": "Also offer beta versions (for testers: newer, less tried)",
        "locator_is": "Locator {loc} (copy)", "loc_to_chat": "Send the locator {loc} to the chat", "loc_to_message": "Send the locator {loc} in a message…",
        "pos_to_chat": "Send this position to the chat", "pos_to_message": "Send this position in a message…", "pos_send_mine": "Send my position to the chat", "pos_insert_mine": "Put my position into the message", "pos_on_map": "Show on the map", "pos_sent_chat": "The position went to the chat",
        "files_pick": "Pick a file…", "files_send_now": "Send now", "files_estimate": "In excellent conditions about {t} (1200 Bd)", "files_estimate_hops": "digipeaters on the way: {n} (each repeats every frame)", "files": "Files", "files_to": "To station", "files_via": "Via digipeaters", "files_accept": "Accept files from other stations (I am asked about each)", "files_about": "Send a file to another station over packet radio: a connected AX.25 link, YAPP like BPQ, WinPack or Paxon. At 1200 Bd about 60–100 bytes a second: small pictures and texts. An interrupted transfer goes on from where it stopped when sent again.", "files_send": "Send a file…", "files_folder": "Open the folder", "files_tx_needed": "Switch Transmit on, otherwise nothing can be sent or acknowledged.", "files_folder_is": "Received files go to {path}", "files_none": "No transfers yet.", "files_left": "{left} to go, about {t}", "files_took": "took {t}, {speed} B/s", "files_state_connecting": "connecting…", "files_state_waiting": "waiting for the other side…", "files_state_offered": "waiting for an answer", "files_state_sending": "sending", "files_state_receiving": "receiving", "files_state_done": "done", "files_state_refused": "refused", "files_state_cancelled": "cancelled", "files_state_failed": "interrupted", "files_cancel": "Cancel", "files_accept_one": "Accept", "files_refuse": "Refuse", "files_save": "Save a copy…", "files_to_needed": "Type the station's callsign first.", "files_offer_title": "A file is coming", "files_offer_text": "{call} wants to send you {name} ({size}). Accept it?",
        "spot_button": "Spot", "spot_title": "Self-spot an activation (SOTA, POTA, WWFF, GMA…)", "spot_program": "Program", "spot_gateway": "Gateway", "spot_ref": "Reference", "spot_freq": "Frequency (MHz)", "spot_mode": "Mode", "spot_comment": "Comment (optional)", "spot_test": "Test only", "spot_hint_aprs2sota": "APRS2SOTA posts the spot on SOTAwatch. Register your callsign with its operator first (sotaspots.co.uk). The answer (Spotted / Error) comes as a message in its conversation. A test spot is posted marked as TEST.", "spot_hint_apspot": "APSPOT posts the spot on pota.app, SOTAwatch or ParksnPeaks; you need an account there. The answer comes as a message in its conversation. A test spot is only answered, not posted.", "spot_send": "Send spot", "spot_bad_ref": "The reference does not look right, e.g. {example}", "spot_bad_freq": "Frequency in MHz, e.g. 7.032 or 145.500", "spot_bad_program": "Pick a program",
        "spot_lighthouse": "Lighthouse", "spot_hint_camilla": "Camilla (DL0QW-12, gma.rocks) posts the spot on GMA, and a SOTA summit on SOTAwatch too: summits, castles (WCA), WWFF, islands (IOTA), lighthouses. For registered GMA users only (free at gma.rocks). It answers with a message in its conversation. A test spot is posted marked as TEST.",
        "services_button": "Services", "services_title": "Services on APRS", "services_hint": "Each one answers a message: pick a command, it goes to the message field, send it. The answer comes back in that conversation.", "svc_type": "Type…", "svc_find": "Where a station was last heard: send its callsign. Answers the time, the iGate, the distance and the locator.", "svc_repeat": "Repeaters nearest to your last position beacon.", "svc_wxnow": "Weather from the weather station nearest to you.", "svc_utc": "The exact time (UTC).", "svc_sat": "Satellite passes over you (satpass iss, satpass so-50), sunrise and sunset, where you are.", "svc_mail": "E-mail from the radio: EMAIL address text, as many messages as needed, then SEND. 5 an hour.",
        "msg_parts": "{n} messages · {chars} chars",
        "conv_delete": "Delete the conversation", "conv_delete_title": "Delete the conversation with {call}?", "conv_delete_ask": "All messages with this station are removed from the app. Messages already sent cannot be taken back.", "more": "More",
        "msg_where": "{d} {dir} · position {age}", "msg_distance_then": "How far the sender was when the message came",
        "offer_tracker": "Offer the tracker when I seem to be driving (needs running in the background)", "drive_title": "You seem to be driving", "drive_text": "Switch the tracker on? Tap to open APRS & Packet.", "drive_ask": "You seem to be on the move and the tracker is off. Switch it on, so your position goes out by itself?", "drive_yes": "Switch on", "drive_no": "Not now", "drive_channel": "Tracker offer",
        "trk_menu_road": "Warn: road incidents ahead", "trk_menu_meet": "Warn: moving stations ahead",
        "profile_pick": "Switch profile (SSID and symbol)", "profile_title": "Station profile", "profile_edit": "Edit profiles", "profile_add_hint": "You can add more profiles (up to three) in Settings › Station.", "profile_now": "From now on everything goes out as {call}", "profile_unused": "— not used", "profile_active": "Active profile", "profiles_hint": "Profiles: up to three SSIDs, each with its own symbol. Tap your callsign in the top bar to switch; from then on everything (position, messages, terminal, chat) goes out under the chosen one.", "profile_dup": "Each profile needs its own SSID.",
        "err_usb_none": "No USB TNC plugged in (an OTG adapter may be needed)", "err_usb_open": "Could not open {dev}", "err_usb_busy": "{dev} is in use", "err_usb_perm": "Not allowed to use {dev}: allow it when Android asks", "err_usb_write": "Writing to the USB TNC failed", "err_bt_none": "This phone has no Bluetooth", "err_bt_perm": "Not allowed to use Bluetooth: allow \"Nearby devices\" for the app", "err_bt_off": "Bluetooth is off: switch it on", "err_bt_nopaired": "No paired Bluetooth device: pair the TNC in Android's Bluetooth settings first", "err_bt_unpaired": "The Bluetooth device {dev} is not paired", "err_bt_connect": "Could not connect to {dev}: {why}", "err_not_connected": "The TNC is not connected",
        "meet_alerts": "Warn about other moving stations ahead (you catch one up, or it comes towards you)", "meet_ahead": "Moving station {d} ahead", "meet_same": "Moving station {d} ahead, going your way", "meet_towards": "Moving station {d} ahead, coming towards you", "meet_across": "Moving station {d} ahead, crossing your way", "sound_meet": "Moving station ahead (tracker)",
        "object_of": "object of {call}",
        "measure_from": "Measure distance from here",
        "measure_from_me": "Distance from my position",
        "measure_hint": "Tap the other point on the map",
        "measure_close": "End measuring",
        "unsaved_title": "Unsaved changes",
        "unsaved_text": "You changed something in Settings and did not save it.",
        "unsaved_discard": "Discard",
        "trk_section": "Tracker",
        "trk_mode": "When to send the position",
        "trk_fixed": "Fixed interval",
        "trk_smart": "Smart (SmartBeaconing)",
        "trk_minutes": "Every",
        "trk_profile": "I travel",
        "trk_walk": "On foot",
        "trk_bike": "By bike",
        "trk_car": "By car",
        "trk_still": "Standing still, once in",
        "trk_hint_fixed": "Started from the position button in the top bar (▶︎). While it runs, the GPS position goes out by itself at this interval – by radio while TX is on, over the internet when that is chosen in Station.",
        "trk_hint_smart": "Like the APRS and LoRa APRS trackers: standing still, once in the time set here; moving, more often the faster you go (down to about once a minute), and at once on a turn, so your track follows the road. Started from the position button in the top bar (▶︎).",
        "pos_send_now": "Send my position now",
        "trk_start": "Start the tracker",
        "trk_stop": "Pause the tracker",
        "trk_settings": "Tracker settings…",
        "trk_off": "The tracker is off",
        "trk_running": "Tracker running – next position in {t}",
        "trk_wait_gps": "The tracker waits for a GPS position",
        "trk_wait_tx": "Transmitting (TX) is off: the position is not sent by radio",
        "trk_no_gps": "The tracker needs a GPS: choose the position source in Settings › GPS",
        "trk_bg_hint": "To keep the tracker going with the screen off, switch on running in the background in Settings.",
        "trk_started": "Tracker started.",
        "trk_stopped": "Tracker paused.",
        "map_source": "Map",
        "map_src_online": "Online map (OpenStreetMap)",
        "map_src_imported": "Imported map",
        "map_src_basic": "Basic offline map",
        "map_src_none": "Imported map (none yet)",
        "map_src_manage": "Manage maps…",
        "maps_section": "Offline maps",
        "maps_hint": "Import a better map for use without internet, e.g. a topographic one, from wherever you get it. Raster tile maps: MBTiles, PMTiles, SQLiteDB (OsmAnd, Locus), a ZIP of z/x/y tiles, or a ZIP/7z with such files inside (7z on a computer with 7-Zip). Vector maps (Mapsforge, vector MBTiles) are not supported. Choose the map with the map button; where the imported map has no tiles the basic map shows.",
        "maps_import": "Import map…",
        "maps_importing": "Importing…",
        "maps_none": "No imported map.",
        "maps_broken": "cannot be opened",
        "maps_remove": "Remove",
        "maps_added": "Map imported: choose it with the map button on the map.",
        "maps_web": "In the browser maps cannot be imported.",
        "map_err_vector": "vector tiles are not supported, only pictures (PNG, JPEG, WebP)",
        "map_err_unknown": "not a supported map file",
        "map_err_empty": "there are no tiles in it",
        "map_err_no7z": "7z needs 7-Zip on this computer (or unpack it first)",
        "map_err_read": "the file cannot be read",
        "bt_device": "Bluetooth device",
        "digi": "Digipeater", "digi_mode": "APRS digipeater", "digi_off": "Off", "digi_fillin": "Fill-in (WIDE1-1) – a home station", "digi_wide": "Full (WIDEn-N) – a site digipeater", "digi_hops": "Hops at most (WIDEn-N)", "digi_aliases": "Also repeat for (aliases, e.g. RELAY)", "digi_hint": "Repeats APRS packets for stations around you, only while Transmit is on. Fill-in helps handhelds and cars reach the nearest big digipeater and is what a home station should run. A full digipeater only in agreement with the local APRS network. Frames addressed to your callsign are repeated too; the same packet only once in 30 seconds.",
        "conn_bt": "TNC over Bluetooth (paired)", "bt_none": "No paired Bluetooth device: pair the TNC in Android's Bluetooth settings, then tap refresh.",
        "conn_ble": "TNC over Bluetooth LE", "ble_device": "Bluetooth LE device", "ble_scanning": "Looking for Bluetooth LE devices…", "ble_none": "No Bluetooth LE device found: switch the TNC's Bluetooth on (KISS), keep it close and tap refresh.",
        "bg_section": "Background and screen", "run_background": "Keep running in the background (Android)", "bg_hint": "Receiving, beacons, messages and TAK go on when the app is not on screen or the phone is locked. Android shows a notification while it runs and needs the location permission for it. Uses more battery.", "keep_screen": "Keep the screen on", "keep_never": "No", "keep_tak": "While TAK runs", "keep_always": "Always (while the app is open)", "bg_notification": "Running: receiving and transmitting go on", "bg_channel": "Running in the background",
        "call_required": "Fill in your callsign and save: without it the app cannot work.",
        "lang_title": "Language", "lang_detected": "Your device uses: {name}. Keep following the device, or pick a language:", "lang_later": "It can be changed later in Settings › App.", "sounds": "Sounds", "sound_test": "Play them", "sound_tx": "Beep when the radio transmits", "sound_messages": "Sound for a new APRS message", "sound_chat": "Sound for a new packet chat message", "sound_tak": "Sound for a new TAK GeoChat message",
        "tak_appeared": "{call} appeared on the map", "tak_moved": "{call} moved {far}",
        "term_new": "New station…",
        "disc_title": "Before you start: this app makes a radio transmit", "disc_intro": "APRS & Packet controls a radio transmitter through the connected TNC: it can send beacons, messages, packet connections, BBS and TAK traffic.", "disc_licence": "Only a holder of a valid amateur radio licence may transmit, and only on the frequencies, with the power and the modes their licence and their country's rules allow.", "disc_harm": "A wrong setting or transmitting on an unsuitable frequency can interfere with other stations and services, including emergency, aviation and distress communications, and so put people and property at risk. Causing interference is against the law and can be punished.", "disc_rx": "Without a licence, use the app for receiving only and leave transmitting switched off (the Transmit switch).", "disc_resp": "You are responsible for everything your station transmits. The app is provided as is, without any warranty (MIT licence); its author is not liable for any damage caused by its use.", "disc_accept": "I understand and agree", "disc_decline": "Decline", "disc_declined": "The app cannot be used without agreeing. If you do not want to agree, uninstall it.", "disc_again": "Show it again",
        "update_download": "Download", "update_apk_hint": "The new version is downloading. Open the downloaded file to install it; the first time, Android asks to allow installing from the browser.",
        "zoom_in": "Zoom in", "zoom_out": "Zoom out", "north_up": "North up",
        "gps_phone": "The phone's GPS", "gps_phone_hint": "The map and the beacon use the phone's location. Android asks for the permission the first time; the location must be switched on.", "gps_phone_denied": "Not allowed to use the location: allow it in the phone's settings for this app", "gps_phone_off": "The phone's location is switched off", "no_position": "No position yet: type it in Settings, use GPS, or long-press the map",
        "baudrate": "Speed (baud)", "refresh_ports": "Look for serial ports",
        "no_ports": "No serial ports found", "txdelay": "TX delay sent to the TNC (ms, 0 = leave)",
        "station": "Station", "callsign": "Callsign", "ssid": "SSID", "symbol": "Icon (APRS symbol)",
        "comment": "Position comment", "digipath": "Digipeater path",
        "latitude": "Latitude", "longitude": "Longitude",
        "position_hint": "Your position for the beacon and the map, in degrees (e.g. 49.7458 and 13.3772), "
                         "or right-click the map: Set as my position. Everyone on aprs.fi will see it.",
        "set_my_position": "Set as my position", "copy_coordinates": "Copy {lat}, {lon}",
        "copied": "Copied", "position_set": "My position set to {lat}, {lon}",
        "beacon": "Send position every (minutes, 0 = off, at least 10)",
        "beacon_is": "Send over the internet too: my position (now, regular, tracker) and messages",
        "tracked": "Callsigns to highlight on the map (comma separated)",
        "incoming": "Accept incoming packet connections",
        "aprsis": "APRS-IS (internet)", "aprsis_on": "Connect to APRS-IS", "server": "Server",
        "passcode": "APRS-IS password (passcode)",
        "pass_hint": "Empty: computed from your callsign (the standard APRS-IS passcode).",
        "radius": "Receive packets within (km of my position, 0 = none)",
        "igate_rx": "iGate: send packets heard on the radio to APRS-IS",
        "igate_tx": "iGate: send internet messages to local stations by radio",
        "licence_ask": "APRS-IS is for licensed radio amateurs only. To switch it on, type:",
        "licence_text": "I hold a valid amateur radio licence",
        "licence_required": "To switch APRS-IS on, type the sentence about your licence exactly as shown.",
        "app_section": "App", "language": "Language", "lang_auto": "System",
        "theme": "Appearance", "theme_auto": "As the system", "theme_light": "Light", "theme_dark": "Dark",
        "save": "Save", "saved": "Saved; the connection restarts with the new settings.",
        "first_run": "Welcome! Set your callsign and how to reach the TNC, then press Save.",
        "aprsis_state": "APRS-IS", "verified": "logged in", "unverified": "connected, not verified (check the passcode)",
        "invalid": "Invalid setting",
        "legend": "Legend", "legend_colours": "Callsign colours",
        "legend_rf": "Heard by your radio", "legend_is": "Seen only on the internet (APRS-IS)",
        "legend_tracked": "Tracked callsign (Settings)", "legend_me": "Your own station",
        "legend_symbols": "Symbols now shown",
        "legend_symbols_hint": "Each station chooses its own APRS symbol: a car, a house, a weather station…",
        "legend_unknown": "Symbol not in the table (code)",
        "show_internet": "Stations from the internet", "map_muted": "Muted map", "thursday": "APRS Thursday", "th_running": "Running now, ends in {t}", "th_next": "Next one starts {when} (in {t})", "th_member": "You are in the HOTG group until {when}", "th_not_member": "Not in the HOTG group: your first message adds you to it", "th_about": "Every Thursday (UTC) radio amateurs all over the world send a short message to the HOTG group. ANSRVR passes it on to everyone who wrote to the group in the last 12 hours, and sends you theirs.", "th_rf_hint": "By radio, replies reach you only through an iGate that gates internet messages to the radio; over the internet (APRS-IS) it always works.", "th_placeholder": "Your message to the group (e.g. where you are, what rig)", "th_send": "Send to HOTG", "th_leave": "Leave the group", "th_map": "Map and check-ins (aprs.to)", "th_empty": "No HOTG messages yet.", "th_wait": "Next message possible in {t} (one per 30 minutes)", "bbs_saved": "Saved BBS", "bbs_save": "Save this BBS (callsign and path)", "bbs_remove": "Remove from saved", "bbs_saved_as": "{call} saved", "bbs": "BBS SERVER", "bbs_switch": "BBS SERVER on", "bbs_off": "BBS SERVER is off. Switching it on turns the app into a packet BBS: everything else (APRS, APRS-IS, iGate, beacon, messages, APRS Thursday, terminal, chat) stops until you switch it off.", "bbs_running": "Running as {call} · connected: {n} · messages: {msgs}", "bbs_error": "BBS SERVER could not start: {error}", "bbs_tx_needed": "Switch Transmit on, otherwise the BBS cannot answer.", "bbs_confirm_title": "Switch BBS SERVER on?", "bbs_confirm_ask": "While the BBS runs, everything else in the app is off. Tune the radio to a packet channel (e.g. 144.8125-144.9625 MHz), never to the APRS frequency 144.800. To switch it on, type:", "bbs_confirm_text": "BBS SERVER must have another frequency than APRS", "bbs_confirm_wrong": "Type the sentence exactly as shown.", "bbs_enable": "Switch on", "cancel": "Cancel", "bbs_folder": "Open the settings folder", "bbs_reload": "Reload settings", "bbs_reloaded": "BBS settings reloaded", "bbs_connected": "Connected", "bbs_nobody": "Nobody connected.", "bbs_messages": "Messages", "bbs_no_messages": "No messages yet.", "bbs_log": "Log", "bbs_delete": "Delete", "bbs_ssid": "BBS SERVER SSID", "term_attempt": "connecting, attempt {n}/{max} (last at {time}, started {start})", "term_stop": "Stop connecting", "bbs_max_sessions": "Clients at the same time", "bbs_idle_sec": "Inactivity timeout (seconds)", "bbs_max_tx": "Maximum TX time per connection (minutes, 0 = no limit)", "bbs_max_messages": "Maximum stored messages (0 = no limit)", "bbs_welcome": "Welcome message (ASCII art welcome; {name}, {bbs}, {new}… are filled in)", "bbs_more": "More options (access, beacon, how long messages are kept) are in bbs.toml in the BBS folder:", "bbs_guide": "Guide", "gps_source": "My position from", "gps_manual": "Typed in (latitude and longitude above)", "gps_usb": "USB GPS module (NMEA)", "gps_device": "GPS port", "gps_auto": "Automatic", "gps_hint": "Cheap USB GPS modules (u-blox, VK-172…) send NMEA at 9600 or 4800 Bd. With a fix, the map and the beacon use the GPS position (and its altitude); without one, the position typed above.", "gps_sats": "{n} sat.", "gps_nofix": "no fix", "gps_same_port": "The GPS must be on another port than the TNC", "tak": "TAK", "tak_off": "TAK is off. Switching it on turns the app into a TAK station over the radio (ATAK-compatible positions and GeoChat in TAK Protocol v1): everything else (APRS, APRS-IS, iGate, beacon, messages, terminal, chat, BBS) stops until you switch it off.", "tak_running": "Running as {call} · team {team} · stations: {n}", "tak_confirm_title": "Switch TAK on?", "tak_confirm_ask": "While TAK runs, everything else in the app is off. Tune the radio to a channel agreed with your team, never to the APRS frequency 144.800. Amateur radio: nothing is encrypted. To switch it on, type:", "tak_confirm_text": "TAK must have another frequency than APRS", "tak_send_position": "Send my position", "tak_stations": "Stations", "tak_no_stations": "No TAK stations heard yet.", "tak_chat": "GeoChat", "tak_everybody": "Everybody", "tak_callsign": "TAK callsign (empty: your callsign)", "tak_team": "Team (colour)", "tak_role": "Role", "tak_interval": "Send my position every (minutes, 0 = only with the button)", "tak_no_chat": "No messages yet.", "tak_tx_needed": "Switch Transmit on, otherwise TAK cannot send.", "map_offline": "Offline map (borders and cities, no internet needed)", "net_offline": "No internet: the map switched to the offline map (borders and cities).", "net_online": "The internet is back: the map uses OpenStreetMap again.", "via_packet": "Packet (AX.25)", "vara_host": "VARA FM address (empty = off)", "vara_port": "Command port (data = +1)", "vara_hint": "VARA FM runs on its own (Windows, or Wine on Linux) with the radio on a sound card such as an AIOC cable; the terminal then offers \"Connection: VARA FM\". Leave the address empty when you don't use VARA.", "vara_connecting": "connecting…", "vara_connected": "connected", "vara_disconnecting": "disconnecting…", "vara_idle": "not connected", "menu": "Menu", "back": "Back", "last_2h": "Last 2 hours",
        "via_heard_rf": "radio", "via_heard_is": "internet",
        "quit_title": "Quit APRS & Packet?",
        "quit_text": "When the app is closed, this stops:",
        "quit_rx": "receiving packets and messages",
        "quit_beacon": "sending your position (beacon)",
        "quit_igate": "the iGate",
        "quit_sessions": "connected packet sessions ({n})",
        "quit_yes": "Quit", "quit_stay": "Keep running", "quit_minimize": "Minimise",
        "update_available": "A new version {version} is out.", "update_show": "Show",
        "update_button": "New version {version}", "update_tooltip": "Open the download page",
        "update_none": "You have the newest version.", "update_never": "Not checked for new versions yet.",
        "update_failed": "Could not check for new versions", "update_checked": "checked {when}",
        "update_check_now": "Check now",
        "check_updates": "Check for new versions once a day (asks GitHub, sends nothing about you)",
        "about": "About", "about_version": "Version {version}",
        "about_what": "An APRS station and packet radio terminal for a radio with a KISS TNC: a map of the "
                      "stations heard, APRS messages with acknowledgement, a terminal for BBSes and nodes, "
                      "packet chat, a frame monitor and APRS-IS with an optional iGate.",
        "about_radio": "Made for the Quansheng UV-K1/UV-K5 V3 with the F4HWN firmware and its KISS TNC app; "
                       "any KISS TNC works (Direwolf, a hardware TNC, a radio on USB or on the network).",
        "about_source": "Source code and documentation (GitHub)", "about_issues": "Report a problem or an idea",
        "about_releases": "New versions", "about_firmware": "F4HWN firmware for Quansheng UV-K1/K5 V3",
        "about_kiss_app": "KISS TNC app for the F4HWN firmware (by F4WAT)",
        "about_ha": "The same as a Home Assistant integration",
        "about_author": "Author",
        "about_contact": "Questions and feedback: GitHub issues, or through ok1sim.cz.",
        "about_together": "Written together with Claude Code (Anthropic).",
        "about_licence": "MIT licence. Map data © OpenStreetMap contributors. APRS parsing by aprslib. "
                         "F4HWN firmware by Armel F4HWN, KISS TNC app by F4WAT.",
        "about_data": "Settings and history",
    },
    "cs": {
        "app_title": "APRS & Packet",
        "map": "Mapa", "messages": "Zprávy", "stations": "Stanice", "terminal": "Terminál",
        "chat": "Chat", "monitor": "Monitor", "settings": "Nastavení",
        "tnc": "TNC", "connected": "připojeno", "disconnected": "nepřipojeno",
        "transmit": "Vysílání", "tx_on": "Vysílání je ZAPNUTÉ", "tx_off": "Vysílání je vypnuté (jen příjem)",
        "tx_refused": "Neodesláno: vysílání je vypnuté",
        "not_sent": "Neodesláno", "send": "Odeslat", "to": "Komu", "text": "Text", "via": "Cesta",
        "via_radio": "Rádiem", "via_internet": "Internetem", "via_both": "Rádiem i internetem",
        "new_message": "Nová zpráva", "message_from": "Zpráva od {call}",
        "state_pending": "čeká na potvrzení", "state_acked": "doručeno", "state_rejected": "odmítnuto",
        "state_failed": "nedoručeno",
        "no_messages": "Zatím žádné zprávy.", "pick_conversation": "Vyber konverzaci nebo začni novou.",
        "no_stations": "Zatím žádné slyšené stanice.", "filter": "Filtr", "last_heard": "slyšeno", "ago": "před {t}",
        "show_on_map": "Ukázat na mapě", "send_message": "Poslat zprávu", "close": "Zavřít",
        "my_position": "Moje poloha", "centre_me": "Vycentrovat na moji polohu",
        "remote": "Stanice", "path": "Přes digipeatery", "connect": "Připojit",
        "disconnect": "Odpojit", "session": "Spojení", "type_here": "Piš a stiskni Enter",
        "not_connected_session": "Nejsi připojený k žádné stanici.",
        "chat_hint": "Packet chat: prostý text na CQ, slyší ho každý na kmitočtu.",
        "monitor_hint": "Každý přijatý a odeslaný rámec, jako na TNC.", "clear": "Vymazat",
        "pause": "Pozastavit", "resume": "Pokračovat",
        "beacon_now": "Poslat polohu teď", "position_sent": "Poloha odeslána",
        "tnc_section": "Připojení k TNC", "connection": "Připojení", "conn_tcp": "KISS přes TCP (síť)",
        "conn_serial": "Sériový port (USB)", "conn_usb": "TNC na USB (OTG kabel)", "host": "Adresa", "port": "Port", "device": "Sériový port",
        "th_starts_in": "Další začíná za {t}",
        "map_trails": "Ocásky (kudy stanice jely za poslední půlhodinu)",
        "map_tools_hide": "Schovat tlačítka mapy", "map_tools_show": "Tlačítka mapy",
        "filter": "Filtr stanic", "filter_on": "Zobrazeno jen: {what}", "filter_all": "Zobrazit všechny stanice", "filter_weather": "Jen meteostanice", "filter_moving": "Jen pohybující se (pohnuly se za posledních 10 min)", "filter_road": "Jen dopravní problémy (nehody, práce na silnici, povodně…)", "filter_weather_short": "meteostanice", "filter_moving_short": "pohybující se", "filter_road_short": "dopravní problémy",
        "filter_repeater": "Jen převaděče (s jejich kmitočtem)", "filter_repeater_short": "převaděče",
        "map_following": "Mapa mě sleduje (tracker); klepnutím se po posunutí mapy hned vrátí na mě",
        "follow_back": "Zpět na mě · {s} s", "follow_back_tip": "Hned zpět na moji polohu (po odpočtu se mapa vrátí sama)",
        "road_alerts": "Upozorňovat na dopravní problémy před sebou (když běží tracker)", "road_alert_km": "Dívat se dopředu", "road_alerts_hint": "Nehody, práce na silnici a další dopravní hlášení na mapě v laloku před tebou: rovně do zvolené vzdálenosti, do stran méně, za tebe nikdy. Pomalu (ve městě) je lalok široký, rychle (hlavní silnice, dálnice) dlouhý a úzký. Bublina a zvuk, u každého jednou.", "road_ahead": "Dopravní hlášení {d} před tebou", "road_left": "vlevo", "road_right": "vpravo", "road_more": "a další před tebou: {n}", "road_show": "Ukázat", "sound_road": "Dopravní problém před tebou (tracker)",
        "about_thanks": "Děkuji radioklubu OK1OMG a Martinovi OK1MDX za pomoc a podporu.",
        "update_beta": "Nabízet i beta verze (pro testery: novější, méně vyzkoušené)",
        "locator_is": "Lokátor {loc} (kopírovat)", "loc_to_chat": "Poslat lokátor {loc} do chatu", "loc_to_message": "Poslat lokátor {loc} ve zprávě…",
        "pos_to_chat": "Poslat tuto polohu do chatu", "pos_to_message": "Poslat tuto polohu ve zprávě…", "pos_send_mine": "Poslat moji polohu do chatu", "pos_insert_mine": "Vložit moji polohu do zprávy", "pos_on_map": "Ukázat na mapě", "pos_sent_chat": "Poloha odešla do chatu",
        "files_pick": "Vybrat soubor…", "files_send_now": "Odeslat", "files_estimate": "Za výborných podmínek asi {t} (1200 Bd)", "files_estimate_hops": "digipeaterů na cestě: {n} (každý opakuje každý rámec)", "files": "Soubory", "files_to": "Komu (stanice)", "files_via": "Přes digipeatery", "files_accept": "Přijímat soubory od jiných stanic (na každý se zeptá)", "files_about": "Pošlete soubor jiné stanici přes packet radio: spojení AX.25 s potvrzováním a protokol YAPP jako u BPQ, WinPacku nebo Paxonu. Při 1200 Bd zhruba 60–100 bajtů za sekundu: malé obrázky a texty. Přerušený přenos při dalším poslání naváže tam, kde skončil.", "files_send": "Poslat soubor…", "files_folder": "Otevřít složku", "files_tx_needed": "Zapni Vysílání, jinak nejde nic poslat ani potvrdit.", "files_folder_is": "Přijaté soubory se ukládají do {path}", "files_none": "Zatím žádné přenosy.", "files_left": "zbývá {left}, asi {t}", "files_took": "trvalo {t}, {speed} B/s", "files_state_connecting": "připojuji…", "files_state_waiting": "čekám na druhou stranu…", "files_state_offered": "čekám na odpověď", "files_state_sending": "odesílám", "files_state_receiving": "přijímám", "files_state_done": "hotovo", "files_state_refused": "odmítnuto", "files_state_cancelled": "zrušeno", "files_state_failed": "přerušeno", "files_cancel": "Zrušit", "files_accept_one": "Přijmout", "files_refuse": "Odmítnout", "files_save": "Uložit kopii…", "files_to_needed": "Nejdřív napiš značku stanice.", "files_offer_title": "Přichází soubor", "files_offer_text": "{call} ti chce poslat {name} ({size}). Přijmout?",
        "spot_button": "Spot", "spot_title": "Ohlásit aktivaci (SOTA, POTA, WWFF, GMA…)", "spot_program": "Program", "spot_gateway": "Brána", "spot_ref": "Reference", "spot_freq": "Kmitočet (MHz)", "spot_mode": "Druh provozu", "spot_comment": "Poznámka (nepovinná)", "spot_test": "Jen zkouška", "spot_hint_aprs2sota": "APRS2SOTA vystaví spot na SOTAwatch. Značku je potřeba nejdřív zaregistrovat u jejího provozovatele (sotaspots.co.uk). Odpověď (Spotted / Error) přijde jako zpráva v její konverzaci. Zkušební spot se vystaví označený jako TEST.", "spot_hint_apspot": "APSPOT vystaví spot na pota.app, SOTAwatch nebo ParksnPeaks; je potřeba tam mít účet. Odpověď přijde jako zpráva v její konverzaci. Na zkušební spot jen odpoví, nic nevystaví.", "spot_send": "Odeslat spot", "spot_bad_ref": "Reference nevypadá správně, např. {example}", "spot_bad_freq": "Kmitočet v MHz, např. 7.032 nebo 145.500", "spot_bad_program": "Vyber program",
        "spot_lighthouse": "Maják", "spot_hint_camilla": "Camilla (DL0QW-12, gma.rocks) vystaví spot na GMA a SOTA vrchol i na SOTAwatch: vrcholy, hrady (WCA), WWFF, ostrovy (IOTA), majáky. Jen pro registrované uživatele GMA (zdarma na gma.rocks). Odpoví zprávou v její konverzaci. Zkušební spot se vystaví označený jako TEST.",
        "services_button": "Služby", "services_title": "Služby na APRS", "services_hint": "Každá odpoví na zprávu: vyber příkaz, vloží se do pole zprávy, pošli ho. Odpověď přijde do té konverzace.", "svc_type": "Napsat…", "svc_find": "Kde byla stanice naposledy slyšet: pošli její značku. Odpoví čas, iGate, vzdálenost a lokátor.", "svc_repeat": "Převaděče nejblíž tvé poslední poloze.", "svc_wxnow": "Počasí z meteostanice nejblíž tobě.", "svc_utc": "Přesný čas (UTC).", "svc_sat": "Přelety satelitů nad tebou (satpass iss, satpass so-50), východ a západ slunce, kde jsi.", "svc_mail": "E-mail z rádia: EMAIL adresa text, klidně víc zpráv, nakonec SEND. 5 za hodinu.",
        "msg_parts": "{n} zprávy · {chars} znaků",
        "conv_delete": "Smazat konverzaci", "conv_delete_title": "Smazat konverzaci s {call}?", "conv_delete_ask": "Všechny zprávy s touto stanicí zmizí z aplikace. Už odeslané zprávy se tím nevrátí.", "more": "Další",
        "msg_where": "{d} {dir} · poloha {age}", "msg_distance_then": "Jak daleko byl odesílatel, když zpráva přišla",
        "offer_tracker": "Nabídnout tracker, když to vypadá, že jedu (potřebuje běh na pozadí)", "drive_title": "Vypadá to, že jedeš", "drive_text": "Zapnout tracker? Klepnutím otevřeš APRS & Packet.", "drive_ask": "Vypadá to, že jsi na cestě, a tracker je vypnutý. Zapnout ho, aby se tvoje poloha posílala sama?", "drive_yes": "Zapnout", "drive_no": "Teď ne", "drive_channel": "Nabídka trackeru",
        "trk_menu_road": "Hlásit dopravní problémy před sebou", "trk_menu_meet": "Hlásit jedoucí stanice před sebou",
        "profile_pick": "Přepnout profil (SSID a ikona)", "profile_title": "Profil stanice", "profile_edit": "Upravit profily", "profile_add_hint": "Další profily (až tři) přidáš v Nastavení › Stanice.", "profile_now": "Od teď se vše posílá jako {call}", "profile_unused": "— nepoužit", "profile_active": "Aktivní profil", "profiles_hint": "Profily: až tři SSID, každé s vlastní ikonou. Přepínají se klepnutím na značku v horní liště; od té chvíle se vše (poloha, zprávy, terminál, chat) posílá pod vybraným.", "profile_dup": "Každý profil musí mít jiné SSID.",
        "err_usb_none": "Není připojené žádné USB TNC (může být potřeba OTG redukce)", "err_usb_open": "Nepodařilo se otevřít {dev}", "err_usb_busy": "{dev} používá jiná aplikace", "err_usb_perm": "Chybí povolení pro {dev}: povol ho, až se Android zeptá", "err_usb_write": "Zápis do USB TNC selhal", "err_bt_none": "Tento telefon nemá Bluetooth", "err_bt_perm": "Chybí povolení pro Bluetooth: povol aplikaci „Zařízení v okolí“", "err_bt_off": "Bluetooth je vypnuté: zapni ho", "err_bt_nopaired": "Žádné spárované Bluetooth zařízení: nejdřív spáruj TNC v nastavení Bluetooth v Androidu", "err_bt_unpaired": "Bluetooth zařízení {dev} není spárované", "err_bt_connect": "Nepodařilo se připojit k {dev}: {why}", "err_not_connected": "TNC není připojené",
        "meet_alerts": "Upozorňovat na jiné jedoucí stanice před sebou (dojíždíš je, nebo jedou proti tobě)", "meet_ahead": "Jedoucí stanice {d} před tebou", "meet_same": "Jedoucí stanice {d} před tebou, jede stejným směrem", "meet_towards": "Jedoucí stanice {d} před tebou, jede proti tobě", "meet_across": "Jedoucí stanice {d} před tebou, křižuje tvůj směr", "sound_meet": "Jedoucí stanice před tebou (tracker)",
        "object_of": "objekt od {call}",
        "measure_from": "Měřit vzdálenost odsud",
        "measure_from_me": "Vzdálenost od mé polohy",
        "measure_hint": "Klepněte na druhý bod na mapě",
        "measure_close": "Ukončit měření",
        "unsaved_title": "Neuložené změny",
        "unsaved_text": "V Nastavení jste něco změnili a neuložili.",
        "unsaved_discard": "Zahodit",
        "trk_section": "Tracker",
        "trk_mode": "Kdy posílat polohu",
        "trk_fixed": "Pevný interval",
        "trk_smart": "Chytře (SmartBeaconing)",
        "trk_minutes": "Každých",
        "trk_profile": "Pohybuji se",
        "trk_walk": "Pěšky",
        "trk_bike": "Na kole",
        "trk_car": "Autem",
        "trk_still": "Když stojím, jednou za",
        "trk_hint_fixed": "Spouští se tlačítkem polohy v horní liště (▶︎). Když běží, poloha z GPS se posílá sama v tomto intervalu – rádiem, když je zapnuté TX, a přes internet, pokud je to zvolené ve Stanici.",
        "trk_hint_smart": "Jako APRS a LoRa APRS trackery: když stojíte, jednou za nastavenou dobu; v pohybu tím častěji, čím rychleji jedete (až zhruba jednou za minutu), a hned v zatáčce, aby stopa sledovala silnici. Spouští se tlačítkem polohy v horní liště (▶︎).",
        "pos_send_now": "Odeslat polohu teď",
        "trk_start": "Spustit tracker",
        "trk_stop": "Pozastavit tracker",
        "trk_settings": "Nastavení trackeru…",
        "trk_off": "Tracker je vypnutý",
        "trk_running": "Tracker běží – další poloha za {t}",
        "trk_wait_gps": "Tracker čeká na polohu z GPS",
        "trk_wait_tx": "Vysílání (TX) je vypnuté: poloha se rádiem neposílá",
        "trk_no_gps": "Tracker potřebuje GPS: vyberte zdroj polohy v Nastavení › GPS",
        "trk_bg_hint": "Aby tracker běžel i se zhasnutým displejem, zapněte v Nastavení běh na pozadí.",
        "trk_started": "Tracker spuštěn.",
        "trk_stopped": "Tracker pozastaven.",
        "map_source": "Mapa",
        "map_src_online": "Online mapa (OpenStreetMap)",
        "map_src_imported": "Stažená mapa",
        "map_src_basic": "Základní offline mapa",
        "map_src_none": "Stažená mapa (zatím žádná)",
        "map_src_manage": "Spravovat mapy…",
        "maps_section": "Offline mapy",
        "maps_hint": "Nahrajte si lepší mapu pro provoz bez internetu, třeba turistickou, odkudkoli (vlastní, koupená…). Rastrové dlaždicové mapy: MBTiles, PMTiles, SQLiteDB (OsmAnd, Locus), ZIP s dlaždicemi z/x/y nebo ZIP/7z, ve kterém jsou takové soubory (7z na počítači se 7-Zipem). Vektorové mapy (Mapsforge, vektorové MBTiles) nejdou. Mapu vyberete tlačítkem mapy; kde stažená mapa nemá dlaždice, ukáže se základní.",
        "maps_import": "Importovat mapu…",
        "maps_importing": "Importuji…",
        "maps_none": "Žádná stažená mapa.",
        "maps_broken": "nejde otevřít",
        "maps_remove": "Odebrat",
        "maps_added": "Mapa nahrána: vyberte ji tlačítkem mapy na mapě.",
        "maps_web": "V prohlížeči nejde mapy importovat.",
        "map_err_vector": "vektorové dlaždice nejdou, jen obrázky (PNG, JPEG, WebP)",
        "map_err_unknown": "není to podporovaný soubor mapy",
        "map_err_empty": "nejsou v něm žádné dlaždice",
        "map_err_no7z": "7z potřebuje na počítači 7-Zip (nebo ho nejdřív rozbalte)",
        "map_err_read": "soubor nejde přečíst",
        "bt_device": "Bluetooth zařízení",
        "digi": "Digipeater", "digi_mode": "APRS digipeater", "digi_off": "Vypnutý", "digi_fillin": "Fill-in (WIDE1-1) – domácí stanice", "digi_wide": "Plný (WIDEn-N) – digipeater na kótě", "digi_hops": "Nejvýš hopů (WIDEn-N)", "digi_aliases": "Přeposílat i pro (aliasy, např. RELAY)", "digi_hint": "Přeposílá APRS pakety stanic kolem vás, jen když je zapnuté Vysílání. Fill-in pomáhá ručkám a autům dosáhnout na nejbližší velký digipeater a je to správná volba pro domácí stanici. Plný digipeater jen po dohodě s místní APRS sítí. Přeposílají se i rámce adresované vaší značce; stejný paket jen jednou za 30 sekund.",
        "conn_bt": "TNC přes Bluetooth (spárované)", "bt_none": "Žádné spárované Bluetooth zařízení: spáruj TNC v nastavení Bluetooth v Androidu a pak klepni na obnovit.",
        "conn_ble": "TNC přes Bluetooth LE", "ble_device": "Bluetooth LE zařízení", "ble_scanning": "Hledám Bluetooth LE zařízení…", "ble_none": "Žádné Bluetooth LE zařízení: zapni na TNC Bluetooth (KISS), dej ho blízko a klepni na obnovit.",
        "bg_section": "Pozadí a obrazovka", "run_background": "Běžet na pozadí (Android)", "bg_hint": "Příjem, majáky, zprávy i TAK běží dál, i když aplikace není na obrazovce nebo je telefon zamčený. Android po tu dobu ukazuje notifikaci a potřebuje k tomu povolení polohy. Víc to vybíjí baterii.", "keep_screen": "Nezhasínat obrazovku", "keep_never": "Ne", "keep_tak": "Když běží TAK", "keep_always": "Vždy (když je aplikace otevřená)", "bg_notification": "Běží: příjem a vysílání pokračují", "bg_channel": "Běh na pozadí",
        "call_required": "Vyplň svou volací značku a ulož: bez ní aplikace nemůže fungovat.",
        "lang_title": "Jazyk", "lang_detected": "Zařízení používá: {name}. Nech jazyk podle zařízení, nebo si vyber jiný:", "lang_later": "Změnit ho jde později v Nastavení › Aplikace.", "sounds": "Zvuky", "sound_test": "Přehrát", "sound_tx": "Pípnout při vysílání", "sound_messages": "Zvuk při nové APRS zprávě", "sound_chat": "Zvuk při nové zprávě v packet chatu", "sound_tak": "Zvuk při nové zprávě v TAK GeoChatu",
        "tak_appeared": "{call} se objevil na mapě", "tak_moved": "{call} se posunul o {far}",
        "term_new": "Nová stanice…",
        "disc_title": "Než začneš: tato aplikace ovládá vysílač", "disc_intro": "APRS & Packet přes připojený TNC ovládá radiový vysílač: umí vysílat majáky, zprávy, packetová spojení, provoz BBS a TAK.", "disc_licence": "Vysílat smí jen držitel platného radioamatérského oprávnění (licence), a to jen na kmitočtech, s výkonem a druhy provozu, které mu oprávnění a předpisy jeho země dovolují.", "disc_harm": "Špatné nastavení nebo vysílání na nevhodném kmitočtu může rušit jiné stanice a služby, včetně záchranných, leteckých a tísňových spojení, a tím ohrozit lidi i majetek. Způsobování rušení je protiprávní a může být potrestáno.", "disc_rx": "Bez licence používej aplikaci jen pro příjem a vysílání nech vypnuté (přepínač Vysílání).", "disc_resp": "Za všechno, co tvoje stanice vyšle, odpovídáš ty. Aplikace je poskytována tak, jak je, bez jakékoli záruky (licence MIT); autor neodpovídá za škody způsobené jejím použitím.", "disc_accept": "Rozumím a souhlasím", "disc_decline": "Odmítnout", "disc_declined": "Bez souhlasu aplikaci nelze používat. Pokud souhlasit nechceš, odinstaluj ji.", "disc_again": "Zobrazit znovu",
        "update_download": "Stáhnout", "update_apk_hint": "Nová verze se stahuje. Otevři stažený soubor a nainstaluj ho; poprvé se Android zeptá, jestli smí prohlížeč instalovat aplikace.",
        "zoom_in": "Přiblížit", "zoom_out": "Oddálit", "north_up": "Sever nahoru",
        "gps_phone": "GPS telefonu", "gps_phone_hint": "Mapa i maják používají polohu telefonu. Android se poprvé zeptá na povolení; poloha musí být zapnutá.", "gps_phone_denied": "Aplikace nesmí používat polohu: povol ji v nastavení telefonu pro tuto aplikaci", "gps_phone_off": "Poloha v telefonu je vypnutá", "no_position": "Zatím žádná poloha: zadej ji v Nastavení, použij GPS, nebo podrž prst na mapě",
        "baudrate": "Rychlost (baud)", "refresh_ports": "Hledat sériové porty",
        "no_ports": "Žádné sériové porty nenalezeny", "txdelay": "TX delay pro TNC (ms, 0 = neměnit)",
        "station": "Stanice", "callsign": "Značka", "ssid": "SSID", "symbol": "Ikona (APRS symbol)",
        "comment": "Komentář k poloze", "digipath": "Cesta přes digipeatery",
        "latitude": "Zeměpisná šířka", "longitude": "Zeměpisná délka",
        "position_hint": "Tvoje poloha pro maják a mapu ve stupních (např. 49.7458 a 13.3772), "
                         "nebo klikni pravým na mapu: Nastavit jako moji polohu. Na aprs.fi ji uvidí každý.",
        "set_my_position": "Nastavit jako moji polohu", "copy_coordinates": "Kopírovat {lat}, {lon}",
        "copied": "Zkopírováno", "position_set": "Moje poloha nastavena na {lat}, {lon}",
        "beacon": "Posílat polohu každých (minut, 0 = ne, nejméně 10)",
        "beacon_is": "Posílat i přes internet: moji polohu (teď, pravidelně, tracker) a zprávy",
        "tracked": "Značky zvýrazněné na mapě (oddělené čárkou)",
        "incoming": "Přijímat příchozí packet spojení",
        "aprsis": "APRS-IS (internet)", "aprsis_on": "Připojit se k APRS-IS", "server": "Server",
        "passcode": "Heslo pro APRS-IS (passcode)",
        "pass_hint": "Prázdné: spočítá se z tvé značky (standardní passcode APRS-IS).",
        "radius": "Přijímat pakety do (km od mé polohy, 0 = žádné)",
        "igate_rx": "iGate: posílat pakety slyšené rádiem do APRS-IS",
        "igate_tx": "iGate: zprávy z internetu pro místní stanice vysílat rádiem",
        "licence_ask": "APRS-IS je jen pro radioamatéry s licencí. Pro zapnutí napiš:",
        "licence_text": "mám platnou radioamatérskou licenci",
        "licence_required": "Pro zapnutí APRS-IS napiš větu o licenci přesně tak, jak je uvedená.",
        "app_section": "Aplikace", "language": "Jazyk", "lang_auto": "Podle systému",
        "theme": "Vzhled", "theme_auto": "Podle systému", "theme_light": "Světlý", "theme_dark": "Tmavý",
        "save": "Uložit", "saved": "Uloženo; spojení se restartuje s novým nastavením.",
        "first_run": "Vítej! Nastav svou značku a připojení k TNC a klikni na Uložit.",
        "aprsis_state": "APRS-IS", "verified": "přihlášeno", "unverified": "připojeno, neověřeno (zkontroluj passcode)",
        "invalid": "Neplatné nastavení",
        "legend": "Legenda", "legend_colours": "Barvy značek",
        "legend_rf": "Slyšeno tvým rádiem", "legend_is": "Jen z internetu (APRS-IS)",
        "legend_tracked": "Sledovaná značka (Nastavení)", "legend_me": "Tvoje stanice",
        "legend_symbols": "Právě zobrazené symboly",
        "legend_symbols_hint": "Každá stanice si sama volí svůj APRS symbol: auto, dům, meteostanici…",
        "legend_unknown": "Symbol, který není v tabulce (kód)",
        "show_internet": "Stanice z internetu", "map_muted": "Tlumená mapa", "thursday": "APRS Thursday", "th_running": "Právě probíhá, končí za {t}", "th_next": "Další začíná {when} (za {t})", "th_member": "Jsi ve skupině HOTG do {when}", "th_not_member": "Nejsi ve skupině HOTG: první zpráva tě do ní přidá", "th_about": "Každý čtvrtek (UTC) posílají radioamatéři z celého světa krátkou zprávu do skupiny HOTG. ANSRVR ji předá všem, kdo do skupiny psali za posledních 12 hodin, a tobě pošle ty jejich.", "th_rf_hint": "Rádiem k tobě odpovědi dojdou jen přes iGate, který posílá zprávy z internetu do rádia; přes internet (APRS-IS) to funguje vždy.", "th_placeholder": "Tvoje zpráva pro skupinu (např. odkud vysíláš, s čím)", "th_send": "Poslat do HOTG", "th_leave": "Odhlásit ze skupiny", "th_map": "Mapa a zapojení (aprs.to)", "th_empty": "Zatím žádné zprávy HOTG.", "th_wait": "Další zprávu můžeš poslat za {t} (jedna za 30 minut)", "bbs_saved": "Uložené BBS", "bbs_save": "Uložit tuto BBS (značku a cestu)", "bbs_remove": "Odebrat z uložených", "bbs_saved_as": "{call} uloženo", "bbs": "BBS SERVER", "bbs_switch": "BBS SERVER zapnutý", "bbs_off": "BBS SERVER je vypnutý. Po zapnutí se z aplikace stane packet BBS: všechno ostatní (APRS, APRS-IS, iGate, maják, zprávy, APRS Thursday, terminál, chat) přestane fungovat, dokud ho nevypneš.", "bbs_running": "Běží jako {call} · připojeno: {n} · zpráv: {msgs}", "bbs_error": "BBS SERVER se nepodařilo spustit: {error}", "bbs_tx_needed": "Zapni Vysílání, jinak BBS nemůže odpovídat.", "bbs_confirm_title": "Zapnout BBS SERVER?", "bbs_confirm_ask": "Dokud BBS běží, je všechno ostatní v aplikaci vypnuté. Nalaď rádio na packetový kanál (např. 144.8125-144.9625 MHz), nikdy ne na APRS kmitočet 144.800. Pro zapnutí napiš:", "bbs_confirm_text": "BBS SERVER musí mít jinou frekvenci než APRS", "bbs_confirm_wrong": "Napiš větu přesně tak, jak je uvedená.", "bbs_enable": "Zapnout", "cancel": "Zrušit", "bbs_folder": "Otevřít složku s nastavením", "bbs_reload": "Načíst nastavení znovu", "bbs_reloaded": "Nastavení BBS načteno znovu", "bbs_connected": "Připojení", "bbs_nobody": "Nikdo není připojený.", "bbs_messages": "Zprávy", "bbs_no_messages": "Zatím žádné zprávy.", "bbs_log": "Log", "bbs_delete": "Smazat", "bbs_ssid": "SSID pro BBS SERVER", "term_attempt": "připojuji se, pokus {n}/{max} (poslední v {time}, začátek v {start})", "term_stop": "Zastavit připojování", "bbs_max_sessions": "Počet klientů najednou", "bbs_idle_sec": "Odpojit po nečinnosti (sekundy)", "bbs_max_tx": "Maximální TX čas na jedno spojení (minuty, 0 = bez omezení)", "bbs_max_messages": "Maximum uložených zpráv (0 = bez omezení)", "bbs_welcome": "Uvítací zpráva (může být i ASCII art; {name}, {bbs}, {new}… se doplní)", "bbs_more": "Další volby (přístup, beacon, jak dlouho držet zprávy) jsou v souboru bbs.toml ve složce BBS:", "bbs_guide": "Návod", "gps_source": "Moje poloha z", "gps_manual": "Zadaná ručně (zeměpisná šířka a délka výše)", "gps_usb": "USB GPS modul (NMEA)", "gps_device": "Port GPS", "gps_auto": "Automaticky", "gps_hint": "Levné USB GPS moduly (u-blox, VK-172…) posílají NMEA rychlostí 9600 nebo 4800 Bd. S fixem používá mapa i maják polohu z GPS (i výšku), bez fixu polohu zadanou výše.", "gps_sats": "{n} sat.", "gps_nofix": "bez fixu", "gps_same_port": "GPS musí být na jiném portu než TNC", "tak": "TAK", "tak_off": "TAK je vypnutý. Po zapnutí se z aplikace stane TAK stanice přes rádio (polohy a GeoChat kompatibilní s ATAK ve formátu TAK Protocol v1): všechno ostatní (APRS, APRS-IS, iGate, maják, zprávy, terminál, chat, BBS) přestane fungovat, dokud ho nevypneš.", "tak_running": "Běží jako {call} · tým {team} · stanic: {n}", "tak_confirm_title": "Zapnout TAK?", "tak_confirm_ask": "Dokud TAK běží, je všechno ostatní v aplikaci vypnuté. Nalaď rádio na kanál domluvený s týmem, nikdy ne na APRS kmitočet 144.800. Radioamatérský provoz: nic se nešifruje. Pro zapnutí napiš:", "tak_confirm_text": "TAK musí mít jinou frekvenci než APRS", "tak_send_position": "Poslat moji polohu", "tak_stations": "Stanice", "tak_no_stations": "Zatím žádné TAK stanice.", "tak_chat": "GeoChat", "tak_everybody": "Všem", "tak_callsign": "Volací znak v TAK (prázdné: tvoje značka)", "tak_team": "Tým (barva)", "tak_role": "Role", "tak_interval": "Posílat moji polohu každých (minut, 0 = jen tlačítkem)", "tak_no_chat": "Zatím žádné zprávy.", "tak_tx_needed": "Zapni Vysílání, jinak TAK nemůže nic poslat.", "map_offline": "Offline mapa (hranice a města, bez internetu)", "net_offline": "Není internet: mapa se přepnula na offline mapu (hranice a města).", "net_online": "Internet je zpět: mapa zase používá OpenStreetMap.", "via_packet": "Packet (AX.25)", "vara_host": "Adresa VARA FM (prázdné = vypnuto)", "vara_port": "Příkazový port (data = +1)", "vara_hint": "VARA FM běží zvlášť (Windows, nebo Wine na Linuxu) s rádiem na zvukové kartě, např. kabelem AIOC; Terminál pak nabídne „Připojení: VARA FM“. Když VARA nepoužíváš, nech adresu prázdnou.", "vara_connecting": "připojuji…", "vara_connected": "připojeno", "vara_disconnecting": "odpojuji…", "vara_idle": "nepřipojeno", "menu": "Nabídka", "back": "Zpět", "last_2h": "Posledních 2 h",
        "via_heard_rf": "rádio", "via_heard_is": "internet",
        "quit_title": "Ukončit APRS & Packet?",
        "quit_text": "Po zavření aplikace se zastaví:",
        "quit_rx": "příjem paketů a zpráv",
        "quit_beacon": "vysílání polohy (maják)",
        "quit_igate": "iGate",
        "quit_sessions": "připojená packet spojení ({n})",
        "quit_yes": "Ukončit", "quit_stay": "Nechat běžet", "quit_minimize": "Minimalizovat",
        "update_available": "Je venku nová verze {version}.", "update_show": "Zobrazit",
        "update_button": "Nová verze {version}", "update_tooltip": "Otevřít stránku ke stažení",
        "update_none": "Máš nejnovější verzi.", "update_never": "Nové verze se ještě nekontrolovaly.",
        "update_failed": "Nové verze se nepodařilo zkontrolovat", "update_checked": "kontrola {when}",
        "update_check_now": "Zkontrolovat teď",
        "check_updates": "Jednou denně zkontrolovat nové verze (dotaz na GitHub, nic o tobě se neposílá)",
        "about": "O aplikaci", "about_version": "Verze {version}",
        "about_what": "APRS stanice a packet radio terminál pro rádio s KISS TNC: mapa slyšených stanic, "
                      "APRS zprávy s potvrzením, terminál pro BBS a nody, packet chat, monitor rámců "
                      "a APRS-IS s volitelnou iGate.",
        "about_radio": "Dělané pro Quansheng UV-K1/UV-K5 V3 s firmwarem F4HWN a jeho aplikací KISS TNC; "
                       "funguje s jakýmkoli KISS TNC (Direwolf, hardwarové TNC, rádio na USB nebo v síti).",
        "about_source": "Zdrojový kód a návod (GitHub)", "about_issues": "Nahlásit chybu nebo nápad",
        "about_releases": "Nové verze", "about_firmware": "Firmware F4HWN pro Quansheng UV-K1/K5 V3",
        "about_kiss_app": "Aplikace KISS TNC pro firmware F4HWN (od F4WAT)",
        "about_ha": "Totéž jako integrace pro Home Assistant",
        "about_author": "Autor",
        "about_contact": "Dotazy a připomínky: GitHub issues nebo přes ok1sim.cz.",
        "about_together": "Napsáno společně s Claude Code (Anthropic).",
        "about_licence": "Licence MIT. Mapová data © přispěvatelé OpenStreetMap. Parsování APRS: aprslib. "
                         "Firmware F4HWN: Armel F4HWN, aplikace KISS TNC: F4WAT.",
        "about_data": "Nastavení a historie",
    },
}


# Code → name in that language, as the language picker lists them.
LANGUAGES: dict[str, str] = {"cs": "Čeština", "en": "English"}
SSID_LABELS: dict[str, list[str]] = {}
EXTRA = ("da", "de", "es", "fr", "hr", "it", "nb", "pl", "pt_BR", "sk", "sl", "sr", "sv", "uk")
for _code in EXTRA:
    _mod = importlib.import_module(f".lang.{_code}", __package__)
    TEXTS[_code] = _mod.TEXTS
    LANGUAGES[_code] = _mod.NAME
    SSID_LABELS[_code] = _mod.SSIDS
LANGUAGES = dict(sorted(LANGUAGES.items(), key=lambda kv: kv[1].casefold()))


def ssid_labels(language: str) -> list[str]:
    from .symbols import SSIDS  # noqa: PLC0415

    return SSIDS.get(language) or SSID_LABELS.get(language) or SSIDS["en"]


# Other names a system locale uses for the same language.
_ALIASES = {"pt": "pt_BR", "no": "nb", "nn": "nb"}


def match_language(value: str) -> str | None:
    """'de_AT.UTF-8' → 'de', 'pt_PT' → 'pt_BR', 'sr_RS@latin' → 'sr'; None when not translated."""
    value = (value or "").split(":")[0].split(".")[0].split("@")[0].replace("-", "_")
    if not value or value in ("C", "POSIX"):
        return None
    if value in TEXTS:
        return value
    base = value.split("_")[0].lower()
    if base in TEXTS:
        return base
    return _ALIASES.get(base)


DEVICE_LANGUAGE: str | None = None  # what the phone / computer says (Flet's device info), set by the app


def system_language() -> str:
    if DEVICE_LANGUAGE:
        return DEVICE_LANGUAGE
    for var in ("LC_ALL", "LC_MESSAGES", "LANG", "LANGUAGE"):
        value = os.environ.get(var, "")
        if value:
            return match_language(value) or "en"
    try:
        lang = locale.getlocale()[0] or ""
    except ValueError:
        lang = ""
    if lang.lower().startswith("czech"):
        return "cs"
    return match_language(lang) or "en"


class Translator:
    def __init__(self, language: str = "") -> None:
        self.language = language if language in TEXTS else system_language()

    def __call__(self, key: str, **kwargs: object) -> str:
        text = TEXTS[self.language].get(key) or TEXTS["en"].get(key) or key
        return text.format(**kwargs) if kwargs else text

    # Messages of the core (English, also in the log) shown in the user's language.
    ERRORS = (
        (r"No USB TNC plugged in.*", "err_usb_none"),
        (r"Could not open (?P<dev>.+)", "err_usb_open"),
        (r"(?P<dev>.+) is in use", "err_usb_busy"),
        (r"Not allowed to use Bluetooth.*", "err_bt_perm"),
        (r"Not allowed to use (?P<dev>.+): allow it when Android asks", "err_usb_perm"),
        (r"Writing to the USB TNC failed", "err_usb_write"),
        (r"This phone has no Bluetooth", "err_bt_none"),
        (r"Bluetooth is off.*", "err_bt_off"),
        (r"No paired Bluetooth device.*", "err_bt_nopaired"),
        (r"The Bluetooth device (?P<dev>.+) is not paired", "err_bt_unpaired"),
        (r"Could not connect to (?P<dev>.+?): (?P<why>.*)", "err_bt_connect"),
        (r"KISS TNC is not connected", "err_not_connected"),
    )

    def error(self, text: str | None) -> str:
        """A core error in this language when it is one we know, else as it is."""
        import re  # noqa: PLC0415

        for pattern, key in self.ERRORS:
            m = re.fullmatch(pattern, (text or "").strip())
            if m and key in TEXTS.get(self.language, {}):
                return self(key, **m.groupdict())
        return text or ""

    def age(self, seconds: float) -> str:
        seconds = max(0, int(seconds))
        if seconds < 60:
            t = f"{seconds} s"
        elif seconds < 3600:
            t = f"{seconds // 60} min"
        elif seconds < 86400:
            t = f"{seconds // 3600} h"
        else:
            t = f"{seconds // 86400} d"
        return self("ago", t=t)

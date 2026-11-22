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
        "conn_serial": "Serial port (USB)", "host": "Host", "port": "Port", "device": "Serial port",
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
        "beacon_is": "Send it regularly over the internet too (APRS-IS)",
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
        "show_internet": "Stations from the internet", "map_muted": "Muted map", "thursday": "APRS Thursday", "th_running": "Running now, ends in {t}", "th_next": "Next one starts {when} (in {t})", "th_member": "You are in the HOTG group until {when}", "th_not_member": "Not in the HOTG group: your first message adds you to it", "th_about": "Every Thursday (UTC) radio amateurs all over the world send a short message to the HOTG group. ANSRVR passes it on to everyone who wrote to the group in the last 12 hours, and sends you theirs.", "th_rf_hint": "By radio, replies reach you only through an iGate that gates internet messages to the radio; over the internet (APRS-IS) it always works.", "th_placeholder": "Your message to the group (e.g. where you are, what rig)", "th_send": "Send to HOTG", "th_leave": "Leave the group", "th_map": "Map and check-ins (aprs.to)", "th_empty": "No HOTG messages yet.", "th_wait": "Next message possible in {t} (one per 30 minutes)", "bbs_saved": "Saved BBS", "bbs_save": "Save this BBS (callsign and path)", "bbs_remove": "Remove from saved", "bbs_saved_as": "{call} saved", "last_2h": "Last 2 hours",
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
        "conn_serial": "Sériový port (USB)", "host": "Adresa", "port": "Port", "device": "Sériový port",
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
        "beacon_is": "Posílat pravidelně i přes internet (APRS-IS)",
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
        "show_internet": "Stanice z internetu", "map_muted": "Tlumená mapa", "thursday": "APRS Thursday", "th_running": "Právě probíhá, končí za {t}", "th_next": "Další začíná {when} (za {t})", "th_member": "Jsi ve skupině HOTG do {when}", "th_not_member": "Nejsi ve skupině HOTG: první zpráva tě do ní přidá", "th_about": "Každý čtvrtek (UTC) posílají radioamatéři z celého světa krátkou zprávu do skupiny HOTG. ANSRVR ji předá všem, kdo do skupiny psali za posledních 12 hodin, a tobě pošle ty jejich.", "th_rf_hint": "Rádiem k tobě odpovědi dojdou jen přes iGate, který posílá zprávy z internetu do rádia; přes internet (APRS-IS) to funguje vždy.", "th_placeholder": "Tvoje zpráva pro skupinu (např. odkud vysíláš, s čím)", "th_send": "Poslat do HOTG", "th_leave": "Odhlásit ze skupiny", "th_map": "Mapa a zapojení (aprs.to)", "th_empty": "Zatím žádné zprávy HOTG.", "th_wait": "Další zprávu můžeš poslat za {t} (jedna za 30 minut)", "bbs_saved": "Uložené BBS", "bbs_save": "Uložit tuto BBS (značku a cestu)", "bbs_remove": "Odebrat z uložených", "bbs_saved_as": "{call} uloženo", "last_2h": "Posledních 2 h",
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


def system_language() -> str:
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

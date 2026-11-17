"""User interface texts in English and Czech."""

from __future__ import annotations

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
        "no_stations": "No stations heard yet.", "filter": "Filter", "only_rf": "Radio only", "last_heard": "heard", "ago": "{t} ago",
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
        "position_hint": "Your position for the beacon and the map, in degrees (e.g. 49.7458 and 13.3772). "
                         "Everyone on aprs.fi will see it.",
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
        "save": "Save", "saved": "Saved; the connection restarts with the new settings.",
        "first_run": "Welcome! Set your callsign and how to reach the TNC, then press Save.",
        "aprsis_state": "APRS-IS", "verified": "logged in", "unverified": "connected, not verified (check the passcode)",
        "invalid": "Invalid setting",
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
        "no_stations": "Zatím žádné slyšené stanice.", "filter": "Filtr", "only_rf": "Jen rádio", "last_heard": "slyšeno", "ago": "před {t}",
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
        "position_hint": "Tvoje poloha pro maják a mapu ve stupních (např. 49.7458 a 13.3772). "
                         "Na aprs.fi ji uvidí každý.",
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
        "save": "Uložit", "saved": "Uloženo; spojení se restartuje s novým nastavením.",
        "first_run": "Vítej! Nastav svou značku a připojení k TNC a klikni na Uložit.",
        "aprsis_state": "APRS-IS", "verified": "přihlášeno", "unverified": "připojeno, neověřeno (zkontroluj passcode)",
        "invalid": "Neplatné nastavení",
    },
}


def system_language() -> str:
    for var in ("LC_ALL", "LC_MESSAGES", "LANG", "LANGUAGE"):
        value = os.environ.get(var, "")
        if value:
            return "cs" if value.lower().startswith(("cs", "sk")) else "en"
    try:
        lang = locale.getlocale()[0] or ""
    except ValueError:
        lang = ""
    return "cs" if lang.lower().startswith(("cs", "sk", "czech")) else "en"


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

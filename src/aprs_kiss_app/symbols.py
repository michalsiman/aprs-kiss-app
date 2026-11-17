"""APRS symbols people use most (table + code) with an emoji to recognise them, and SSID conventions."""

# (symbol, emoji, English, Czech)
SYMBOLS: list[tuple[str, str, str, str]] = [
    ('/-', '🏠', 'House', 'Dům'),
    ('/>', '🚗', 'Car', 'Auto'),
    ('/[', '🚶', 'Person (jogger)', 'Osoba (chodec)'),
    ('/b', '🚲', 'Bicycle', 'Kolo'),
    ('/<', '🏍️', 'Motorcycle', 'Motorka'),
    ('/k', '🛻', 'Pickup truck', 'Pick-up'),
    ('/u', '🚚', 'Truck (18-wheeler)', 'Kamion'),
    ('/v', '🚐', 'Van', 'Dodávka'),
    ('/j', '🚙', 'Jeep', 'Terénní auto'),
    ('/R', '🚌', 'Recreational vehicle', 'Obytný vůz'),
    ('/U', '🚌', 'Bus', 'Autobus'),
    ('/s', '🚤', 'Ship, power boat', 'Loď (motorová)'),
    ('/Y', '⛵', 'Yacht (sail)', 'Plachetnice'),
    ("/'", '✈️', 'Small aircraft', 'Malé letadlo'),
    ('/X', '🚁', 'Helicopter', 'Vrtulník'),
    ('/O', '🎈', 'Balloon', 'Balón'),
    ('/;', '⛺', 'Campground, portable', 'Kemp, portable'),
    ('/y', '📡', 'House with yagi', 'Dům s anténou'),
    ('/r', '🗼', 'Antenna, repeater', 'Anténa, převaděč'),
    ('/#', '🔁', 'Digipeater', 'Digipeater'),
    ('I&', '🌐', 'iGate (RX and TX)', 'iGate (RX i TX)'),
    ('R&', '📥', 'iGate, receive only', 'iGate jen příjem'),
    ('/_', '🌦️', 'Weather station', 'Meteostanice'),
    ('/a', '🚑', 'Ambulance', 'Sanitka'),
    ('/f', '🚒', 'Fire truck', 'Hasiči'),
    ('/+', '➕', 'Red Cross', 'Červený kříž'),
    ('/h', '🏥', 'Hospital', 'Nemocnice'),
    ('/o', '🏢', 'EOC (emergency centre)', 'Krizové centrum'),
    ('/E', '👁️', 'Eyeball (event)', 'Akce, pozorování'),
    ('/$', '☎️', 'Phone', 'Telefon'),
]

_EMOJI = {s: e for s, e, _, _ in SYMBOLS}

# SSID conventions (APRS SSID recommendations by Bob Bruninga, WB4APR).
SSIDS = {
    "en": ["0 – home station, primary", "1 – generic additional station, digi, mobile, wx", "2 – generic additional station", "3 – generic additional station", "4 – generic additional station", "5 – other networks (D-STAR, iPhone, Android…)", "6 – special activity, satellite, camping", "7 – handheld, walkie-talkie", "8 – boat, sailboat, RV, second main mobile", "9 – primary mobile (car)", "10 – internet, iGate, EchoLink, Winlink", "11 – balloon, aircraft, spacecraft", "12 – APRStt, DTMF, one-way tracker", "13 – weather station", "14 – truck", "15 – generic additional station"],
    "cs": ["0 – domácí stanice, hlavní", "1 – další stanice, digi, mobil, meteo", "2 – další stanice", "3 – další stanice", "4 – další stanice", "5 – jiné sítě (D-STAR, iPhone, Android…)", "6 – zvláštní akce, satelit, kempování", "7 – ruční stanice (ručka)", "8 – loď, karavan, druhé auto", "9 – hlavní mobilní (auto)", "10 – internet, iGate, EchoLink, Winlink", "11 – balón, letadlo, kosmická loď", "12 – APRStt, DTMF, jednosměrný tracker", "13 – meteostanice", "14 – nákladní auto", "15 – další stanice"],
}


def emoji(table: str | None, code: str | None) -> str:
    """An emoji for a station's symbol; overlay tables fall back to the alternate table's symbol."""
    if not code:
        return "📍"
    table = table or "/"
    if table not in "/\\":
        return _EMOJI.get(table + code) or _EMOJI.get("\\" + code) or "📍"
    return _EMOJI.get(table + code, "📍")

#!/usr/bin/env python3
"""Screenshots for the README and the blog: the app in a browser (Flet web), driven over Chrome's CDP.

Runs the simulated TNC (tests/fake_tnc.py --scene) and the app as a web server with a prepared data
folder (settings, messages, #APRSThursday), clicks through the screens and saves
assets/<name>.png (English, dark), assets/<name>-light.png, assets/cs/<name>.png, assets/cs/<name>-light.png.

    python3 tools/screenshots.py [name ...]      (all of them without names)

Needs google-chrome and the `websockets` package (in the app's .venv).
"""

from __future__ import annotations

import asyncio
import base64
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

import websockets

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
PY = str(ROOT / ".venv" / "bin" / "python")
TNC_PORT = 8011
APP_PORT = 8770
CDP_PORT = 9340
DESK = (1300, 820, 1)
PHONE = (412, 870, 2.5)


def free(port: int) -> None:
    with socket.socket() as s:
        if s.connect_ex(("127.0.0.1", port)) == 0:
            raise SystemExit(f"port {port} is in use")


def config(lang: str, theme: str, **extra) -> dict:
    now = time.time()
    return {
        "callsign": "OK1SIM-7", "connection": "tcp", "host": "127.0.0.1", "port": TNC_PORT,
        "symbol": "/-", "comment": "APRS & Packet", "latitude": 49.7475, "longitude": 13.3776,
        "language": lang, "language_asked": True, "disclaimer_accepted": True, "theme": theme,
        "gps_source": "manual", "map_trails": True, "map_tools_hidden": False, "check_updates": False,
        "aprsis_radius_km": 50, "tracked_callsigns": "OK1CAR-9", "bbs_sentence_ok": True, "tak_sentence_ok": True,
        "position_ambiguity": 2,  # Settings › Position privacy shows it in use
        "seen_version": "9.9.9",  # no "what is new" after an update over the screens
        "tak_callsign": "OK1SIM", "tak_team": "Cyan", "vara_host": "", "beacon_minutes": 30,
        **extra, "_now": now,
    }


def state(lang: str) -> dict:
    now = time.time()
    cs = lang == "cs"
    msgs = [
        ("in", "DL1ABC-9", "OK1SIM-7", "Gruss aus Bayern, bin morgen in Plzen" if cs else "Greetings from Bavaria, in Plzen tomorrow", 9000),
        ("out", "OK1SIM-7", "DL1ABC-9", "Super, ozvi se na 145.500" if cs else "Great, call me on 145.500", 8800),
        ("in", "REPEAT", "OK1SIM-7", "OK0BP 145.6625 -0.6 88.5 Plzen 12km", 7200),
        ("in", "OK2XYZ-7", "OK1SIM-7", "Díky za spojení, 73!" if cs else "Thanks for the QSO, 73!", 5400),
        ("in", "OK1ABC-9", "OK1SIM-7", "Ahoj, jsem na D5 u Rokycan, slyšíš mě?" if cs else "Hi, I am on the D5 near Rokycany, copy?", 1500),
        ("out", "OK1SIM-7", "OK1ABC-9", "Slyším 5/9, šťastnou cestu!" if cs else "Copy 5/9, safe trip!", 1380),
        ("in", "OK1MNO-7", "OK1SIM-7", "Jsem na Krkavci s OK1LOR-7, výhled je super" if cs else "On top of Krkavec with OK1LOR-7, great view", 600),
        ("out", "OK1SIM-7", "OK1MNO-7", "Pošli fotku :-)" if cs else "Send a photo :-)", 540),
        ("in", "OK1MNO-7", "OK1SIM-7", "Za chvíli, ještě vybaluju anténu" if cs else "In a moment, unpacking the antenna", 420),
        ("in", "OK1ABC-9", "OK1SIM-7", ("Stojím tady: " if cs else "Parked here: ") + "QTH 49.69500, 13.42000", 240),
        ("in", "OK1ABC-9", "OK1SIM-7", "Dáš kafe?" if cs else "Coffee?", 120),
    ]
    th = [
        ("ANSRVR", "You are now joined to HOTG for 12 hours", "server", 3000),
        ("DL1ABC-9", "Happy Thursday from Munich, mobile with FTM-400", "in", 2700),
        ("OK1SIM-7", "Zdravím z Plzně, Quansheng + APRS & Packet" if cs else "Greetings from Plzen, Quansheng + APRS & Packet", "out", 2400),
        ("G4XYZ", "Good evening from Kent, IC-705 portable", "in", 2000),
        ("W1AW-10", "73 from Newington, CT – www.arrl.org", "in", 1500),
    ]
    bulletins = [
        ("OK1KPL-10", "BLN1", "bulletin", "Klubový kroužek dnes ve 20:00 na OK0BPL 439.350 MHz" if cs
         else "Club net tonight at 20:00 on OK0BPL 439.350 MHz", 1500, 4),
        ("OK1WX-13", "BLN2WX", "group", "Výstraha: silný vítr až 70 km/h, dnes 14–22 h" if cs
         else "Alert: strong wind up to 70 km/h, today 14–22 h", 1800, 3),
        ("OK1KPL-10", "BLNA", "announcement", "Setkání radioamatérů Rokycany, sobota 9:00, sokolovna" if cs
         else "Hamfest in Rokycany, Saturday 9:00, Sokol hall", 7600, 6),
        ("OK1DOP-1", "BLN3", "bulletin", "Převáděč OK0BL mimo provoz kvůli údržbě do neděle" if cs
         else "Repeater OK0BL off the air for maintenance until Sunday", 10800, 9),
    ]
    return {
        "msg_counter": 12,
        "messages": [{"direction": d, "from": f, "to": t, "text": x, "time": now - ago, "msg_no": str(i + 1),
                      "via": "radio", **({"km": 6.2, "bearing": 150} if d == "in" else {})}
                     for i, (d, f, t, x, ago) in enumerate(msgs)],
        "thursday": [{"time": now - ago, "from": f, "text": x, "kind": k, "via": "internet"} for f, x, k, ago in th],
        "thursday_joined": now - 2400, "thursday_cq": now - 2400,
        "bulletins": {"heard": [
            {"from": f, "addressee": a, "kind": k, "line": a[3], "group": a[4:], "text": x, "time": now - ago,
             "last": now - ago + 60, "count": n, "via": "radio", "read": ago > 2000}
            for f, a, k, x, ago, n in bulletins],
            "mine": [{"addressee": "BLN4", "kind": "bulletin", "via": "both", "created": now - 2400,
                      "until": now - 2400 + 4 * 3600, "sent": 5, "next": now + 480, "last_sent": now - 720,
                      "text": "Packet BBS OK1SIM-1 na 144.875, přijímá zprávy" if cs
                      else "Packet BBS OK1SIM-1 on 144.875, takes messages"}]},
    }


class Browser:
    def __init__(self, size):
        self.w, self.h, self.scale = size

    async def __aenter__(self):
        self.dir = tempfile.mkdtemp(prefix="shots-chrome-")
        self.proc = subprocess.Popen(["google-chrome", "--headless=new", "--disable-gpu", f"--remote-debugging-port={CDP_PORT}",
                                      f"--user-data-dir={self.dir}", "--hide-scrollbars", f"--window-size={self.w},{self.h}",
                                      "about:blank"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(100):
            try:
                tabs = json.load(urllib.request.urlopen(f"http://127.0.0.1:{CDP_PORT}/json"))
                break
            except OSError:
                await asyncio.sleep(0.1)
        url = next(t["webSocketDebuggerUrl"] for t in tabs if t["type"] == "page")
        self.ws = await websockets.connect(url, max_size=100_000_000)
        self.n = 0
        await self.call("Emulation.setDeviceMetricsOverride", width=self.w, height=self.h,
                        deviceScaleFactor=self.scale, mobile=self.w < 600)
        return self

    async def __aexit__(self, *exc):
        await self.ws.close()
        self.proc.terminate()
        self.proc.wait()
        shutil.rmtree(self.dir, ignore_errors=True)

    async def call(self, method, **params):
        self.n += 1
        my = self.n
        await self.ws.send(json.dumps({"id": my, "method": method, "params": params}))
        while True:
            msg = json.loads(await self.ws.recv())
            if msg.get("id") == my:
                return msg.get("result", {})

    async def wait(self, seconds):
        await asyncio.sleep(seconds)

    async def click(self, x, y, pause=1.2):
        for kind in ("mouseMoved", "mousePressed", "mouseReleased"):
            await self.call("Input.dispatchMouseEvent", type=kind, x=x, y=y, button="left", clickCount=1)
        await asyncio.sleep(pause)

    async def type(self, text, pause=0.6):
        await self.call("Input.insertText", text=text)
        await asyncio.sleep(pause)

    async def key(self, key="Enter", pause=1.0):
        code = {"Enter": 13, "Escape": 27, "Tab": 9}[key]
        for kind in ("keyDown", "keyUp"):
            await self.call("Input.dispatchKeyEvent", type=kind, key=key, code=key, windowsVirtualKeyCode=code,
                            nativeVirtualKeyCode=code, text="\r" if key == "Enter" and kind == "keyDown" else "")
        await asyncio.sleep(pause)

    async def scroll(self, x, y, dy, pause=1.0):
        await self.call("Input.dispatchMouseEvent", type="mouseWheel", x=x, y=y, deltaX=0, deltaY=dy)
        await asyncio.sleep(pause)

    async def shot(self, path: Path):
        data = await self.call("Page.captureScreenshot", format="png")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(base64.b64decode(data["data"]))
        print("  saved", path)


class Run:
    """The fake TNC and the app (web) with prepared settings, for one language, theme and screen."""

    def __init__(self, lang, theme, phone=False, tak=False, send_file=0, usb=False, unread=None, **conf):
        self.lang, self.theme, self.phone, self.tak, self.conf = lang, theme, phone, tak, conf
        self.usb, self.unread = usb, unread or {}
        self.send_file = send_file

    async def __aenter__(self):
        free(TNC_PORT)
        free(APP_PORT)
        self.data = Path(tempfile.mkdtemp(prefix="aprs-kiss-"))
        c = config(self.lang, self.theme, **self.conf)
        c.pop("_now")
        (self.data / "config.json").write_text(json.dumps(c))
        (self.data / "state.json").write_text(json.dumps(state(self.lang)))
        # unread conversations, with how many messages each: the counts on the circles, filters and menu
        (self.data / "unread.json").write_text(json.dumps({"OK1ABC-9": 2, "OK1MNO-7": 1, "OK2XYZ-7": 1,
                                                           **self.unread}))
        env = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
        self.tnc = subprocess.Popen([PY, str(ROOT / "tests" / "fake_tnc.py"), "--port", str(TNC_PORT), "--scene",
                                     "--interval", "6", "--message-every", "0", *(["--tak"] if self.tak else []),
                                     *(["--send-file", str(self.send_file)] if self.send_file else [])],
                                    env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        app_env = {**env, "APRS_KISS_DATA": str(self.data), "FLET_FORCE_WEB_SERVER": "true"}
        if self.phone:
            app_env["APRS_KISS_PHONE"] = "1"
        if self.usb:  # the phone's TNC choices: USB and Bluetooth too
            app_env["APRS_KISS_USB"] = "1"
        self.app = subprocess.Popen([PY, "-c", "import flet as ft; from aprs_kiss_app.app import main; "
                                     f"ft.run(main, port={APP_PORT}, view=ft.AppView.WEB_BROWSER, assets_dir={str(ROOT / 'src' / 'assets')!r})"],
                                    env=app_env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(100):
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{APP_PORT}/")
                break
            except OSError:
                await asyncio.sleep(0.2)
        self.browser = Browser(PHONE if self.phone else DESK)
        b = await self.browser.__aenter__()
        await b.call("Page.navigate", url=f"http://127.0.0.1:{APP_PORT}/")
        await b.wait(14)
        return b

    async def __aexit__(self, *exc):
        await self.browser.__aexit__(*exc)
        for p in (self.app, self.tnc):
            p.terminate()
            p.wait()
        shutil.rmtree(self.data, ignore_errors=True)


def out(name, lang, theme) -> Path:
    folder = ASSETS / "cs" if lang == "cs" else ASSETS
    return folder / f"{name}{'-light' if theme == 'light' else ''}.png"


# ─── what to photograph (desktop 1300×820) ────────────────────────────────

# the rail has a gap above each section (packet radio, settings)
RAIL = {"map": 35, "messages": 100, "bulletins": 165, "thursday": 228, "stations": 292, "terminal": 370,
        "chat": 434, "files": 498, "monitor": 562, "bbs": 626, "tak": 690, "settings": 768}
SECTION = {"tnc": 92, "station": 154, "privacy": 219, "gps": 283, "tracker": 347, "digi": 411, "aprsis": 475,
           "vara": 540, "tak": 604, "bbs": 668, "maps": 732, "background": 796, "sounds": 860}


async def desktop(lang, theme, only):
    want = lambda name: not only or name in only  # noqa: E731
    cs = lang == "cs"
    async with Run(lang, theme, bbs_sentence_ok=False) as b:
        await b.wait(4)
        if want("map"):
            await b.shot(out("map", lang, theme))
        if want("map-filter") or want("map-repeaters"):
            await b.click(295, 80)
            await b.click(400, 140, 1.5)  # moving only: ticked, the menu stays open
            if want("map-filter"):
                await b.shot(out("map-filter", lang, theme))
            await b.click(400, 140, 1)  # moving off again
            await b.click(400, 188, 4)  # repeaters only
            await b.key("Escape", 2)
            if want("map-repeaters"):
                await b.shot(out("map-repeaters", lang, theme))
            await b.click(295, 80)
            await b.click(400, 300, 3)  # show all
            await b.key("Escape", 2)
        if want("map-source") or want("map-offline"):
            await b.click(376, 80)
            await b.click(460, 265, 3)  # the basic offline map: chosen, the menu stays open over it
            if want("map-source"):
                await b.shot(out("map-source", lang, theme))
            await b.key("Escape", 2)
            if want("map-offline"):
                await b.shot(out("map-offline", lang, theme))
            await b.click(376, 80)
            await b.click(460, 88, 2)  # online again
            await b.key("Escape", 2)
        if want("tracker-menu"):
            await b.click(1154, 26, 2)
            await b.shot(out("tracker-menu", lang, theme))
            await b.key("Escape", 2)
        await b.click(1210, 26, 5)  # transmit on (the message bar goes away)
        if want("messages"):
            await b.click(52, RAIL["messages"], 2)
            await b.click(250, 192, 2)  # OK1ABC-9: the newest, with a position in its message
            await b.shot(out("messages", lang, theme))
        if want("messages-unread"):
            await b.click(52, RAIL["messages"], 2)
            await b.click(240, 132, 2)  # Unread: only the conversations with unread messages, their counts
            await b.shot(out("messages-unread", lang, theme))
            await b.click(150, 132, 2)  # All again
        if want("bulletins") or want("bulletin-new"):
            await b.click(52, RAIL["bulletins"], 2)
            if want("bulletins"):
                await b.shot(out("bulletins", lang, theme))
            if want("bulletin-new"):
                await b.click(1180, 795, 2)  # New bulletin
                await b.type("Dnes 19:00 test APRS & Packet na 144.800, hlaste se" if cs
                             else "Tonight 19:00 APRS & Packet test on 144.800, check in", 1.5)
                await b.shot(out("bulletin-new", lang, theme))
                await b.key("Escape", 2)
        if want("thursday"):
            await b.click(52, RAIL["thursday"], 2)
            await b.shot(out("thursday", lang, theme))
        if want("stations") or want("station"):
            await b.click(52, RAIL["stations"], 2)
            if want("stations"):
                await b.shot(out("stations", lang, theme))
            if want("station"):
                await b.click(400, 140, 2.5)  # the first station's details: map, message, QRZ.com
                await b.shot(out("station", lang, theme))
                await b.key("Escape", 2)
        if want("terminal"):
            await b.click(52, RAIL["terminal"], 2)
            await b.click(200, 141)
            await b.type("OK0BBS")
            await b.click(478, 88, 6)  # connect
            await b.click(300, 785)
            await b.type("L")
            await b.key("Enter", 4)
            await b.shot(out("terminal", lang, theme))
        if want("chat"):
            await b.click(52, RAIL["chat"], 2)
            await b.click(500, 785)
            await b.type("Ahoj, je dnes večer někdo na packetu?" if cs else "Hello, anyone on packet tonight?")
            await b.key("Enter", 5)
            await b.shot(out("chat", lang, theme))
        if want("monitor"):
            await b.click(52, RAIL["monitor"], 2)
            await b.shot(out("monitor", lang, theme))
        if want("settings") or want("settings-tracker") or want("settings-more") or want("settings-privacy"):
            await b.click(52, RAIL["settings"], 2)
            if want("settings"):
                await b.click(700, SECTION["station"], 2)
                await b.shot(out("settings", lang, theme))
                await b.click(700, SECTION["station"], 2)
            if want("settings-privacy"):
                await b.click(700, SECTION["privacy"], 2)
                await b.shot(out("settings-privacy", lang, theme))
                await b.click(700, SECTION["privacy"], 2)
            if want("settings-tracker"):
                await b.click(700, SECTION["tracker"], 2)
                await b.shot(out("settings-tracker", lang, theme))
                await b.click(700, SECTION["tracker"], 2)
            if want("settings-more"):
                await b.click(700, SECTION["background"], 2)
                await b.scroll(700, 500, 900, 2)
                await b.click(700, 614, 2)  # sounds, now on screen
                await b.shot(out("settings-more", lang, theme))
        if want("bbs-confirm"):
            await b.click(52, RAIL["bbs"], 2)
            await b.click(190, 96, 2)
            await b.shot(out("bbs-confirm", lang, theme))
    if want("settings-tnc"):
        # a radio with a built-in KISS TNC over Bluetooth LE: the device and its frequency
        async with Run(lang, theme, connection="ble") as b:
            await b.click(52, RAIL["settings"], 2)
            await b.click(700, SECTION["tnc"], 2)
            await b.shot(out("settings-tnc", lang, theme))
    if want("bbs"):
        async with Run(lang, theme, bbs_enabled=True) as b:
            await b.click(52, RAIL["bbs"], 3)
            await b.shot(out("bbs", lang, theme))
    if want("files") or want("files-offer"):
        async with Run(lang, theme, send_file=20, files_accept=True) as b:
            await b.click(1210, 26, 3)  # transmit on: the link needs our acknowledgements
            await b.click(52, RAIL["files"], 3)
            await b.wait(12)  # OK1XYZ connects and offers a picture
            if want("files-offer"):
                await b.shot(out("files-offer", lang, theme))
            await b.click(777, 457, 25)  # accept, and let a part of it come in
            if want("files"):
                await b.shot(out("files", lang, theme))
    if want("tak"):
        async with Run(lang, theme, tak=True, tak_enabled=True) as b:
            await b.wait(25)  # the team reports in
            await b.click(52, RAIL["tak"], 4)
            await b.shot(out("tak", lang, theme))


# ─── the phone (412×870 css px) ────────────────────────────────────────────

# the menu has headings (APRS, Packet radio) and a line above the settings
DRAWER = {"messages": 186, "bulletins": 234, "thursday": 282, "stations": 330, "terminal": 418, "chat": 466,
          "files": 514, "monitor": 562, "tak": 610, "settings": 675}


async def phone(lang, theme, only):
    want = lambda name: not only or name in only  # noqa: E731
    if any(want(n) for n in ("phone-map", "phone-menu", "phone-filter", "phone-profiles", "phone-settings",
                             "phone-messages", "phone-bulletins")):
        profiles = json.dumps([{"ssid": 7, "symbol": "/["}, {"ssid": 9, "symbol": "/>"}, {"ssid": 0, "symbol": "/-"}])
        async with Run(lang, theme, phone=True, profiles=profiles, symbol="/[") as b:
            await b.wait(4)
            if want("phone-map"):
                await b.shot(out("phone-map", lang, theme))
            if want("phone-filter"):
                await b.click(190, 72, 1)
                await b.click(150, 130, 2)  # weather stations only: the box ticked, the menu open
                await b.shot(out("phone-filter", lang, theme))
                await b.key("Escape", 2)
            if want("phone-profiles"):
                await b.click(80, 32, 2)
                await b.shot(out("phone-profiles", lang, theme))
                await b.key("Escape", 2)
            if want("phone-menu"):
                await b.click(24, 32, 2)
                await b.shot(out("phone-menu", lang, theme))
                await b.key("Escape", 2)
            if want("phone-messages"):
                await b.click(24, 32, 2)
                await b.click(100, DRAWER["messages"], 3)
                await b.shot(out("phone-messages", lang, theme))
            if want("phone-bulletins"):
                await b.click(24, 32, 2)
                await b.click(100, DRAWER["bulletins"], 3)
                await b.shot(out("phone-bulletins", lang, theme))
            if want("phone-settings"):
                await b.click(24, 32, 2)
                await b.click(100, DRAWER["settings"], 3)
                await b.click(200, 333, 3)  # the tracker section
                await b.shot(out("phone-settings", lang, theme))
    if want("phone-tnc"):
        # every way to a TNC on a phone: TCP/IP, USB (serial), Bluetooth and Bluetooth LE
        async with Run(lang, theme, phone=True, usb=True, connection="ble") as b:
            await b.click(24, 32, 2)
            await b.click(100, DRAWER["settings"], 3)
            await b.click(200, 76, 3)  # the TNC section
            await b.click(150, 140, 2)  # the connection list, open
            await b.shot(out("phone-tnc", lang, theme))
    if want("phone-tak") or want("phone-tak-chat"):
        async with Run(lang, theme, phone=True, tak=True, tak_enabled=True) as b:
            await b.wait(25)
            if want("phone-tak"):
                await b.shot(out("phone-tak", lang, theme))
            if want("phone-tak-chat"):
                await b.click(73, 68, 3)  # the GeoChat tab
                await b.call("Input.dispatchMouseEvent", type="mouseMoved", x=200, y=820)  # no tooltip
                await b.wait(2)
                await b.shot(out("phone-tak-chat", lang, theme))


async def main(only):
    for lang in ("cs", "en"):
        for theme in ("dark", "light"):
            print(lang, theme)
            await desktop(lang, theme, only)
            await phone(lang, theme, only)


if __name__ == "__main__":
    asyncio.run(main(set(sys.argv[1:])))

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
        "tak_callsign": "OK1SIM", "tak_team": "Cyan", "vara_host": "", "beacon_minutes": 30,
        **extra, "_now": now,
    }


def state(lang: str) -> dict:
    now = time.time()
    cs = lang == "cs"
    msgs = [
        ("in", "OK1ABC-9", "OK1SIM-7", "Ahoj, jsem na D5 u Rokycan, slyšíš mě?" if cs else "Hi, I am on the D5 near Rokycany, copy?", 1500),
        ("out", "OK1SIM-7", "OK1ABC-9", "Slyším 5/9, šťastnou cestu!" if cs else "Copy 5/9, safe trip!", 1380),
        ("in", "OK1MNO-7", "OK1SIM-7", "Jsem na Krkavci, výhled je super" if cs else "On top of Krkavec, great view", 600),
        ("in", "OK1ABC-9", "OK1SIM-7", ("Stojím tady: " if cs else "Parked here: ") + "QTH 49.69500, 13.42000", 240),
        ("out", "OK1SIM-7", "OK1MNO-7", "Pošli fotku :-)" if cs else "Send a photo :-)", 540),
    ]
    th = [
        ("ANSRVR", "You are now joined to HOTG for 12 hours", "server", 3000),
        ("DL1ABC-9", "Happy Thursday from Munich, mobile with FTM-400", "in", 2700),
        ("OK1SIM-7", "Zdravím z Plzně, Quansheng + APRS & Packet" if cs else "Greetings from Plzen, Quansheng + APRS & Packet", "out", 2400),
        ("G4XYZ", "Good evening from Kent, IC-705 portable", "in", 2000),
        ("W1AW-10", "73 from Newington, CT", "in", 1500),
    ]
    return {
        "msg_counter": 12,
        "messages": [{"direction": d, "from": f, "to": t, "text": x, "time": now - ago, "msg_no": str(i + 1),
                      "via": "radio", **({"km": 6.2, "bearing": 150} if d == "in" else {})}
                     for i, (d, f, t, x, ago) in enumerate(msgs)],
        "thursday": [{"time": now - ago, "from": f, "text": x, "kind": k, "via": "internet"} for f, x, k, ago in th],
        "thursday_joined": now - 2400, "thursday_cq": now - 2400,
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

    def __init__(self, lang, theme, phone=False, tak=False, send_file=0, **conf):
        self.lang, self.theme, self.phone, self.tak, self.conf = lang, theme, phone, tak, conf
        self.send_file = send_file

    async def __aenter__(self):
        free(TNC_PORT)
        free(APP_PORT)
        self.data = Path(tempfile.mkdtemp(prefix="aprs-kiss-"))
        c = config(self.lang, self.theme, **self.conf)
        c.pop("_now")
        (self.data / "config.json").write_text(json.dumps(c))
        (self.data / "state.json").write_text(json.dumps(state(self.lang)))
        env = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
        self.tnc = subprocess.Popen([PY, str(ROOT / "tests" / "fake_tnc.py"), "--port", str(TNC_PORT), "--scene",
                                     "--interval", "6", "--message-every", "0", *(["--tak"] if self.tak else []),
                                     *(["--send-file", str(self.send_file)] if self.send_file else [])],
                                    env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        app_env = {**env, "APRS_KISS_DATA": str(self.data), "FLET_FORCE_WEB_SERVER": "true"}
        if self.phone:
            app_env["APRS_KISS_PHONE"] = "1"
        self.app = subprocess.Popen([PY, "-c", "import flet as ft; from aprs_kiss_app.app import main; "
                                     f"ft.run(main, port={APP_PORT}, view=ft.AppView.WEB_BROWSER)"],
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

RAIL = {"map": 35, "messages": 100, "thursday": 165, "stations": 228, "terminal": 292, "chat": 356,
        "files": 420, "monitor": 484, "bbs": 548, "tak": 612, "settings": 676}
SECTION = {"tnc": 92, "station": 154, "gps": 219, "tracker": 283, "digi": 347, "aprsis": 411, "vara": 475,
           "tak": 540, "bbs": 604, "maps": 668, "background": 732, "sounds": 796}


async def desktop(lang, theme, only):
    want = lambda name: not only or name in only  # noqa: E731
    cs = lang == "cs"
    async with Run(lang, theme, bbs_sentence_ok=False) as b:
        await b.wait(4)
        if want("map"):
            await b.shot(out("map", lang, theme))
        if want("map-filter") or want("map-repeaters"):
            await b.click(307, 92)
            if want("map-filter"):
                await b.shot(out("map-filter", lang, theme))
            await b.click(420, 200, 4)  # repeaters only
            if want("map-repeaters"):
                await b.shot(out("map-repeaters", lang, theme))
            await b.click(307, 92)
            await b.click(420, 310, 4)  # show all
        if want("map-offline"):
            await b.click(387, 92)
            await b.click(494, 208, 3)  # the basic offline map
            await b.shot(out("map-offline", lang, theme))
            await b.click(387, 92)
            await b.click(494, 96, 2)  # online again
        await b.click(1210, 26, 5)  # transmit on (the message bar goes away)
        if want("messages"):
            await b.click(52, RAIL["messages"], 2)
            await b.click(170, 133, 2)  # OK1ABC-9: the newest, with a position in its message
            await b.shot(out("messages", lang, theme))
        if want("thursday"):
            await b.click(52, RAIL["thursday"], 2)
            await b.shot(out("thursday", lang, theme))
        if want("stations"):
            await b.click(52, RAIL["stations"], 2)
            await b.shot(out("stations", lang, theme))
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
        if want("settings") or want("settings-tracker") or want("settings-more"):
            await b.click(52, RAIL["settings"], 2)
            if want("settings"):
                await b.click(700, SECTION["station"], 2)
                await b.shot(out("settings", lang, theme))
                await b.click(700, SECTION["station"], 2)
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

DRAWER = {"messages": 139, "thursday": 195, "stations": 251, "terminal": 307, "chat": 363, "files": 419,
          "monitor": 475, "tak": 530, "settings": 587}


async def phone(lang, theme, only):
    want = lambda name: not only or name in only  # noqa: E731
    if any(want(n) for n in ("phone-map", "phone-menu", "phone-filter", "phone-profiles", "phone-settings")):
        profiles = json.dumps([{"ssid": 7, "symbol": "/["}, {"ssid": 9, "symbol": "/>"}, {"ssid": 0, "symbol": "/-"}])
        async with Run(lang, theme, phone=True, profiles=profiles, symbol="/[") as b:
            await b.wait(4)
            if want("phone-map"):
                await b.shot(out("phone-map", lang, theme))
            if want("phone-filter"):
                await b.click(196, 78, 2)
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
            if want("phone-settings"):
                await b.click(24, 32, 2)
                await b.click(100, DRAWER["settings"], 3)
                await b.click(200, 268, 3)  # the tracker section
                await b.shot(out("phone-settings", lang, theme))
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

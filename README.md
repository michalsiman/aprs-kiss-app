# APRS & Packet – standalone app

An APRS station and packet radio terminal for a radio with a **KISS TNC**, as a normal desktop
application – no Home Assistant, no web server. It is the standalone sibling of the
[APRS & Packet Home Assistant integration](https://github.com/michalsiman/aprs-kiss-ha) and shares
its radio core.

Made for the Quansheng UV-K1/UV-K5 V3 with the F4HWN firmware, but any KISS TNC works
(Direwolf, a hardware TNC, the radio's USB serial port, or the KISS TCP bridge from the integration).

**Status: 0.1.0, Linux first.** The same code is meant to be built for Windows, macOS, Android
and iOS later (see [Platforms](#platforms)).

## What it does

- **Map** of heard stations (OpenStreetMap), your own position, tracked callsigns highlighted
- **APRS messages** as conversations, retried until acknowledged, delivery state shown;
  incoming messages acknowledged automatically
- **Stations** heard on the radio or seen on APRS-IS: distance, direction, comment, weather
- **Packet terminal**: AX.25 connected mode to BBSes and nodes, optional incoming connections
- **Packet chat** (plain text to CQ) and a TNC-style **frame monitor**
- **APRS-IS** (internet) with optional RX and TX iGate
- Position beacon, status, unproto
- English and Czech

> **Transmitting is off by default.** Switch *Transmit* on in the top bar only if you hold an amateur
> radio licence. APRS-IS can be switched on only after typing the licence statement.

## Install and run (Linux)

Python 3.10 or newer.

```bash
pipx install "aprs-kiss[desktop] @ git+https://github.com/michalsiman/aprs-kiss-app"
aprs-kiss
```

Or from a checkout:

```bash
git clone https://github.com/michalsiman/aprs-kiss-app && cd aprs-kiss-app
python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"
.venv/bin/flet run src/main.py      # or: .venv/bin/aprs-kiss
```

The first start opens **Settings**: set your callsign, your position and how to reach the TNC:

- **KISS over TCP** – Direwolf (port 8001), or the radio shared on the network with
  [`kiss_tcp_bridge.py`](https://github.com/michalsiman/aprs-kiss-ha/tree/main/bridge)
- **Serial port** – the radio plugged into this computer; pick it from the list
  (`/dev/serial/by-id/...` names stay the same after replugging). Your user needs to be in the
  `dialout` group: `sudo usermod -aG dialout $USER`, then log in again.

Settings and message history live in `~/.local/share/aprs-kiss/` (`APRS_KISS_DATA` overrides it).

### Trying it without a radio

```bash
.venv/bin/python tests/fake_tnc.py --port 8001 --mycall OK1SIM-7
```

A simulated TNC: stations, a weather report and messages arrive every few seconds, it acknowledges
your messages, answers chat and runs a small BBS (`OK0BBS`: H, L, B). Point the app at
`127.0.0.1:8001`.

### A packaged build

`flet build linux` makes a self-contained bundle (no Python needed on the target). The
*Build Linux app* GitHub workflow does it and attaches a `.tar.gz` to each `v*` release.

## How it is built

```
src/
  aprs_kiss_core/   the radio, no user interface: KISS, AX.25 (UI + connected mode), APRS,
                    APRS-IS/iGate, the station (acks, retries, limits) and the Engine that
                    ties it together and announces events to listeners
  aprs_kiss_app/    the Flet user interface: one view per screen
  main.py           entry point for `flet run` / `flet build`
tests/              unit tests, engine tests against fake_tnc.py
```

- **Flet** (Python, drawn by Flutter): one code base for desktop and mobile, a native window,
  no web server.
- **Transports are pluggable** (`aprs_kiss_core.connection.register_transport`): TCP and
  serial are built in; Android USB host and Bluetooth TNCs will be added as their own transports
  without touching the KISS/AX.25 code.
- The core modules are the same as in the Home Assistant integration (`hub.py` there,
  `engine.py` here). The plan is to publish the core as one package both use.

## Platforms

| | Linux | Windows | macOS | Android | iOS |
|---|---|---|---|---|---|
| KISS over TCP | ✅ | planned | planned | planned | planned |
| USB serial | ✅ | planned (COM ports) | planned | needs a USB-host transport | ❌ (iOS) |
| Bluetooth TNC | – | – | – | planned | BLE only |
| Running in the background | ✅ | ✅ | ✅ | needs a foreground service | limited by iOS |

## Tests

```bash
.venv/bin/python -m unittest discover -s tests -t .
```

## Licence

MIT. Map data © OpenStreetMap contributors.

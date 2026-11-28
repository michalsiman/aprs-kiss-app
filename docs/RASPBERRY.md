# APRS & Packet on a Raspberry Pi

A Raspberry Pi next to the radio as a station of its own: iGate, digipeater, beacon, messages, packet. It starts
when powered, comes back after a power cut and shows the whole app on a touch screen. It can be set up from a
phone or a computer in a browser too.

**It takes about half an hour, mostly waiting.**

## What you need

- **A Raspberry Pi 3B, 3B+, 4 or 5** and its power supply (Pi 4: USB-C 5 V / 3 A, Pi 3: micro-USB 5 V / 2.5 A).
- **A microSD card**, 16 GB or more.
- **A TNC**: a KISS TNC on USB (a radio with KISS over USB, NinoTNC, Mobilinkd…), a network KISS TNC, or a sound
  card / an AIOC or DigiRig cable with Direwolf.
- **A screen (optional)**: a 5" HDMI touch display (800×480), the official 7" Raspberry Pi display or any
  monitor. Without one it works too – then only over the web.

## 1. Prepare the card

1. Install **Raspberry Pi Imager** on your computer: [raspberrypi.com/software](https://www.raspberrypi.com/software/).
2. Choose the **device** (your Pi), the **operating system**:
   - with a screen: **Raspberry Pi OS (64-bit)** – with the desktop,
   - without one: **Raspberry Pi OS Lite (64-bit)**,

   and the **card**. Click *Next*, and *Edit settings* when asked about customisation:
   - **Hostname**: `aprs` (the Pi is then `aprs.local` in the network),
   - **a username and password** (e.g. `pi` and a password of your own),
   - **Wi-Fi**: the network's name, password and country (not needed with a network cable),
   - on the **Services** tab enable **SSH** (password login).
3. Save, confirm writing and wait for Imager to finish.

## 2. Connect and power on

Put the card in the Pi, connect the screen (a 5" HDMI display sits on the GPIO pins and takes the HDMI
connector from its box), the TNC to USB and the power last. The first start takes a few minutes (the Pi
grows its partition and restarts once).

## 3. Log in to the Pi

From a computer in the same network open a terminal (Windows: *PowerShell*, macOS and Linux: *Terminal*):

```bash
ssh pi@aprs.local
```

(`pi` is your username.) Answer `yes` about the key fingerprint and type the password. With a keyboard and a
screen on the Pi you can open its *Terminal* instead.

## 4. Install the app – one command

Pick the line for your screen and paste it in the terminal:

| Screen | Command |
|---|---|
| 5" HDMI with a stylus touch (Waveshare and clones, 800×480) | `curl -fsSL https://aprs.ok1sim.cz/pi.sh \| bash -s -- --touch-5inch` |
| official 7", another touch screen or a plain monitor | `curl -fsSL https://aprs.ok1sim.cz/pi.sh \| bash` |
| no screen (Raspberry Pi OS Lite) | `curl -fsSL https://aprs.ok1sim.cz/pi.sh \| bash -s -- --no-display` |

The script installs what is needed and at the end asks for a **web password** – set one, the web can
transmit. About 5 minutes on a Pi 4, up to 15 on a Pi 3. Then restart the Pi:

```bash
sudo reboot
```

## 5. Set up the station

On a phone or a computer in the same network open **http://aprs.local:8080** (or the address the install
printed), log in and fill in **Settings**:

- **TNC connection**: a TNC on USB is *Serial port (USB)* `/dev/ttyACM0` or `/dev/ttyUSB0`; a network TNC *KISS over
  TCP (network)*; a sound card *Sound-card modem (Direwolf)*.
- **Station**: the callsign with its SSID, position, comment, beacon.
- **APRS-IS** (iGate), **Digipeater** as you need.
- **Station telemetry**: packet counts (heard, digipeated, gated) and the farthest station heard as graphs on
  aprs.fi – *Internet* is enough.

Save and switch **TX** on in the top bar. The same works on the Pi's touch screen (the ☰ menu at the top
left). The Pi remembers transmitting over a restart.

Done. From now on the Pi starts by itself – the station, the screen and the web.

## Updating

Run the install command from step 4 again. Settings, messages and the password stay.

## When something does not work

- **The screen stays black or shows only the desktop**: give it 1–2 minutes after starting. `systemctl status
  aprs-kiss` shows the service, `journalctl -u aprs-kiss -f` its log.
- **Touch does nothing or lands elsewhere**: installed with `--touch-5inch`? In `/boot/firmware/config.txt`, on
  the line `dtoverlay=ads7846,…`, change `swapxy=0` to `swapxy=1` (axes swapped) or swap the `xmin` and `xmax`
  values (an axis reversed) and restart.
- **`aprs.local` does not open**: use the Pi's IP address – the install prints it, so does your router or
  `hostname -I`.
- **The USB TNC is not there**: `ls /dev/ttyACM* /dev/ttyUSB*` shows whether the Pi sees it. The port needs
  the user in the `dialout` group – the script adds it, it applies after a restart.
- **Port 8080 is taken**: install with `--port 8081` (and open `http://aprs.local:8081`).
- **Forgotten web password**:
  `/opt/aprs-kiss/venv/bin/aprs-kiss-server --set-password && sudo systemctl restart aprs-kiss`
- **Only a dashboard on the screen** instead of the app (lamps, counters, last frames): install with
  `--dashboard`.

## Uninstalling

```bash
sudo systemctl disable --now aprs-kiss
sudo rm -rf /opt/aprs-kiss /etc/systemd/system/aprs-kiss.service
rm -f ~/.config/autostart/aprs-kiss-display.desktop
sed -i '/aprs-kiss/d' ~/.config/labwc/autostart
```

Settings and messages are in `~/.local/share/aprs-kiss` – delete them if you no longer want them.

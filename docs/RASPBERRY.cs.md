# APRS & Packet na Raspberry Pi

Raspberry Pi vedle rádia jako samostatná APRS stanice: iGate, digipeater, maják, zprávy, packet. Běží samo od
zapnutí, po výpadku proudu naběhne znovu a na dotykovém displeji ukazuje celou aplikaci. Nastavovat se dá
i z telefonu nebo počítače přes prohlížeč.

**Celé to zabere asi půl hodiny, většinou čekáním.**

## Co potřebuješ

- **Raspberry Pi 3B, 3B+, 4 nebo 5** a jeho zdroj (Pi 4: USB-C 5 V / 3 A, Pi 3: micro-USB 5 V / 2,5 A).
- **microSD kartu** 16 GB nebo větší.
- **TNC**: KISS TNC na USB (rádio s KISS přes USB, NinoTNC, Mobilinkd…), síťové KISS TNC, nebo zvukovou
  kartu / kabel AIOC či DigiRig s Direwolfem.
- **Displej (nepovinně)**: 5" HDMI dotykový 800×480, oficiální 7" displej Raspberry Pi nebo jakýkoli monitor.
  Bez displeje to jde také – ovládá se pak jen přes web.

## 1. Připrav kartu

1. Do počítače nainstaluj **Raspberry Pi Imager** z [raspberrypi.com/software](https://www.raspberrypi.com/software/).
2. Vyber **zařízení** (tvoje Pi), **operační systém**:
   - s displejem: **Raspberry Pi OS (64-bit)** – s plochou,
   - bez displeje: **Raspberry Pi OS Lite (64-bit)**,

   a **kartu**. Klikni na *Další* a na otázku o úpravě nastavení *Upravit nastavení*:
   - **Hostname**: `aprs` (pak bude Pi v síti jako `aprs.local`),
   - **uživatelské jméno a heslo** (třeba `pi` a vlastní heslo),
   - **Wi-Fi**: název sítě, heslo a země **CZ** (s kabelem do sítě není potřeba),
   - na kartě **Služby** zapni **SSH** (přihlášení heslem).
3. Ulož, potvrď zápis a počkej, až Imager skončí.

## 2. Zapoj a zapni

Kartu dej do Pi, připoj displej (5" HDMI displej se nasadí na piny GPIO a propojí HDMI spojkou z balení),
TNC do USB a nakonec zdroj. První start trvá pár minut (Pi si zvětší oddíl na kartě a jednou se restartuje).

## 3. Připoj se k Pi

Z počítače ve stejné síti otevři terminál (Windows: *PowerShell*, macOS a Linux: *Terminál*) a napiš:

```bash
ssh pi@aprs.local
```

(`pi` nahraď svým uživatelským jménem.) Na otázku o otisku klíče odpověz `yes` a zadej heslo.
Máš-li u Pi klávesnici a displej, můžeš místo toho otevřít *Terminál* přímo na Pi.

## 4. Nainstaluj aplikaci – jeden příkaz

Vyber řádek podle svého displeje a vlož ho do terminálu:

| Displej | Příkaz |
|---|---|
| 5" HDMI s dotykem na stylus (Waveshare a klony, 800×480) | `curl -fsSL https://michalsiman.github.io/aprs-kiss-app/pi.sh \| bash -s -- --touch-5inch` |
| oficiální 7", jiný dotykový nebo obyčejný monitor | `curl -fsSL https://michalsiman.github.io/aprs-kiss-app/pi.sh \| bash` |
| bez displeje (Raspberry Pi OS Lite) | `curl -fsSL https://michalsiman.github.io/aprs-kiss-app/pi.sh \| bash -s -- --no-display` |

Skript sám nainstaluje, co je potřeba, a na konci se zeptá na **heslo k webu** – nastav ho, přes web se dá
vysílat. Na Pi 4 to trvá kolem 5 minut, na Pi 3 až 15. Pak Pi restartuj:

```bash
sudo reboot
```

## 5. Nastav stanici

Na telefonu nebo počítači ve stejné síti otevři **http://aprs.local:8080** (nebo adresu, kterou ukazuje konec
instalace), přihlas se heslem a v **Nastavení** vyplň:

- **Připojení k TNC**: TNC na USB je *Sériový port (USB)* `/dev/ttyACM0` nebo `/dev/ttyUSB0`; síťové TNC
  *KISS přes TCP (síť)*; zvuková karta *Zvukový modem (Direwolf)*.
- **Stanice**: značka se SSID, poloha, komentář, maják.
- podle potřeby **APRS-IS** (iGate), **Digipeater**.
- **Telemetrie stanice**: počty paketů (přijaté, přeposlané, přes iGate) a nejvzdálenější slyšená stanice
  jako grafy na aprs.fi – stačí *Internetem*.

Ulož a zapni **TX** v horní liště. Totéž můžeš udělat přímo na dotykovém displeji Pi (menu ☰ vlevo nahoře).
Zapnuté vysílání si Pi pamatuje i po restartu.

Hotovo. Pi teď po každém zapnutí naběhne samo – stanice, displej i web.

## Aktualizace

Spusť znovu instalační příkaz z kroku 4. Nastavení, zprávy i heslo zůstanou.

## Když něco nejde

- **Displej je černý nebo ukazuje jen plochu**: po startu počkej 1–2 minuty. Stav služby ukáže
  `systemctl status aprs-kiss`, její výpis `journalctl -u aprs-kiss -f`.
- **Dotyk nereaguje nebo jde jinam, než ťukáš**: instalovals s `--touch-5inch`? V souboru
  `/boot/firmware/config.txt` na řádku `dtoverlay=ads7846,…` změň `swapxy=0` na `swapxy=1` (prohozené osy) nebo
  prohoď hodnoty `xmin` a `xmax` (převrácená osa) a restartuj.
- **`aprs.local` nejde otevřít**: použij IP adresu Pi – ukazuje ji konec instalace, router, nebo příkaz
  `hostname -I`.
- **TNC na USB není vidět**: `ls /dev/ttyACM* /dev/ttyUSB*` ukáže, jestli ho Pi zná. Přístup k portu má
  uživatel ve skupině `dialout` – skript ho tam přidá, platí to po restartu.
- **Port 8080 je obsazený**: instaluj s `--port 8081` (a otevírej `http://aprs.local:8081`).
- **Zapomenuté heslo k webu**:
  `/opt/aprs-kiss/venv/bin/aprs-kiss-server --set-password && sudo systemctl restart aprs-kiss`
- **Jen přehled místo celé aplikace na displeji** (kontrolky, počítadla, poslední rámce): instaluj
  s `--dashboard`.

## Odinstalace

```bash
sudo systemctl disable --now aprs-kiss
sudo rm -rf /opt/aprs-kiss /etc/systemd/system/aprs-kiss.service
rm -f ~/.config/autostart/aprs-kiss-display.desktop
sed -i '/aprs-kiss/d' ~/.config/labwc/autostart
```

Nastavení a zprávy jsou v `~/.local/share/aprs-kiss` – smaž je, pokud je už nechceš.

# Packet chat – specification

**English** · [Česky](CHAT.cs.md)

The packet chat of APRS & Packet is plain text in AX.25 UI frames ("unproto"), the way packet
operators chatted long before APRS. There is no server, no session and no acknowledgement:
whoever is on the frequency reads it. Any software that can send and receive AX.25 UI frames
(through a KISS TNC, Direwolf, a hardware TNC…) can take part by following this page.

## Sending

One message is one AX.25 UI frame:

| Field | Value |
|---|---|
| Destination | `CQ` (SSID 0) |
| Source | the sender's callsign with SSID, e.g. `OK1SIM-14` |
| Digipeater path | none (direct) |
| Control | `0x03` (UI, poll/final bit clear) |
| PID | `0xF0` (no layer 3) |
| C bits (AX.25 v2) | command frame: destination SSID byte has bit 7 set, source SSID byte has it clear |
| Information field | the text, **UTF-8** |

Rules for the text:

- Leading and trailing whitespace is removed; an empty message is not sent.
- Line breaks inside a message are sent as CR (`0x0D`).
- No prefix: the sender's callsign is the frame's source, so do **not** add `OK1SIM: ` in front.
- Keep the information field to at most **256 bytes** (the AX.25 default N1; UTF-8 accented letters
  take 2 bytes). A longer message is sent as several frames, split between words; APRS & Packet does
  this itself.
- **The information field must not start with one of these characters:** `! = / @ ; ) ` ' : > ? < $ _ { } * #`.
  They are APRS data type identifiers, and receivers would treat the frame as APRS, not chat. When a
  message starts with one, put a space in front of it (APRS & Packet does this itself); receivers
  strip it again.

Example: `OK1SIM-14>CQ <UI>: Ahoj Pepo, slyšíš?`

```
AX.25:  86 a2 40 40 40 40 e0  9e 96 62 a6 92 9a 7d  03  f0  41 68 6f 6a 20 50 65 70 6f 2c 20 73 6c 79 c5 a1 c3 ad c5 a1 3f
        CQ          (C=1)     OK1SIM-14     (end)  UI  PID "Ahoj Pepo, slyšíš?" (UTF-8)
KISS:   c0 00 <the AX.25 bytes above> c0
```

(The FCS is added by the TNC; the KISS frame carries the AX.25 frame without it, as usual.)

## Receiving

A received UI frame is a chat message when **all** of these hold:

1. The control field is UI (`0x03`, with or without the P/F bit) and the information field is not empty.
2. The destination is `CQ`, `QST` or `ALL` (any SSID), **or** your own callsign with SSID.
3. It is not APRS: the destination does not start with `AP`, and the first byte of the information
   field is not one of `! = / @ ; ) ` ' : > ? < $ _ { } * #`.
4. It is not from your own callsign (a digipeated copy of your own message).

Frames to other destinations (`ID`, `BEACON`, `MAIL`, a digipeater's `DX` report…) are automatic
and are not shown as chat; APRS & Packet keeps them in its frame monitor.

Then:

- Decode the information field as **UTF-8**; replace bytes that are not valid UTF-8 (older software
  may send Latin-1 or CP852).
- Turn CR LF and CR into line breaks and remove leading and trailing whitespace.
- If the text starts with the sender's callsign followed by `: ` (e.g. `OK1ABC: hello`, the way some
  older programs send), remove that prefix.
- **Duplicates:** the same text from the same source within **30 seconds** is shown once (digipeaters
  and several iGates repeat frames).
- The digipeater path is not used, and the PID is not checked (`0xF0` is expected).

## What chat does not do

- No acknowledgement and no retries: a message may be lost and nobody is told.
- No addressing to one station in the APRS & Packet app: it always sends to `CQ`. It does show messages
  sent to your own callsign, so other software can address one station.
- No encryption; amateur radio rules apply.

## Compatibility

- Works through any KISS TNC that passes UI frames, including the KISS TNC app of the F4HWN firmware
  for the Quansheng UV-K1/K5 V3.
- Classic packet terminals in unproto mode to `CQ` (`UNPROTO CQ` on a hardware TNC, Direwolf with a
  KISS client…) interoperate as long as they send UTF-8 or plain ASCII.

# TAK over the radio – specification

**English** · [Česky](TAK.cs.md)

In TAK mode APRS & Packet is a TAK station over the radio: it sends its position and GeoChat to
other stations and shows theirs on its map. While TAK runs, everything else in the app is off
(switching it on takes a typed confirmation); tune the radio to a channel agreed with your team,
never to the APRS frequency.

## On the air

| | |
|---|---|
| Frame | AX.25 UI, destination `TAK`, source the sender's callsign, no digipeater path |
| Control / PID | `0x03` / `0xF0` |
| Information field | one **TAK Protocol version 1** message, mesh-framed: `0xBF 0x01 0xBF` followed by a protobuf `TakMessage` with one `CotEvent` (the `.proto` files of [takproto](https://github.com/snstac/takproto)) |
| Size | at most 256 bytes per frame |
| Encryption | none – amateur radio |

**Position (PLI):** `type` `a-f-G-U-C`, `uid` the callsign with SSID, `how` `m-g`, `lat`/`lon`, `hae`
from the GPS (otherwise 9999999), `ce`/`le` 10, `staleTime` three position intervals later;
`detail.contact.callsign`, `detail.group` (team colour and role, ATAK's names), `detail.track` (speed in
m/s and course). About 150 bytes; sent every *N* minutes (Settings › TAK) and with the button.

**GeoChat:** `type` `b-t-f`, `uid` `GeoChat.<sender uid>.<room>.<id>`, `how` `h-g-i-g-o`, no position,
`detail.xmlDetail`:

```xml
<__chat chatroom="All" senderCallsign="OK1SIM"/><remarks to="All">the text</remarks>
```

The room is `All` for everybody, or the recipient's uid for one station. This is ATAK's GeoChat
without its optional attributes (ATAK's own form is about 500 bytes, too long for one frame); receivers
also read ATAK's full form (`All Chat Rooms`). A longer text is sent as several events, split between
words.

Received events with a position (any `a-…` type, spot markers) are shown on the map, coloured by team
(or by affiliation: friend blue, hostile red, neutral green, unknown yellow) and faded once stale.

## Compatibility

The payload is TAK Protocol v1, so ATAK, WinTAK, iTAK, takproto and PyTAK read and write it. Between
a TAK client and the radio a gateway is needed (APRS & Packet does not bridge to a network); the
compact GeoChat is valid CoT that ATAK displays.

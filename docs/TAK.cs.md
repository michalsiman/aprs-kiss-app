# TAK přes rádio – specifikace

[English](TAK.md) · **Česky**

V režimu TAK je APRS & Packet TAK stanicí přes rádio: posílá svoji polohu a GeoChat ostatním
stanicím a jejich polohy ukazuje na své mapě. Dokud TAK běží, je všechno ostatní v aplikaci vypnuté
(zapnutí vyžaduje napsat potvrzovací větu); rádio nalaďte na kanál domluvený s týmem, nikdy ne na
kmitočet APRS.

## Ve vzduchu

| | |
|---|---|
| Rámec | AX.25 UI, cíl `TAK`, zdroj značka odesílatele, bez cesty přes digipeatery |
| Control / PID | `0x03` / `0xF0` |
| Informační pole | jedna zpráva **TAK Protocol version 1** s mesh hlavičkou: `0xBF 0x01 0xBF` a za ní protobuf `TakMessage` s jedním `CotEvent` (soubory `.proto` z [takproto](https://github.com/snstac/takproto)) |
| Velikost | nejvýš 256 bajtů na rámec |
| Šifrování | žádné – radioamatérský provoz |

**Poloha (PLI):** `type` `a-f-G-U-C`, `uid` značka se SSID, `how` `m-g`, `lat`/`lon`, `hae` z GPS
(jinak 9999999), `ce`/`le` 10, `staleTime` za tři intervaly polohy; `detail.contact.callsign`,
`detail.group` (barva týmu a role, názvy jako v ATAK), `detail.track` (rychlost v m/s a kurz).
Zhruba 150 bajtů; posílá se každých *N* minut (Nastavení › TAK) a tlačítkem.

**GeoChat:** `type` `b-t-f`, `uid` `GeoChat.<uid odesílatele>.<místnost>.<id>`, `how` `h-g-i-g-o`,
bez polohy, `detail.xmlDetail`:

```xml
<__chat chatroom="All" senderCallsign="OK1SIM"/><remarks to="All">text zprávy</remarks>
```

Místnost je `All` pro všechny, nebo uid příjemce pro jednu stanici. Je to GeoChat z ATAK bez
nepovinných atributů (vlastní tvar ATAK má kolem 500 bajtů, na jeden rámec moc); přijímač čte
i plný tvar z ATAK (`All Chat Rooms`). Delší text se pošle jako několik událostí, rozdělený mezi slovy.

Přijaté události s polohou (jakýkoliv typ `a-…`, značky) se ukážou na mapě, barevně podle týmu
(nebo příslušnosti: přítel modrá, nepřítel červená, neutrální zelená, neznámý žlutá) a po vypršení
platnosti zešednou.

## Kompatibilita

Obsah je TAK Protocol v1, takže ho čte i zapisuje ATAK, WinTAK, iTAK, takproto a PyTAK. Mezi TAK
klientem a rádiem je potřeba brána (APRS & Packet do sítě nepřeposílá); kompaktní GeoChat je platné
CoT, které ATAK zobrazí.

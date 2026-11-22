# Packet chat – specifikace

[English](CHAT.md) · **Česky**

Packet chat v aplikaci APRS & Packet je prostý text v AX.25 UI rámcích („unproto“), tak jak si
packetáři psali dávno před APRS. Není tu server, spojení ani potvrzování: přečte to každý, kdo je
na kmitočtu. Zapojit se může jakýkoliv software, který umí posílat a přijímat AX.25 UI rámce (přes
KISS TNC, Direwolf, hardwarové TNC…), když dodrží tuto stránku.

## Odesílání

Jedna zpráva je jeden AX.25 UI rámec:

| Pole | Hodnota |
|---|---|
| Cíl (destination) | `CQ` (SSID 0) |
| Zdroj (source) | značka odesílatele se SSID, např. `OK1SIM-14` |
| Cesta přes digipeatery | žádná (přímo) |
| Control | `0x03` (UI, bit poll/final vynulovaný) |
| PID | `0xF0` (bez vrstvy 3) |
| C bity (AX.25 v2) | rámec typu command: v bajtu SSID cíle je bit 7 nastavený, v bajtu SSID zdroje vynulovaný |
| Informační pole | text v **UTF-8** |

Pravidla pro text:

- Mezery a konce řádků na začátku a na konci se odstraní; prázdná zpráva se neposílá.
- Konce řádků uvnitř zprávy se posílají jako CR (`0x0D`).
- Bez předpony: značka odesílatele je zdrojem rámce, takže na začátek **nepřidávejte** `OK1SIM: `.
- Informační pole držte nejvýš na **256 bajtech** (výchozí N1 v AX.25; písmena s diakritikou mají
  v UTF-8 2 bajty). Delší zpráva se pošle jako několik rámců, rozdělená mezi slovy; APRS & Packet to
  dělá sám.
- **Informační pole nesmí začínat žádným z těchto znaků:** `! = / @ ; ) ` ' : > ? < $ _ { } * #`.
  Jsou to identifikátory typu APRS dat a přijímač by rámec bral jako APRS, ne jako chat. Když zpráva
  takovým znakem začíná, dejte před něj mezeru (APRS & Packet to dělá sám); přijímač ji zase odstraní.

Příklad: `OK1SIM-14>CQ <UI>: Ahoj Pepo, slyšíš?`

```
AX.25:  86 a2 40 40 40 40 e0  9e 96 62 a6 92 9a 7d  03  f0  41 68 6f 6a 20 50 65 70 6f 2c 20 73 6c 79 c5 a1 c3 ad c5 a1 3f
        CQ          (C=1)     OK1SIM-14   (konec)  UI  PID "Ahoj Pepo, slyšíš?" (UTF-8)
KISS:   c0 00 <bajty AX.25 výše> c0
```

(Kontrolní součet FCS přidává TNC; KISS rámec nese AX.25 rámec bez něj, jak je zvykem.)

## Příjem

Přijatý UI rámec je zpráva chatu, když platí **všechno** z tohoto:

1. Pole control je UI (`0x03`, s bitem P/F i bez něj) a informační pole není prázdné.
2. Cíl je `CQ`, `QST` nebo `ALL` (jakékoliv SSID), **nebo** vaše vlastní značka se SSID.
3. Není to APRS: cíl nezačíná na `AP` a první bajt informačního pole není žádný z
   `! = / @ ; ) ` ' : > ? < $ _ { } * #`.
4. Není od vaší vlastní značky (kopie vaší zprávy od digipeateru).

Rámce na jiné cíle (`ID`, `BEACON`, `MAIL`, hlášení `DX` od digipeateru…) jsou automatické a jako
chat se nezobrazují; APRS & Packet je ukazuje v monitoru rámců.

Pak:

- Informační pole dekódujte jako **UTF-8**; bajty, které nejsou platné UTF-8, nahraďte (starší
  software může posílat Latin-1 nebo CP852).
- CR LF a CR převeďte na konce řádků a odstraňte mezery na začátku a na konci.
- Když text začíná značkou odesílatele a `: ` (např. `OK1ABC: ahoj`, jak to posílají některé starší
  programy), předponu odstraňte.
- **Duplicity:** stejný text od stejného zdroje během **30 sekund** se zobrazí jen jednou
  (digipeatery a různé iGaty rámce opakují).
- Cesta přes digipeatery se nepoužívá a PID se nekontroluje (očekává se `0xF0`).

## Co chat neumí

- Žádné potvrzení ani opakování: zpráva se může ztratit a nikdo se to nedozví.
- Aplikace APRS & Packet neposílá zprávu jedné stanici: posílá vždy na `CQ`. Zprávy poslané na vaši
  značku ale zobrazí, takže jiný software může psát jedné stanici.
- Žádné šifrování; platí pravidla radioamatérského provozu.

## Kompatibilita

- Funguje přes jakékoliv KISS TNC, které propouští UI rámce, včetně aplikace KISS TNC ve firmwaru
  F4HWN pro Quansheng UV-K1/K5 V3.
- Klasické packetové terminály v režimu unproto na `CQ` (`UNPROTO CQ` na hardwarovém TNC, Direwolf
  s KISS klientem…) jsou kompatibilní, pokud posílají UTF-8 nebo čisté ASCII.

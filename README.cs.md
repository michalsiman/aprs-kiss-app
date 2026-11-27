# APRS & Packet – samostatná aplikace

[English](README.md) · **Česky**

[![stable](https://img.shields.io/github/v/release/michalsiman/aprs-kiss-app?label=ostr%C3%A1%20verze&color=2ea043)](https://github.com/michalsiman/aprs-kiss-app/releases/latest)
[![beta](https://img.shields.io/github/v/release/michalsiman/aprs-kiss-app?include_prereleases&label=beta&color=d29922)](https://github.com/michalsiman/aprs-kiss-app/releases)
[![downloads](https://img.shields.io/github/downloads/michalsiman/aprs-kiss-app/total?label=sta%C5%BEen%C3%AD)](https://github.com/michalsiman/aprs-kiss-app/releases)
[![tests](https://img.shields.io/github/actions/workflow/status/michalsiman/aprs-kiss-app/tests.yml?branch=main&label=testy)](https://github.com/michalsiman/aprs-kiss-app/actions/workflows/tests.yml)
[![licence](https://img.shields.io/github/license/michalsiman/aprs-kiss-app?label=licence)](LICENSE)
[![platforms](https://img.shields.io/badge/platformy-Linux%20%7C%20Windows%20%7C%20Android%20%7C%20macOS%20%7C%20iOS-3D46B2)](#platformy)
![languages](https://img.shields.io/badge/jazyky-16-3D46B2)
[![python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![flet](https://img.shields.io/badge/Flet-1.1.2-5C2D91)](https://flet.dev/)
![ham](https://img.shields.io/badge/ham%20radio-APRS%20%C2%B7%20AX.25%20%C2%B7%20KISS-e8590c)

<p align="center"><a href="assets/cs/map.png"><picture><source media="(prefers-color-scheme: light)" srcset="assets/cs/map-light.png"><img src="assets/cs/map.png" width="50%" alt="APRS & Packet na počítači: mapa se stanicemi, převaděči a ocásky"></picture></a></p>

APRS stanice a packet radio terminál pro rádio s **KISS TNC** jako obyčejná aplikace pro počítač
i **telefon s Androidem** – bez Home Assistantu, bez webového serveru. Je to samostatný sourozenec
[integrace APRS & Packet pro Home Assistant](https://github.com/michalsiman/aprs-kiss-ha) a sdílí
s ní rádiové jádro.

Dělaná pro Quansheng UV-K1/UV-K5 V3 s [firmwarem F4HWN](https://github.com/armel/uv-k1-k5v3-firmware-custom)
a jeho [aplikací KISS TNC](https://github.com/armel/uv-k1-k5v3-firmware-custom/wiki/App-KISS-TNC), ale funguje
s jakýmkoliv KISS TNC (Direwolf, hardwarové TNC, USB sériový port rádia nebo KISS TCP most z integrace).
Ověřená funkčnost i s ručkami **VGC VR-N76** a **AnyTone UV890**.

> **📻 VGC VR-N76 (a jeho dvojčata BTECH UV-PRO, Radioddity GA-5WB):** vyzkoušené na pásmu přes Bluetooth
> s vestavěným KISS TNC rádia – bez kabelu a bez dalšího TNC. **Nově od verze 1.4 aplikace rádio i naladí** –
> stačí zadat frekvenci v *Nastavení › Připojení k TNC* a klepnout na *Naladit* (firmware 0.7.11 a novější).

**Stav: verze 1.5, aktivní vývoj.** Ostré verze (1.0, 1.1 … 1.5) jednou za čas, mezi nimi **beta verze** pro
testery – zaškrtněte v Nastavení *Nabízet i beta verze* (viz [CHANGELOG](CHANGELOG.md), anglicky).
Připravená pro **Linux**, **Windows** a **Android**; sestavení pro **macOS** a **iOS** existují, ale na
skutečném Macu, iPhonu ani iPadu je zatím nikdo nevyzkoušel – **hledáme testery** (viz [Platformy](#platformy)).

**Vyzkoušeno na pásmu** (děkuji!): Linux a Windows s **Quanshengem** na USB kabelu; Windows s **VGC VR-N76**
a **AnyTone 890** přes Bluetooth; **Direwolf** přes TCP/IP z jiného počítače; **tracker** na Androidu v autě
s Quanshengem na USB kabelu i samostatně přes internet (APRS-IS). **Budu moc rád za nové testery a zpětnou
vazbu** – jakékoli rádio, TNC i platforma: napište [issue](https://github.com/michalsiman/aprs-kiss-app/issues).

## Funkce v kostce

<table>
<tr><td width="33%" valign="top"><h3>🗺️ Živá mapa</h3>Stanice s APRS symboly, ocásky, převaděče s kmitočtem; OpenStreetMap, OpenTopoMap i offline.</td><td width="33%" valign="top"><h3>✉️ Zprávy</h3>Konverzace s počty nepřečtených a hledáním; polohy, odkazy a zmíněné stanice se otevřou na mapě.</td><td width="33%" valign="top"><h3>📧 Winlink e-mail</h3>Čtení a posílání e-mailů přes APRS a bránu WLNK-1 – přihlášení vyřeší aplikace sama.</td></tr>
<tr><td width="33%" valign="top"><h3>🚗 Tracker</h3>Pevný interval nebo jako SmartBeaconing; mapa tě sleduje jako navigace.</td><td width="33%" valign="top"><h3>⚠️ Výstrahy před tebou</h3>Nehody, práce na silnici, požáry, povodně a protijedoucí stanice v laloku před tebou.</td><td width="33%" valign="top"><h3>🆘 Mic-E a NOUZE</h3>Kratší polohy se stavem; NOUZE s potvrzením a červeně na mapě.</td></tr>
<tr><td width="33%" valign="top"><h3>🌡️ Počasí z okolí</h3>Průměr meteostanic do 20 km v rohu mapy.</td><td width="33%" valign="top"><h3>📻 Jakékoli KISS TNC</h3>TCP/IP, USB, Bluetooth i Bluetooth LE; ladí rádia VR-N76 / UV-PRO.</td><td width="33%" valign="top"><h3>🔁 Digipeater a iGate</h3>Fill-in nebo wide digipeater; RX i TX iGate do APRS-IS.</td></tr>
<tr><td width="33%" valign="top"><h3>💻 Packet terminál</h3>Spojení AX.25 na BBS a nody, i přes VARA FM.</td><td width="33%" valign="top"><h3>📁 Soubory</h3>Posílání a příjem souborů přes packet rádio (YAPP), s průběhem a zbývajícím časem.</td><td width="33%" valign="top"><h3>🗄️ BBS SERVER</h3>Vlastní packet BBS – příkazy ve stylu W0RLI / MBL / FBB.</td></tr>
<tr><td width="33%" valign="top"><h3>🎯 TAK</h3>Polohy a GeoChat kompatibilní s ATAK přes rádio.</td><td width="33%" valign="top"><h3>🏔️ Spot a služby</h3>Ohlášení SOTA, POTA, WWFF …; FIND, REPEAT, WXNOW a další.</td><td width="33%" valign="top"><h3>📅 #APRSThursday</h3>Týdenní síť HOTG na vlastní obrazovce.</td></tr>
<tr><td width="33%" valign="top"><h3>🧭 Navigace a sdílení</h3>Otevři stanici nebo bod v navigaci, nebo ho pošli dál.</td><td width="33%" valign="top"><h3>🌍 16 jazyků</h3>km nebo míle, °C nebo °F, hPa nebo inHg – podle telefonu či počítače.</td><td width="33%" valign="top"><h3>🖥️ Všude</h3>Linux, Windows, macOS, Android, iOS – jedna aplikace, světlá i tmavá.</td></tr>
</table>

## Co umí

### APRS

- **Mapa** slyšených stanic (OpenStreetMap) s APRS symboly a popisky značek v rámečku, vaše poloha,
  zvýrazněné sledované značky. Tlačítka pro vycentrování na vás, *Tlumená mapa*, která mapu ztlumí,
  aby stanice vynikly, stanice z internetu zapnout/vypnout, jen *Posledních 2 h* a legenda
  symbolů – malé ikonky, které svítí, když jsou zapnuté. Tlačítka zoomu, kompas, který mapu vrátí severem
  nahoru, měřítko; dvěma prsty se mapa otočí jen výrazným natočením. **Nabídky zůstávají otevřené**, když v nich zaškrtáváte nebo vybíráte mapu (prázdný rámeček ukazuje, co je vypnuté); zavře je tlačítko zpět nebo klepnutí mimo ně. Pravé tlačítko (na telefonu podržení
  prstu) na mapě: *Nastavit jako moji polohu*. Kreslí se jen stanice v okolí toho, co je na obrazovce,
  takže mapa zůstává svižná i na telefonu.
- **Online mapy**: OpenStreetMap, nebo **topografická OpenTopoMap** (vrstevnice, stínování terénu).
- **Offline mapa** přímo v aplikaci: hranice států, pobřeží a asi 1 000 větších měst (Natural Earth),
  v Evropě i dálnice a hlavní silnice (Natural Earth), asi 67 000 obcí nad 1 000 obyvatel a 30 nejvyšších
  hor každé země (GeoNames) – s přiblížením přibývají další. I v tmavém režimu je světlá, stejně jako mapy online. Přepíná se jedním tlačítkem; **když není internet, mapa se na ni
  přepne sama** a oznámí to, a jakmile se internet vrátí, vrátí se k OpenStreetMap.
- **Filtry mapy** (trychtýř): jen **meteostanice**, jen **jedoucí** stanice (pohnuly se za posledních
  10 minut; nově slyšená stanice zůstane, dokud není jasné, že stojí), jen **převaděče**, jen **výstrahy**
  (nehody, práce na silnici, požáry, povodně, mlha, sníh – v Česku, USA, Austrálii, Portugalsku…) – libovolně kombinovatelné, pamatují se. Ve stejné
  nabídce i **jak daleko**: stanice z internetu do 20, 50 nebo 100 km (server APRS-IS dostane novou oblast
  hned) a stanice z rádia do 20, 50, 100 km nebo bez omezení. Pod tlačítky mapy malý řádek ukazuje, kolik
  stanic je právě **na mapě**; klepnutím se ukáže, kolik je různých značek a která stanice je nejblíž
  a nejdál (*Počet bodů na mapě* v nabídce mapy řádek schová).
- **Převaděče ukazují kmitočet** přímo ve štítku – pásmo barevně (2 m zeleně, 70 cm purpurově) a druh
  provozu, pokud je v komentáři (DMR, D-Star, C4FM, NXDN, TETRA). Stejně tak **meteostanice ukazují
  teplotu**.
- **Kilometry nebo míle, °C nebo °F, hPa nebo inHg** (Nastavení › Aplikace): podle telefonu či počítače (míle
  v USA a Británii, Fahrenheit a palce rtuti v USA), nebo podle volby. Řídí se tím vzdálenosti, měřítko mapy,
  poloměry ve filtru, rychlosti, výšky, teploty i tlak.
- **Teplota z okolí** v rohu mapy: průměr z meteostanic do 20 km (údaje nejvýš 2 hodiny staré), i s vlhkostí
  a tlakem, pokud je posílají; obnovuje se každých 5 minut, při otevřených tlačítkách mapy se posune pod ně,
  vypíná se v nabídce mapy. Klepnutím na ni se ukážou stanice, ze kterých je spočítaná: jejich hodnoty,
  vzdálenost a směr, stáří údaje.
- **Značky se nepřekrývají**: stanice na jednom místě nebo blízko sebe se rozestoupí, tenká šedá čára vede
  ze středu symbolu k tečce, kde stanice opravdu je – čáry se nekříží a žádná tečka se neschová pod symbol
  jiné stanice. **Ocásky** (poslední půlhodina, i vaše vlastní z GPS),
  APRS **objekty** jako samostatná místa, nesmyslné skoky se ignorují. **Měření vzdálenosti** podržením
  prstu na dvou bodech.
- **Mapa jako navigace, když běží tracker**: jste uprostřed s přiblížením na ulice; posunete-li mapou,
  tlačítko **Zpět na mě** odpočítává 15 s a pak se mapa vrátí sama.
- **Upozornění před vámi, když běží tracker** (vypnutá, dokud je nezapnete): **výstrahy**
  a **jiné jedoucí stanice** (jedou stejným směrem, proti vám, nebo křižují) v laloku před vámi – při
  rychlé jízdě dlouhém a úzkém, ve městě širokém, nikdy za vámi; bublina a zvuk.
- **Profily**: až tři SSID vaší značky, každé s vlastní ikonou (auto, ručka, domov), komentářem a způsobem
  trackeru; horní lišta ukazuje vedle značky ikonu aktivního profilu, klepnutím se přepne – poloha, zprávy,
  terminál, vše jde pod ním.
- **APRS-IS**: jedním přepínačem se poloha (teď, pravidelně, tracker) i zprávy posílají i přes internet;
  s vypnutým vysíláním jde vše jen přes internet.
- **Mic-E**: poloha kratší ve vysílání, se stavem – i **NOUZE (EMERGENCY)** (s potvrzením, červené SOS v horní
  liště, dokud ji neukončíte); stanice v nouzi jsou na mapě červeně.
- **Tracker**: tlačítko polohy v horní liště pošle polohu jednou, nebo spustí tracker (▶) – poloha z GPS
  se pak posílá sama, v pevném intervalu nebo **chytře (SmartBeaconing)** jako APRS a LoRa APRS trackery:
  když stojíte zřídka, čím rychleji jedete tím častěji, hned v zatáčce; s kurzem a rychlostí. Rádiem jde,
  když je zapnuté TX (a přes internet, pokud je to zvolené).
- **Vlastní offline mapa** (Nastavení › Offline mapy): nahrajte si lepší mapu, třeba turistickou,
  odkudkoli – rastrové dlaždicové mapy **MBTiles, PMTiles, SQLiteDB** (OsmAnd, Locus), **ZIP** s dlaždicemi
  z/x/y nebo ZIP/7z, ve kterém jsou takové soubory (7z na počítači se 7-Zipem). I víc map naráz; tlačítkem
  mapy se volí *online*, *stažená* a *základní offline*. Vektorové mapy (Mapsforge, vektorové MBTiles) nejdou.
- **Zprávy** jako konverzace: každá s **barevným kolečkem s písmenem** (první písmeno za číslicí, OK1ABC → A)
  a **červeným počtem nepřečtených zpráv**; filtry **Vše / Nepřečtené** s počty a **hledání** ve značkách
  i textech (bez ohledu na velikost písmen a diakritiku); *⋮ › Označit vše jako přečtené*. Nepřečtené zůstanou
  nepřečtené i po restartu a aktualizaci. Opakované až do potvrzení, se stavem doručení, příchozí se
  potvrzují automaticky; nová zpráva na libovolnou značku kulatým **+**. **Rádiem a internetem** jsou dvě
  ikony (ruční vysílačka a zeměkoule), jedna nebo obě, zapamatované. Delší text odejde jako více zpráv
  číslovaných 1/2, 2/2 …; v konverzaci je vidět, jak daleko stanice je (i jak daleko byla, když zpráva
  přišla) s tlačítkem na mapu; zpět z konverzace vede nejdřív na seznam; konverzace jde smazat.
- **Notifikace** nové zprávy nebo řádku chatu, když se zrovna nedíváte: na Androidu na pozadí (klepnutí
  otevře konverzaci; uvádí, kolik je celkem nepřečtených), na Linuxu, Windows a macOS, když okno není vepředu.
- **Stanice zmíněné ve zprávě** (OK6DJ-6 v odpovědi WXNOW, „pozdravuj OK1ABC“): malé tlačítko u zprávy
  nabídne ty, které známe s polohou, i se vzdáleností a směrem; klepnutím se ukáže na mapě.
- **Odkazy na web** ve zprávách, v APRS Thursday a v chatu jdou otevřít; klepnutí nejdřív ukáže, kam odkaz
  vede, a upozorní, že za obsah stránky nikdo neručí (může být škodlivá).
- **Navigovat sem / Sdílet tuto polohu** u stanice i u libovolného bodu na mapě: navigační nebo mapová aplikace
  v telefonu (Android se zeptá, která), nebo sdílení do jiné aplikace; na počítači webová mapa a zkopírovaný text.
- **Poloha ve zprávách a v chatu**: pošlete svoji, nebo libovolné místo vybrané na mapě – jako souřadnice
  nebo jako lokátor (nabídka mapy ukazuje lokátor každého místa); poloha napsaná ve zprávě nebo v chatu
  (desetinné stupně, stupně a minuty, APRS zápis, lokátor) se otevře na mapě se špendlíkem.
- **Ohlášení aktivace** (Zprávy › Spot): SOTA, POTA, WWFF, SIOTA, GMA, hrady WCA, IOTA a majáky –
  self-spot jde rádiem jako APRS zpráva na APRS2SOTA, Camillu (GMA) nebo APSPOT, zkontrolovaný a zkrácený,
  aby se vešel, s odpovědí brány v její konverzaci.
- **Winlink e-mail** (APRSLink, WLNK-1): přihlášení jedním tlačítkem (do éteru jdou jen tři znaky hesla
  Winlink), seznam, čtení, odpověď, přeposlání a mazání e-mailů, psaní nového po řádcích – vše jako APRS zprávy.
- **Služby na APRS** (Zprávy › Služby): FIND (kde byla stanice naposledy slyšet), REPEAT (nejbližší
  převaděče), WXNOW (počasí z nejbližší meteostanice), UTC, přelety satelitů a východ slunce (9M2PJU-4),
  e-mail (MAILMY) – klepnutím se příkaz vloží do zprávy, odpověď přijde zprávou.
- **#APRSThursday**: vlastní sekce pro čtvrteční síť HOTG přes ANSRVR – zapojení jedním tlačítkem,
  zprávy skupiny zvlášť mimo běžné zprávy (přeposílání z ANSRVR se do Zpráv nikdy nedostane), kdy začíná
  další akce, odhlášení ze skupiny; rádiem, internetem nebo obojím, zapamatované.
- **Stanice** slyšené rádiem nebo viděné na APRS-IS: vzdálenost, směr, komentář, počasí, cesta;
  řazení podle času, vzdálenosti nebo značky; filtr a legenda; počítadlo ukazuje zobrazené z celkového počtu a prázdný seznam řekne proč. Detail stanice
  nabízí mapu, zprávu a **katalogy značek** (QRZ.com, HamQTH, QRZCQ – značka bez SSID – a aprs.fi). Objeví se i stanice, které iGate pošle z internetu do rádia (pakety třetí strany).
- **Maják polohy** každých N minut a tlačítko *Poslat polohu teď* v horní liště; status a unproto.
  Ikona (APRS symbol), komentář, SSID a cesta v Nastavení.
- **Digipeater**: fill-in (WIDE1-1, pro domácí stanici) nebo plný (WIDEn-N s omezením počtu hopů),
  rámce adresované vaší značce nebo aliasům (např. RELAY), stejný paket jen jednou za 30 sekund.
- **APRS-IS** (internet) s volitelným **iGate** pro příjem i vysílání; zprávy, které vám iGate pošle
  rádiem, se přijmou a potvrdí.
- **Poloha z GPS**: z GPS telefonu (na telefonu bez ručně zadané polohy výchozí; Nastavení ukazuje,
  kde podle ní jste), nebo z **USB GPS modulu** (NMEA, u-blox/VK-172 a podobné, rychlost se zjistí sama): s fixem používá jeho polohu
  mapa, maják (i s výškou) a TAK; stav GPS je v horní liště.

### Packet rádio

- **Terminál**: AX.25 spojení s BBS a nody, klidně přes digipeatery; seznam **uložených BBS** k výběru;
  pokusy o připojení s časy a tlačítko *Zastavit připojování*; volitelně příchozí spojení.
- **Terminál přes VARA FM**: stejný terminál přes VARA FM místo AX.25 – *Připojení: VARA FM*.
  VARA běží zvlášť (Windows, nebo Wine na Linuxu) s rádiem na zvukové kartě, např. kabelem AIOC;
  aplikace s ní mluví přes její TCP rozhraní (porty 8300/8301) a ukazuje průběh spojení, PTT
  a buffer pro vysílání.
- **Soubory**: posílání a příjem souborů přes packet radio – YAPP (standard BPQ, WinPacku, Paxonu) přes
  spojení AX.25 s potvrzováním; před odesláním odhad času, během přenosu průběh, rychlost a zbývající čas;
  každý příchozí soubor se nejdřív nabídne; přerušený přenos naváže.
- **Chat**: prostý text na CQ, QST, ALL nebo vám, slyší ho všichni na kmitočtu; automatické rámce jako
  DX hlášení digipeaterů do chatu nepatří. Jak ho použít v jiném softwaru popisuje
  **[specifikace chatu](docs/CHAT.cs.md)**.
- **Monitor**: všechny přijaté i odeslané rámce jako na TNC, s pozastavením a vymazáním; umí skrýt
  řádky z APRS-IS a TAK rámce ukazuje dekódované.
- **BBS SERVER**: vlastní packetová BBS na vaší značce s vlastním SSID – klasické příkazy W0RLI / MBL / FBB,
  osobní zprávy a bulletiny, limity pro počet klientů, nečinnost, čas vysílání a počet uložených zpráv;
  nastavení a texty v obyčejných souborech (bbs.toml, welcome.txt, …), každá zpráva v jednom textovém
  souboru. Dokud běží, je všechno ostatní v aplikaci vypnuté (rádio je na kmitočtu BBS, nikdy ne na
  144.800); zapnutí vyžaduje napsat potvrzovací větu. Viz **[návod k BBS SERVER](docs/BBS.cs.md)**.
- **TAK**: aplikace jako TAK stanice přes rádio – polohy a GeoChat kompatibilní s ATAK (TAK Protocol v1
  v AX.25 UI rámcích), vlastní mapa se stanicemi barevně podle týmu, seznam stanic, zprávy všem nebo
  jedné stanici; tým, role a značka v Nastavení; kdo se objevil na mapě a kdo se posunul jak daleko,
  ukazuje GeoChat. Na telefonu jsou mapa a GeoChat dvě obrazovky a na ikonce GeoChatu je počet
  nepřečtených zpráv. Rámce se vejdou i do LoRa KISS modemů (MeshCore). Stejně jako BBS SERVER vypne
  všechno ostatní.
  Viz **[specifikace TAK](docs/TAK.cs.md)**.

### Aplikace

- **Menu v sekcích**: APRS (mapa, zprávy, APRS Thursday, stanice), packet radio (terminál, chat, soubory,
  monitor, BBS, TAK) a nastavení – nadpisy v menu telefonu, mezery na počítači.
- **Horní lišta jako přístrojová deska**, na počítači i na telefonu: kontrolky **TNC**, **IS** a **GPS**
  svítí zeleně, když fungují, tlačítko polohy / trackeru, **TX** s červeným rámečkem při zapnutém vysílání
  a celé červené, když rámec odchází do éteru (IS na vteřinu zčervená, když něco jde do APRS-IS). Na počítači
  jsou kontrolky větší a po najetí myší řeknou svůj stav; na telefonu jsou TNC, IS a GPS v jednom malém
  bloku, aby se vešla celá značka.
- **Čtyři cesty k TNC**: **KISS přes TCP/IP** (Direwolf, síťový most, Wi-Fi TNC), **sériový/USB port**
  (seznam portů, na Linuxu se stálými názvy `/dev/serial/by-id`; na telefonu USB port přes OTG kabel),
  **Bluetooth** (spárované TNC nebo rádio, profil sériového portu) a **Bluetooth LE** (KISS přes BLE);
  TX delay pro TNC; po výpadku se připojí sama.
- **Ladění rádia z aplikace**: rádia s vestavěným KISS TNC přes Bluetooth – **VGC VR-N76, BTECH UV-PRO,
  Radioddity GA-5WB** (firmware 0.7.11 a novější) – se naladí v *Nastavení › Připojení k TNC* (*Naladit*,
  a *Vlastní* je vrátí), příkazem KISS SetHardware. Výkon se takhle nastavit nedá.
- **16 jazyků**: brazilská portugalština, čeština, dánština, angličtina, francouzština, chorvatština,
  italština, němčina, norština (bokmål), polština, slovenština, slovinština, srbština (cyrilice),
  španělština, švédština a ukrajinština; řídí se jazykem systému, nebo si ho vyberete v Nastavení.
- **Světlý a tmavý** vzhled podle systému, nebo podle volby v Nastavení.
- **Zvuky**: pípnutí při vysílání, zvuk při nové APRS zprávě, zprávě v chatu a v TAK GeoChatu – každý
  jde v Nastavení zapnout nebo vypnout.
- **Nezhasínat obrazovku**: nikdy, když běží TAK, nebo vždy.
- **Nastavení ve sbalených blocích**; značka je povinná (dokud není uložená, je orámovaná červeně).
  Potvrzovací věty (TAK, BBS SERVER, licence pro APRS-IS) se opisují jen jednou, ne pokaždé.
- **Při prvním spuštění** se zeptá na jazyk (nabídne jazyk zařízení) a ukáže upozornění, které je
  potřeba přijmout: vysílat smí jen držitel radioamatérské licence.
- Dá vědět, když vyjde nová verze: nejvýš jednou denně se zeptá GitHubu na poslední vydání,
  nic o vás neposílá; v Nastavení se dá vypnout. Na Androidu *Stáhnout* rovnou stáhne nové .apk.
- **Protokol pro hledání chyb**: *O aplikaci › Zkopírovat protokol* dá konec malého protokolu do schránky
  (co se dělo před zaseknutím; hlídač zapíše, co aplikaci blokuje). Když Android na telefonu na pozadí
  restartuje zobrazovací část aplikace, vrátí se aplikace na obrazovku, kterou jste měli otevřenou.

### Na telefonu (Android)

- Obrazovky jsou v nabídce, která se vysune ze strany (☰); horní lišta je jako přístrojová deska:
  kontrolky **TNC**, **IS** a **GPS** svítí zeleně, když fungují, **TX** má červený rámeček, když je
  vysílání zapnuté, a je celá červená, když rámec právě odchází do éteru – klepnutím na TX se vysílání
  zapne nebo vypne, klepnutí na TNC nebo GPS ukáže jejich stav.
- **TNC na USB portu telefonu** (OTG kabel): Quansheng s KISS firmwarem F4HWN a další CDC-ACM TNC,
  kabely CP210x a FTDI; **přes Bluetooth** (spárované TNC nebo rádio se sériovým profilem SPP, např.
  Mobilinkd TNC3 nebo ručka s Bluetooth KISS TNC); **přes Bluetooth LE** (KISS over BLE: LoRa APRS tracker,
  Mobilinkd TNC4, PicoAPRS …, najde je hledání v Nastavení); nebo po síti.
- **GPS telefonu** jako vaše poloha.
- **Běh na pozadí** (Nastavení › Pozadí a obrazovka): příjem, majáky, zprávy i TAK běží dál, i když
  aplikace není na obrazovce nebo je telefon zamčený; ukazuje to notifikace.

> **Vysílání je ve výchozím stavu vypnuté.** *Vysílání* v horní liště zapněte jen tehdy, když máte
> radioamatérské oprávnění. APRS-IS jde zapnout až po napsání věty o licenci.

## Snímky obrazovky

Pořízené se simulovaným TNC (`tests/fake_tnc.py --scene --tak`, `tools/screenshots.py`); kliknutím se
zvětší. Řídí se motivem GitHubu, stejně jako aplikace: používá světlý nebo tmavý režim systému.

### Na telefonu

<table>
<tr><td width="33%" align="center"><a href="assets/cs/phone-map.png"><picture><source media="(prefers-color-scheme: light)" srcset="assets/cs/phone-map-light.png"><img src="assets/cs/phone-map.png" width="200" alt="Mapa"></picture></a><br><b>Mapa</b></td><td width="33%" align="center"><a href="assets/cs/phone-filter.png"><picture><source media="(prefers-color-scheme: light)" srcset="assets/cs/phone-filter-light.png"><img src="assets/cs/phone-filter.png" width="200" alt="Filtry a dosah"></picture></a><br><b>Filtry a dosah</b></td><td width="33%" align="center"><a href="assets/cs/phone-menu.png"><picture><source media="(prefers-color-scheme: light)" srcset="assets/cs/phone-menu-light.png"><img src="assets/cs/phone-menu.png" width="200" alt="Menu v sekcích"></picture></a><br><b>Menu v sekcích</b></td></tr>
<tr><td width="33%" align="center"><a href="assets/cs/phone-messages.png"><picture><source media="(prefers-color-scheme: light)" srcset="assets/cs/phone-messages-light.png"><img src="assets/cs/phone-messages.png" width="200" alt="Zprávy"></picture></a><br><b>Zprávy</b></td><td width="33%" align="center"><a href="assets/cs/phone-profiles.png"><picture><source media="(prefers-color-scheme: light)" srcset="assets/cs/phone-profiles-light.png"><img src="assets/cs/phone-profiles.png" width="200" alt="Profily (SSID)"></picture></a><br><b>Profily (SSID)</b></td><td width="33%" align="center"><a href="assets/cs/phone-tnc.png"><picture><source media="(prefers-color-scheme: light)" srcset="assets/cs/phone-tnc-light.png"><img src="assets/cs/phone-tnc.png" width="200" alt="TNC: TCP/IP, USB, Bluetooth, BLE"></picture></a><br><b>TNC: TCP/IP, USB, Bluetooth, BLE</b></td></tr>
<tr><td width="33%" align="center"><a href="assets/cs/phone-settings.png"><picture><source media="(prefers-color-scheme: light)" srcset="assets/cs/phone-settings-light.png"><img src="assets/cs/phone-settings.png" width="200" alt="Nastavení"></picture></a><br><b>Nastavení</b></td><td width="33%" align="center"><a href="assets/cs/phone-tak.png"><picture><source media="(prefers-color-scheme: light)" srcset="assets/cs/phone-tak-light.png"><img src="assets/cs/phone-tak.png" width="200" alt="Mapa TAK"></picture></a><br><b>Mapa TAK</b></td><td width="33%" align="center"><a href="assets/cs/phone-tak-chat.png"><picture><source media="(prefers-color-scheme: light)" srcset="assets/cs/phone-tak-chat-light.png"><img src="assets/cs/phone-tak-chat.png" width="200" alt="TAK GeoChat"></picture></a><br><b>TAK GeoChat</b></td></tr>
</table>

### Na počítači

<table>
<tr>
<td colspan="2"><a href="assets/cs/map.png"><picture><source media="(prefers-color-scheme: light)" srcset="assets/cs/map-light.png"><img src="assets/cs/map.png" alt="Mapa: symboly, převaděče s kmitočtem, nehoda, ocásky"></picture></a><br><sub>Mapa: symboly, převaděče s kmitočtem, nehoda, ocásky</sub></td>
</tr>
<tr>
<td width="50%"><a href="assets/cs/map-filter.png"><picture><source media="(prefers-color-scheme: light)" srcset="assets/cs/map-filter-light.png"><img src="assets/cs/map-filter.png" alt="Filtry mapy: nabídka zůstává při zaškrtávání otevřená"></picture></a><br><sub>Filtry mapy: nabídka zůstává při zaškrtávání otevřená</sub></td>
<td width="50%"><a href="assets/cs/map-repeaters.png"><picture><source media="(prefers-color-scheme: light)" srcset="assets/cs/map-repeaters-light.png"><img src="assets/cs/map-repeaters.png" alt="Jen převaděče s kmitočtem, pásmem a druhem provozu"></picture></a><br><sub>Jen převaděče s kmitočtem, pásmem a druhem provozu</sub></td>
</tr>
<tr>
<td width="50%"><a href="assets/cs/map-source.png"><picture><source media="(prefers-color-scheme: light)" srcset="assets/cs/map-source-light.png"><img src="assets/cs/map-source.png" alt="Volba mapy: online, stažená, základní offline"></picture></a><br><sub>Volba mapy: online, stažená, základní offline</sub></td>
<td width="50%"><a href="assets/cs/map-offline.png"><picture><source media="(prefers-color-scheme: light)" srcset="assets/cs/map-offline-light.png"><img src="assets/cs/map-offline.png" alt="Základní offline mapa (bez internetu)"></picture></a><br><sub>Základní offline mapa (bez internetu)</sub></td>
</tr>
<tr>
<td width="50%"><a href="assets/cs/messages.png"><picture><source media="(prefers-color-scheme: light)" srcset="assets/cs/messages-light.png"><img src="assets/cs/messages.png" alt="Zprávy: konverzace s počty nepřečtených, filtry a hledáním"></picture></a><br><sub>Zprávy: konverzace s počty nepřečtených, filtry a hledáním</sub></td>
<td width="50%"><a href="assets/cs/messages-unread.png"><picture><source media="(prefers-color-scheme: light)" srcset="assets/cs/messages-unread-light.png"><img src="assets/cs/messages-unread.png" alt="Jen nepřečtené konverzace"></picture></a><br><sub>Jen nepřečtené konverzace</sub></td>
</tr>
<tr>
<td width="50%"><a href="assets/cs/tracker-menu.png"><picture><source media="(prefers-color-scheme: light)" srcset="assets/cs/tracker-menu-light.png"><img src="assets/cs/tracker-menu.png" alt="Nabídka polohy a trackeru"></picture></a><br><sub>Nabídka polohy a trackeru</sub></td>
<td width="50%"><a href="assets/cs/station.png"><picture><source media="(prefers-color-scheme: light)" srcset="assets/cs/station-light.png"><img src="assets/cs/station.png" alt="Detail stanice: mapa, zpráva, katalogy značek"></picture></a><br><sub>Detail stanice: mapa, zpráva, katalogy značek</sub></td>
</tr>
<tr>
<td width="50%"><a href="assets/cs/thursday.png"><picture><source media="(prefers-color-scheme: light)" srcset="assets/cs/thursday-light.png"><img src="assets/cs/thursday.png" alt="#APRSThursday"></picture></a><br><sub>#APRSThursday</sub></td>
<td width="50%"><a href="assets/cs/stations.png"><picture><source media="(prefers-color-scheme: light)" srcset="assets/cs/stations-light.png"><img src="assets/cs/stations.png" alt="Stanice se vzdáleností a směrem"></picture></a><br><sub>Stanice se vzdáleností a směrem</sub></td>
</tr>
<tr>
<td width="50%"><a href="assets/cs/terminal.png"><picture><source media="(prefers-color-scheme: light)" srcset="assets/cs/terminal-light.png"><img src="assets/cs/terminal.png" alt="Terminál: připojeno k BBS přes AX.25"></picture></a><br><sub>Terminál: připojeno k BBS přes AX.25</sub></td>
<td width="50%"><a href="assets/cs/chat.png"><picture><source media="(prefers-color-scheme: light)" srcset="assets/cs/chat-light.png"><img src="assets/cs/chat.png" alt="Packet chat"></picture></a><br><sub>Packet chat</sub></td>
</tr>
<tr>
<td width="50%"><a href="assets/cs/monitor.png"><picture><source media="(prefers-color-scheme: light)" srcset="assets/cs/monitor-light.png"><img src="assets/cs/monitor.png" alt="Monitor rámců"></picture></a><br><sub>Monitor rámců</sub></td>
<td width="50%"><a href="assets/cs/settings-tracker.png"><picture><source media="(prefers-color-scheme: light)" srcset="assets/cs/settings-tracker-light.png"><img src="assets/cs/settings-tracker.png" alt="Tracker a upozornění před tebou"></picture></a><br><sub>Tracker a upozornění před tebou</sub></td>
</tr>
<tr>
<td width="50%"><a href="assets/cs/files.png"><picture><source media="(prefers-color-scheme: light)" srcset="assets/cs/files-light.png"><img src="assets/cs/files.png" alt="Soubory: příjem obrázku přes packet radio, průběh a zbývající čas"></picture></a><br><sub>Soubory: příjem obrázku přes packet radio, průběh a zbývající čas</sub></td>
<td width="50%"><a href="assets/cs/files-offer.png"><picture><source media="(prefers-color-scheme: light)" srcset="assets/cs/files-offer-light.png"><img src="assets/cs/files-offer.png" alt="Soubor od jiné stanice se nejdřív nabídne"></picture></a><br><sub>Soubor od jiné stanice se nejdřív nabídne</sub></td>
</tr>
<tr>
<td colspan="2"><a href="assets/cs/tak.png"><picture><source media="(prefers-color-scheme: light)" srcset="assets/cs/tak-light.png"><img src="assets/cs/tak.png" alt="TAK: stanice podle týmů a GeoChat"></picture></a><br><sub>TAK: stanice podle týmů a GeoChat</sub></td>
</tr>
<tr>
<td width="50%"><a href="assets/cs/bbs.png"><picture><source media="(prefers-color-scheme: light)" srcset="assets/cs/bbs-light.png"><img src="assets/cs/bbs.png" alt="BBS SERVER"></picture></a><br><sub>BBS SERVER</sub></td>
<td width="50%"><a href="assets/cs/bbs-confirm.png"><picture><source media="(prefers-color-scheme: light)" srcset="assets/cs/bbs-confirm-light.png"><img src="assets/cs/bbs-confirm.png" alt="BBS SERVER se zapíná opsáním věty"></picture></a><br><sub>BBS SERVER se zapíná opsáním věty</sub></td>
</tr>
<tr>
<td width="50%"><a href="assets/cs/settings.png"><picture><source media="(prefers-color-scheme: light)" srcset="assets/cs/settings-light.png"><img src="assets/cs/settings.png" alt="Nastavení: stanice a profily"></picture></a><br><sub>Nastavení: stanice a profily</sub></td>
<td width="50%"><a href="assets/cs/settings-tnc.png"><picture><source media="(prefers-color-scheme: light)" srcset="assets/cs/settings-tnc-light.png"><img src="assets/cs/settings-tnc.png" alt="TNC přes Bluetooth LE a frekvence rádia (VR-N76, UV-PRO, GA-5WB)"></picture></a><br><sub>TNC přes Bluetooth LE a frekvence rádia (VR-N76, UV-PRO, GA-5WB)</sub></td>
</tr>
<tr>
<td colspan="2"><a href="assets/cs/settings-more.png"><picture><source media="(prefers-color-scheme: light)" srcset="assets/cs/settings-more-light.png"><img src="assets/cs/settings-more.png" width="50%" alt="Nastavení: pozadí a obrazovka, zvuky"></picture></a><br><sub>Nastavení: pozadí a obrazovka, zvuky</sub></td>
</tr>
</table>

## Instalace (Windows)

Stáhněte **`aprs-kiss-…-windows-x64-setup.exe`** z
[posledního vydání](https://github.com/michalsiman/aprs-kiss-app/releases/latest) a spusťte ho, nebo vezměte
**`…-windows-x64.zip`** a rozbalte ho kamkoliv. Rádio na USB se v Nastavení ukáže jako COM port.

## Instalace (macOS)

Stáhněte **`aprs-kiss-…-macos.dmg`** z
[posledního vydání](https://github.com/michalsiman/aprs-kiss-app/releases/latest), otevřete ho a přetáhněte
*APRS & Packet* do Aplikací. Aplikace není podepsaná u Applu (bez placeného vývojářského účtu), takže
poprvé na ni **klikněte pravým › Otevřít › Otevřít**, nebo ji povolte v *Nastavení systému › Soukromí
a zabezpečení › Přesto otevřít*. Rádio na USB se v Nastavení ukáže jako `/dev/cu.usbserial…` /
`/dev/cu.usbmodem…`. Verze pro macOS se sestavuje na GitHubu bez Macu, na kterém by se dala vyzkoušet – **hledáme testery**:
napište do [issues](https://github.com/michalsiman/aprs-kiss-app/issues), jak to dopadlo.

## Instalace (Android)

Stáhněte v telefonu **`aprs-kiss-…-android.apk`** z
[posledního vydání](https://github.com/michalsiman/aprs-kiss-app/releases/latest) a otevřete ho; Android
se jednou zeptá, jestli smí prohlížeč nebo správce souborů instalovat aplikace. V telefonu se aplikace
připojuje k TNC **přes USB port telefonu** (Nastavení › Připojení: TNC na USB, přes OTG kabel nebo
redukci; Quansheng s KISS firmwarem F4HWN a další CDC-ACM TNC, kabely CP210x a FTDI; Android se jednou
zeptá, jestli to aplikaci povolí) nebo **po síti (KISS přes TCP)**: Direwolf na počítači, rádio sdílené
přes [`kiss_tcp_bridge.py`](https://github.com/michalsiman/aprs-kiss-ha/tree/main/bridge) nebo Wi-Fi TNC.
Obrazovky jsou upravené pro telefon a přepínají se v nabídce, která se vysune ze strany (☰). Polohu může aplikace
brát z **GPS telefonu** (Nastavení › GPS). BBS SERVER a USB GPS moduly jsou jen pro počítače.
Soubor .apk je podepsaný vlastním klíčem projektu, takže nová verze se nainstaluje přes předchozí (od 0.1.30;
starší je potřeba jednou odinstalovat); aplikace dá vědět, když nová verze vyjde, a stáhne ji.
Připravuje se vydání v Google Play.

## Instalace (iPhone, iPad)

Apple pouští aplikace do iPhonu jen přes App Store nebo podepsané vývojářským účtem, který tento
projekt nemá. Ve vydání je **nepodepsaný `aprs-kiss-…-ios-unsigned.ipa`**, který si do zařízení dáte
nástrojem pro sideloading jako [AltStore](https://altstore.io/) nebo [Sideloadly](https://sideloadly.io/);
ten ho podepíše vaším vlastním Apple ID (s bezplatným Apple ID je potřeba ho každých 7 dní obnovit).
K TNC se připojuje po síti nebo přes **Bluetooth LE** (KISS over BLE – klasický sériový Bluetooth iOS
aplikacím nedovolí).
**Na skutečném iPhonu ani iPadu zatím vyzkoušený není – hledáme testery:** pokud to můžete zkusit,
napište prosím, jak to dopadlo, do [issues](https://github.com/michalsiman/aprs-kiss-app/issues).

## Instalace (Linux)

**S automatickými aktualizacemi (Flatpak):** otevřete
**[michalsiman.github.io/aprs-kiss-app](https://michalsiman.github.io/aprs-kiss-app/)** a klikněte na
*Instalovat*, nebo spusťte

```bash
flatpak install https://michalsiman.github.io/aprs-kiss-app/aprs-kiss.flatpakref
```

(Bez `--user`: Správce aktualizací a Správce softwaru v Linux Mintu vidí jen celosystémovou
instalaci, takže tam se aktualizace objeví.) Funguje na každé distribuci s Flatpakem (Linux Mint,
Fedora, Ubuntu s Flatpakem, …). Nové verze pak chodí spolu s ostatními aktualizacemi z vlastního
podepsaného Flatpak repozitáře (otisk klíče `0E31 685C C5D6 4B8C 7837  B62F 66ED ABD8 50DC 14BD`).

**Nebo si stáhněte balíček** z [posledního vydání](https://github.com/michalsiman/aprs-kiss-app/releases/latest)
a otevřete ho dvojklikem:

- **`aprs-kiss-…-x86_64.flatpak`**: stejný Flatpak jako jeden soubor; aktualizuje se také
  z repozitáře výše (vydání od 0.1.5).
- **`aprs-kiss_…_amd64.deb`**: Debian, Ubuntu, Linux Mint (22.04 / Debian 12 a novější).
- **`aprs-kiss-…-linux-x86_64.tar.gz`**: rozbalte kamkoliv a spusťte `./aprs-kiss`.

Žádný z nich nepotřebuje Python. Pro TNC na USB sériovém portu musí být váš uživatel ve skupině
`dialout`: `sudo usermod -aG dialout $USER`, pak se odhlaste a znovu přihlaste.

### S Pythonem

Python 3.10 nebo novější.

```bash
pipx install "aprs-kiss[desktop] @ git+https://github.com/michalsiman/aprs-kiss-app"
aprs-kiss
```

Nebo ze zdrojových kódů:

```bash
git clone https://github.com/michalsiman/aprs-kiss-app && cd aprs-kiss-app
python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"
.venv/bin/flet run src/main.py      # nebo: .venv/bin/aprs-kiss
```

Při prvním spuštění se otevře **Nastavení**: zadejte svou značku, polohu a jak se dostat k TNC:

- **KISS přes TCP** – Direwolf (port 8001), nebo rádio sdílené po síti pomocí
  [`kiss_tcp_bridge.py`](https://github.com/michalsiman/aprs-kiss-ha/tree/main/bridge)
- **Sériový port** – rádio připojené k tomuto počítači; vyberte ho ze seznamu
  (názvy `/dev/serial/by-id/...` zůstanou stejné i po přepojení). Váš uživatel musí být ve skupině
  `dialout`: `sudo usermod -aG dialout $USER`, pak se odhlaste a znovu přihlaste.

Nastavení a historie zpráv jsou v `~/.local/share/aprs-kiss/` (změníte proměnnou `APRS_KISS_DATA`).

### Vyzkoušení bez rádia

```bash
.venv/bin/python tests/fake_tnc.py --port 8001 --mycall OK1SIM-7
```

Simulované TNC: každých pár sekund přijdou stanice, meteo hlášení a zprávy, potvrzuje vaše zprávy,
odpovídá v chatu a provozuje malou BBS (`OK0BBS`: H, L, B). Aplikaci nasměrujte na
`127.0.0.1:8001`. S `--tak` posílá i TAK stanice a GeoChat pro režim TAK.

```bash
.venv/bin/python tests/fake_vara.py --port 8300
```

Simulovaná VARA FM pro terminál: v Nastavení › VARA FM zadejte `127.0.0.1`, port 8300, a připojte se
přes *Připojení: VARA FM* na libovolnou značku (odpoví malá BBS: L, B; `NOANSWER` neodpoví nikdy).

### Balíčky

Workflow *Release packages* jednou spustí `flet build linux` a z výsledku udělá archiv, `.deb`
(`packaging/deb/build-deb.sh`) a Flatpak (`packaging/flatpak/`), které připojí ke každému vydání
`v*`. Položka do menu, AppStream metainfo a ikony jsou v `packaging/linux/`.

## Jak je postavená

```
src/
  aprs_kiss_core/   rádio, bez uživatelského rozhraní: KISS, AX.25 (UI i spojení), APRS,
                    APRS-IS/iGate, stanice (potvrzení, opakování, limity), BBS server (bbs/),
                    TAK (tak.py), USB GPS (gps.py), VARA FM (vara.py), APRS Thursday (thursday.py),
                    spoty (spotting.py), služby na APRS (services.py), způsoby připojení TNC
                    (android_usb.py, android_bt.py, ble.py) a Engine, který to spojuje a hlásí
                    události posluchačům
  aprs_kiss_app/    uživatelské rozhraní ve Fletu: jedna obrazovka = jeden view; data offline mapy (offline/)
  main.py           vstupní bod pro `flet run` / `flet build`
packages/
  flet-ble-kiss/    vlastní rozšíření Fletu: KISS přes Bluetooth LE v Dartu (universal_ble)
tests/              testy jednotek, testy enginu proti fake_tnc.py a fake_vara.py
```

- **Flet** (Python, vykresluje Flutter): jeden kód pro počítač i mobil, nativní okno,
  žádný webový server.
- **Způsoby připojení jsou rozšiřitelné** (`aprs_kiss_core.connection.register_transport`): TCP
  a sériový port jsou vestavěné; USB na Androidu, klasický Bluetooth (SPP) a Bluetooth LE jsou vlastní
  způsoby připojení bez zásahu do kódu KISS/AX.25. Bluetooth LE jde přes vlastní rozšíření Fletu
  (`packages/flet-ble-kiss`), které `flet build` přidá do sestavení pro každou platformu; při spuštění
  ze zdrojáků bez něj se Bluetooth LE prostě nenabízí.
- Moduly jádra jsou stejné jako v integraci pro Home Assistant (tam `hub.py`, tady `engine.py`).
  V plánu je vydat jádro jako jeden balíček, který budou používat obě.

Soukromí: aplikace nic nesbírá; viz [zásady ochrany osobních údajů](https://michalsiman.github.io/aprs-kiss-app/privacy.html).

## Platformy

Linux, Windows a Android se používají každý den; macOS a iOS se sestavují, ale nejsou vyzkoušené (hledáme testery).

| | Linux | Windows | macOS (nevyzkoušeno) | Android | iOS (nevyzkoušeno) |
|---|---|---|---|---|---|
| KISS přes TCP | ✅ | ✅ | ✅ | ✅ | ✅ (sideloading) |
| USB sériový port | ✅ | ✅ (COM porty) | ✅ | ✅ (OTG: CDC-ACM, CP210x, FTDI) | ❌ (iOS) |
| Bluetooth TNC (SPP) | ✅ (jako sériový port: rfcomm) | ✅ (jako COM port) | – | ✅ (spárované, v Nastavení) | ❌ (jen BLE) |
| Bluetooth LE TNC (KISS over BLE) | ✅ | ✅ | ✅ | ✅ | ✅ |
| USB GPS modul | ✅ | ✅ (COM porty) | ✅ | – | ❌ |
| GPS telefonu | – | – | – | ✅ | ✅ |
| VARA FM | ✅ (VARA ve Wine) | ✅ | VARA na jiném počítači | VARA na jiném počítači | VARA na jiném počítači |
| BBS SERVER | ✅ | ✅ | ✅ | – (jen počítače) | – (jen počítače) |
| Běh na pozadí | ✅ | ✅ | ✅ | ✅ (v Nastavení, s notifikací) | omezeno iOS |
| Nezhasínání obrazovky, zvuky | ✅ | ✅ | ✅ | ✅ | ✅ |

## Testy

```bash
.venv/bin/python -m unittest discover -s tests -t .
```

## Autoři a licence

- Napsal [Michal Šiman](https://github.com/michalsiman) ([OK1SIM](https://ok1sim.cz/)) společně
  s [Claude Code](https://claude.com/claude-code).
- Uživatelské rozhraní [Flet](https://flet.dev) (Flutter), mapy [flutter_map](https://github.com/fleaflet/flutter_map)
  přes flet-map, mapová data © přispěvatelé OpenStreetMap.
- Offline mapa z [Natural Earth](https://www.naturalearthdata.com/) (volné dílo) a
  [GeoNames](https://www.geonames.org/) (CC BY 4.0).
- Zpracování APRS [aprslib](https://github.com/rossengeorgiev/aprs-python).
- [Firmware F4HWN](https://github.com/armel/uv-k1-k5v3-firmware-custom) pro Quansheng UV-K1/K5 V3 od **Armela F4HWN**,
  jeho [aplikace KISS TNC](https://github.com/armel/uv-k1-k5v3-firmware-custom/wiki/App-KISS-TNC) od **F4WAT**.

Licence MIT, viz [LICENSE](LICENSE).

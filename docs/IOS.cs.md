# APRS & Packet na iPhonu a iPadu

*[English](IOS.md) · také na [webu](https://aprs.ok1sim.cz/ios.html)*

Aplikace zatím není v App Storu. Vyzkoušet ji ale můžeš hned: počítač ji podepíše tvým vlastním Apple ID a
nahraje do telefonu. S bezplatným Apple ID vydrží **7 dní**, pak ji stačí obnovit jedním kliknutím. Zabere to
asi 15 minut.

**Hledáme testery:** iOS verze se sestavuje, ale na skutečném iPhonu ji ještě nikdo nezkoušel. Napiš prosím,
jak to dopadlo, do [issues](https://github.com/michalsiman/aprs-kiss-app/issues). Hlavně když to nepůjde.

## Co potřebuješ

- **iPhone nebo iPad** s iOS 15 nebo novějším a USB kabel
- **Počítač s Windows nebo macOS** (z Linuxu to oficiálně nejde)
- **Apple ID**: stačí běžné bezplatné. Doporučujeme si na to založit vedlejší Apple ID, protože heslo se
  zadává do aplikace třetí strany.
- **TNC po síti nebo přes Bluetooth LE**: iOS nedovolí aplikacím USB sériový port ani klasický Bluetooth.
  Funguje KISS přes TCP (Direwolf, síťové TNC,
  [kiss_tcp_bridge](https://github.com/michalsiman/aprs-kiss-ha/tree/main/bridge)) a KISS přes BLE (VR-N76,
  UV-PRO, Mobilinkd TNC4…). APRS-IS jde i bez TNC.

## 1. Stáhni aplikaci

Z [posledního vydání](https://github.com/michalsiman/aprs-kiss-app/releases/latest) stáhni do počítače
`aprs-kiss-…-ios-unsigned.ipa`.

## 2. Nainstaluj Sideloadly

- Stáhni [Sideloadly](https://sideloadly.io/) pro Windows nebo macOS a nainstaluj ho.
- **Windows:** potřebuje ještě **iTunes** a **iCloud**. Stáhni je **přímo z webu Apple**, verze z Microsoft
  Store nefungují. Odkazy jsou na stránce Sideloadly.
- Připoj iPhone kabelem, odemkni ho a potvrď *Důvěřovat tomuto počítači*.

## 3. Nahraj aplikaci do telefonu

1. Spusť Sideloadly a nahoře vyber svůj iPhone.
2. Přetáhni stažený `.ipa` do okna (nebo klikni na ikonu IPA).
3. Do *Apple ID* zadej e-mail svého Apple ID a klikni na **Start**. Zeptá se na heslo a případně na
   ověřovací kód.
4. Počkej na *Done*. Na ploše telefonu se objeví APRS & Packet.

## 4. Povol aplikaci v telefonu

1. Otevři **Nastavení › Obecné › Správa VPN a zařízení**, klepni na své Apple ID a dej **Důvěřovat**.
2. **iOS 16 a novější:** zapni **Nastavení › Soukromí a zabezpečení › Režim pro vývojáře** a telefon
   restartuj. Položka se ukáže až po nahrání první aplikace.
3. Spusť APRS & Packet, povol Bluetooth a polohu a v **Nastavení › Připojení** zvol TNC.

## 5. Po 7 dnech

S bezplatným Apple ID aplikace po 7 dnech přestane startovat (data v ní zůstanou). Připoj telefon a v
Sideloadly dej znovu **Start** se stejným souborem. Nebo v Sideloadly zapni *automatické obnovování* a
postará se o to sám, když je počítač zapnutý a telefon na stejné Wi-Fi. Stejně nahraješ i novou verzi.
S placeným vývojářským účtem Apple (99 USD ročně) vydrží aplikace rok.

## Když něco nejde

- **Sideloadly nevidí telefon:** na Windows musí být iTunes z webu Apple, ne z Microsoft Store. Odemkni
  telefon, zkus jiný kabel a potvrď *Důvěřovat*.
- **„Maximum number of apps“ nebo „App ID limit“:** bezplatné Apple ID může mít najednou nejvýš 3 takto
  nahrané aplikace a 10 nových App ID za týden. Smaž v telefonu jinou nahranou aplikaci, nebo týden počkej.
- **Aplikace se hned zavře:** zkontroluj krok 4 (Důvěřovat a Režim pro vývojáře). Pokud to nepomůže, pošli
  nám do issues verzi iOS a model telefonu.
- **Bez Sideloadly:** stejně funguje [AltStore](https://altstore.io/). Na počítači s Windows nebo macOS
  spusť AltServer, pak otevři `.ipa` v aplikaci AltStore v telefonu, která ji obnovuje přes Wi-Fi.

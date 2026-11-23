# Google Play – co je připravené a co zbývá

Aplikace zatím **není** v Google Play. Tady je všechno, co je k tomu potřeba, aby se dala kdykoli zveřejnit.

## Připravené v projektu

- **Balíček pro Google Play (`.aab`)** – vydání na GitHubu ho přikládá jako `aprs-kiss-X.Y.Z-google-play.aab`,
  jakmile jsou nastavená tajemství `ANDROID_KEYSTORE_B64` a `ANDROID_KEYSTORE_PASSWORD` (bez nich se nevyrábí:
  Google Play potřebuje pokaždé stejný klíč).
- **Verze pro Google Play se sama neaktualizuje** – nemá kontrolu nových verzí ani stahování `.apk`
  (to pravidla Google Play zakazují); aktualizuje ji Google Play. Řídí to `src/aprs_kiss_app/distribution.py`,
  který workflow při sestavení `.aab` přepne na `play`.
- **Číslo sestavení (versionCode)** roste s verzí: 0.1.28 → 1028 (Google Play odmítne stejné nebo nižší).
- **Cílová verze Androidu**: `target_sdk_version = 36` (Android 16) v `pyproject.toml`.
- **Upozornění při prvním spuštění** (licence, rušení, odpovědnost) – je třeba ho přijmout.
- **Zásady ochrany osobních údajů**: https://michalsiman.github.io/aprs-kiss-app/privacy.html
  (zdroj `packaging/flatpak/site/privacy.html`, zveřejní se s dalším vydáním).
- **Podklady do obchodu** v této složce:
  - `listing-en.txt`, `listing-cs.txt` – název, krátký a úplný popis,
  - `icon-512.png` – ikona 512×512,
  - `feature-graphic-1024x500.png` – úvodní obrázek,
  - `screenshots/` – 4 snímky telefonu 1030×2060.

## Zbývá udělat (ručně, v Play Console)

1. Nastavit na GitHubu tajemství s klíčem (příkazy výše v historii; klíč `~/.config/aprs-kiss/android-release.jks`).
   Klíč a heslo **nikdy neztratit** – bez nich nejde vydat aktualizaci.
2. Založit vývojářský účet na https://play.google.com/console (25 USD jednorázově, ověření totožnosti).
3. Vytvořit aplikaci: název *APRS & Packet*, výchozí jazyk, *Aplikace*, *Zdarma*.
4. **Podepisování aplikací Google Play**: nechat Google spravovat podpisový klíč; náš klíč je *upload key*.
5. Vyplnit **Obsah aplikace**:
   - Zásady ochrany soukromí – odkaz výše.
   - Reklamy – ne.
   - Přístup k aplikaci – vše je dostupné bez přihlášení.
   - Hodnocení obsahu – dotazník (komunikace, bez násilí atd.).
   - Cílové publikum – 18+ (není pro děti).
   - **Bezpečnost dat**: shromažďuje se *poloha (přesná)* – jen v zařízení a v hlášení polohy, které uživatel sám
     vysílá / posílá do APRS-IS; nic se nesdílí s autorem ani třetími stranami k reklamě/analytice; šifrování
     při přenosu: APRS-IS je nešifrovaný (to je v pořádku uvést); smazání dat: odinstalací.
   - Oprávnění k poloze – jen při používání (ne na pozadí): „poloha pro mapu a APRS maják“.
6. **Uzavřený test**: nahrát `.aab`, přidat aspoň **12 testerů** (e-maily), nechat běžet **14 dní**
   (povinné u nových osobních účtů), pak požádat o produkční přístup.
7. **Záznam v obchodě**: texty z `listing-*.txt`, obrázky z této složky, kategorie *Komunikace*, kontakt.
8. Po schválení zveřejnit. Každá další verze: tag → GitHub vytvoří nový `.aab` → nahrát do Play Console.

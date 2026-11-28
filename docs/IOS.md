# APRS & Packet on an iPhone or iPad

*[Česky](IOS.cs.md) · also on the [website](https://aprs.ok1sim.cz/ios.html)*

The app is not in the App Store yet. You can try it right now, though: a computer signs it with your own
Apple ID and puts it on your phone. With a free Apple ID it runs for **7 days**, then you refresh it with one
click. It takes about 15 minutes.

**Testers wanted:** the iOS version is built, but nobody has tried it on a real iPhone yet. Please tell us how
it went in the [issues](https://github.com/michalsiman/aprs-kiss-app/issues), especially if it does not work.

## What you need

- **An iPhone or iPad** with iOS 15 or later, and a USB cable
- **A Windows or macOS computer** (there is no official way from Linux)
- **An Apple ID**: a normal free one is enough. Consider a spare Apple ID for this, since its password goes
  into a third-party app.
- **A TNC on the network or over Bluetooth LE**: iOS lets apps use no USB serial port and no classic
  Bluetooth. KISS over TCP works (Direwolf, a network TNC,
  [kiss_tcp_bridge](https://github.com/michalsiman/aprs-kiss-ha/tree/main/bridge)), and so does KISS over BLE
  (VR-N76, UV-PRO, Mobilinkd TNC4…). APRS-IS works without a TNC.

## 1. Download the app

From the [latest release](https://github.com/michalsiman/aprs-kiss-app/releases/latest), download
`aprs-kiss-…-ios-unsigned.ipa` to the computer.

## 2. Install Sideloadly

- Download [Sideloadly](https://sideloadly.io/) for Windows or macOS and install it.
- **Windows:** it also needs **iTunes** and **iCloud**. Get them **straight from Apple's website**, because
  the Microsoft Store versions do not work. Sideloadly's page links them.
- Connect the iPhone with the cable, unlock it and confirm *Trust This Computer*.

## 3. Put the app on the phone

1. Start Sideloadly and pick your iPhone at the top.
2. Drag the downloaded `.ipa` into the window (or click the IPA icon).
3. Enter your Apple ID e-mail under *Apple ID* and click **Start**. It asks for the password and maybe a
   verification code.
4. Wait for *Done*. APRS & Packet appears on the phone's home screen.

## 4. Allow the app on the phone

1. Go to **Settings › General › VPN & Device Management**, tap your Apple ID and choose **Trust**.
2. **iOS 16 and later:** switch on **Settings › Privacy & Security › Developer Mode** and restart the phone.
   The item shows up only after the first app is installed.
3. Start APRS & Packet, allow Bluetooth and location, and pick the TNC in **Settings › Connection**.

## 5. After 7 days

With a free Apple ID the app stops starting after 7 days (its data stays). Connect the phone and click
**Start** in Sideloadly again with the same file. Or switch on *automatic refresh* in Sideloadly and it does
this by itself while the computer is on and the phone is on the same Wi-Fi. A new version goes on the same
way. With a paid Apple developer account (99 USD a year) the app lasts a year.

## When something does not work

- **Sideloadly does not see the phone:** on Windows, iTunes has to come from Apple's website, not the
  Microsoft Store. Unlock the phone, try another cable and confirm *Trust*.
- **"Maximum number of apps" or "App ID limit":** a free Apple ID can have at most 3 sideloaded apps at a
  time and 10 new App IDs a week. Delete another sideloaded app or wait a week.
- **The app closes at once:** check step 4 (Trust and Developer Mode). If that does not help, send us the iOS
  version and the phone model in the issues.
- **Without Sideloadly:** [AltStore](https://altstore.io/) works the same way. Run AltServer on a Windows or
  macOS computer, then open the `.ipa` in the AltStore app on the phone, which refreshes it over Wi-Fi.

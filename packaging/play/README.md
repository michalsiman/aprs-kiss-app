# Google Play – what is ready and what is left

The app is **not** on Google Play yet. Everything needed to publish it later is here; the step-by-step
checklist (Play Console forms, the closed test with 12 testers for 14 days, Data safety answers) is in
[README.cs.md](README.cs.md).

Ready in the project:

- `aprs-kiss-X.Y.Z-google-play.aab` attached to each GitHub release once the signing secrets
  `ANDROID_KEYSTORE_B64` and `ANDROID_KEYSTORE_PASSWORD` are set (the upload key must be the same every time).
- The Google Play build has no new-version check and no .apk download (Google Play policy);
  `src/aprs_kiss_app/distribution.py` is switched to `play` by the release workflow for that build.
- versionCode grows with the version (0.1.28 → 1028); `target_sdk_version = 36`.
- A first-start warning that has to be accepted (licence, interference, responsibility).
- Privacy policy: https://michalsiman.github.io/aprs-kiss-app/privacy.html (`packaging/flatpak/site/privacy.html`).
- Store listing: `listing-en.txt`, `listing-cs.txt`, `icon-512.png`, `feature-graphic-1024x500.png`, `screenshots/`.

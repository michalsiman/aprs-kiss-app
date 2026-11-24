#!/usr/bin/env python3
"""Add the USB device filter to the main activity of Flet's build template.

Android shows "Open APRS & Packet to handle <device>?" when a radio is plugged in only if the activity
has the USB_DEVICE_ATTACHED intent filter (pyproject: tool.flet.android.activity) AND a <meta-data>
pointing to the list of devices (src/android_res/xml/device_filter.xml). Flet 1.1.2's template has no
place for activity meta-data, so the release workflow downloads the template, adds the line here and
builds the Android app from it:  python3 packaging/android/patch_template.py <template>/build
"""

import sys
from pathlib import Path

ANCHOR = "<!-- flet: end of activity intent filters {% endfor %} -->"
LINE = ('\n            <meta-data android:name="android.hardware.usb.action.USB_DEVICE_ATTACHED"'
        ' android:resource="@xml/device_filter" />')

manifest = Path(sys.argv[1]) / "{{cookiecutter.out_dir}}" / "android" / "app" / "src" / "main" / "AndroidManifest.xml"
text = manifest.read_text(encoding="utf-8")
if "USB_DEVICE_ATTACHED" not in text:
    if ANCHOR not in text:
        sys.exit(f"The template changed: no '{ANCHOR}' in {manifest}")
    manifest.write_text(text.replace(ANCHOR, ANCHOR + LINE, 1), encoding="utf-8")
print("USB device filter added to", manifest)

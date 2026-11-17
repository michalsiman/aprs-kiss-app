"""Entry point of the APRS & Packet app (`flet run` / `flet build` start here)."""

import flet as ft

from aprs_kiss_app.app import main

if __name__ == "__main__":
    ft.run(main)

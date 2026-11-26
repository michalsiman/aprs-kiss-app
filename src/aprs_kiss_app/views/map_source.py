"""Which map is under the stations: OpenStreetMap online, the user's imported map, or the bundled one.

One button on the map (and on the TAK map) opens a short menu with the three; its icon shows the
current one. Without internet the app falls back to an offline map by itself, the imported one
when there is one and it was not switched off.
"""

from __future__ import annotations

import flet as ft

from .base import stay_item

ICONS = {"online": ft.Icons.CLOUD_OUTLINED, "imported": ft.Icons.TERRAIN, "basic": ft.Icons.CLOUD_OFF}


LABEL_WIDTH = 170  # the round mark, the icon and this fit a pop-up menu (Flutter: at most 280 wide)


def _label(text: str) -> ft.Control:
    """"Online map (OpenStreetMap)": the part in brackets on a second, smaller line, so long names
    stay inside the menu on a phone."""
    if text.endswith(")") and " (" in text:
        main, sub = text[:-1].split(" (", 1)
        return ft.Column([ft.Text(main, max_width=LABEL_WIDTH),
                          ft.Text(sub, size=12, color=ft.Colors.ON_SURFACE_VARIANT, max_width=LABEL_WIDTH)],
                         spacing=0, tight=True)
    return ft.Text(text, max_width=LABEL_WIDTH)  # a long name (Slovenian…) wraps inside the menu


def _choice_icon(icon, on: bool) -> ft.Control:
    """One of several, only one chosen: a round mark (an empty faint ring when not chosen) and the icon."""
    mark = ft.Icon(ft.Icons.RADIO_BUTTON_CHECKED if on else ft.Icons.RADIO_BUTTON_UNCHECKED, size=22,
                   color=ft.Colors.PRIMARY if on else ft.Colors.with_opacity(0.4, ft.Colors.ON_SURFACE))
    return ft.Row([mark, ft.Icon(icon)], spacing=12, tight=True)


class MapSourceButton:
    def __init__(self, app, extra: list | None = None) -> None:
        self.app = app
        t = app.t
        # a choice leaves the menu open (the mark moves); back or a tap outside closes it
        self.items, self.boxes = {}, {}
        for key in ("online", "imported", "basic"):
            self.items[key], self.boxes[key] = stay_item(ft.Text(""), lambda _e, k=key: self._pick(k))
        manage = ft.PopupMenuItem(t("map_src_manage"), icon=ft.Icons.FOLDER_OPEN,
                                  on_click=lambda _e: app.select("settings"))
        self.icon = ft.Icon(ICONS["online"])
        self.face = ft.Container(self.icon, padding=8, shape=ft.BoxShape.CIRCLE)
        self.control = ft.PopupMenuButton(content=self.face, tooltip=t("map_source"),
                                          items=[*self.items.values(), ft.PopupMenuItem(), *(extra or []), manage])
        self.refresh()

    def refresh(self) -> None:
        mode = self.app.map_mode()
        has_imported = self.app.has_imported_maps()
        texts = {"online": "map_src_online", "imported": "map_src_imported" if has_imported else "map_src_none",
                 "basic": "map_src_basic"}
        for key, box in self.boxes.items():
            box.content = ft.Row([_choice_icon(ICONS[key], key == self.app.wanted_map_mode()),
                                  _label(self.app.t(texts[key]))], spacing=12, tight=True,
                                 vertical_alignment=ft.CrossAxisAlignment.CENTER)
        self.items["imported"].disabled = self.boxes["imported"].disabled = not has_imported
        self.icon.icon = ICONS[mode]
        self.icon.color = ft.Colors.PRIMARY if mode != "online" else None
        self.face.bgcolor = ft.Colors.with_opacity(0.18, ft.Colors.PRIMARY) if mode != "online" else None

    def _pick(self, mode: str) -> None:
        self.app.set_map_mode(mode)

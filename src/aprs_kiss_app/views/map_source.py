"""Which map is under the stations: OpenStreetMap online, the user's imported map, or the bundled one.

One button on the map (and on the TAK map) opens a short menu with the three; its icon shows the
current one. Without internet the app falls back to an offline map by itself, the imported one
when there is one and it was not switched off.
"""

from __future__ import annotations

import flet as ft

ICONS = {"online": ft.Icons.CLOUD_OUTLINED, "imported": ft.Icons.TERRAIN, "basic": ft.Icons.CLOUD_OFF}


class MapSourceButton:
    def __init__(self, app, extra: list | None = None) -> None:
        self.app = app
        t = app.t
        self.items = {
            "online": ft.PopupMenuItem(t("map_src_online"), icon=ICONS["online"],
                                       on_click=lambda _e: self._pick("online")),
            "imported": ft.PopupMenuItem(t("map_src_imported"), icon=ICONS["imported"],
                                         on_click=lambda _e: self._pick("imported")),
            "basic": ft.PopupMenuItem(t("map_src_basic"), icon=ICONS["basic"],
                                      on_click=lambda _e: self._pick("basic")),
        }
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
        for key, item in self.items.items():
            item.checked = key == self.app.wanted_map_mode()
        self.items["imported"].disabled = not has_imported
        self.items["imported"].content = self.app.t("map_src_imported" if has_imported else "map_src_none")
        self.icon.icon = ICONS[mode]
        self.icon.color = ft.Colors.PRIMARY if mode != "online" else None
        self.face.bgcolor = ft.Colors.with_opacity(0.18, ft.Colors.PRIMARY) if mode != "online" else None

    def _pick(self, mode: str) -> None:
        self.app.set_map_mode(mode)

"""The phone's menu (the ☰ drawer), drawn by the app: flat rows, the chosen one with a coloured bar at the left
edge, a faint tint of the whole row and its icon and text in the accent colour (like Slack, Discord, VS Code),
small grey section headings, an unread count as a pill at the right."""

from __future__ import annotations

import flet as ft

ROW_HEIGHT = 48


class MenuRow:
    def __init__(self, icon, selected_icon, label: str, on_click) -> None:
        self.plain, self.chosen_icon = icon, selected_icon or icon
        self.icon = ft.Icon(icon, size=22)
        self.text = ft.Text(label, size=15, no_wrap=True, overflow=ft.TextOverflow.ELLIPSIS, expand=True)
        self.badge_text = ft.Text("", size=11, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE)
        self.badge = ft.Container(self.badge_text, bgcolor=ft.Colors.RED_600, border_radius=10, visible=False,
                                  padding=ft.Padding.symmetric(horizontal=7, vertical=1))
        self.bar = ft.Container(width=4, height=28, border_radius=ft.BorderRadius.only(top_right=3, bottom_right=3))
        self.control = ft.Container(
            ft.Row([self.bar, ft.Container(width=16), self.icon, ft.Container(width=16), self.text, self.badge,
                    ft.Container(width=16)], spacing=0, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            height=ROW_HEIGHT, on_click=on_click, ink=True)
        self.set_selected(False)

    def set_selected(self, on: bool) -> None:
        self.bar.bgcolor = ft.Colors.PRIMARY if on else ft.Colors.TRANSPARENT
        self.control.bgcolor = ft.Colors.with_opacity(0.10, ft.Colors.PRIMARY) if on else None
        self.icon.icon = self.chosen_icon if on else self.plain
        self.icon.color = ft.Colors.PRIMARY if on else ft.Colors.ON_SURFACE_VARIANT
        self.text.color = ft.Colors.PRIMARY if on else ft.Colors.ON_SURFACE
        self.text.weight = ft.FontWeight.W_600 if on else ft.FontWeight.NORMAL

    def set_badge(self, text: str | None) -> None:
        self.badge.visible = bool(text)
        self.badge_text.value = text or ""


def heading(text: str) -> ft.Control:
    """A section's name: small, grey, spaced capitals."""
    return ft.Container(ft.Text(text.upper(), size=11, weight=ft.FontWeight.W_600, color=ft.Colors.ON_SURFACE_VARIANT,
                                style=ft.TextStyle(letter_spacing=1.2)),
                        padding=ft.Padding.only(left=20, top=18, bottom=6))


def header(title: str, subtitle: str) -> ft.Control:
    return ft.Container(ft.Column([ft.Text(title, size=19, weight=ft.FontWeight.BOLD),
                                   ft.Text(subtitle, size=12, color=ft.Colors.ON_SURFACE_VARIANT)], spacing=2),
                        padding=ft.Padding.only(left=20, top=22, bottom=6))


def divider() -> ft.Control:
    return ft.Container(ft.Divider(height=1), padding=ft.Padding.symmetric(vertical=8))

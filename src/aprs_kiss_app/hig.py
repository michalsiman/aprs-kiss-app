"""Experimental look after Apple's Human Interface Guidelines (HIG) – the "hig" branch only.

What it changes compared with the Material look of the main version:
- Apple's system colours (systemBlue accent, systemGreen / Red / Orange for states), grouped
  backgrounds: a light grey page with white rounded groups (in dark mode black with dark grey groups);
- the iOS / macOS type scale (Body 17 pt on a phone, a smaller macOS scale on a computer);
- controls: green switches, round check marks, filled rounded buttons without shadows, text fields
  as grey rounded fills without a frame, rounded dialogs and message bars, no ink ripples;
- navigation: a sidebar on a computer (like macOS apps) and a tab bar at the bottom of a phone with
  "More" for the rest (like iOS apps) instead of the Material rail and the slide-in menu.
"""

from __future__ import annotations

import flet as ft

# Apple system colours (light, dark)
BLUE = ("#007AFF", "#0A84FF")
GREEN = ("#34C759", "#30D158")
RED = ("#FF3B30", "#FF453A")
ORANGE = ("#FF9500", "#FF9F0A")
GRAY = ("#8E8E93", "#8E8E93")

RADIUS = 10          # buttons, fields
GROUP_RADIUS = 12    # grouped sections, cards
DIALOG_RADIUS = 14


def system(color: tuple[str, str], dark: bool) -> str:
    return color[1] if dark else color[0]


def _scheme(dark: bool) -> ft.ColorScheme:
    if dark:
        return ft.ColorScheme(
            primary=BLUE[1], on_primary="#FFFFFF", primary_container="#0A2A4D", on_primary_container="#8EC5FF",
            secondary=GRAY[1], on_secondary="#FFFFFF", secondary_container="#2C2C2E", on_secondary_container="#FFFFFF",
            tertiary="#BF5AF2", on_tertiary="#FFFFFF", tertiary_container="#3A2147", on_tertiary_container="#E5B8FA",
            error=RED[1], on_error="#FFFFFF", error_container="#4A1512", on_error_container="#FFB4AE",
            surface="#000000", on_surface="#FFFFFF", on_surface_variant="#8D8D93",
            outline="#38383A", outline_variant="#2C2C2E", shadow="#000000", scrim="#000000",
            inverse_surface="#F2F2F7", on_inverse_surface="#000000", inverse_primary=BLUE[0],
            surface_tint="#00000000",
            surface_container_lowest="#000000", surface_container_low="#1C1C1E", surface_container="#1C1C1E",
            surface_container_high="#2C2C2E", surface_container_highest="#3A3A3C",
            surface_bright="#2C2C2E", surface_dim="#000000",
        )
    return ft.ColorScheme(
        primary=BLUE[0], on_primary="#FFFFFF", primary_container="#E3EEFF", on_primary_container="#004FA8",
        secondary=GRAY[0], on_secondary="#FFFFFF", secondary_container="#E5E5EA", on_secondary_container="#000000",
        tertiary="#AF52DE", on_tertiary="#FFFFFF", tertiary_container="#F3E3FA", on_tertiary_container="#5A1F78",
        error=RED[0], on_error="#FFFFFF", error_container="#FFE5E3", on_error_container="#A0150D",
        surface="#F2F2F7", on_surface="#000000", on_surface_variant="#6C6C70",
        outline="#C6C6C8", outline_variant="#E5E5EA", shadow="#000000", scrim="#000000",
        inverse_surface="#1C1C1E", on_inverse_surface="#FFFFFF", inverse_primary=BLUE[1],
        surface_tint="#00000000",
        surface_container_lowest="#FFFFFF", surface_container_low="#FFFFFF", surface_container="#FFFFFF",
        surface_container_high="#E9E9EB", surface_container_highest="#D1D1D6",
        surface_bright="#FFFFFF", surface_dim="#E5E5EA",
    )


def _type(phone: bool) -> ft.TextTheme:
    """iOS: Large Title 34, Title1 28, Title2 22, Title3 20, Headline 17 semibold, Body 17, Callout 16,
    Subhead 15, Footnote 13, Caption 12. macOS is smaller (Body 13); a computer gets a scale in between."""
    s = (lambda n: n) if phone else (lambda n: round(n * 0.82))
    st = lambda n, w=None: ft.TextStyle(size=s(n), weight=w, color=ft.Colors.ON_SURFACE)  # noqa: E731
    semi = ft.FontWeight.W_600
    return ft.TextTheme(
        display_small=st(34, ft.FontWeight.BOLD), headline_medium=st(28, ft.FontWeight.BOLD),
        headline_small=st(22, ft.FontWeight.BOLD),
        title_large=st(20, semi), title_medium=st(17, semi), title_small=st(15, semi),
        body_large=st(17), body_medium=st(15), body_small=st(13),
        label_large=st(17), label_medium=st(13), label_small=st(12),
    )


def theme(dark: bool, phone: bool) -> ft.Theme:
    accent = system(BLUE, dark)
    fill = "#2C2C2E" if dark else "#E9E9EB"            # tertiary system fill: fields, grey buttons
    group = "#1C1C1E" if dark else "#FFFFFF"
    sep = "#38383A" if dark else "#C6C6C8"
    shape = ft.RoundedRectangleBorder(radius=RADIUS)
    btn_pad = ft.Padding.symmetric(horizontal=16 if phone else 14, vertical=11 if phone else 8)
    label = ft.TextStyle(size=17 if phone else 14, weight=ft.FontWeight.W_500)
    return ft.Theme(
        color_scheme=_scheme(dark),
        use_material3=True,
        text_theme=_type(phone),
        visual_density=ft.VisualDensity.STANDARD if phone else ft.VisualDensity.COMPACT,
        scaffold_bgcolor=_scheme(dark).surface,
        canvas_color=group,
        splash_color=ft.Colors.TRANSPARENT,                  # no Material ink ripples
        highlight_color=ft.Colors.with_opacity(0.10, ft.Colors.ON_SURFACE),
        hover_color=ft.Colors.with_opacity(0.05, ft.Colors.ON_SURFACE),
        divider_color=sep,
        page_transitions=ft.PageTransitionsTheme(
            android=ft.PageTransitionTheme.CUPERTINO, ios=ft.PageTransitionTheme.CUPERTINO,
            linux=ft.PageTransitionTheme.CUPERTINO, macos=ft.PageTransitionTheme.CUPERTINO,
            windows=ft.PageTransitionTheme.CUPERTINO),
        filled_button_theme=ft.FilledButtonTheme(style=ft.ButtonStyle(
            shape=shape, padding=btn_pad, elevation=0, text_style=label, bgcolor=accent, color="#FFFFFF")),
        # "tinted" buttons (HIG): the accent on a light accent background
        button_theme=ft.ButtonTheme(style=ft.ButtonStyle(
            shape=shape, padding=btn_pad, elevation=0, text_style=label,
            bgcolor=ft.Colors.with_opacity(0.15, accent), color=accent)),
        outlined_button_theme=ft.OutlinedButtonTheme(style=ft.ButtonStyle(
            shape=shape, padding=btn_pad, text_style=label, bgcolor=fill, color=accent,
            side=ft.BorderSide(0, ft.Colors.TRANSPARENT))),
        text_button_theme=ft.TextButtonTheme(style=ft.ButtonStyle(
            shape=shape, text_style=label, color=accent, overlay_color=ft.Colors.TRANSPARENT)),
        icon_button_theme=ft.IconButtonTheme(style=ft.ButtonStyle(color=accent, overlay_color=ft.Colors.TRANSPARENT)),
        switch_theme=ft.SwitchTheme(
            thumb_color={ft.ControlState.DEFAULT: "#FFFFFF"},
            track_color={ft.ControlState.SELECTED: system(GREEN, dark), ft.ControlState.DEFAULT: fill},
            track_outline_color={ft.ControlState.DEFAULT: ft.Colors.TRANSPARENT},
        ),
        checkbox_theme=ft.CheckboxTheme(
            shape=ft.CircleBorder(), fill_color={ft.ControlState.SELECTED: accent},
            check_color={ft.ControlState.DEFAULT: "#FFFFFF"},
            border_side=ft.BorderSide(1.5, "#636366" if dark else "#C7C7CC"),
        ),
        radio_theme=ft.RadioTheme(fill_color={ft.ControlState.SELECTED: accent}),
        slider_theme=ft.SliderTheme(active_track_color=accent, inactive_track_color=fill, thumb_color="#FFFFFF",
                                    track_height=4, overlay_color=ft.Colors.TRANSPARENT),
        input_decoration_theme=ft.InputDecorationTheme(
            filled=True, fill_color=fill, dense=not phone,
            content_padding=ft.Padding.symmetric(horizontal=12, vertical=12 if phone else 10),
        ),
        dialog_theme=ft.DialogTheme(
            bgcolor="#2C2C2E" if dark else "#F2F2F7", elevation=0,
            shape=ft.RoundedRectangleBorder(radius=DIALOG_RADIUS),
            title_text_style=ft.TextStyle(size=17, weight=ft.FontWeight.W_600, color=ft.Colors.ON_SURFACE),
        ),
        card_theme=ft.CardTheme(color=group, elevation=0, shape=ft.RoundedRectangleBorder(radius=GROUP_RADIUS)),
        # Settings' folded sections become rounded white groups on the grey page
        expansion_tile_theme=ft.ExpansionTileTheme(
            bgcolor=group, collapsed_bgcolor=group, icon_color=GRAY[0], collapsed_icon_color=GRAY[0],
            text_color=ft.Colors.ON_SURFACE, collapsed_text_color=ft.Colors.ON_SURFACE,
            shape=ft.RoundedRectangleBorder(radius=GROUP_RADIUS),
            collapsed_shape=ft.RoundedRectangleBorder(radius=GROUP_RADIUS),
        ),
        list_tile_theme=ft.ListTileTheme(icon_color=accent, shape=ft.RoundedRectangleBorder(radius=RADIUS)),
        divider_theme=ft.DividerTheme(color=sep, thickness=0.5, space=1),
        snackbar_theme=ft.SnackBarTheme(
            behavior=ft.SnackBarBehavior.FLOATING, elevation=0, bgcolor="#3A3A3C" if dark else "#1C1C1E",
            shape=ft.RoundedRectangleBorder(radius=DIALOG_RADIUS)),
        navigation_bar_theme=ft.NavigationBarTheme(
            bgcolor=ft.Colors.with_opacity(0.94, "#161618" if dark else "#F9F9F9"), elevation=0,
            indicator_color=ft.Colors.TRANSPARENT, height=58 if phone else 64,
            label_text_style={ft.ControlState.SELECTED: ft.TextStyle(size=10, weight=ft.FontWeight.W_500, color=accent),
                              ft.ControlState.DEFAULT: ft.TextStyle(size=10, weight=ft.FontWeight.W_500, color=GRAY[0])},
            label_behavior=ft.NavigationBarLabelBehavior.ALWAYS_SHOW,
        ),
        tooltip_theme=ft.TooltipTheme(
            decoration=ft.BoxDecoration(bgcolor="#3A3A3C" if dark else "#F2F2F7", border_radius=6),
            text_style=ft.TextStyle(size=12, color=ft.Colors.ON_SURFACE)),
        scrollbar_theme=ft.ScrollbarTheme(thickness=4, radius=2, thumb_color=ft.Colors.with_opacity(0.35, GRAY[0])),
        segmented_button_theme=ft.SegmentedButtonTheme(),
        popup_menu_theme=ft.PopupMenuTheme(color=group, elevation=4, shape=ft.RoundedRectangleBorder(radius=GROUP_RADIUS)),
        progress_indicator_theme=ft.ProgressIndicatorTheme(color=accent),
    )


def sidebar_item(icon, label: str, selected: bool, on_click, badge: str | None = None) -> ft.Container:
    """One row of a macOS-style sidebar: an icon in the accent colour and a label; the chosen row
    on a rounded tinted background."""
    return ft.Container(
        ft.Row([ft.Icon(icon, size=18, color=ft.Colors.PRIMARY),
                ft.Text(label, size=14, weight=ft.FontWeight.W_500 if selected else None, expand=True,
                        no_wrap=True, overflow=ft.TextOverflow.ELLIPSIS),
                ft.Container(ft.Text(badge or "", size=11, color=ft.Colors.ON_SURFACE_VARIANT), visible=bool(badge))],
               spacing=10),
        padding=ft.Padding.symmetric(horizontal=10, vertical=7), border_radius=7,
        bgcolor=ft.Colors.with_opacity(0.16, ft.Colors.PRIMARY) if selected else None,
        on_click=on_click,
    )

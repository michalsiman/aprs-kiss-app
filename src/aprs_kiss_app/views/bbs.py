"""BBS SERVER: the app as a packet BBS. Switching it on takes a typed sentence and turns everything else off."""

from __future__ import annotations

import re
import time
import unicodedata

import flet as ft

from aprs_kiss_core.bbs import BbsConfigError
from aprs_kiss_core.config import Config

from ..i18n import TEXTS
from .base import MONO, View, clock, short_path


GUIDE_EN = "https://github.com/michalsiman/aprs-kiss-app/blob/main/docs/BBS.md"
GUIDE_CS = "https://github.com/michalsiman/aprs-kiss-app/blob/main/docs/BBS.cs.md"


def _plain(text: str) -> str:
    text = unicodedata.normalize("NFKD", text or "")
    text = "".join(c for c in text if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", text.lower()).strip(" .!")


def confirmed(text: str) -> bool:
    """The safety sentence, typed in any of the app's languages (case and accents do not matter)."""
    return bool(_plain(text)) and _plain(text) in {_plain(t["bbs_confirm_text"]) for t in TEXTS.values()
                                                   if "bbs_confirm_text" in t}


class BbsView(View):
    key = "bbs"
    lazy = True
    icon = ft.Icons.DNS_OUTLINED
    selected_icon = ft.Icons.DNS

    def build(self) -> ft.Control:
        self._signature = None
        self.switch = ft.Switch(label=self.t("bbs"), value=self.engine.bbs_mode, on_change=self._toggle)
        self.state = ft.Text(size=15, weight=ft.FontWeight.BOLD)
        self.hint = ft.Text(size=12, color=ft.Colors.ON_SURFACE_VARIANT)
        self.folder = ft.Text(short_path(self.engine.bbs_folder()), size=12, font_family=MONO, selectable=True)
        self.tools = ft.Row([
            ft.TextButton(self.t("bbs_folder"), icon=ft.Icons.FOLDER_OPEN, on_click=self._open_folder),
            ft.TextButton(self.t("bbs_reload"), icon=ft.Icons.REFRESH, on_click=self._reload),
        ], wrap=True)
        self.guide = ft.TextButton(self.t("bbs_guide"), icon=ft.Icons.MENU_BOOK, url=GUIDE_CS if self.t.language == "cs"
                                   else GUIDE_EN)
        self.users = ft.Column(spacing=2)
        self.messages = ft.ListView(expand=True, spacing=0)
        self.log = ft.ListView(expand=True, spacing=0, auto_scroll=True)
        header = ft.Container(
            ft.Column([ft.Row([ft.Icon(ft.Icons.DNS, color=ft.Colors.PRIMARY), self.switch, self.guide]), self.state,
                       self.hint,
                       self.folder, self.tools], spacing=4, tight=True),
            padding=12, border_radius=8, bgcolor=ft.Colors.SURFACE_CONTAINER,
        )

        def panel(title: str, body: ft.Control, expand: int = 1) -> ft.Control:
            return ft.Container(
                ft.Column([ft.Text(title, weight=ft.FontWeight.BOLD), body], expand=True, spacing=6),
                expand=expand, padding=10, border_radius=8, bgcolor=ft.Colors.SURFACE_CONTAINER_LOWEST,
            )

        self.body = ft.Row([
            ft.Column([panel(self.t("bbs_connected"), self.users, 0), panel(self.t("bbs_log"), self.log)],
                      expand=1),
            panel(self.t("bbs_messages"), self.messages, 2),
        ], expand=True, vertical_alignment=ft.CrossAxisAlignment.STRETCH)
        return ft.Column([header, self.body], expand=True)

    def on_event(self, kind, data) -> None:
        if kind in ("bbs", "update"):
            self._signature = None

    def refresh(self) -> None:
        eng = self.engine
        bbs = eng.bbs
        signature = (eng.bbs_mode, eng.bbs_error, eng.station.tx_enabled, int(time.time() // 30),
                     tuple(bbs.conns) if bbs else (), len(bbs.store.messages) if bbs else 0,
                     len(bbs.log) and bbs.log[-1] if bbs else None)
        if signature == self._signature:
            return
        self._signature = signature
        self.switch.value = eng.bbs_mode
        self.body.visible = self.tools.visible = self.folder.visible = bbs is not None
        if eng.bbs_error:
            self.state.value, self.state.color = self.t("bbs_error", error=eng.bbs_error), ft.Colors.ERROR
        elif bbs:
            self.state.value = self.t("bbs_running", call=bbs.call, n=len(bbs.conns), msgs=len(bbs.store.messages))
            self.state.color = ft.Colors.GREEN
        else:
            self.state.value, self.state.color = self.t("bbs_off"), None
        self.hint.value = self.t("bbs_tx_needed") if bbs and not eng.station.tx_enabled else ""
        self.hint.visible = bool(self.hint.value)
        if not bbs:
            return
        now = time.time()
        self.users.controls = [
            ft.Text(f"{c.remote}  ({int((now - c.since) // 60)} min)", font_family=MONO, size=13)
            for c in bbs.conns.values()] or [ft.Text(self.t("bbs_nobody"), color=ft.Colors.ON_SURFACE_VARIANT)]
        self.messages.controls = [self._row(m) for m in reversed(bbs.rows())] or [
            ft.Text(self.t("bbs_no_messages"), color=ft.Colors.ON_SURFACE_VARIANT)]
        self.log.controls = [ft.Text(f"{clock(t)}  {text}", font_family=MONO, size=12) for t, text in bbs.log]

    def _row(self, m: dict) -> ft.Control:
        return ft.ListTile(
            leading=ft.Text(f"#{m['number']}\n{m['kind']}", font_family=MONO, size=12),
            title=ft.Text(m["subject"], weight=None if m["read"] else ft.FontWeight.BOLD, max_lines=1,
                          overflow=ft.TextOverflow.ELLIPSIS),
            subtitle=ft.Text(f"{m['from']} → {m['to']} · {clock(m['date'])} · {m['size']} B", size=12),
            trailing=ft.IconButton(ft.Icons.DELETE_OUTLINE, tooltip=self.t("bbs_delete"),
                                   on_click=lambda _e, n=m["number"]: self._delete(n)),
            dense=True, on_click=lambda _e, msg=m: self._open(msg),
        )

    # ─── actions ──────────────────────────────────────────────────────────

    def _open(self, m: dict) -> None:
        self.app.show_dialog(ft.AlertDialog(
            title=ft.Text(f"#{m['number']} {m['subject']}"),
            content=ft.Column([
                ft.Text(f"{m['from']} → {m['to']}" + (f" @ {m['at']}" if m["at"] else "") + f" · {clock(m['date'])}",
                        size=12, color=ft.Colors.ON_SURFACE_VARIANT),
                ft.Text(m["body"], font_family=MONO, selectable=True),
            ], tight=True, scroll=ft.ScrollMode.AUTO, width=560),
            actions=[ft.TextButton(self.t("close"), on_click=lambda _e: self.app.page.pop_dialog())],
        ))

    def _delete(self, number: int) -> None:
        if self.engine.bbs:
            self.engine.bbs.sysop_delete(number)
        self._signature = None
        self.refresh()
        self.app.page.update()

    async def _open_folder(self, _e) -> None:
        folder = self.engine.bbs_folder()
        try:
            await ft.UrlLauncher().launch_url(folder.as_uri())
        except Exception:  # noqa: BLE001 - the path is shown under the switch anyway
            await ft.Clipboard().set(str(folder))
            self.app.toast(f"{self.t('copied')}: {folder}")

    def _reload(self, _e) -> None:
        try:
            self.engine.bbs_reload()
            self.app.toast(self.t("bbs_reloaded"))
        except BbsConfigError as err:
            self.app.toast(str(err), error=True)
        self._signature = None
        self.refresh()
        self.app.page.update()

    async def _toggle(self, e) -> None:
        if not e.control.value:
            await self._apply(False)
            return
        e.control.value = False  # only after the sentence
        self.app.page.update()
        field = ft.TextField(autofocus=True, width=520)
        error = ft.Text("", color=ft.Colors.ERROR, size=12)

        async def enable(_e) -> None:
            if not confirmed(field.value or ""):
                error.value = self.t("bbs_confirm_wrong")
                self.app.page.update()
                return
            self.app.page.pop_dialog()
            await self._apply(True)

        field.on_submit = enable
        self.app.show_dialog(ft.AlertDialog(
            modal=True,
            title=ft.Text(self.t("bbs_confirm_title")),
            content=ft.Column([
                ft.Text(self.t("bbs_confirm_ask")),
                ft.Text(self.t("bbs_confirm_text"), weight=ft.FontWeight.BOLD, selectable=True),
                field, error,
            ], tight=True, width=520),
            actions=[ft.TextButton(self.t("cancel"), on_click=lambda _e: self.app.page.pop_dialog()),
                     ft.FilledButton(self.t("bbs_enable"), icon=ft.Icons.DNS, on_click=enable)],
        ))

    async def _apply(self, on: bool) -> None:
        data = {**self.engine.config.to_dict(), "bbs_enabled": on}
        if on:
            data["tak_enabled"] = False  # one exclusive mode at a time
        conf = Config.from_dict(data).validate()
        await self.app.apply_config(conf)

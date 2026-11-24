"""Files: send a file to another station over packet radio and receive files (YAPP).

Nothing of APRS: a connected AX.25 link to the other station (it acknowledges and repeats frames),
YAPP on top, the standard of packet radio file transfer (BPQ, WinPack, Paxon, …). Progress, speed and
the time left are shown; an interrupted transfer goes on from where it stopped when sent again.
"""

from __future__ import annotations

import asyncio
import logging
import time
from pathlib import Path

import flet as ft

from .base import View, clock

_LOGGER = logging.getLogger(__name__)
ACTIVE = ("connecting", "waiting", "offered", "sending", "receiving")


def size_text(n: float) -> str:
    return f"{n:.0f} B" if n < 1024 else f"{n / 1024:.1f} kB" if n < 1024 * 1024 else f"{n / 1024 / 1024:.1f} MB"


SPEED_DIRECT = (60, 100)  # bytes a second over a direct 1200 Bd link (acknowledgements, TX delay)


def estimate(size: int, hops: int = 0) -> tuple[float, float]:
    """(shortest, longest) seconds for a file at 1200 Bd; each digipeater on the way repeats every frame,
    so the time grows with them."""
    slow, fast = SPEED_DIRECT
    return size / fast * (hops + 1), size / slow * (hops + 1)


def duration(seconds: float) -> str:
    seconds = max(0, int(seconds))
    return f"{seconds // 60}:{seconds % 60:02d}" if seconds < 3600 else f"{seconds // 3600} h {seconds % 3600 // 60} min"


class FilesView(View):
    key = "files"
    lazy = True
    icon = ft.Icons.ATTACH_FILE
    selected_icon = ft.Icons.ATTACH_FILE

    def build(self) -> ft.Control:
        t = self.t
        conf = self.engine.config
        self.remote = ft.TextField(label=t("files_to"), width=150, dense=True,
                                   capitalization=ft.TextCapitalization.CHARACTERS)
        self.path = ft.TextField(label=t("files_via"), width=190, dense=True, on_change=lambda _e: self._show_picked(),
                                 capitalization=ft.TextCapitalization.CHARACTERS)
        # the file picked, shown with the estimated time before it goes
        self.picked: tuple[str, bytes] | None = None
        self.picked_box = ft.Container(visible=False, padding=10, border_radius=8,
                                       bgcolor=ft.Colors.SECONDARY_CONTAINER)
        self.accept = ft.Switch(label=t("files_accept"), value=conf.files_accept, on_change=self._accept_changed)
        self.list = ft.ListView(expand=True, spacing=6, padding=ft.Padding.all(8))
        self.hint = ft.Text(size=12, color=ft.Colors.ON_SURFACE_VARIANT)
        self._signature = None
        self.refresh()
        return ft.Column([
            ft.Text(t("files_about"), size=12, color=ft.Colors.ON_SURFACE_VARIANT),
            ft.Row([self.remote, self.path,
                    ft.FilledTonalButton(t("files_pick"), icon=ft.Icons.ATTACH_FILE, on_click=self._pick)],
                   wrap=True, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            self.picked_box,
            self.accept, self.hint,
            ft.Container(self.list, expand=True, border_radius=8, bgcolor=ft.Colors.SURFACE_CONTAINER_LOWEST),
            ft.Row([ft.TextButton(t("files_folder"), icon=ft.Icons.FOLDER_OPEN, on_click=self._open_folder)]),
        ], expand=True)

    def on_event(self, kind, data) -> None:
        if kind in ("files", "update"):
            self._signature = None

    def refresh(self) -> None:
        eng = self.engine
        now = time.time()
        rows = list(reversed(eng.transfers))
        active = any(r["state"] in ACTIVE for r in rows)
        signature = (tuple((r["remote"], r["state"], eng.transfer_progress(r), r.get("name")) for r in rows),
                     int(now) if active else 0, eng.station.tx_enabled, eng.config.files_accept)
        if signature == self._signature:
            return
        self._signature = signature
        t = self.t
        hints = []
        if not eng.station.tx_enabled:
            hints.append(t("files_tx_needed"))
        if eng.config.files_accept:
            hints.append(t("files_folder_is", path=str(eng.files_folder())))
        self.hint.value = " ".join(hints)
        self.hint.visible = bool(hints)
        self.list.controls = [self._row(r, now) for r in rows] or [
            ft.Text(t("files_none"), color=ft.Colors.ON_SURFACE_VARIANT)]

    def _row(self, r: dict, now: float) -> ft.Control:
        t = self.t
        out = r["direction"] == "out"
        done = self.engine.transfer_progress(r)
        size = r.get("size") or 0
        state = r["state"]
        parts = [f"{'→' if out else '←'} {r['remote']}", size_text(size) if size else ""]
        if state in ("sending", "receiving") and r.get("data_started"):
            moved = done - r.get("offset", 0)
            elapsed = max(1.0, now - r["data_started"])
            speed = moved / elapsed
            parts.append(f"{size_text(done)} / {size_text(size)}")
            if speed > 0:
                parts.append(f"{speed:.0f} B/s")
                parts.append(t("files_left", t=duration((size - done) / speed)))
        elif state == "done" and r.get("ended"):
            took = max(1.0, r["ended"] - r.get("data_started", r["started"]))
            parts.append(t("files_took", t=duration(took), speed=f"{(size - r.get('offset', 0)) / took:.0f}"))
        status = t(f"files_state_{state}")
        if r.get("detail") and state in ("refused", "cancelled", "failed"):
            status += f" ({r['detail']})"
        color = {"done": ft.Colors.GREEN, "refused": ft.Colors.ERROR, "cancelled": ft.Colors.ERROR,
                 "failed": ft.Colors.ERROR}.get(state, ft.Colors.PRIMARY)
        actions: list[ft.Control] = []
        if state in ACTIVE:
            actions.append(ft.IconButton(ft.Icons.CLOSE, tooltip=t("files_cancel"),
                                         on_click=lambda _e, k=r["remote"]: self.engine.cancel_transfer(k)))
        if state == "offered" and not out:
            actions[:0] = [ft.TextButton(t("files_accept_one"), on_click=lambda _e, k=r["remote"]: self._answer(k, True)),
                           ft.TextButton(t("files_refuse"), on_click=lambda _e, k=r["remote"]: self._answer(k, False))]
        if state == "done" and not out and r.get("path") and self.app.mobile:
            actions.append(ft.IconButton(ft.Icons.SAVE_ALT, tooltip=t("files_save"),
                                         on_click=lambda _e, p=r["path"]: self.app.page.run_task(self._save_copy, p)))
        return ft.Container(
            ft.Column([
                ft.Row([ft.Icon(ft.Icons.UPLOAD if out else ft.Icons.DOWNLOAD, size=18),
                        ft.Text(r.get("name") or "…", weight=ft.FontWeight.BOLD, expand=True,
                                overflow=ft.TextOverflow.ELLIPSIS, no_wrap=True),
                        ft.Text(clock(r["started"]), size=11, color=ft.Colors.ON_SURFACE_VARIANT), *actions],
                       vertical_alignment=ft.CrossAxisAlignment.CENTER),
                ft.ProgressBar(value=(done / size) if size else None, visible=state in ("sending", "receiving")),
                ft.Text(" · ".join(p for p in parts if p), size=12, color=ft.Colors.ON_SURFACE_VARIANT),
                ft.Text(status, size=12, color=color),
            ], spacing=4, tight=True),
            padding=10, border_radius=8, bgcolor=ft.Colors.SURFACE_CONTAINER,
        )

    # ─── actions ──────────────────────────────────────────────────────────

    def _answer(self, remote: str, yes: bool) -> None:
        self.engine.answer_file(remote, yes)
        self._signature = None
        self.refresh()
        self.app.page.update()

    async def _pick(self, _e) -> None:
        try:
            files = await ft.FilePicker().pick_files(dialog_title=self.t("files_send"))
        except Exception as err:  # noqa: BLE001 - no picker (some web setups)
            _LOGGER.warning("File picker failed: %s", err)
            files = None
        if not files or not files[0].path:
            return
        f = files[0]
        try:
            data = await asyncio.to_thread(Path(f.path).read_bytes)
        except OSError as err:
            self.app.toast(str(err), error=True)
            return
        self.picked = (f.name, data)
        self._show_picked()

    def _show_picked(self) -> None:
        """The picked file: its size, how long it will take, and Send."""
        if not self.picked:
            self.picked_box.visible = False
            self.app.page.update()
            return
        name, data = self.picked
        hops = len([p for p in (self.path.value or "").replace(" ", ",").split(",") if p.strip()])
        short, long = estimate(len(data), hops)  # in excellent conditions: the shorter one
        est = f"{max(1, round(short))} s" if short < 60 else f"{round(short / 60)} min" if short < 3600 \
            else f"{int(short // 3600)} h {round(short % 3600 / 60)} min"
        t = self.t
        self.picked_box.content = ft.Column([
            ft.Row([ft.Icon(ft.Icons.INSERT_DRIVE_FILE, size=20),
                    ft.Text(name, weight=ft.FontWeight.BOLD, expand=True, overflow=ft.TextOverflow.ELLIPSIS),
                    ft.Text(size_text(len(data)))], vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ft.Text(t("files_estimate", t=est), weight=ft.FontWeight.BOLD,
                    color=ft.Colors.ERROR if short > 30 * 60 else None),
            ft.Text(t("files_estimate_hops", n=hops), size=12, color=ft.Colors.ON_SURFACE_VARIANT, visible=hops > 0),
            ft.Row([ft.FilledButton(t("files_send_now"), icon=ft.Icons.SEND, on_click=self._send_picked),
                    ft.TextButton(t("cancel"), on_click=lambda _e: self._forget())], wrap=True),
        ], spacing=6, tight=True)
        self.picked_box.visible = True
        self.app.page.update()

    def _forget(self) -> None:
        self.picked = None
        self._show_picked()

    def _send_picked(self, _e) -> None:
        remote = (self.remote.value or "").strip().upper()
        if not remote:
            self.app.toast(self.t("files_to_needed"), error=True)
            return
        if not self.picked:
            return
        name, data = self.picked
        try:
            self.engine.send_file(remote, name, data, (self.path.value or "").strip())
        except Exception as err:  # noqa: BLE001 - not connected, TX off, already sending
            self.app.toast(str(err), error=True)
            return
        self.picked = None
        self.picked_box.visible = False
        self._signature = None
        self.refresh()
        self.app.page.update()

    def _accept_changed(self, e) -> None:
        self.engine.config.files_accept = bool(e.control.value)
        self.engine.accept_incoming = self.engine.config.accept_incoming or self.engine.config.files_accept
        self.app.save_config_soon()
        self._signature = None
        self.refresh()
        self.app.page.update()

    async def _open_folder(self, _e) -> None:
        folder = self.engine.files_folder()
        folder.mkdir(parents=True, exist_ok=True)
        try:
            await ft.UrlLauncher().launch_url(folder.as_uri())
        except Exception:  # noqa: BLE001 - the path is shown anyway
            self.app.toast(str(folder))

    async def _save_copy(self, path: str) -> None:
        """A phone: the received file into a place the user picks (Downloads, …)."""
        try:
            data = await asyncio.to_thread(Path(path).read_bytes)
            await ft.FilePicker().save_file(file_name=Path(path).name, src_bytes=data)
        except Exception as err:  # noqa: BLE001
            self.app.toast(str(err), error=True)

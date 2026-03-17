"""Custom Textual widgets for each dashboard panel."""

from __future__ import annotations

from typing import Dict, List, Optional

from textual.widgets import DataTable, Static

from .collectors import DutStatus, ModeInfo, RelayState, ServiceState
from .config import CHANNEL_NAMES, CHANNEL_PINS, INFRA_CHANNELS, RELAY_CHANNEL_COUNT


# ---------------------------------------------------------------------------
# Mode header
# ---------------------------------------------------------------------------
class ModeHeader(Static):
    """Top bar showing current testbed mode."""

    def update_mode(self, info: ModeInfo) -> None:
        mode_upper = info.mode.upper()
        style_map = {
            "LIBREMESH": "[bold green]",
            "OPENWRT": "[bold cyan]",
            "HYBRID": "[bold yellow]",
        }
        color = style_map.get(mode_upper, "[bold red]")
        text = f" Modo: {color}{mode_upper}[/]  ({info.detail})"
        self.update(text)


# ---------------------------------------------------------------------------
# Relay panel
# ---------------------------------------------------------------------------
class RelayPanel(DataTable):
    """Table of relay channel states."""

    def on_mount(self) -> None:
        self.add_columns("Canal", "Pin", "Dispositivo", "Estado")
        self.cursor_type = "none"
        self.zebra_stripes = True

    def update_relays(self, state: RelayState) -> None:
        self.clear()
        if state.error:
            self.add_row("--", "--", f"[red]{state.error}[/]", "--")
            return
        for ch in range(RELAY_CHANNEL_COUNT):
            name = CHANNEL_NAMES.get(ch, f"Canal {ch}")
            pin = CHANNEL_PINS.get(ch, "?")
            is_on = state.channels.get(ch)
            if is_on is None:
                status_str = "[dim]?[/]"
            elif is_on:
                status_str = "[bold green]ON[/]"
            else:
                status_str = "[red]OFF[/]"
            self.add_row(str(ch), pin, name, status_str)


# ---------------------------------------------------------------------------
# Services panel
# ---------------------------------------------------------------------------
class ServicesPanel(DataTable):
    """Table of systemd service states."""

    def on_mount(self) -> None:
        self.add_columns("Servicio", "Estado")
        self.cursor_type = "none"
        self.zebra_stripes = True

    def update_services(self, services: List[ServiceState]) -> None:
        self.clear()
        for svc in services:
            status = svc.status
            if status == "active":
                styled = "[bold green]active[/]"
            elif status == "inactive":
                styled = "[dim]inactive[/]"
            elif status == "failed":
                styled = "[bold red]failed[/]"
            else:
                styled = f"[yellow]{status}[/]"
            self.add_row(svc.name, styled)


# ---------------------------------------------------------------------------
# Pools panel
# ---------------------------------------------------------------------------
class PoolsPanel(Static):
    """Shows pool assignments."""

    def update_pools(
        self, pools: Dict[str, List[str]], error: str = ""
    ) -> None:
        if error:
            self.update(f"[red]{error}[/]")
            return
        lines = []
        for pool_name in ("libremesh", "openwrt"):
            duts = pools.get(pool_name, [])
            color = "green" if pool_name == "libremesh" else "cyan"
            lines.append(f"[bold {color}]{pool_name}:[/]")
            if duts:
                for d in duts:
                    lines.append(f"  {d}")
            else:
                lines.append("  [dim](empty)[/]")
        self.update("\n".join(lines))


# ---------------------------------------------------------------------------
# DUTs panel
# ---------------------------------------------------------------------------
class DutsPanel(DataTable):
    """Table with combined DUT status."""

    def on_mount(self) -> None:
        self.add_columns("DUT", "Pool", "Puerto", "Power", "Relé", "SSH", "Place")
        self.cursor_type = "none"
        self.zebra_stripes = True

    def update_duts(self, duts: List[DutStatus]) -> None:
        self.clear()
        for d in duts:
            is_poe = "poe" in d.pdu_name.lower()
            power = "PoE" if is_poe else "Relé"

            if d.relay_on is None:
                relay_str = "[dim]-[/]" if is_poe else "[dim]?[/]"
            elif d.relay_on:
                relay_str = "[bold green]ON[/]"
            else:
                relay_str = "[red]OFF[/]"

            if d.ssh_ok is None:
                ssh_str = "[dim]…[/]"
            elif d.ssh_ok:
                ssh_str = "[bold green]OK[/]"
            else:
                ssh_str = "[bold red]FAIL[/]"

            place_str = d.place_status or "[dim]-[/]"
            if "acquired" in place_str:
                place_str = f"[yellow]{place_str}[/]"
            elif place_str == "free":
                place_str = f"[green]{place_str}[/]"

            pool_color = {"libremesh": "green", "openwrt": "cyan"}.get(d.pool, "dim")
            pool_str = f"[{pool_color}]{d.pool}[/]"

            self.add_row(
                d.name,
                pool_str,
                str(d.switch_port),
                power,
                relay_str,
                ssh_str,
                place_str,
            )

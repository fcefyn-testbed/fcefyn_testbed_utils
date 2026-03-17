"""Textual application: layout, keybindings and refresh timers."""

from __future__ import annotations

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Footer, Header, Static

from . import collectors
from .config import FAST_REFRESH_SECONDS, SLOW_REFRESH_SECONDS
from .widgets import DutsPanel, ModeHeader, PoolsPanel, RelayPanel, ServicesPanel

HELP_TEXT = """\
[bold]testbed-status[/] — TUI de estado del lab FCEFyN

[bold]Keybindings:[/]
  [cyan]r[/]   Refresh inmediato
  [cyan]q[/]   Salir
  [cyan]?[/]   Mostrar/ocultar esta ayuda
"""


class HelpOverlay(Static):
    """Modal help text toggled with '?'."""

    DEFAULT_CSS = """
    HelpOverlay {
        display: none;
        layer: overlay;
        dock: bottom;
        width: 100%;
        max-height: 12;
        background: $surface;
        border-top: solid $accent;
        padding: 1 2;
    }
    """


class TestbedStatusApp(App):
    """Read-only TUI dashboard for the FCEFyN HIL testbed."""

    TITLE = "Testbed FCEFyN"
    CSS = """
    #mode-header {
        height: 3;
        background: $surface;
        border-bottom: solid $accent;
        padding: 0 1;
        content-align: center middle;
    }
    #top-row {
        height: 1fr;
    }
    #bottom-row {
        height: 1fr;
    }
    #relay-container, #services-container, #pools-container, #duts-container {
        border: solid $primary;
        padding: 0 1;
    }
    #relay-container { width: 1fr; }
    #services-container { width: 1fr; }
    #pools-container { width: 1fr; }
    #duts-container { width: 2fr; }
    """

    BINDINGS = [
        Binding("q", "quit", "Salir"),
        Binding("r", "refresh_all", "Refresh"),
        Binding("question_mark", "toggle_help", "Ayuda"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        yield ModeHeader(id="mode-header")
        with Vertical():
            with Horizontal(id="top-row"):
                with Container(id="relay-container"):
                    yield Static("[bold]Relés Arduino[/]")
                    yield RelayPanel()
                with Container(id="services-container"):
                    yield Static("[bold]Servicios[/]")
                    yield ServicesPanel()
            with Horizontal(id="bottom-row"):
                with Container(id="pools-container"):
                    yield Static("[bold]Pools[/]")
                    yield PoolsPanel(id="pools-panel")
                with Container(id="duts-container"):
                    yield Static("[bold]DUTs[/]")
                    yield DutsPanel()
        yield HelpOverlay(HELP_TEXT, id="help-overlay")
        yield Footer()

    async def on_mount(self) -> None:
        await self._refresh_fast()
        await self._refresh_slow()
        self.set_interval(FAST_REFRESH_SECONDS, self._refresh_fast)
        self.set_interval(SLOW_REFRESH_SECONDS, self._refresh_slow)

    # -- Fast refresh: mode, relays, services --------------------------
    async def _refresh_fast(self) -> None:
        mode_info = await collectors.get_mode()
        self.query_one(ModeHeader).update_mode(mode_info)

        relay_state = await collectors.get_relay_status()
        self.query_one(RelayPanel).update_relays(relay_state)

        services = await collectors.get_services_status()
        self.query_one(ServicesPanel).update_services(services)

    # -- Slow refresh: pools, SSH, places ------------------------------
    async def _refresh_slow(self) -> None:
        pool_cfg = await collectors.get_pool_config()
        self.query_one(PoolsPanel).update_pools(
            pool_cfg.pools, error=pool_cfg.error,
        )

        relay_state = await collectors.get_relay_status()
        ssh_results = await collectors.check_all_duts_ssh(pool_cfg.duts)
        places = await collectors.get_labgrid_places()

        dut_statuses = collectors.build_dut_statuses(
            pool_cfg, relay_state, ssh_results, places,
        )
        self.query_one(DutsPanel).update_duts(dut_statuses)

    # -- Actions -------------------------------------------------------
    async def action_refresh_all(self) -> None:
        await self._refresh_fast()
        await self._refresh_slow()

    def action_toggle_help(self) -> None:
        overlay = self.query_one("#help-overlay", HelpOverlay)
        overlay.display = not overlay.display

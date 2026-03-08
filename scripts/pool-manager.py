#!/usr/bin/env python3
"""
pool-manager - Generate labgrid exporter configs and configure the switch
               based on pool-config.yaml DUT assignments.

Supports three testbed modes derived from pool-config.yaml:
  - libremesh-only: all DUTs in libremesh pool (VLAN 200)
  - openwrt-only:   all DUTs in openwrt pool (isolated VLANs 100-108)
  - hybrid:         DUTs split across both pools simultaneously

Usage:
  pool-manager.py --generate            # Print generated exporter configs (dry run)
  pool-manager.py --apply               # Apply switch config + write exporter files
  pool-manager.py --apply --no-switch   # Write exporter files only (skip switch SSH)
  pool-manager.py --apply --force       # Always apply full config (ignore state file)

Differential apply: When re-applying hybrid config, only changed ports are configured.
State is stored in ~/.config/labgrid-switch-state.yaml. Use --force to bypass.

Output exporter files are written next to pool-config.yaml as:
  exporter-libremesh.yaml
  exporter-openwrt.yaml  (only when openwrt pool is non-empty)
"""

import argparse
import logging
import os
import sys
import time
from pathlib import Path

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML not installed. Run: pip install pyyaml", file=sys.stderr)
    sys.exit(1)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

SCRIPT_DIR = Path(__file__).parent
CONFIG_DIR = SCRIPT_DIR.parent / "configs"
POOL_CONFIG_PATH = CONFIG_DIR / "pool-config.yaml"

# Add scripts dir to path for switch_state import
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

# Optional: switch state for differential apply
try:
    from switch_state import (
        load_switch_state,
        save_hybrid_state,
        is_hybrid_state_valid_for_diff,
    )
except ImportError:
    load_switch_state = None
    save_hybrid_state = None
    is_hybrid_state_valid_for_diff = None

VLAN_MESH = 200
TFTP_IP_MESH = "192.168.200.1"


# ---------------------------------------------------------------------------
# Config loading and validation
# ---------------------------------------------------------------------------

def load_pool_config(path: Path) -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def validate_config(config: dict) -> list[str]:
    """Return list of error strings (empty → valid)."""
    errors = []
    duts_db = config.get("duts", {})
    pools = config.get("pools", {})

    assigned: dict[str, str] = {}
    for pool_name, pool in pools.items():
        for dut in pool.get("duts", []):
            if dut not in duts_db:
                errors.append(f"Pool '{pool_name}': DUT '{dut}' not in duts database")
            if dut in assigned:
                errors.append(
                    f"DUT '{dut}' assigned to both '{assigned[dut]}' and '{pool_name}'"
                )
            assigned[dut] = pool_name

    return errors


# ---------------------------------------------------------------------------
# Exporter YAML generation
# ---------------------------------------------------------------------------

def _dut_block_base(dut_name: str, hw: dict) -> dict:
    """Build the common exporter block fields for a DUT."""
    block: dict = {
        "location": hw["location"],
        "RawSerialPort": {
            "port": hw["serial_port"],
            "speed": hw["serial_speed"],
        },
        "PDUDaemonPort": {
            "host": hw["pdu_host"],
            "pdu": hw["pdu_name"],
            "index": hw["pdu_index"],
        },
    }
    return block


def generate_libremesh_exporter(dut_names: list[str], duts_db: dict) -> str:
    """Generate exporter YAML for the libremesh pool (all DUTs on VLAN 200)."""
    lines = [
        "# LibreMesh pool exporter — all DUTs share VLAN 200.",
        "# NetworkService addresses use fixed IPs (10.13.200.x) configured via",
        "# serial console by conftest.py before SSH access.",
        "",
    ]

    for dut_name in dut_names:
        hw = duts_db[dut_name]
        fixed_ip = hw["libremesh_fixed_ip"]
        tftp_path = hw["tftp_path"]
        entry_name = f"labgrid-fcefyn-{dut_name}"

        lines.append(f"{entry_name}:")
        lines.append(f"  location: {hw['location']}")
        lines.append(f"  RawSerialPort:")
        lines.append(f"    port: \"{hw['serial_port']}\"")
        lines.append(f"    speed: {hw['serial_speed']}")
        lines.append(f"  PDUDaemonPort:")
        lines.append(f"    host: {hw['pdu_host']}")
        lines.append(f"    pdu: {hw['pdu_name']}")
        lines.append(f"    index: {hw['pdu_index']}")
        lines.append(f"  TFTPProvider:")
        lines.append(f"    internal: \"/srv/tftp/{tftp_path}\"")
        lines.append(f"    external: \"{tftp_path}\"")
        lines.append(f"    external_ip: \"{TFTP_IP_MESH}\"")
        lines.append(f"  NetworkService:")
        lines.append(f"    address: \"{fixed_ip}%vlan{VLAN_MESH}\"")
        lines.append(f"    username: \"root\"")
        lines.append("")

    return "\n".join(lines)


def generate_openwrt_exporter(dut_names: list[str], duts_db: dict) -> str:
    """Generate exporter YAML for the openwrt pool (each DUT in isolated VLAN)."""
    lines = [
        "# OpenWrt pool exporter — each DUT in its own isolated VLAN (100-108).",
        "# DUT default IP is 192.168.1.1; host reaches it via per-DUT VLAN interface.",
        "",
    ]

    for dut_name in dut_names:
        hw = duts_db[dut_name]
        vlan = hw["switch_vlan_isolated"]
        tftp_path = hw["tftp_path"]
        tftp_ip = f"192.168.{vlan}.1"
        entry_name = f"labgrid-fcefyn-{dut_name}"

        lines.append(f"{entry_name}:")
        lines.append(f"  location: {hw['location']}")
        lines.append(f"  RawSerialPort:")
        lines.append(f"    port: \"{hw['serial_port']}\"")
        lines.append(f"    speed: {hw['serial_speed']}")
        lines.append(f"  PDUDaemonPort:")
        lines.append(f"    host: {hw['pdu_host']}")
        lines.append(f"    pdu: {hw['pdu_name']}")
        lines.append(f"    index: {hw['pdu_index']}")
        lines.append(f"  TFTPProvider:")
        lines.append(f"    internal: \"/srv/tftp/{tftp_path}\"")
        lines.append(f"    external: \"{tftp_path}\"")
        lines.append(f"    external_ip: \"{tftp_ip}\"")
        lines.append(f"  NetworkService:")
        lines.append(f"    address: \"192.168.1.1%vlan{vlan}\"")
        lines.append(f"    username: \"root\"")
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Switch configuration for hybrid mode
# ---------------------------------------------------------------------------

SLEEP_AFTER_SEND = 0.5
SLEEP_AFTER_PROMPT = 0.5
SLEEP_INITIAL = 2
SLEEP_CLEAR = 1
PROMPT_TIMEOUT = 12


def _wait_for_prompt(channel, timeout_sec: float = PROMPT_TIMEOUT) -> bool:
    deadline = time.time() + timeout_sec
    buf = ""
    while time.time() < deadline:
        if channel.recv_ready():
            data = channel.recv(1024).decode("utf-8", errors="replace")
            buf += data
            if "#" in buf or ">" in buf:
                return True
        else:
            time.sleep(0.1)
    logger.warning("Prompt timeout. Last output: %s", buf[-200:] if buf else "(none)")
    return False


def _send_cmd(channel, cmd: str) -> None:
    channel.send(cmd + "\r\n")
    time.sleep(SLEEP_AFTER_SEND)
    if not _wait_for_prompt(channel, PROMPT_TIMEOUT):
        logger.warning("Prompt not seen after: %s", cmd)
    time.sleep(SLEEP_AFTER_PROMPT)


def _get_port_assignments(
    openwrt_duts: list[str],
    libremesh_duts: list[str],
    duts_db: dict,
) -> tuple[list[tuple[int, str, int]], set[int]]:
    """Return (port_assignments, active_isolated_vlans)."""
    active_isolated_vlans: set[int] = set()
    port_assignments: list[tuple[int, str, int]] = []

    for dut_name in openwrt_duts:
        hw = duts_db[dut_name]
        vlan = hw["switch_vlan_isolated"]
        active_isolated_vlans.add(vlan)
        port_assignments.append((hw["switch_port"], "isolated", vlan))
        if "switch_port_poe" in hw:
            port_assignments.append((hw["switch_port_poe"], "isolated", vlan))

    for dut_name in libremesh_duts:
        hw = duts_db[dut_name]
        vlan = hw["switch_vlan_isolated"]
        port_assignments.append((hw["switch_port"], "mesh", vlan))
        if "switch_port_poe" in hw:
            port_assignments.append((hw["switch_port_poe"], "mesh", vlan))

    return port_assignments, active_isolated_vlans


def compute_desired_hybrid_state(
    openwrt_duts: list[str],
    libremesh_duts: list[str],
    duts_db: dict,
    uplink_ports: list[int],
) -> tuple[dict, list[int]]:
    """
    Compute desired hybrid state as (ports dict, uplink_tagged_vlans list).
    ports: {"11": {"pool": "libremesh", "vlan": 200}, ...}
    """
    port_assignments, active_isolated_vlans = _get_port_assignments(
        openwrt_duts, libremesh_duts, duts_db
    )
    ports: dict = {}
    for port, pool, isolated_vlan in port_assignments:
        vlan = VLAN_MESH if pool == "mesh" else isolated_vlan
        ports[str(port)] = {"pool": pool, "vlan": vlan}

    uplink_tagged_vlans = sorted(active_isolated_vlans)
    if libremesh_duts:
        uplink_tagged_vlans.append(VLAN_MESH)
        uplink_tagged_vlans = sorted(set(uplink_tagged_vlans))

    return ports, uplink_tagged_vlans


def build_hybrid_switch_commands(
    openwrt_duts: list[str],
    libremesh_duts: list[str],
    duts_db: dict,
    uplink_ports: list[int],
    ports_to_include: set[int] | None = None,
    include_uplinks: bool = True,
) -> list[str]:
    """
    Build TP-Link CLI commands for hybrid VLAN assignment.
    Each DUT port is configured independently based on its pool.
    Uplink ports are tagged for all active VLANs.

    If ports_to_include is set, only those port numbers are configured (for differential apply).
    If include_uplinks is False, uplink port config is skipped.
    """
    port_assignments, active_isolated_vlans = _get_port_assignments(
        openwrt_duts, libremesh_duts, duts_db
    )

    cmds = ["enable", "configure"]

    if libremesh_duts:
        cmds.extend(["vlan 200", 'name "mesh"', "exit"])

    for port, pool, isolated_vlan in port_assignments:
        if ports_to_include is not None and port not in ports_to_include:
            continue
        cmds.append(f"interface gigabitEthernet 1/0/{port}")
        if pool == "isolated":
            cmds.append("no switchport general allowed vlan 200")
            cmds.append(f"switchport general allowed vlan {isolated_vlan} untagged")
            cmds.append(f"switchport pvid {isolated_vlan}")
            if port == 1:
                cmds.append("power inline supply disable")
        else:
            cmds.append(f"no switchport general allowed vlan {isolated_vlan}")
            cmds.append("switchport general allowed vlan 200 untagged")
            cmds.append("switchport pvid 200")
            if port == 1:
                cmds.append("power inline supply disable")
        cmds.append("exit")

    if include_uplinks and uplink_ports:
        all_vlans = sorted(active_isolated_vlans)
        if libremesh_duts:
            all_vlans.append(VLAN_MESH)
        all_vlans = sorted(set(all_vlans))
        if all_vlans:
            vlan_str = ",".join(str(v) for v in all_vlans)
            for uplink_port in uplink_ports:
                cmds.append(f"interface gigabitEthernet 1/0/{uplink_port}")
                cmds.append(f"switchport general allowed vlan {vlan_str} tagged")
                cmds.append("exit")

    cmds.append("end")
    return cmds


def load_switch_password() -> str:
    """Load switch password from poe_switch_control.conf."""
    config_paths = (
        os.path.expanduser("~/.config/poe_switch_control.conf"),
        "/etc/poe_switch_control.conf",
    )
    for path in config_paths:
        if os.path.isfile(path) and os.access(path, os.R_OK):
            with open(path) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, _, value = line.partition("=")
                        if key.strip() == "POE_SWITCH_PASSWORD":
                            return value.strip().strip("'\"")
    return os.environ.get("POE_SWITCH_PASSWORD", "")


def apply_switch_config(
    host: str,
    user: str,
    password: str,
    commands: list[str],
) -> bool:
    try:
        import paramiko
    except ImportError:
        logger.error("paramiko not installed. Run: pip install paramiko")
        return False

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(
            host,
            username=user,
            password=password,
            look_for_keys=False,
            allow_agent=False,
            timeout=10,
        )
    except Exception as e:
        logger.error("SSH to switch failed: %s", e)
        return False

    try:
        channel = client.invoke_shell()
        channel.settimeout(20)
        time.sleep(SLEEP_INITIAL)
        channel.send("\r\n")
        time.sleep(SLEEP_CLEAR)
        if not _wait_for_prompt(channel, PROMPT_TIMEOUT):
            logger.error("No initial prompt from switch")
            return False

        for cmd in commands:
            logger.debug("Switch cmd: %s", cmd)
            _send_cmd(channel, cmd)

        logger.info("Switch configuration applied successfully")
        return True
    except Exception as e:
        logger.error("Switch command execution failed: %s", e)
        return False
    finally:
        client.close()


# ---------------------------------------------------------------------------
# Testbed mode detection
# ---------------------------------------------------------------------------

def detect_mode(pools: dict) -> str:
    openwrt_duts = pools.get("openwrt", {}).get("duts", [])
    libremesh_duts = pools.get("libremesh", {}).get("duts", [])
    if openwrt_duts and libremesh_duts:
        return "hybrid"
    if openwrt_duts:
        return "openwrt-only"
    if libremesh_duts:
        return "libremesh-only"
    return "empty"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate labgrid exporter configs from pool-config.yaml",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--config",
        default=str(POOL_CONFIG_PATH),
        help=f"Path to pool-config.yaml (default: {POOL_CONFIG_PATH})",
    )
    parser.add_argument(
        "--generate",
        action="store_true",
        help="Print generated exporter configs and switch commands (no changes)",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write exporter files and configure the switch",
    )
    parser.add_argument(
        "--no-switch",
        action="store_true",
        help="Skip switch SSH configuration (write exporter files only)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Always apply full switch config (ignore state file, no differential)",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable debug logging",
    )
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    if not args.generate and not args.apply:
        parser.print_help()
        return 1

    config_path = Path(args.config)
    config = load_pool_config(config_path)
    out_dir = config_path.parent

    errors = validate_config(config)
    if errors:
        for err in errors:
            logger.error("Config error: %s", err)
        return 2

    duts_db = config["duts"]
    pools = config.get("pools", {})
    openwrt_duts = pools.get("openwrt", {}).get("duts", [])
    libremesh_duts = pools.get("libremesh", {}).get("duts", [])
    switch_cfg = config.get("switch", {})
    uplink_ports = switch_cfg.get("uplink_ports", [])

    mode = detect_mode(pools)
    logger.info("Detected testbed mode: %s", mode)
    logger.info("  OpenWrt pool:   %s", openwrt_duts or "(empty)")
    logger.info("  LibreMesh pool: %s", libremesh_duts or "(empty)")

    lm_exporter = generate_libremesh_exporter(libremesh_duts, duts_db) if libremesh_duts else ""
    ow_exporter = generate_openwrt_exporter(openwrt_duts, duts_db) if openwrt_duts else ""
    desired_ports, desired_uplink_vlans = compute_desired_hybrid_state(
        openwrt_duts, libremesh_duts, duts_db, uplink_ports
    )
    switch_cmds = build_hybrid_switch_commands(
        openwrt_duts, libremesh_duts, duts_db, uplink_ports
    )

    if args.generate:
        if lm_exporter:
            print("=== exporter-libremesh.yaml ===")
            print(lm_exporter)
        if ow_exporter:
            print("=== exporter-openwrt.yaml ===")
            print(ow_exporter)
        print("=== Switch commands ===")
        for cmd in switch_cmds:
            print(f"  {cmd}")
        return 0

    if args.apply:
        if lm_exporter:
            out_file = out_dir / "exporter-libremesh.yaml"
            out_file.write_text(lm_exporter)
            logger.info("Written: %s", out_file)

        if ow_exporter:
            out_file = out_dir / "exporter-openwrt.yaml"
            out_file.write_text(ow_exporter)
            logger.info("Written: %s", out_file)

        if not args.no_switch:
            password = load_switch_password()
            if not password:
                logger.error(
                    "Switch password not found. Set POE_SWITCH_PASSWORD in "
                    "~/.config/poe_switch_control.conf or via env var."
                )
                return 3

            # Differential apply: only configure changed ports
            apply_cmds = switch_cmds
            if (
                not args.force
                and load_switch_state
                and save_hybrid_state
                and is_hybrid_state_valid_for_diff
            ):
                current_state = load_switch_state()
                if is_hybrid_state_valid_for_diff(current_state):
                    current_ports = current_state.get("hybrid_ports") or {}
                    current_uplink_vlans = current_state.get("uplink_tagged_vlans") or []
                    ports_changed: set[int] = set()
                    for port_str, desired_cfg in desired_ports.items():
                        current_cfg = current_ports.get(port_str)
                        if current_cfg != desired_cfg:
                            ports_changed.add(int(port_str))
                    uplinks_changed = sorted(desired_uplink_vlans) != sorted(
                        current_uplink_vlans
                    )
                    if not ports_changed and not uplinks_changed:
                        logger.info("Switch config unchanged, skipping SSH")
                        apply_cmds = []
                    else:
                        apply_cmds = build_hybrid_switch_commands(
                            openwrt_duts,
                            libremesh_duts,
                            duts_db,
                            uplink_ports,
                            ports_to_include=ports_changed,
                            include_uplinks=uplinks_changed,
                        )
                        logger.info(
                            "Differential apply: %d ports, uplinks=%s",
                            len(ports_changed),
                            uplinks_changed,
                        )

            if apply_cmds:
                success = apply_switch_config(
                    switch_cfg.get("host", "192.168.0.1"),
                    switch_cfg.get("user", "admin"),
                    password,
                    apply_cmds,
                )
                if not success:
                    logger.error("Switch configuration failed")
                    return 4
                if save_hybrid_state and (openwrt_duts or libremesh_duts):
                    save_hybrid_state(desired_ports, desired_uplink_vlans)
            else:
                success = True
        else:
            logger.info("Switch configuration skipped (--no-switch)")
            logger.info("Would send %d commands to switch", len(switch_cmds))

        print()
        print("Next steps:")
        if mode in ("libremesh-only", "hybrid"):
            print("  1. Deploy libremesh exporter via Ansible:")
            print("     cp configs/exporter-libremesh.yaml "
                  "<fork-openwrt-tests>/ansible/files/exporter/labgrid-fcefyn/exporter.yaml")
            print("     cd <fork-openwrt-tests>/ansible && ansible-playbook -i inventory.ini "
                  "playbook_labgrid.yml --tags export")
        if mode in ("openwrt-only", "hybrid"):
            print("  2. Deploy openwrt exporter via Ansible (openwrt-tests repo):")
            print("     cp configs/exporter-openwrt.yaml "
                  "<openwrt-tests>/ansible/files/exporter/labgrid-fcefyn/exporter.yaml")
            print("     cd <openwrt-tests>/ansible && ansible-playbook -i inventory.ini "
                  "playbook_labgrid.yml --tags export")
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())

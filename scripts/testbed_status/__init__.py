"""
testbed-status: TUI dashboard for the FCEFyN HIL testbed.

Displays real-time status of:
  - DUT VLAN state (isolated / mesh per port)
  - Arduino relay channels (DUTs + infrastructure)
  - Systemd services (exporters, pdudaemon, dnsmasq, etc.)
  - DUT definitions from dut-config.yaml
  - DUT SSH reachability and Labgrid place status

Usage:
  testbed-status          # launch TUI
  testbed-status --help   # show help

Keybindings:
  r   Force immediate refresh
  q   Quit
  ?   Show help
"""

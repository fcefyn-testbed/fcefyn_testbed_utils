# Recovering the lab host after a reboot

What to do after the lab host (`labgrid-fcefyn`) reboots — planned or unplanned (power outage, kernel update, accidental `reboot`).

Most things come back automatically thanks to `systemctl enable` on the relevant units, but some pieces need a manual nudge. This page is the checklist.

---

## 1. Verify automatic services came up

Run the [pre-test sanity check](pre-test-checklist.md). The expected outcome is all seven core units `active`:

```sh
systemctl is-active \
  labgrid-coordinator \
  labgrid-exporter \
  pdudaemon \
  ser2net \
  dnsmasq \
  arduino-relay-daemon \
  prometheus \
  grafana-server
```

If any unit is not active, start it and check its log:

```sh
sudo systemctl restart <unit>
sudo journalctl -u <unit> --boot -n 80 --no-pager
```

## 2. Re-arm Wake-on-LAN

The kernel resets the WoL flag on every boot. The [`wol`](../../ansible/roles/wol/README.md) role installs a oneshot unit that re-applies it, but verify it ran:

```sh
sudo ethtool enp0s25 | grep "Wake-on"
# Wake-on: g       <- correct
# Wake-on: d       <- WoL disabled, fix below
```

If the flag is wrong:

```sh
sudo systemctl start wol.service
sudo ethtool enp0s25 | grep "Wake-on"
```

## 3. DUT autossh tunnels

`autossh` units come up automatically, but the actual SSH sessions need the DUTs to be reachable. If a DUT was powered off during the reboot:

```sh
# List failed tunnel units
systemctl --failed --type=service | grep dut-metrics-tunnel

# Restart all DUT tunnels
sudo systemctl restart 'dut-metrics-tunnel-*'
```

Prometheus will show the relevant targets as `up` within ~15 s once tunnels reconnect.

## 4. WireGuard

```sh
sudo wg show wg0
```

If there is no recent handshake:

```sh
sudo systemctl restart wg-quick@wg0
sudo wg show wg0
```

If the handshake stays absent for more than 1 min, check connectivity to the peer endpoint:

```sh
PEER=$(sudo wg show wg0 endpoints | awk '{print $2}' | cut -d: -f1)
nc -uvz "$PEER" 51820
```

## 5. ZeroTier

```sh
zerotier-cli info
zerotier-cli listnetworks
```

`info` should say `ONLINE`. If it stays `OFFLINE` for more than a minute:

```sh
sudo systemctl restart zerotier-one
```

If the network was never authorised before the reboot (new install), the lab admin needs to authorise this node in [ZeroTier Central](https://my.zerotier.com).

## 6. TFTP root health

Stale symlinks from a failed run survive reboots. Trigger the cleanup once:

```sh
sudo systemctl start tftp-cleanup.service
journalctl -u tftp-cleanup.service -n 50
```

## 7. Quick smoke test

```sh
uv run labgrid-client places
uv run labgrid-client -p labgrid-fcefyn-openwrt_one lock
uv run labgrid-client -p labgrid-fcefyn-openwrt_one power cycle
uv run labgrid-client -p labgrid-fcefyn-openwrt_one unlock
```

This verifies the coordinator, exporter, and `pdudaemon` chain end-to-end without flashing anything.

## When power was cut hard

If the host went down ungracefully (UPS empty, plug pulled), additionally check:

- `df -h` - no filesystem read-only.
- `dmesg | grep -i 'i/o error\|EXT4-fs error'` - no disk errors.
- `lsblk` - all expected disks present.

If the root filesystem went read-only, fix the underlying disk issue before bringing services back up.

### Arduino relay daemon

After a hard power cut, the daemon may keep a stale serial connection while still reporting **active (running)**; relay commands then fail with **`Input/output error`**. See [Observed failure](../configuracion/arduino-relay.md#self-healing) for the full symptom table. Recovery uses heartbeat, `BindsTo`, and udev `SYSTEMD_WANTS` ([Self-healing](../configuracion/arduino-relay.md#self-healing)). Verify:

```sh
arduino_relay_control.py status
```

If it reports `Input/output error` or the service is `failed`:

```sh
sudo systemctl restart arduino-relay-daemon
arduino_relay_control.py status
```

If the restart limit was reached:

```sh
sudo systemctl reset-failed arduino-relay-daemon
sudo systemctl start arduino-relay-daemon
```

### Managed switch (TP-Link SG2016P)

After a hard power cut, the switch may **look** factory-reset (default IP `192.168.0.1`, flat VLAN 1) even when the hardware did not reset: TP-Link JetStream keeps CLI changes in RAM until `copy running-config startup-config`. See [Observed failure](../configuracion/switch-config.md#config-persistence). Current `switch-vlan` saves to flash automatically after each change.

After a host reboot, `/tmp` is recreated. Confirm the switch SSH lock is world-writable ([Switch SSH lock](../configuracion/switch-config.md#switch-lock)):

```sh
ls -la /tmp/switch.lock
# expected: -rw-rw-rw-
sudo systemd-tmpfiles --create   # if missing or not world-writable
```

If the switch still shows defaults, recovery procedure:

1. Disconnect all DUT cables from the switch, leave only gateway and laptop connected (avoids `192.168.1.1` conflicts on flat VLAN 1).
2. Access the web UI at `http://192.168.0.1`, log in with factory credentials.
3. Change credentials to the lab-standard ones.
4. Re-enable SSH if disabled.
5. Run `switch-vlan --init` from the lab host (applies topology and saves to flash).
6. Reconnect DUT cables.

After reconfiguration, verify with `switch_healthcheck.py`:

```sh
switch_healthcheck.py
```

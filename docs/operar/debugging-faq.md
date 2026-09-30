# Debugging FAQ

Common problems and solutions when running tests on the FCEFyN testbed.

---

## Labgrid / place issues

### `labgrid-client places` returns no places or an empty list

- Check that `labgrid-exporter` is running on the lab host: `systemctl status labgrid-exporter`
- Check that `labgrid-coordinator` is running on the lab host: `systemctl status labgrid-coordinator`
- Verify WireGuard connectivity from the lab host to the upstream VM: `ping <upstream-vm-wg-ip>`

### `labgrid-client lock` hangs or times out

Another job is holding the lock. Check who has it:

```bash
labgrid-client -p labgrid-fcefyn-belkin_rt3200_1 who
```

If the previous job crashed without releasing, unlock manually:

```bash
labgrid-client -p labgrid-fcefyn-belkin_rt3200_1 unlock --kick
```

### `LG_PLACE not set` error

Export the environment variable before running pytest:

```bash
export LG_PLACE=labgrid-fcefyn-belkin_rt3200_1
```

---

## TFTP / boot issues

### DUT does not boot via TFTP (timeout waiting for SSH)

1. Check the TFTP symlink exists and points to the right image:
   ```bash
   ls -la /srv/tftp/belkin_rt3200_1/
   ```
2. Check `dnsmasq` is running: `systemctl status dnsmasq`
3. Check the DUT is on the correct VLAN (isolated, not mesh)
4. Check power cycle actually happened: `labgrid-client power status`
5. Check the DUT serial console for boot errors: `labgrid-client console`

### `initramfs-kernel.bin` vs `sysupgrade.bin` — which one?

Always use `initramfs-kernel.bin` for CI testing. It boots from RAM without writing to flash. The `sysupgrade.bin` writes to NAND and changes the device state permanently — never use it in automated tests.

### UBI error on Belkin RT3200 first boot

The device may still have a non-UBI layout. Migrate once following [OpenWrt TOH](https://openwrt.org/toh/linksys/e8450) before running initramfs tests.

---

## SSH / network issues

### `ssh: connect to host ... port 22: Connection refused`

DUT did not finish booting. Wait longer or check the serial console:

```bash
labgrid-client -p labgrid-fcefyn-belkin_rt3200_1 console
```

### `Host key verification failed`

The DUT gets a new SSH host key on each TFTP boot. Clear it:

```bash
ssh-keygen -R 192.168.1.1   # or the DUT IP
```

In tests this is handled automatically via `StrictHostKeyChecking=no` in the SSH driver config.

### `labgrid-bound-connect: Permission denied`

The runner must connect as the `labgrid-dev` user. Check `LG_PROXY` is set and the SSH key for `labgrid-dev` is loaded.

---

## Switch lock (`/tmp/switch.lock`)

Symptoms: `Permission denied: '/tmp/switch.lock'`, `Timed out after 60.0s waiting for switch lock`, mesh pytest `VLAN switch to 200 failed`.

Canonical procedure, causes, and host files: [Switch SSH lock](../configuracion/switch-config.md#switch-lock).

---

## Virtual mesh (QEMU) issues

### `batctl n` shows no neighbors after VMs start

1. Check `vwifi-server` is running on the host: `pgrep vwifi-server`
2. Check `vwifi-client` started in each VM: `ssh -p 10022 root@127.0.0.1 'logread | grep vwifi'`
3. Check `wlan0-mesh` is up: `ip link show wlan0-mesh` — if `NO-CARRIER`, `wpad` may be missing
4. Verify `kmod-mac80211-hwsim` is loaded: `lsmod | grep hwsim`

### `wlan0-mesh: NO-CARRIER`

`wpad-basic-mbedtls` is not installed in the image. Rebuild the image including that package (see [QEMU setup](qemu-setup.md)).

### VM SSH does not come up

QEMU may be OOM or the image path is wrong. Check:

```bash
ps aux | grep qemu   # is the process running?
dmesg | tail -20     # OOM killer?
```

Reduce `MESH_NODES` or add more RAM per VM (`-m 512M`).

### `iperf3` test skipped

`iperf3` is not in the image. Install it at runtime:

```bash
ssh -p 10022 root@127.0.0.1 'opkg update && opkg install iperf3'
```

Or rebuild the image with `iperf3` included.

---

## CI / dashboard issues

### Dashboard shows "No workflow runs found"

The GitHub API rate limit (60 req/hour unauthenticated) may have been hit. Wait and reload, or press **R** to refresh.

### Card shows "Test details not yet published"

`collect-lime-results.yml` (every 6 h) hasn't pulled the `report.xml` for that device/release yet, or the CI artifact failed to upload. Verify the `test-results-*` artifact exists on the run in `lime-packages` Actions, then trigger the collect workflow manually from this repo: **Actions → Collect lime-packages test results → Run workflow**.

### Dashboard shows stale data after a new run

Force-refresh with `Ctrl+Shift+R` or click the **Refresh** button in the header.

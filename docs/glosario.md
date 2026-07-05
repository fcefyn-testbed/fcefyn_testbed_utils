# Glossary

Key terms used across the FCEFyN testbed documentation.

---

**auto-merge**
: A GitHub Pull Request setting that merges the PR automatically as soon as all required reviews and status checks pass. The CI results pipeline relies on it so the bot PR opened by `collect-lime-results.yml` lands on `develop` without manual intervention. Requires the repo-level "Allow auto-merge" toggle to be on.

**autossh**
: An `ssh` wrapper that monitors the connection and brings it back up when it drops. The lab uses it to keep the SSH tunnels from the host to each DUT's exporter port (`dut-metrics-tunnel-<name>.service`), so when the DUT's VLAN changes during a test, Prometheus recovers the scrape without intervention.

**batman-adv**
: B.A.T.M.A.N. Advanced — a mesh routing protocol implemented as a Linux kernel module. Operates at Layer 2, handling frame forwarding between mesh nodes. Used by LibreMesh for L2 mesh connectivity.

**babeld**
: A distance-vector routing daemon implementing the Babel routing protocol (RFC 8966). Used by LibreMesh for IPv4/IPv6 routing on top of the batman-adv mesh.

**batctl**
: batman-adv CLI. `batctl n` lists neighbors, `batctl o` the originator table, `batctl if` shows which hardware interfaces are attached to the mesh. The `test_mesh.py` tests rely on it to validate that the mesh actually formed.

**conntrack**
: Linux kernel table that tracks network connections (TCP, UDP, etc.) — Netfilter uses it for NAT and stateful filtering. On the orchestrator it fills quickly because of `autossh` tunnels and labgrid SSH proxies; once it approaches the limit (`node_nf_conntrack_entries_limit`), new flows start being dropped.

**dnsmasq**
: Lightweight server that combines DHCP, DNS, and TFTP. The lab uses it to serve initramfs images to DUTs over TFTP at boot, and as DHCP server on some isolated VLANs.

**DUT** (Device Under Test)
: A physical router connected to the lab and managed by Labgrid. Each DUT has a place name (e.g. `belkin_rt3200_1`), a VLAN, serial console, and power control.

**dropbear**
: Lightweight SSH server that ships by default on OpenWrt. Tests SSH into the DUTs through dropbear; `test_dropbear_startup` waits up to 120 s for the daemon to start listening on `0.0.0.0:22` before declaring the DUT ready.

**DTB (Device Tree Blob)**
: Binary file compiled from a `.dts` (Device Tree Source). Describes the hardware to the Linux kernel (memory, CPUs, peripherals, MTD partitions). The `/chosen/bootargs` node can fix kernel boot parameters; on ath79 with `CONFIG_MIPS_CMDLINE_FROM_DTB=y`, those values take precedence over U-Boot `bootargs`. The CI pipeline patches DTBs to inject the OEM MAC or force the legacy SPI-NAND layout on Belkin RT3200.

**initramfs**
: An in-memory root filesystem loaded by the kernel at boot. Used for CI testing because the device boots from RAM via TFTP — no flash write occurs. The device returns to its previous state on power cycle.

**FIT image (Flattened Image Tree)**
: Image format that U-Boot can boot: combines kernel, DTB, and ramdisk in a single `.itb`. The lime-packages pipeline emits FIT images for the MediaTek targets (Belkin RT3200, BPi-R4, OpenWrt One) and injects `bootargs` so U-Boot uses the initramfs from RAM.

**iperf3**
: TCP/UDP throughput measurement tool. The virtual-mesh tests use it (when present in the image) to measure bandwidth between mesh nodes.

**JUnit XML**
: A standard XML format for test results, originally from the Java JUnit framework. pytest generates JUnit XML with `--junitxml`. The dashboard parses these files to show per-test-case results.

**KVM (Kernel-based Virtual Machine)**
: Linux module providing hardware-assisted virtualization (`/dev/kvm`). QEMU uses it so VMs run at near-native speed. The CI's `enable_kvm.sh` step installs a udev rule that grants `rw` on `/dev/kvm` to the runner user.

**Labgrid**
: Open-source framework for embedded board testing. Manages place reservations, power control, serial console, and SSH access to DUTs. Used to coordinate test access across multiple CI jobs and lab hosts.

**labgrid-bound-connect**
: A script that acts as an SSH ProxyCommand. It uses `socat` to bind a TCP connection to a specific VLAN interface on the lab host, routing SSH traffic to the correct DUT.

**LibreMesh**
: An OpenWrt-based firmware distribution for community mesh networks. Includes batman-adv, babeld, shared-state, and other mesh networking components. The primary firmware under test in this lab.

**lime-packages**
: The GitHub repository (`libremesh/lime-packages`) that contains the LibreMesh CI workflow (`build-firmware.yml`). Builds firmware, runs tests, and publishes results.

**ImageBuilder (OpenWrt)**
: Container that assembles OpenWrt firmware images from pre-compiled packages (without rebuilding the kernel). The workflow's `build-image` stage uses it to combine the lime-packages feed with the base rootfs for each target/release.

**mac80211_hwsim**
: A Linux kernel module that creates virtual IEEE 802.11 (WiFi) radios. Used in combination with vwifi to simulate WiFi connectivity between QEMU VMs without physical hardware.

**node_openwrt_info**
: A Prometheus metric exported by node_exporter (with custom textfile collector or scrape labels) on each DUT, carrying `firmware` and `target` as labels so the Lab Overview dashboard can show what's running on each device.

**node_systemd_unit_state**
: A node_exporter metric describing whether a systemd unit is in a given state (`active`, `failed`, `inactive`, …). Used by the Orchestrator Host dashboard's Lab Services section to assert that `labgrid-exporter.service`, `pdudaemon.service`, and `ser2net.service` are running.

**NTP (Network Time Protocol)**
: Protocol for synchronising the system clock with trusted time peers. The orchestrator uses whatever time daemon the OS provides (systemd-timesyncd by default, chrony if installed) to keep the clock aligned. The Orchestrator Host dashboard's "NTP offset" panel reads `node_timex_offset_seconds`, a kernel-timex metric that works regardless of which daemon is running.

**opkg / apk**
: OpenWrt package managers. `opkg` is used in 24.10.x and earlier (`.ipk` packages); `apk` (apk-tools 3.x) replaced opkg starting in 25.12.x with `.apk` packages and a binary index `packages.adb`. The CI has to branch on the format because the `make image` flags differ.

**openwrt-tests**
: The test suite and pytest infrastructure (in `lime-packages`) that defines the test cases for both physical DUTs and virtual mesh nodes.

**OpenWrt SDK**
: Pre-compiled toolchain set (one per architecture) that lets you compile OpenWrt packages without the full buildroot. The CI's `build-feed` stage uses it via `openwrt/gh-action-sdk@v9` to produce the `.ipk` / `.apk` files for the lime-packages feed.

**pdudaemon**
: A daemon that controls power to DUTs via relay boards or PDUs. Exposes an HTTP API. The lab uses an Arduino with electromechanical relay modules (DUTs, DC 12V) and SSR modules (infrastructure: cooler and main PSU) controlled by pdudaemon.

**PAT (Personal Access Token)**
: A GitHub credential scoped per user. The CI results pipeline uses two fine-grained PATs as repository secrets in `fcefyn_testbed_utils`: `LIME_PACKAGES_TOKEN` (Actions: Read on `lime-packages`, for downloading artifacts) and `BOT_PR_TOKEN` (Contents + Pull Requests: Write on this repo, for opening the auto-merged bot PR).

**place**
: A Labgrid concept representing one testable resource (a DUT with all its attached resources). A place has a name (e.g. `labgrid-fcefyn-belkin_rt3200_1`) and is registered with the coordinator.

**prometheus-node-exporter-lua**
: A Lua reimplementation of node_exporter, much lighter, designed for OpenWrt (where the Go version would not fit in flash). DUTs run it bound to loopback (`127.0.0.1:9100`); the host scrapes it through an autossh tunnel.

**QEMU**
: An open-source machine emulator. Used to run LibreMesh x86_64 firmware images as virtual machines for CI mesh tests without physical hardware.

**report.xml**
: The JUnit XML file generated by pytest after a test run. Published to GitHub Pages and parsed by the dashboard to show per-test-case results.

**shared-state-async**
: LibreMesh CLI to read and write data types synced between mesh nodes. Hooks under `/usr/share/shared-state/hooks/` define what gets synchronised (e.g. `bat-hosts`: MAC → LiMe hostname mapping). The `test_mesh_shared_state_sync.py` tests verify that the data actually propagates.

**ser2net**
: A daemon that forwards serial ports (USB-to-serial adapters) over TCP. Labgrid uses ser2net to access DUT serial consoles remotely.

**shared-state**
: A LibreMesh subsystem that synchronizes structured data (e.g. hostname→MAC mappings) between mesh nodes. Tests verify that data written on one node propagates to others.

**sysupgrade**
: OpenWrt utility to flash a new image, optionally preserving UCI config (or wiping it with `-n`). **Not used in CI tests**: images are loaded into RAM via TFTP (initramfs), the flash is never written, so the DUT comes back to the same state after every test.

**TFTP**
: Trivial File Transfer Protocol. Used to deliver the initramfs kernel image to DUTs at boot via the lab's dnsmasq TFTP server.

**UBI / UBIFS**
: Unsorted Block Image filesystem. The flash layout used by OpenWrt on the Belkin RT3200. Requires a one-time migration from the stock layout before initramfs tests can run.

**UCI (Unified Configuration Interface)**
: OpenWrt's configuration system: flat files under `/etc/config/` and the `uci` CLI (`uci show lime-defaults`, `uci set lime.*`, `uci commit`). Tests use `uci show` to verify that LibreMesh applied the expected protos; workflows manage each DUT's config through UCI.

**ubus**
: OpenWrt's inter-process bus (similar to D-Bus but lighter). Services such as netifd, hostapd, and dnsmasq expose JSON methods over it. Tests use `ubus call system board` to read the DUT's model, kernel, distro and revision.

**VLAN**
: Virtual LAN. The lab uses VLANs to isolate DUT traffic: VLAN 100–104 for isolated testing, VLAN 200 for mesh mode (DUTs see each other).

**vwifi**
: A virtual WiFi relay tool that forwards mac80211_hwsim frames between QEMU VMs over TCP. Allows VMs on the same host to form a real IEEE 802.11 mesh. See [vwifi setup](diseno/vwifi.md).

**vwifi-server / vwifi-client**
: Process pair that forwards `mac80211_hwsim` frames between QEMU VMs over TCP, emulating a shared radio medium. `vwifi-server` runs on the lab host and `vwifi-client` inside each VM. Lets the VMs form a real 802.11 mesh without physical hardware for the `test-mesh-qemu` jobs.

**WireGuard**
: A modern VPN protocol. Used to connect the lab host to the upstream SSH gateway VM, enabling GitHub-hosted runners (openwrt-tests) to reach the lab's DUTs over an encrypted tunnel. The self-hosted runner (lime-packages physical tests) runs directly on the lab host.

**create-pull-request (CI action)**
: Third-party GitHub Action that creates PRs via the GitHub REST API instead of `git push` + `gh pr create`. `collect-lime-results.yml` uses it with `sign-commits: true` so the bot's commits land signed with GitHub's web-flow key (they show as "Verified"). Requires a PAT with **Contents: write** and **Pull requests: write** scopes on this repo, stored as the `BOT_PR_TOKEN` secret; the default `GITHUB_TOKEN` is not enough because the org has the "Allow GitHub Actions to create and approve pull requests" toggle disabled.

**workflow_dispatch**
: A GitHub Actions trigger that allows manually starting a workflow from the GitHub UI or API, with optional input parameters (e.g. selecting an OpenWrt release version).

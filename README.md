# Hardware-in-the-Loop (HIL) Testing Utilities

Utilities and scripts for managing physical hardware in OpenWrt testing infrastructure. 
This repository provides tools for controlling Arduino-based relay controllers, 
managing TFTP servers, and automating device setup for HIL testing with labgrid.

## Overview

This project provides automation tools for:

- **Arduino Relay Control**: Control power and serial isolation for physical devices
- **TFTP Server Management**: Automated firmware deployment for U-Boot recovery
- **Device Setup**: Automated physical device configuration and verification
- **Serial Communication**: Utilities for testing and verifying serial connections

## Repository Structure

```
pi-hil-testing-utils/
├── arduino/              # Arduino firmware and sketches
│   └── relay_ctrl.ino   # Relay controller firmware
├── configs/              # System configuration files
│   └── 99-serial-devices.rules  # Udev rules for serial devices
├── firmwares/           # Firmware images organized by device
│   ├── belkin_rt3200/
│   ├── gl-mt300n-v2/
│   └── qemu/
└── scripts/             # Automation scripts
    ├── arduino_relay_control.py    # Relay control CLI
    ├── poe_switch_control.py       # PoE port control (TP-Link SG2016P)
    ├── arduino_daemon.py            # Persistent relay daemon
    ├── setup_tftp_server.sh        # TFTP server setup
    ├── tftp_firmware_manage.sh     # Firmware management
    ├── setup_physical_device.sh    # Device setup automation
    ├── identify_devices.sh         # Serial device identification
    ├── check_router_serial_conn.py # Serial communication tester
    ├── verify_uboot_recovery.sh    # U-Boot recovery verification
    ├── start_daemon.sh             # Daemon startup script
    ├── generate_places_yaml.py    # Generate labgrid places.yaml
    └── labgrid_manager.sh          # Manage labgrid coordinator and exporter
```

## Quick Start

### Prerequisites

- Python 3.6+
- `pyserial` Python package
- `dnsmasq` (for TFTP server)
- `ser2net` 3.5.x (for serial-over-network access)
- Arduino with relay controller firmware

### Basic Installation

```bash
# Install Python dependencies
pip install pyserial

# Install arduino_relay_control.py to system path (for use with pdudaemon)
# This makes it available system-wide, consistent with other lab setups
sudo cp scripts/arduino_relay_control.py /usr/local/bin/arduino_relay_control.py
sudo chmod +x /usr/local/bin/arduino_relay_control.py

# Setup TFTP server with device directories
cd scripts
./setup_tftp_server.sh

# Test Arduino relay controller
arduino_relay_control.py status
# Or using full path:
# python3 scripts/arduino_relay_control.py status
```

## Complete Setup for Labgrid Integration

This section covers the complete setup required for integrating with `openwrt-tests` and labgrid.

### 1. Install System Dependencies

```bash
# Install required packages
sudo apt install dnsmasq pipx libsystemd-dev pkg-config python3-dev

# Ensure pipx is in PATH
pipx ensurepath
```

**ser2net**: Required by Labgrid for serial port access over network. **Important:** While `ser2net 3.5.x` is the recommended version for Labgrid RFC2217 compatibility, we found that **`ser2net 4.6.5`** (compiled from source) works better for our setup, especially with CH340-based serial adapters (like GL.iNet MT300N-v2). The Ubuntu 24.04 repo version (`4.6.0`) has known issues.

**dnsmasq**: Used as TFTP server for firmware deployment. Configuration will be created by the setup script.

### 1.1. Installing ser2net 4.6.5 (Recommended)

```bash
# Install build dependencies
sudo apt install build-essential libgensio-dev libyaml-dev

# Download ser2net 4.6.5
wget https://github.com/cminyard/ser2net/archive/refs/tags/v4.6.5.tar.gz
tar -xzf v4.6.5.tar.gz
cd ser2net-4.6.5

# Compile and install
./reconf
./configure
make
sudo make install

# Verify installation (should show version 4.6.5)
/usr/local/sbin/ser2net -v

# Remove the repo version if installed
sudo apt remove ser2net --purge -y
```

After installation, `ser2net 4.6.5` will be installed to `/usr/local/sbin/ser2net` and will be used by labgrid-exporter.

**Note:** If you experience issues with Belkin RT3200 devices, you can try `ser2net 3.5.1` instead. However, 4.6.5 has better compatibility with CH340 adapters and resolved buffer overflow issues we encountered.

### 2. Install PDUDaemon

PDUDaemon provides a standardized interface for power management that integrates with labgrid:

```bash
sudo apt install pipx
# Install pdudaemon from GitHub (same version as openwrt-tests uses)
pipx install git+https://github.com/jonasjelonek/pdudaemon.git@main
```

### 3. Install Arduino Relay Control Script

Install the relay control script to a system-wide location:

```bash
# Install arduino_relay_control.py to system path
sudo cp scripts/arduino_relay_control.py /usr/local/bin/arduino_relay_control.py
sudo chmod +x /usr/local/bin/arduino_relay_control.py
```

This allows `pdudaemon` to call it from a standard location, consistent with other lab setups.

### 4. Configure PDUDaemon

Create the PDUDaemon configuration directory and file (the file should be an exact copy of the one available
at openwrt-tests/ansible/files/exporter/labgrid-fcefyn/pdudaemon.conf):

```bash
# Create configuration directory
sudo mkdir -p /etc/pdudaemon

# Copy configuration file (or create it)
sudo cp ansible/files/exporter/labgrid-fcefyn/pdudaemon.conf /etc/pdudaemon/pdudaemon.conf

# Create configuration file
sudo tee /etc/pdudaemon/pdudaemon.conf > /dev/null << 'EOF'
{
    "daemon": {
        "hostname": "localhost",
        "port": 16421,
        "logging_level": "INFO",
        "listener": "http"
    },
    "pdus": {
        "fcefyn-arduino": {
            "driver": "localcmdline",
            "cmd_on": "/usr/local/bin/arduino_relay_control.py on %s",
            "cmd_off": "/usr/local/bin/arduino_relay_control.py off %s"
        },
        "fcefyn-arduino-glinet": {
            "driver": "localcmdline",
            "cmd_on": "/usr/local/bin/arduino_relay_control.py on %s --glinet-sequence",
            "cmd_off": "/usr/local/bin/arduino_relay_control.py off %s"
        }
    }
}
EOF

# Set proper permissions
sudo chmod 644 /etc/pdudaemon/pdudaemon.conf
```

**Configuration Notes**:
- The `%s` placeholder is required by the `localcmdline` driver and will be replaced with the relay index
- `fcefyn-arduino-glinet` uses the `--glinet-sequence` flag to handle the GL.iNet MT300N-v2's special power sequence (disconnect serial → power on → reconnect serial)
- Relay mapping:
  - Index 0 (Relay 0): GL.iNet MT300N-v2
  - Index 2 (Relay 2): Belkin RT3200 #1
  - Index 3 (Relay 3): Belkin RT3200 #2

### 5. Create PDUDaemon Systemd Service

Create a systemd service to run PDUDaemon automatically:

```bash
# Find the pdudaemon binary location (usually in ~/.local/bin after pipx install)
which pdudaemon
# Example output: /home/user/.local/bin/pdudaemon

# Create systemd service (replace /home/user/.local/bin/pdudaemon with your actual path)
sudo tee /etc/systemd/system/pdudaemon.service > /dev/null << 'EOF'
[Unit]
Description=Control and Queueing daemon for PDUs

[Service]
ExecStart=/home/franco/.local/bin/pdudaemon --conf=/etc/pdudaemon/pdudaemon.conf
Type=simple
User=franco
Restart=on-abnormal

[Install]
WantedBy=multi-user.target
EOF

# Replace /home/user with your actual username and update the ExecStart path accordingly
# If pdudaemon is installed to a different location, update the ExecStart path

# Reload systemd
sudo systemctl daemon-reload

# Start and enable pdudaemon service
sudo systemctl start pdudaemon
sudo systemctl enable pdudaemon

# Verify service is running
sudo systemctl status pdudaemon
```

**Important**: Replace `/home/user/.local/bin/pdudaemon` with the actual path returned by `which pdudaemon`, and update the `User=` field with your actual username.

### 6. Install Labgrid (for Local Testing)

For local testing before connecting to the global coordinator:

```bash
pip install labgrid
```

## Scripts Documentation

### Arduino Relay Control

**`arduino_relay_control.py`** - Main CLI for controlling relays

```bash
# Turn on relay channel 2
arduino_relay_control.py on 2

# Turn off relay channel 2
arduino_relay_control.py off 2

# Check status of all relays
arduino_relay_control.py status

# Turn on multiple relays
arduino_relay_control.py on 0 1 2

# Use custom serial port
arduino_relay_control.py --port /dev/ttyUSB0 on 1

# GL.iNet MT300N-v2 special sequence (disconnect serial → power on → reconnect serial)
arduino_relay_control.py on 0 --glinet-sequence
arduino_relay_control.py off 0 --glinet-sequence

# OpenWRT One (PoE on switch port 1) - requires POE_SWITCH_PASSWORD env var
export POE_SWITCH_PASSWORD='switch_admin_password'
poe_switch_control.py on 1
poe_switch_control.py off 1
poe_switch_control.py cycle 1
```

**Note**: After installation to `/usr/local/bin/`, you can use `arduino_relay_control.py` directly without `python3` prefix, as it has a shebang (`#!/usr/bin/env python3`).

**Features**:
- Persistent connection to avoid Arduino reset
- Automatic daemon detection
- Multi-channel control
- Pulse commands for power cycling
- Special GL.iNet sequence support (`--glinet-sequence` flag)

**GL.iNet Power Sequence**: When using `--glinet-sequence` with relay 0, the script automatically:
1. Disconnects serial line (relay 1 ON)
2. Powers on device (relay 0 ON)
3. Waits 2 seconds for boot
4. Reconnects serial line (relay 1 OFF)

### TFTP Server Management

**`setup_tftp_server.sh`** - Setup TFTP server with device directories

```bash
# Setup with default devices
./setup_tftp_server.sh

# Custom device list
export HIL_TESTBED_DEVICES="router1:My Router,router2:Another Router"
./setup_tftp_server.sh
```

**`tftp_firmware_manage.sh`** - Manage firmware images

```bash
# Upload firmware to device
./tftp_firmware_manage.sh upload firmware.itb --device belkin_rt3200_1

# List all devices and images
./tftp_firmware_manage.sh list-devices

# List images for specific device
./tftp_firmware_manage.sh list belkin_rt3200_1

# Verify image integrity
./tftp_firmware_manage.sh verify belkin_rt3200_1/firmware.itb
```

### Device Setup

**`setup_physical_device.sh`** - Automated device setup for GL-MT300N-V2

Verifies Arduino connectivity, serial ports, power sequencing, and dependencies.

**`identify_devices.sh`** - Identify USB serial devices

Helps create udev rules for consistent device naming.

**`check_router_serial_conn.py`** - Test serial communication

```bash
python3 check_router_serial_conn.py /dev/glinet-mango --verbose
```

### Labgrid Management

**`labgrid_manager.sh`** - Manage local labgrid coordinator and exporter

This script provides easy management of the labgrid coordinator and exporter services for local testing.

```bash
# Start both coordinator and exporter
./scripts/labgrid_manager.sh start both

# Restart both services
./scripts/labgrid_manager.sh restart both

# Check status
./scripts/labgrid_manager.sh status

# View logs
./scripts/labgrid_manager.sh logs both

# Stop both services
./scripts/labgrid_manager.sh stop both

# Start/stop individual services
./scripts/labgrid_manager.sh start coordinator
./scripts/labgrid_manager.sh restart exporter
./scripts/labgrid_manager.sh logs exporter
```

**Features**:
- Automatically generates `places.yaml` if missing
- Checks service status before starting/stopping
- Provides colored output for better visibility
- Lists available places when checking status
- Handles service restarts gracefully

**Environment Variables**:
- `LABGRID_COORDINATOR_DIR`: Coordinator directory (default: `~/labgrid-coordinator`)
- `LABGRID_EXPORTER_CONFIG`: Exporter config file path
- `LG_CROSSBAR`: Crossbar URL (default: `ws://localhost:20408/ws`)
- `OPENWRT_TESTS_DIR`: openwrt-tests repository directory (default: `~/Documents/openwrt-tests`)

**Logs**:
- Coordinator logs: `$LABGRID_COORDINATOR_DIR/coordinator.log`
- Exporter logs: `$LABGRID_COORDINATOR_DIR/exporter.log`

## Configuration

### Environment Variables

- `HIL_TFTP_ROOT`: TFTP server root directory (default: `/srv/tftp`)
- `HIL_TESTBED_DEVICES`: Comma-separated device list with descriptions
- `TFTP_USER`: TFTP server user (default: `tftp`)

### Arduino Serial Port

By default, scripts expect Arduino at `/dev/arduino-relay`. To use a different port:

```bash
arduino_relay_control.py --port /dev/ttyUSB0 on 1
```

### Udev Rules

Create `/etc/udev/rules.d/99-serial-devices.rules` for consistent device naming:

```
SUBSYSTEM=="tty", ATTRS{idVendor}=="XXXX", ATTRS{idProduct}=="YYYY", SYMLINK+="arduino-relay", MODE="0666", GROUP="dialout"
```

Use `identify_devices.sh` to help generate these rules.

## Local Testing with Labgrid

Before connecting to the global coordinator, test your exporter locally:

### 1. Start Local Coordinator and Exporter

**Using the management script (recommended)**:

```bash
# Start both coordinator and exporter
./scripts/labgrid_manager.sh start both

# Check status
./scripts/labgrid_manager.sh status
```

**Manual method**:

```bash
# Start local coordinator
labgrid-coordinator

# Or run in background
labgrid-coordinator &
```

```bash
# In another terminal
export LG_CROSSBAR=ws://localhost:20408/ws
labgrid-exporter /path/to/exporter.yaml
```

**Note**: The exporter requires places to be created. Generate `~/labgrid-coordinator/places.yaml` using the helper script:

```bash
# Generate places.yaml for labgrid-fcefyn (default)
python3 scripts/generate_places_yaml.py

# Or for a different lab
python3 scripts/generate_places_yaml.py --lab labgrid-hsn

# See all options
python3 scripts/generate_places_yaml.py --help
```

The script automatically detects the `openwrt-tests` directory and uses the `labnet.yaml` and template from there.

The `labgrid_manager.sh` script automatically generates `places.yaml` if it's missing when starting the coordinator.

### 3. Verify Devices

```bash
export LG_CROSSBAR=ws://localhost:20408/ws

# List available places (devices)
labgrid-client places

# Or view all resources
labgrid-client resources
```

### 4. Test Device Control

```bash
# Set environment
export LG_CROSSBAR=ws://localhost:20408/ws
export LG_PLACE="labgrid-fcefyn-belkin_rt3200_1"

# Lock device
labgrid-client lock

# Test power control (watch the device physically!)
labgrid-client power off
sleep 3
labgrid-client power on

# Test serial console (optional)
labgrid-client console

# Release device
labgrid-client unlock
```

### 5. Run Test Locally

```bash
export LG_CROSSBAR=ws://localhost:20408/ws
export LG_ENV=targets/belkin_rt3200_1.yaml
export LG_PLACE=labgrid-fcefyn-belkin_rt3200_1
export LG_IMAGE=/srv/tftp/belkin_rt3200_1/openwrt-mediatek-mt7622-linksys_e8450-ubi-initramfs-recovery.itb

pytest tests/test_base.py::test_shell -v --lg-log
```

## Local Testing vs Production

### Understanding the Architecture

**Local Testing Setup** (what you're running now):
```
┌─────────────────────────────┐
│  Local Coordinator          │  ← Testing only
│  (your machine)             │
└──────────┬──────────────────┘
           │
    ┌──────▼───────┐
    │ Local        │  ← Your exporter
    │ Exporter     │
    └──────┬───────┘
           │
    ┌──────▼───────┐
    │ Your         │  ← Your physical devices
    │ Routers      │
    └──────────────┘
```

**Production Setup** (after PR is merged):
```
                ┌─────────────────────────────┐
                │  Global Coordinator         │  ← Shared by all labs
                │  (remote server)            │
                └──────────┬──────────────────┘
                           │
           ┌───────────────┼───────────────┐
           │               │               │
    ┌──────▼───────┐ ┌────▼──────┐  ┌────▼──────┐
    │ Your         │ │ Lab HSN   │  │ Other     │
    │ Exporter     │ │ Exporter  │  │ Labs...   │
    └──────┬───────┘ └───────────┘  └───────────┘
           │
    ┌──────▼───────┐
    │ Your         │
    │ Routers      │
    └──────────────┘
```

### What Gets Used in Production

**Files that will be deployed to production:**
- ✅ `openwrt-tests/ansible/files/exporter/labgrid-fcefyn/exporter.yaml` - Your physical resource configuration
- ✅ `openwrt-tests/ansible/files/exporter/labgrid-fcefyn/pdudaemon.conf` - Your PDU configuration
- ✅ `openwrt-tests/labnet.yaml` (your lab section) - Lab metadata and device list
- ✅ `openwrt-tests/targets/linksys_e8450.yaml` - Shared target configuration (if modified)

**Files used ONLY for local testing:**
- ❌ Your local coordinator instance
- ❌ `~/labgrid-coordinator/places.yaml` (generated locally)
- ❌ Lab-specific helper scripts

In production, your exporter connects to the **global coordinator** (remote server), not your local one.

## Adding New Devices

This section covers how to add additional devices to your lab setup.

### Prerequisites

Before adding a device:
1. Physical device is connected and powered
2. Serial adapter is connected and identified
3. Relay channel is assigned for power control
4. Network configuration is planned (IP address, TFTP server)

### Step-by-Step Process

#### 1. Update Exporter Configuration

Add the new device to your exporter configuration in `openwrt-tests`:

```bash
cd ~/Documents/openwrt-tests
vim ansible/files/exporter/labgrid-fcefyn/exporter.yaml
```

Add a new section for your device:

```yaml
labgrid-fcefyn-belkin_rt3200_3:
  location: fcefyn-testbed
  RawSerialPort:
    port: "/dev/belkin-rt3200-3"  # Serial device name from udev rules
    speed: 115200
  PDUDaemonPort:
    host: localhost:16421
    pdu: fcefyn-arduino            # PDU name from pdudaemon.conf
    index: 3                        # Relay channel number
  TFTPProvider:
    internal: "/srv/tftp/belkin_rt3200_3/"
    external: "belkin_rt3200_3/"
    external_ip: "192.168.20.234"  # Optional: TFTP server IP
  NetworkService:
    address: "192.168.20.184"      # Device IP address
    username: "root"
```

**Note on `external_ip`:** The `external_ip` field (optional) specifies the TFTP server IP address. When set, the strategy automatically configures U-Boot with:
- `serverip` = `external_ip` (TFTP server)
- `ipaddr` = `external_ip + 1` (device, temporary during U-Boot only)

This temporary IP is **only used during firmware download** in U-Boot. After booting OpenWrt, the device uses the IP from `NetworkService.address`. Multiple devices can share the same `external_ip` since only one boots at a time. If `external_ip` is not specified, IPs must be configured in the target YAML.

**Note on firmware location:** Firmwares can be stored anywhere accessible by labgrid. For organization, it's recommended to keep them in `/srv/tftp/firmwares/<device_type>/` and set `LG_IMAGE` to that path (e.g., `LG_IMAGE=/srv/tftp/firmwares/belkin_rt3200/firmware.itb`).

#### 2. Update labnet.yaml

Add the device instance to your lab's configuration:

```bash
vim labnet.yaml
```

Under your lab section, add to `device_instances`:

```yaml
labs:
  labgrid-fcefyn:
    proxy: labgrid-fcefyn
    maintainers: "@francoriba"
    devices:
      - linksys_e8450
      - gl_mt300n_v2
    device_instances:
      linksys_e8450:
        - belkin_rt3200_1
        - belkin_rt3200_2
        - belkin_rt3200_3  # ← Add new instance
    developers:
      - francoriba
```

#### 3. Create TFTP Directory

Create and configure the TFTP directory for the new device:

```bash
sudo mkdir -p /srv/tftp/belkin_rt3200_3/
sudo chown -R $USER /srv/tftp/belkin_rt3200_3/
sudo chmod -R 775 /srv/tftp/belkin_rt3200_3/
```

#### 4. Regenerate places.yaml

The coordinator needs an updated `places.yaml` to recognize the new device:

```bash
cd ~/pi/pi-hil-testing-utils
python3 scripts/generate_places_yaml.py

# Verify the new place was generated
grep "belkin_rt3200_3" ~/labgrid-coordinator/places.yaml
```

**When to regenerate places.yaml:**
- ✅ After adding a new device to `labnet.yaml`
- ✅ After removing a device from `labnet.yaml`
- ✅ After changing device names or instances
- ❌ NOT needed when changing exporter.yaml only
- ❌ NOT needed when changing target configurations

#### 5. Restart Services

**Restart the exporter** (always needed after exporter.yaml changes):

```bash
cd ~/pi/pi-hil-testing-utils
./scripts/labgrid_manager.sh restart exporter
```

**Restart the coordinator** (needed after places.yaml changes):

```bash
./scripts/labgrid_manager.sh restart coordinator
```

Or restart both at once:

```bash
./scripts/labgrid_manager.sh restart both
```

#### 6. Verify New Device

Check that the new device is available:

```bash
export LG_CROSSBAR=ws://localhost:20408/ws

# List all places (should show new device)
labgrid-client places | grep belkin_rt3200_3

# View resources for new device
labgrid-client resources | grep belkin_rt3200_3
```

Expected output:
```
franco-desktop/labgrid-fcefyn-belkin_rt3200_3/NetworkService
franco-desktop/labgrid-fcefyn-belkin_rt3200_3/PDUDaemonPort
franco-desktop/labgrid-fcefyn-belkin_rt3200_3/NetworkSerialPort
franco-desktop/labgrid-fcefyn-belkin_rt3200_3/RemoteTFTPProvider
```

#### 7. Test New Device

Test basic functionality:

```bash
export LG_CROSSBAR=ws://localhost:20408/ws
export LG_PLACE=labgrid-fcefyn-belkin_rt3200_3

# Test power control
labgrid-client lock
labgrid-client power cycle
labgrid-client unlock

# Test serial console
labgrid-client lock
labgrid-client console
# Press Ctrl+] to exit console
labgrid-client unlock
```

### Common Issues When Adding Devices

**"place pattern matches nothing"**
- Solution: Regenerate places.yaml and restart coordinator
- Check: `labgrid-client places` to see available places

**"no matching remote resource"**
- Solution: Restart exporter after updating exporter.yaml
- Check: `labgrid-client resources` to see exported resources

**"Permission denied" on TFTP directory**
- Solution: Ensure correct ownership and permissions on `/srv/tftp/device_name/`
- Check: `ls -ld /srv/tftp/device_name/`

**PDU control fails**
- Solution: Verify relay index matches physical wiring
- Check: Test relay directly with `arduino_relay_control.py status`

## Validation Workflow

Before contributing your lab to the `openwrt-tests` project, follow this validation workflow:

### 1. Verify Physical Setup

```bash
# Check serial devices
ls -l /dev/belkin-rt3200-* /dev/glinet-* /dev/arduino-relay

# Test Arduino relay controller
arduino_relay_control.py status

# Test PDUDaemon
curl -X PUT http://localhost:16421/power/control/fcefyn-arduino/2/on
curl -X PUT http://localhost:16421/power/control/fcefyn-arduino/2/off
```

### 2. Verify Service Status

```bash
cd ~/pi/pi-hil-testing-utils

# Check all services
./scripts/labgrid_manager.sh status

# View logs if issues found
./scripts/labgrid_manager.sh logs coordinator
./scripts/labgrid_manager.sh logs exporter
```

### 3. Verify Device Availability

```bash
export LG_CROSSBAR=ws://localhost:20408/ws

# List all your devices
labgrid-client places

# Should show:
# labgrid-fcefyn-belkin_rt3200_1
# labgrid-fcefyn-belkin_rt3200_2
# labgrid-fcefyn-belkin_rt3200_3
# labgrid-fcefyn-gl_mt300n_v2
```

### 4. Test Each Device Capability

For each device, verify:

**Power Control:**
```bash
export LG_PLACE=labgrid-fcefyn-belkin_rt3200_1
labgrid-client lock
labgrid-client power off
labgrid-client power on
labgrid-client power cycle
labgrid-client unlock
```

**Serial Console:**
```bash
export LG_PLACE=labgrid-fcefyn-belkin_rt3200_1
labgrid-client lock
labgrid-client console
# Verify you can see output
# Press Ctrl+] to exit
labgrid-client unlock
```

**TFTP Boot (with openwrt-tests):**
```bash
cd ~/Documents/openwrt-tests
export LG_CROSSBAR=ws://localhost:20408/ws
export LG_PLACE=labgrid-fcefyn-belkin_rt3200_1
export LG_IMAGE=/srv/tftp/firmwares/belkin_rt3200/openwrt-23.05.5-mediatek-mt7622-linksys_e8450-ubi-initramfs-recovery.itb

labgrid-client lock
pytest tests/test_base.py::test_shell -v --lg-log
labgrid-client unlock
```

### 5. Run Full Test Suite

Once basic tests pass, run the full test suite:

```bash
cd ~/Documents/openwrt-tests
export LG_CROSSBAR=ws://localhost:20408/ws
export LG_PLACE=labgrid-fcefyn-belkin_rt3200_1
export LG_IMAGE=/srv/tftp/firmwares/belkin_rt3200/openwrt-23.05.5-mediatek-mt7622-linksys_e8450-ubi-initramfs-recovery.itb

# Run all basic tests
pytest tests/test_base.py -v --lg-log

# Test multiple devices
for place in labgrid-fcefyn-belkin_rt3200_{1,2,3}; do
    echo "Testing $place..."
    export LG_PLACE=$place
    pytest tests/test_base.py::test_shell -v --lg-log
done
```

## VLAN Configuration for Multiple Devices

When running multiple devices of the same model (e.g., three Belkin RT3200 routers), they all boot with the same default IP address (`192.168.1.1`). To avoid IP conflicts and align with the `openwrt-tests` standard, each device must be isolated in its own VLAN.

### Why VLANs?

**The Problem:**
- All OpenWrt devices boot with default IP: `192.168.1.1`
- Multiple identical devices → IP conflict
- Cannot test multiple devices simultaneously

**The Solution:**
- Isolate each device in a separate VLAN
- Each VLAN is a virtual network segment
- Devices can have the same IP without conflict
- Server has a virtual interface in each VLAN

### Network Architecture

```
                    MikroTik Hex (Router)
                    VLAN 100: 192.168.100.254/24
                    VLAN 200: 192.168.200.254/24
                    VLAN 300: 192.168.300.254/24
                           │
                           │ (trunk: all VLANs)
                           │
                    TP-Link SG2008P (Switch)
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
    Port 1 (trunk)    Port 5-7 (access)  Port 7 (hybrid)
        │              │ VLAN 100         │
   MikroTik         Belkin #1      franco-desktop
                    (untagged)      - VLAN 20 (tagged)
                                    - VLAN 100 (tagged)
                                    - VLAN 200 (tagged)
                                    - VLAN 300 (tagged)
```

### VLAN Assignments

| Device | VLAN ID | Switch Port | PVID | Server IP | Device IP | Subnet |
|--------|---------|-------------|------|-----------|-----------|---------|
| Belkin RT3200 #1 | 100 | 5 | 100 | 192.168.100.1, 192.168.1.100 | 192.168.1.1 | /24 |
| Belkin RT3200 #2 | 200 | 6 | 200 | 192.168.200.1, 192.168.1.200 | 192.168.1.1 | /24 |
| Belkin RT3200 #3 | 300 | 7 | 300 | 192.168.300.1, 192.168.1.300 | 192.168.1.1 | /24 |
| GL.iNet MT300N-v2 | 400 | 8 | 400 | 192.168.400.1, 192.168.1.400 | 192.168.1.1 | /24 |
| Openwrt One | 103 | 9 | 103 | 192.168.103.1, 192.168.1.1 | 192.168.1.1 | /24 |

**Important:** Each server VLAN interface needs **TWO IP addresses**:
- `192.168.X.1/24`: For TFTP/DHCP server communication
- `192.168.1.X/24`: For SSH communication with devices (they boot at `192.168.1.1`)

### Step-by-Step VLAN Configuration

#### 1. Configure MikroTik Router

Create VLAN interfaces and assign IPs:

```routeros
# Create VLAN 100
/interface vlan
add interface=LAN-TRUNK name=vlan100-testbed vlan-id=100

# Assign IP to MikroTik in VLAN 100
/ip address
add address=192.168.100.254/24 interface=vlan100-testbed network=192.168.100.0

# Add firewall rule to allow access from VLAN 100
/ip firewall filter
add action=accept chain=input comment="Allow access from VLAN100 testbed to router" \
    in-interface=vlan100-testbed \
    place-before=[find comment="Block anything that is not explicitly allowed"]

# Repeat for VLANs 200, 300, 400...
```

#### 2. Configure TP-Link Switch

Access the switch web interface and configure VLANs:

**A. Create VLANs:**
```
VLAN → 802.1Q VLAN → VLAN Config

VLAN ID: 100, Name: testbed-belkin1
VLAN ID: 200, Name: testbed-belkin2
VLAN ID: 300, Name: testbed-belkin3
VLAN ID: 400, Name: testbed-glinet
VLAN ID:    , Name: openwrt-One
```

**B. Configure Port Membership:**

For **Port 1** (MikroTik uplink):
```
Tagged VLANs: 10, 20, 30, 40, 50, 100, 200, 300, 400
PVID: 1
```

For **Port 5** (Belkin #1):
```
Untagged VLAN: 100
PVID: 100
```

For **Port 7** (franco-desktop server):
```
Tagged VLANs: 20, 100, 200, 300, 400
PVID: 20
```

#### 3. Configure Server VLAN Interfaces

Use NetworkManager to create VLAN interfaces on the server:

**For VLAN 100 (Belkin #1):**

```bash
# Create VLAN interface
sudo nmcli connection add type vlan \
  con-name vlan100 \
  ifname vlan100 \
  dev enp0s31f6 \
  id 100

# Configure BOTH IP addresses (CRITICAL!)
sudo nmcli connection modify vlan100 \
  ipv4.method manual \
  ipv4.addresses "192.168.100.1/24,192.168.1.100/24"

# Disable IPv6
sudo nmcli connection modify vlan100 ipv6.method ignore

# Enable auto-connection
sudo nmcli connection modify vlan100 connection.autoconnect yes

# Activate the connection
sudo nmcli connection up vlan100

# Verify both IPs are assigned
ip addr show vlan100 | grep inet
# Should show:
# inet 192.168.100.1/24 ...
# inet 192.168.1.100/24 ...
```

**Why TWO IP addresses?**
- `192.168.100.1/24`: TFTP server listens here, U-Boot downloads firmware from this IP
- `192.168.1.100/24`: SSH ProxyCommand connects to devices on `192.168.1.1` through this IP

**Without `192.168.1.100/24`, SSH will fail with "No route to host"**

Repeat for VLANs 200, 300, 400 with corresponding IPs.

#### 4. Configure dnsmasq for VLANs

Update `/etc/dnsmasq.d/tftp.conf` to serve DHCP/TFTP on all VLAN interfaces:

```bash
sudo tee /etc/dnsmasq.d/tftp.conf > /dev/null << 'EOF'
# Disable DNS completely
port=0

# DHCP Configuration for each VLAN
interface=vlan100
dhcp-range=vlan100,192.168.100.100,192.168.100.200,24h

interface=vlan200
dhcp-range=vlan200,192.168.200.100,192.168.200.200,24h

interface=vlan300
dhcp-range=vlan300,192.168.300.100,192.168.300.200,24h

interface=vlan400
dhcp-range=vlan400,192.168.400.100,192.168.400.200,24h

# TFTP Configuration
enable-tftp
tftp-root=/srv/tftp/

# Listen on all VLAN interfaces and localhost
listen-address=192.168.100.1
listen-address=192.168.200.1
listen-address=192.168.300.1
listen-address=192.168.400.1
listen-address=127.0.0.1
bind-interfaces
EOF

# Restart dnsmasq
sudo systemctl restart dnsmasq
sudo systemctl status dnsmasq
```

#### 5. Install Required Tools

**labgrid-bound-connect:**

This tool is required for SSH connections through VLANs. It uses `socat` to bind SSH to a specific network interface.

```bash
# Install from labgrid repository
cd ~/Documents/labgrid
sudo cp helpers/labgrid-bound-connect /usr/local/sbin/labgrid-bound-connect
sudo chmod +x /usr/local/sbin/labgrid-bound-connect

# Verify installation
which labgrid-bound-connect
labgrid-bound-connect --help
```

**socat:**

Required by `labgrid-bound-connect` for network binding:

```bash
sudo apt-get update
sudo apt-get install -y socat
```

**Configure sudoers:**

`labgrid-bound-connect` must run with sudo to bind to specific interfaces:

```bash
sudo tee /etc/sudoers.d/labgrid << 'EOF'
# Allow labgrid commands without password
franco ALL=(ALL) NOPASSWD: /usr/local/sbin/labgrid-bound-connect
EOF

sudo chmod 440 /etc/sudoers.d/labgrid
sudo visudo -c  # Verify syntax

# Test sudo without password
sudo labgrid-bound-connect --help
# Should NOT ask for password
```

**Replace `franco` with your actual username.**

#### 6. Update Exporter Configuration

Update your exporter YAML with VLAN-specific IPs:

```yaml
# ~/Documents/openwrt-tests/ansible/files/exporter/labgrid-fcefyn/exporter.yaml

labgrid-fcefyn-belkin_rt3200_1:
  location: fcefyn-testbed
  RawSerialPort:
    port: "/dev/belkin-rt3200-1"
    speed: 115200
  PDUDaemonPort:
    host: localhost:16421
    pdu: fcefyn-arduino
    index: 2
  TFTPProvider:
    internal: "/srv/tftp/belkin_rt3200_1/"
    external: "belkin_rt3200_1/"
    external_ip: "192.168.100.1"  # Server IP in VLAN 100
  NetworkService:
    address: "192.168.1.1%vlan100"  # Device IP with VLAN interface
    username: "root"

# Repeat for other devices with vlan200, vlan300, vlan400...
```

**Key fields:**
- `external_ip`: Server's TFTP IP in the VLAN (for U-Boot firmware download)
- `address`: Device's default IP with `%vlanXXX` suffix (for SSH through specific VLAN)

### Common Issues and Solutions

#### Issue 1: SSH Timeout - "No route to host"

**Symptom:**
```
ERROR: Timeout while waiting for ssh connection
Connection timed out during banner exchange
```

**Cause:** Missing the second IP address (`192.168.1.X/24`) on the VLAN interface.

**Solution:**
```bash
# Add the missing IP
sudo nmcli connection modify vlan100 +ipv4.addresses "192.168.1.100/24"
sudo nmcli connection down vlan100 && sudo nmcli connection up vlan100

# Verify both IPs
ip addr show vlan100 | grep inet
```

#### Issue 2: labgrid-bound-connect Not Found

**Symptom:**
```
ERROR: Missing socat binary
sudo: a password is required
```

**Solution:**
```bash
# Install socat
sudo apt-get install -y socat

# Install labgrid-bound-connect
sudo cp ~/Documents/labgrid/helpers/labgrid-bound-connect /usr/local/sbin/
sudo chmod +x /usr/local/sbin/labgrid-bound-connect

# Configure sudoers (see section above)
```

#### Issue 3: TFTP Download Fails

**Symptom:**
```
TFTP error: File not found
```

**Solution:**
```bash
# Verify dnsmasq is listening on VLAN interface
sudo ss -ulnp | grep :69

# Should show:
# 192.168.100.1:69

# Check TFTP directory permissions
ls -ld /srv/tftp/belkin_rt3200_1/
sudo chown -R $USER:$USER /srv/tftp/
```

#### Issue 4: Device Not Reachable After Boot

**Symptom:**
- `test_shell` passes (serial console works)
- `test_ssh` fails (network not reachable)

**Cause:** Device boots correctly but network is not configured.

**Solution:** Verify:
```bash
# Check device is reachable
ping -c 3 192.168.1.1

# If fails, check VLAN interface has both IPs
ip addr show vlan100 | grep "192.168.1.100"

# Check device serial console for network errors
labgrid-client console
# Run: ip addr show br-lan
```

### Testing VLAN Configuration

After configuration, verify each device:

```bash
cd ~/Documents/openwrt-tests
export LG_CROSSBAR=ws://localhost:20408/ws
export LG_PLACE=labgrid-fcefyn-belkin_rt3200_1
export LG_IMAGE=/srv/tftp/firmwares/belkin_rt3200/openwrt-23.05.5-mediatek-mt7622-linksys_e8450-ubi-initramfs-recovery.itb

# Restart labgrid to apply changes
cd ~/pi/pi-hil-testing-utils
./scripts/labgrid_manager.sh restart both

# Run tests
cd ~/Documents/openwrt-tests
labgrid-client lock
pytest tests/test_base.py -v
labgrid-client unlock
```

**Expected results:**
```
9 passed, 2 skipped in ~40s

✅ test_shell          - Serial console works
✅ test_ssh            - SSH through VLAN works
✅ test_firmware_version
✅ test_dropbear_startup
✅ test_echo
✅ test_uname
✅ test_ubus_system_board
✅ test_free_memory
✅ test_kernel_errors
⏭️ test_sysupgrade_backup (skipped - initramfs firmware)
⏭️ test_sysupgrade_backup_u (skipped - initramfs firmware)
```

### Migrating Additional Devices

To migrate Belkin #2, #3, or GL.iNet to VLANs 200, 300, 400:

1. **Create VLAN in MikroTik** (repeat for each VLAN ID)
2. **Configure Switch ports** (assign PVID to device ports)
3. **Create VLAN interface on server** with TWO IPs
4. **Update dnsmasq** to listen on new VLAN
5. **Update exporter.yaml** with new VLAN settings
6. **Restart labgrid** services
7. **Test** the device

Follow the same pattern as VLAN 100, just change the VLAN ID and IP addresses accordingly.

### Network Topology Summary

**Before VLANs (problematic):**
```
All devices in VLAN 20 → IP conflict (all use 192.168.1.1)
```

**After VLANs (working):**
```
VLAN 100: Belkin #1  → 192.168.1.1 (isolated)
VLAN 200: Belkin #2  → 192.168.1.1 (isolated)
VLAN 300: Belkin #3  → 192.168.1.1 (isolated)
VLAN 400: GL.iNet    → 192.168.1.1 (isolated)
```

Each device has its own isolated network segment, enabling simultaneous testing of multiple identical devices.

---

## Troubleshooting: Devices with Non-OpenWrt Firmware

### Problem: Device has LibreMesh or other custom firmware

If a device has LibreMesh, DD-WRT, or other custom firmware instead of OpenWrt vanilla, it may have different:
- Network configuration (mesh networks, different IP schemes)
- Shell prompts that don't match labgrid expectations
- VLAN configurations that prevent network access

**Symptoms:**
- Tests fail with "Failed to transition to state shell"
- Network unreachable when trying to download firmware
- Serial console shows LibreMesh/custom firmware banner

### Solution: Flash OpenWrt Vanilla via Serial Console

#### Step 1: Connect via screen (bypass labgrid)

```bash
# Connect directly to the serial port
sudo screen /dev/belkin-rt3200-X 115200
# Replace X with device number (1, 2, 3, etc.)

# Press Enter to activate the console
```

#### Step 2: Configure network access

LibreMesh ports may not be in the bridge. Check and fix:

```bash
# See which interfaces are in br-lan
brctl show br-lan

# If WAN port is missing (and device is connected via WAN), add it
brctl addif br-lan wan
ip link set wan up

# If device is connected via LAN port, move cable to a LAN port
# LibreMesh LAN ports (lan1-4) are already in br-lan
```

#### Step 3: Add device to VLAN 20 temporarily (for download only)

In your TP-Link switch web interface:
1. Find the device's port (e.g., port 6)
2. Add it to VLAN 20 as **UNTAGGED**
3. This allows access to the main network temporarily

#### Step 4: Configure IP on the device

```bash
# Configure br-lan for main network (VLAN 20)
ip addr add 192.168.20.50/24 dev br-lan
ip route add default via 192.168.20.1

# Test connectivity
ping -c 3 192.168.20.234
```

#### Step 5: Download and flash OpenWrt vanilla

```bash
cd /tmp

# Download OpenWrt sysupgrade firmware
wget http://192.168.20.234:8000/firmwares/belkin_rt3200/openwrt-23.05.5-mediatek-mt7622-linksys_e8450-ubi-squashfs-sysupgrade.itb -O sysupgrade.itb

# Verify download (should be ~9.5 MB)
ls -lh sysupgrade.itb

# Flash WITHOUT saving LibreMesh config (-n flag)
sysupgrade -n -v /tmp/sysupgrade.itb

# Device will reboot with OpenWrt vanilla
```

#### Step 6: Cleanup

After device reboots with OpenWrt:

1. **Exit screen**: Ctrl+A then K, confirm with y
2. **Remove device from VLAN 20** in switch config
3. **Leave device only in its dedicated VLAN** (e.g., VLAN 102)
4. **Test with labgrid**:

```bash
export LG_CROSSBAR=ws://localhost:20408/ws
export LG_PLACE=labgrid-fcefyn-belkin_rt3200_X
export LG_IMAGE=/srv/tftp/firmwares/belkin_rt3200/openwrt-23.05.5-mediatek-mt7622-linksys_e8450-ubi-initramfs-recovery.itb

cd ~/Documents/openwrt-tests
labgrid-client lock
pytest tests/test_base.py -v
labgrid-client unlock
```

**Expected:** 9 passed, 2 skipped

### Starting HTTP server for firmware downloads

If you need to serve firmware files:

```bash
# Start simple HTTP server in /srv/tftp
cd /srv/tftp
python3 -m http.server 8000 &

# Firmware will be available at:
# http://192.168.20.234:8000/firmwares/...
```

Stop when done:

```bash
pkill -f "http.server 8000"
```

---

## Known Issues and Workarounds

### ser2net Version Compatibility

**Issue:** Different ser2net versions have varying compatibility with serial adapters and labgrid.

**Findings:**
- **ser2net 4.6.0** (Ubuntu 24.04 repo): RFC2217 compatibility issues with pyserial/labgrid
- **ser2net 3.5.1**: Works well with FTDI adapters (Belkin RT3200), recommended by labgrid docs
- **ser2net 4.6.5**: Best overall compatibility, resolves CH340 buffer overflow issues (GL.iNet MT300N-v2)

https://github.com/cminyard/ser2net/tags

**Resolution:** Compile and install `ser2net 4.6.5` from source (see installation instructions above).

### GL.iNet MT300N-v2 Special Requirements

**Issue:** The GL.iNet MT300N-v2 has unique boot behavior that requires special handling:

1. **Serial Line Interference:** The device's CH340 USB-to-serial chip interferes with boot if the serial line is active during power-on
2. **CH340 Buffer Overflow:** ser2net 3.5.1 and 4.6.0 cause "buffer overflow detected" errors with CH340 adapters
3. **U-Boot Detection:** Device may boot directly to OpenWrt, bypassing U-Boot, making TFTP recovery difficult

### VLAN Configuration Summary

**Purpose:** Isolate multiple identical devices (same default IP `192.168.1.1`) in separate network segments.

**Components Configured:**
- **MikroTik Hex Router:** Created VLAN interfaces (100, 101, 102, 103), assigned gateway IPs, configured firewall rules
- **TP-Link SG2008P Switch:** Configured port membership (trunk/tagged/untagged), set PVIDs per device
- **Ubuntu Server:** Created VLAN interfaces via NetworkManager, assigned dual IPs per VLAN (TFTP IP + SSH IP)
- **dnsmasq:** Configured DHCP/TFTP listeners on all VLAN interfaces
- **labgrid:** Updated exporter with `%vlanXXX` notation for device addresses

**Key Learnings:**
- Each server VLAN interface needs **two IP addresses**: one for TFTP (`192.168.X.1/24`) and one for SSH (`192.168.1.X/24`)
- `labgrid-bound-connect` and `socat` are required for SSH over VLANs
- Sudoers configuration must allow `labgrid-bound-connect` without password
- Switch port configuration must match physical connections (trunk for MikroTik/server, access for devices)

**Result:** Successfully isolated 3x Belkin RT3200 devices in VLANs 100, 101, 102. GL.iNet MT300N-v2 assigned VLAN 103 (pending full automation).

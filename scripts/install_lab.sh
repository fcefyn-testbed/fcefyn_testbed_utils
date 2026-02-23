#!/bin/bash
#
# install_lab.sh - Automated installation script for FCEFYN HIL Testing Lab
#
# Usage: ./install_lab.sh [--skip-vlan] [--skip-firmware]
#
# This script installs and configures all components needed for the lab.
# Some steps require manual intervention (marked with MANUAL).
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_header() { echo -e "\n${BLUE}═══════════════════════════════════════════════════════════════${NC}"; echo -e "${BLUE}  $1${NC}"; echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}\n"; }
print_success() { echo -e "${GREEN}✓${NC} $1"; }
print_warning() { echo -e "${YELLOW}⚠${NC} $1"; }
print_error() { echo -e "${RED}✗${NC} $1"; }
print_info() { echo -e "${BLUE}ℹ${NC} $1"; }
print_manual() { echo -e "${YELLOW}[MANUAL]${NC} $1"; }

# Parse arguments
SKIP_VLAN=false
SKIP_FIRMWARE=false
for arg in "$@"; do
    case $arg in
        --skip-vlan) SKIP_VLAN=true ;;
        --skip-firmware) SKIP_FIRMWARE=true ;;
    esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"

print_header "FCEFYN HIL Testing Lab Installation"
echo "This script will install and configure the following components:"
echo "  - System dependencies"
echo "  - ser2net 4.6.5 (compiled from source)"
echo "  - Labgrid (aparcar fork)"
echo "  - PDUDaemon"
echo "  - Arduino relay control script"
echo "  - dnsmasq (TFTP server)"
echo "  - VLAN interfaces"
echo ""
read -p "Continue? [y/N] " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 1
fi

# Step 1: System Dependencies
print_header "Step 1: Installing System Dependencies"

sudo apt update
sudo apt install -y \
    python3-pip \
    python3-venv \
    python3-dev \
    pipx \
    dnsmasq \
    build-essential \
    libgensio-dev \
    libyaml-dev \
    libsystemd-dev \
    pkg-config \
    socat \
    screen \
    git \
    curl \
    wget

pipx ensurepath
export PATH="$PATH:$HOME/.local/bin"
print_success "System dependencies installed"

# Step 2: ser2net 4.6.5
print_header "Step 2: Installing ser2net 4.6.5"

if /usr/local/sbin/ser2net -v 2>&1 | grep -q "4.6.5"; then
    print_success "ser2net 4.6.5 already installed"
else
    print_info "Compiling ser2net 4.6.5 from source..."
    cd /tmp
    rm -rf ser2net-4.6.5 v4.6.5.tar.gz
    wget -q https://github.com/cminyard/ser2net/archive/refs/tags/v4.6.5.tar.gz
    tar -xzf v4.6.5.tar.gz
    cd ser2net-4.6.5
    ./reconf
    ./configure
    make -j$(nproc)
    sudo make install
    
    # Remove repo version if installed
    sudo apt remove ser2net --purge -y 2>/dev/null || true
    
    print_success "ser2net 4.6.5 installed"
fi

# Step 3: Labgrid
print_header "Step 3: Installing Labgrid"

if pipx list | grep -q labgrid; then
    print_warning "Labgrid already installed via pipx, reinstalling..."
    pipx uninstall labgrid || true
fi

pipx install git+https://github.com/aparcar/labgrid.git@aparcar/staging
print_success "Labgrid installed"

# Install labgrid-bound-connect
print_info "Installing labgrid-bound-connect helper..."
LABGRID_HELPERS=$(pipx runpip labgrid show labgrid | grep Location | awk '{print $2}')/../../../share/labgrid/helpers
if [ -f "$LABGRID_HELPERS/labgrid-bound-connect" ]; then
    sudo cp "$LABGRID_HELPERS/labgrid-bound-connect" /usr/local/sbin/
    sudo chmod +x /usr/local/sbin/labgrid-bound-connect
    print_success "labgrid-bound-connect installed"
else
    print_warning "labgrid-bound-connect not found in package, will need manual installation"
    print_manual "Copy labgrid-bound-connect from labgrid repo to /usr/local/sbin/"
fi

# Step 4: PDUDaemon
print_header "Step 4: Installing PDUDaemon"

if pipx list | grep -q pdudaemon; then
    print_success "PDUDaemon already installed"
else
    pipx install git+https://github.com/jonasjelonek/pdudaemon.git@main
    print_success "PDUDaemon installed"
fi

# Step 5: Arduino Relay Control and PoE Switch Control
print_header "Step 5: Installing Power Control Scripts"

pip install paramiko --quiet 2>/dev/null || pip3 install paramiko --quiet 2>/dev/null || true

if [ -f "$REPO_DIR/scripts/arduino_relay_control.py" ]; then
    sudo cp "$REPO_DIR/scripts/arduino_relay_control.py" /usr/local/bin/
    sudo chmod +x /usr/local/bin/arduino_relay_control.py
    print_success "arduino_relay_control.py installed to /usr/local/bin/"
else
    print_error "arduino_relay_control.py not found in $REPO_DIR/scripts/"
    exit 1
fi

if [ -f "$REPO_DIR/scripts/poe_switch_control.py" ]; then
    sudo cp "$REPO_DIR/scripts/poe_switch_control.py" /usr/local/bin/
    sudo chmod +x /usr/local/bin/poe_switch_control.py
    print_success "poe_switch_control.py installed to /usr/local/bin/"
fi

# Step 6: PDUDaemon Configuration
print_header "Step 6: Configuring PDUDaemon"

sudo mkdir -p /etc/pdudaemon
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
        },
        "fcefyn-poe-openwrt-one": {
            "driver": "localcmdline",
            "cmd_on": "/usr/local/bin/poe_switch_control.py on %s",
            "cmd_off": "/usr/local/bin/poe_switch_control.py off %s"
        }
    }
}
EOF
sudo chmod 644 /etc/pdudaemon/pdudaemon.conf
print_success "PDUDaemon configuration created"

# Create systemd service
PDUDAEMON_PATH=$(which pdudaemon)
sudo tee /etc/systemd/system/pdudaemon.service > /dev/null << EOF
[Unit]
Description=PDUDaemon - Power Distribution Unit Controller
After=network.target

[Service]
ExecStart=$PDUDAEMON_PATH --conf=/etc/pdudaemon/pdudaemon.conf
Type=simple
User=$USER
Restart=on-abnormal

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable pdudaemon
print_success "PDUDaemon systemd service created"

# Step 7: TFTP Server
print_header "Step 7: Configuring TFTP Server (dnsmasq)"

sudo mkdir -p /srv/tftp/{firmwares/belkin_rt3200,belkin_rt3200_1,belkin_rt3200_2,belkin_rt3200_3,gl_mt300n_v2}
sudo chown -R $USER:$USER /srv/tftp
sudo chmod -R 755 /srv/tftp

# Remove old config if exists
sudo rm -f /etc/dnsmasq.d/tftp-only.conf

sudo tee /etc/dnsmasq.d/tftp.conf > /dev/null << 'EOF'
# Disable DNS
port=0

# DHCP/TFTP per VLAN
interface=vlan100
dhcp-range=vlan100,192.168.100.100,192.168.100.200,24h

interface=vlan101
dhcp-range=vlan101,192.168.101.100,192.168.101.200,24h

interface=vlan102
dhcp-range=vlan102,192.168.102.100,192.168.102.200,24h

interface=vlan103
dhcp-range=vlan103,192.168.103.100,192.168.103.200,24h

# TFTP
enable-tftp
tftp-root=/srv/tftp/

# Listen addresses
listen-address=192.168.100.1
listen-address=192.168.101.1
listen-address=192.168.102.1
listen-address=192.168.103.1
listen-address=127.0.0.1
bind-interfaces
EOF

print_success "dnsmasq TFTP configuration created"

# Step 8: VLAN Interfaces
if [ "$SKIP_VLAN" = false ]; then
    print_header "Step 8: Configuring VLAN Interfaces"
    
    # Detect ethernet interface
    IFACE=$(ip route | grep default | awk '{print $5}' | head -1)
    echo "Detected ethernet interface: $IFACE"
    read -p "Is this correct? [y/N] " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        read -p "Enter the correct interface name: " IFACE
    fi
    
    for VLAN in 100 101 102 103; do
        if nmcli connection show vlan$VLAN &>/dev/null; then
            print_warning "VLAN $VLAN already exists, skipping..."
        else
            print_info "Creating VLAN $VLAN..."
            sudo nmcli connection add type vlan con-name vlan$VLAN ifname vlan$VLAN dev $IFACE id $VLAN
            
            # Calculate IPs
            TFTP_IP="192.168.$VLAN.1/24"
            SSH_IP="192.168.1.$VLAN/24"
            
            sudo nmcli connection modify vlan$VLAN ipv4.method manual ipv4.addresses "$TFTP_IP,$SSH_IP"
            sudo nmcli connection modify vlan$VLAN ipv6.method ignore connection.autoconnect yes
            sudo nmcli connection up vlan$VLAN || print_warning "Could not bring up vlan$VLAN (switch may not be connected)"
            print_success "VLAN $VLAN configured"
        fi
    done
else
    print_warning "Skipping VLAN configuration (--skip-vlan)"
fi

# Step 9: Sudoers
print_header "Step 9: Configuring Sudoers"

sudo tee /etc/sudoers.d/labgrid > /dev/null << EOF
# Allow labgrid SSH proxy without password
$USER ALL=(ALL) NOPASSWD: /usr/local/sbin/labgrid-bound-connect
EOF
sudo chmod 440 /etc/sudoers.d/labgrid

if sudo visudo -c; then
    print_success "Sudoers configured"
else
    print_error "Sudoers configuration error!"
    sudo rm /etc/sudoers.d/labgrid
fi

# Step 10: Labgrid Coordinator Directory
print_header "Step 10: Creating Labgrid Coordinator Directory"

mkdir -p ~/labgrid-coordinator
if [ -f "$REPO_DIR/configs/places.yaml" ]; then
    cp "$REPO_DIR/configs/places.yaml" ~/labgrid-coordinator/
    print_success "places.yaml copied"
else
    print_warning "places.yaml not found, will need to be generated"
fi

# Step 11: Download Firmware
if [ "$SKIP_FIRMWARE" = false ]; then
    print_header "Step 11: Downloading OpenWrt Firmware"
    
    FIRMWARE_URL="https://downloads.openwrt.org/releases/23.05.5/targets/mediatek/mt7622/openwrt-23.05.5-mediatek-mt7622-linksys_e8450-ubi-initramfs-recovery.itb"
    FIRMWARE_PATH="/srv/tftp/firmwares/belkin_rt3200/openwrt-23.05.5-mediatek-mt7622-linksys_e8450-ubi-initramfs-recovery.itb"
    
    if [ -f "$FIRMWARE_PATH" ]; then
        print_success "Firmware already exists"
    else
        print_info "Downloading firmware..."
        wget -q --show-progress -O "$FIRMWARE_PATH" "$FIRMWARE_URL"
        print_success "Firmware downloaded"
    fi
else
    print_warning "Skipping firmware download (--skip-firmware)"
fi

# Step 12: Start Services
print_header "Step 12: Starting Services"

sudo systemctl restart dnsmasq
sudo systemctl start pdudaemon

if systemctl is-active --quiet dnsmasq; then
    print_success "dnsmasq is running"
else
    print_error "dnsmasq failed to start"
fi

if systemctl is-active --quiet pdudaemon; then
    print_success "pdudaemon is running"
else
    print_warning "pdudaemon may not be running (Arduino might not be connected)"
fi

# Final Summary
print_header "Installation Complete!"

echo -e "${GREEN}Installed components:${NC}"
echo "  ✓ ser2net 4.6.5"
echo "  ✓ Labgrid (aparcar fork)"
echo "  ✓ PDUDaemon"
echo "  ✓ Arduino relay control"
echo "  ✓ dnsmasq TFTP server"
echo "  ✓ VLAN interfaces"
echo ""
echo -e "${YELLOW}Manual steps required:${NC}"
echo "  1. Configure udev rules for serial devices:"
echo "     sudo nano /etc/udev/rules.d/99-hil-devices.rules"
echo "     (See MIGRATION.md for details)"
echo ""
echo "  2. Clone openwrt-tests repository:"
echo "     cd ~/Documents"
echo "     git clone https://github.com/YOUR_USERNAME/openwrt-tests.git"
echo ""
echo "  3. Generate SSH key for the lab:"
echo "     ssh-keygen -t ed25519 -C 'fcefyn-lab' -f ~/.ssh/fcefyn_lab"
echo ""
echo "  4. Run verification:"
echo "     ./scripts/verify_installation.sh"
echo ""
print_info "See MIGRATION.md for complete documentation."


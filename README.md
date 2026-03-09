# pi-hil-testing-utils

Infraestructura complementaria del banco de pruebas HIL (Hardware-in-the-Loop) de FCEFyN: configs, scripts y firmwares que no están en libremesh-tests.

---

## Estructura

```
pi-hil-testing-utils/
├── configs/          # Documentación y configs del lab
│   ├── README.md     # Índice, orden de lectura
│   ├── host-config.md, tftp-server.md, switch-config.md, ...
│   └── ssh_config_fcefyn, 99-serial-devices.rules, ...
├── scripts/          # Utilidades Python/shell
│   ├── switch/       # Switch SSH, VLANs, PoE, pool-manager
│   ├── testbed-mode.sh, arduino_*.py, ...
├── firmwares/        # Imágenes por dispositivo (qemu, Belkin, etc.)
└── arduino/          # Firmware del controlador de relés
```

---

## Setup (Ansible)

El setup productivo y local se hace con **Ansible** desde libremesh-tests (o openwrt-tests):

```bash
cd openwrt-tests   # o libremesh-tests
ansible-playbook -i inventory.ini playbook_labgrid.yml -l labgrid-fcefyn -K
```

El playbook despliega exporter, PDUDaemon, dnsmasq, netplan, places.yaml, etc. Ver [configs/ansible-labgrid.md](configs/ansible-labgrid.md).

---

## Scripts

| Script | Uso |
|--------|-----|
| `scripts/switch/poe_switch_control.py` | Puertos PoE del switch TP-Link (OpenWRT One, Librerouter). |
| `scripts/switch/switch_vlan_preset.py` | Cambia VLANs del switch (isolated vs mesh). |
| `scripts/switch/pool-manager.py` | Modo híbrido: exporters por pool, switch differential apply. |
| `arduino_relay_control.py` | Control de relés Arduino (power on/off). Usado por PDUDaemon. |
| `arduino_daemon.py` | Daemon de conexión persistente al Arduino. Servicio `arduino-relay-daemon`. |
| `generate_places_yaml.py` | Genera `places.yaml` desde labnet.yaml. |
| `identify_devices.sh` | Identificación de dispositivos seriales por udev. |
| `start_daemon.sh` | Arranque manual del daemon Arduino. |
| `resolve_target.py` | Resuelve target file desde device name. |

Los scripts de control deben estar en `/usr/local/bin/` o en el PATH; el playbook puede copiarlos.

---

## Prerrequisitos

- **git-lfs** — `apt install git-lfs` antes de clonar (firmwares).
- Python 3, `pyserial`, `pipx`, dnsmasq, ser2net — el playbook Ansible instala la mayoría.

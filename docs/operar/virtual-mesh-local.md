# Running the virtual mesh locally

How to launch QEMU-based virtual mesh nodes on a developer machine using
[vwifi](https://github.com/sysprog21/vwifi) for WiFi simulation, and run the
libremesh-tests suite against them without physical hardware.

---

## 1. Check the source image

The build source image lives in:

```
firmwares/qemu/libremesh/lime-<version>-viwifi-x86-64-generic-ext4-combined.img
```

The `vms/node*.img` files are **working copies** created by QEMU at runtime —
they are not the source image and should not be used as a base.

```bash
# Check size (should be ~121 MB) and date
ls -lh firmwares/qemu/libremesh/*.img

# Confirm it is a bootable x86 disk
file firmwares/qemu/libremesh/lime-*.img
# Expected: "DOS/MBR boot sector"

# Check the LibreMesh version inside the image
strings firmwares/qemu/libremesh/lime-*.img | grep -i 'DISTRIB_RELEASE\|lime_release'

# Hash for comparison with previous builds
md5sum firmwares/qemu/libremesh/lime-*.img
```

---

## 2. Launch the VMs

```bash
# From the repo root
VIRTUAL_MESH_IMAGE=firmwares/qemu/libremesh/lime-*.img ./vms/launch_debug_vms.sh
```

Available environment variables:

| Variable | Default | Description |
|---|---|---|
| `VIRTUAL_MESH_IMAGE` | — | Path to the image (required) |
| `VIRTUAL_MESH_NODES` | `2` | Number of VMs to start |
| `VIRTUAL_MESH_BOOT_TIMEOUT` | `120` | Seconds to wait for boot |
| `VIRTUAL_MESH_CONVERGENCE_WAIT` | `60` | Seconds to wait for mesh convergence |
| `VIRTUAL_MESH_SKIP_VWIFI` | `0` | Skip vwifi setup (useful for quick debugging) |

### SSH into the nodes

```bash
ssh -o StrictHostKeyChecking=no -p 2222 root@127.0.0.1  # VM 1
ssh -o StrictHostKeyChecking=no -p 2223 root@127.0.0.1  # VM 2
```

---

## 3. Run the tests

With the VMs already running:

```bash
# All tests
pytest tests/mesh/ -v

# Node health only (interfaces, services, UCI, kernel)
pytest tests/mesh/test_mesh_node_basic.py -v

# Network connectivity (ping bat0, unique IPs, inter-node visibility)
pytest tests/mesh/test_mesh_basic.py -v

# batman-adv (TQ, originators, symmetry, statistics)
pytest tests/mesh/test_mesh_batman.py -v
```

With 3 nodes:

```bash
VIRTUAL_MESH_NODES=3 VIRTUAL_MESH_IMAGE=firmwares/qemu/libremesh/lime-*.img \
  ./vms/launch_debug_vms.sh &

# Wait for "Debug session ready", then:
VIRTUAL_MESH_NODES=3 pytest tests/mesh/ -v
```

---

## 4. Useful commands inside a node

```bash
batctl n          # direct batman-adv neighbours
batctl o          # originator table (all mesh routes)
batctl if         # batman slave interfaces
batctl s          # traffic statistics
ip addr show bat0 # node IP on the mesh
logread | grep lime-config   # verify lime-config ran
uci show vwifi               # vwifi client config
```

---

## 5. Related pages

- [Virtual mesh design](../diseno/virtual-mesh.md) — architecture, CI integration, fixture variables
- [Build firmware](build-firmware-manual.md) — how to build the QEMU vwifi image
- [Running tests](lab-running-tests.md) — physical DUT tests

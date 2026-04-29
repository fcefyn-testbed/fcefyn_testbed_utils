# lime-packages CI: hardware tests

After the firmware build in [lime-packages CI: firmware build](lime-packages-ci-flow.md),
a downstream job runs the [libremesh-tests](https://github.com/fcefyn-testbed/libremesh-tests)
suite on physical hardware in the FCEFYN lab.

---

## Flow

```
lime-packages PR build succeeds
        ↓
  Download firmware artifact
        ↓
  self-hosted runner (testbed-fcefyn)
  Reserve DUT via labgrid
        ↓
  Load firmware via TFTP (RAM boot)
  No flash written
        ↓
  pytest (libremesh-tests)
        ↓
  Release DUT
  Report results on PR
```

---

## Runner

Tests run on the `testbed-fcefyn` self-hosted runner (the T430 machine in the FCEFYN lab).
This runner is shared with the `flash_and_test` job in
[build-and-test-libremesh.yml](../operar/ci-build-and-test.md).

Setup: [GitHub Actions self-hosted runner](../configuracion/ci-runner.md).

---

## DUT reservation

The job uses `labgrid-client reserve --wait` so it queues until the requested device is
free. If multiple CI jobs run at the same time (e.g. two open PRs), the second job waits
rather than failing.

---

## Test suite

The [libremesh-tests](https://github.com/fcefyn-testbed/libremesh-tests) suite validates:

- Device boots and reaches a shell
- LibreMesh packages are installed and services start
- Basic mesh configuration is applied
- Network interfaces are configured correctly

Tests use the `LG_IMAGE` firmware loaded via TFTP — the device boots into RAM, runs the
test fixture, and is powered off at teardown. The flash is never written.

---

## Relationship to this repo

The `flash_and_test` job in `build-and-test-libremesh.yml` follows the same pattern but
uses firmware built by the SDK + ImageBuilder pipeline in this repo instead of the
lime-packages fork. See [CI: Build & Test](../operar/ci-build-and-test.md).

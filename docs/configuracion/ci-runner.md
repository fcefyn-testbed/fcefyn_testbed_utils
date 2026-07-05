# GitHub Actions self-hosted runner

To run libremesh-tests workflows on the lab host, we installed a **GitHub Actions self-hosted runner**. Daily, Healthcheck, and Pull Request jobs run on this hardware instead of GitHub-hosted or third-party runners.  This is on overview of the steps to set up a function runner for the testbed.

---

## 1. Requirements

- GitHub account/repo (e.g. `francoriba/libremesh-tests` or the relevant org).
- SSH access to the lab host.

---

## 2. Installation

1. Download the runner from [GitHub Actions Runner](https://github.com/actions/runner/releases) (Linux x64).

2. In the repo: **Settings** → **Actions** → **Runners** → **New self-hosted runner**. Copy the configure command.

3. On the lab host:

   ```bash
   mkdir -p ~/actions-runner && cd ~/actions-runner
   # Download the .tar.gz from the release, extract
   ./config.sh --url https://github.com/OWNER/REPO --token TOKEN
   ```

4. During setup:
   - **Runner name**: e.g. `runner-fcefyn` or `labgrid-fcefyn`
   - **Additional labels**: e.g. `testbed-fcefyn` (for `runs-on: [self-hosted, testbed-fcefyn]` in workflows)

5. Install and start the service:

   ```bash
   sudo ./svc.sh install
   sudo ./svc.sh start
   ```

---

## 3. Verification

```bash
sudo systemctl status actions.runner.*
```

In GitHub, the runner should show **Idle** under **Settings** → **Actions** → **Runners**.

---

## 4. Permissions on /etc/labgrid

The Labgrid coordinator writes under `/etc/labgrid` (place/resource state). Wrong permissions cause `PermissionError` on save. The libremesh-tests playbook should create `/etc/labgrid` with `owner: labgrid-dev` and `group: labgrid-dev`. To fix manually:

```bash
sudo chown -R labgrid-dev:labgrid-dev /etc/labgrid
sudo systemctl restart labgrid-coordinator
```

---

## 5. Move runner to another repo (if needed)

To move the runner from one repo to another (or user to org):

1. On host: `./config.sh remove --token TOKEN` (token from current repo/org UI).
2. In new repo/org: **New self-hosted runner** → copy the new command.
3. Run `./config.sh` with new URL and token.
4. `sudo ./svc.sh uninstall` then `sudo ./svc.sh install` + `sudo ./svc.sh start`.

---

## 6. Organisation registration

The runner (`fcefyn-runner`) is registered in the **`libremesh`**
GitHub organisation (`Settings > Actions > Runners`). It services
workflows from any repo in the org, including `libremesh/lime-packages`.

The runner group's `allows_public_repositories` must be `true` for it
to pick up jobs from public repos.

The systemd service is named `actions.runner.libremesh.fcefyn-runner.service`.

---

## 7. Workflows that use this runner

The following workflows target this runner with `runs-on: [self-hosted, testbed-fcefyn]`:

| Workflow | Repository | Trigger | What it does on the runner |
|----------|-----------|---------|---------------------------|
| `build-firmware.yml` | `libremesh/lime-packages` | PR, `workflow_dispatch`, schedule | Physical tests (`test-firmware`, `test-mesh`) after environment approval |
| `build-and-test-libremesh.yml` | `fcefyn-testbed/fcefyn_testbed_utils` | Manual (`workflow_dispatch`) | Downloads firmware, reserves DUT via labgrid, loads firmware, runs libremesh-tests |

See [CI: Build & Test](../operar/ci-build-and-test.md) for full usage instructions.

---

## 8. Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| Runner shows **Offline** in GitHub | Service stopped | `sudo systemctl restart actions.runner.*` |
| `flash_and_test` job queued but never starts | Runner offline or label mismatch | Check runner labels include `testbed-fcefyn` |
| `PermissionError` on labgrid coordinator | Wrong `/etc/labgrid` ownership | See §4 above |
| Job fails at "Reserve DUT" | DUT locked by a previous run | `labgrid-client -p <place> unlock` |

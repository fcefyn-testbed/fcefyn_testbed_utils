# Onboarding a new researcher

End-to-end checklist for getting a new researcher access to the FCEFyN testbed so they can run tests, edit code, and merge PRs.

For purely external developers (no lab access, just running tests remotely), see [Developer remote access](developer-remote-access.md) instead.

---

## 1. GitHub access

1. Ask the new researcher for their GitHub username and the **public** part of an SSH key they will use for git over SSH.
2. Add them to the `fcefyn-testbed` GitHub organisation as a member (for lab infra repos).
3. If they need to approve physical test runs, add them as a reviewer in the `physical-lab` environment: `libremesh/lime-packages` > Settings > Environments > `physical-lab` > Required reviewers.
4. If they will work on `libremesh-tests`, grant them access in the `libremesh` org.

## 2. SSH keys on the lab host

1. Append their `ed25519` (or `rsa`) public key to `/home/laryc/.ssh/authorized_keys` on the lab host.
2. Verify they can reach the host from outside (after step 3 they will use ZeroTier; before that, the lab admin can give them a temporary forwarded port).

## 3. ZeroTier (remote access)

1. Send them the install/auth guide: [ZeroTier remote access](zerotier-remote-access.md).
2. After they join the network with `zerotier-cli join <network-id>`, authorise their node in [ZeroTier Central](https://my.zerotier.com) (the [`zerotier` Ansible role README](../../ansible/roles/zerotier/README.md) explains this step).
3. Assign them a stable IP under "Managed IPs" in ZeroTier Central. Send them their assigned IP.

They should now be able to `ssh laryc@<assigned-zt-ip>`.

## 4. Local tooling

Ask them to install on their personal machine:

- `uv` (`pip install uv` or [official installer](https://docs.astral.sh/uv/)) — runs the test suites in `libremesh-tests`.
- `gh` CLI — useful for workflow dispatch and PR review (`brew install gh` / `apt install gh`).
- A GPG key set up locally — **signed commits are required** on this repo.

GPG key quick setup:

```sh
gpg --full-generate-key                 # ed25519 recommended
gpg --list-secret-keys --keyid-format=long
git config --global user.signingkey <KEYID>
git config --global commit.gpgsign true
# Add the public key to GitHub: https://github.com/settings/keys
```

## 5. First test run

Walk them through a minimal verification that everything works end-to-end:

1. Clone `libremesh-tests` and `fcefyn_testbed_utils` locally.
2. From the lab host (over ZeroTier SSH), check the labgrid coordinator and exporter are up:

   ```sh
   systemctl status labgrid-coordinator labgrid-exporter
   uv run labgrid-client places
   ```

3. Trigger one CI run from their GitHub account: open a PR to `libremesh/lime-packages`, watch the build + test jobs flow, approve the `physical-lab` environment when prompted (if they are a reviewer).
4. Open the [CI dashboard](https://fcefyn-testbed.github.io/fcefyn_testbed_utils/ci-results/dashboard.html) and check their run appears.

## 6. Documentation pointers

- **Day-to-day operations:** [Routine operations](lab-routine-operations.md), [Running tests](lab-running-tests.md), [Labgrid commands](labgrid-useful-commands.md).
- **When something breaks:** [Debugging FAQ](debugging-faq.md).
- **Adding a new DUT:** [Adding a DUT](dut-onboarding.md), then [DUT provisioning](provision-dut.md), [DUT exporter setup](setup-dut-exporter.md).
- **Glossary:** [Glossary](../glosario.md) — central place for jargon (Labgrid, batman-adv, FIT image, etc.).

## 7. House rules

- All work goes through PRs to `develop`. Direct pushes to `develop` and `main` are blocked.
- Commits must be GPG-signed.
- The `summary` job in `lime-packages` CI is a required status check; if it fails, fix the cause, do not merge with `--admin`.
- The lab host is shared. Before doing anything destructive (rebooting, stopping daemons), check the calendar and announce on the lab chat.

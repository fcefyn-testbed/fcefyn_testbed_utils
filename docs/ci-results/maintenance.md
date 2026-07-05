# Dashboard Maintenance

## Updating the device list

Edit `docs/ci-results/results/devices.json` and open a PR to `develop`. Changes take effect after the next Pages deploy.

See [Device Registry](devices.md) for the full field reference.

## Rotating the tokens

The pull pipeline uses two fine-grained PATs stored as repository secrets in `fcefyn_testbed_utils`. PATs expire — when they do, the `collect-lime-results.yml` workflow fails on the step that uses the expired token.

### `LIME_PACKAGES_TOKEN`

Used to list runs and download artifacts from `lime-packages`. A 401/403 on the "Download lime-packages report.xml artifacts" step means this token expired.

1. Generate a new fine-grained PAT at `github.com/settings/personal-access-tokens/new`:
    - Resource owner: `libremesh`
    - Repository access: only `lime-packages`
    - Permissions: **Actions: Read-only** (Metadata: Read is added automatically)
2. `Settings → Secrets and variables → Actions` on `fcefyn_testbed_utils`
3. Update `LIME_PACKAGES_TOKEN` with the new value

### `BOT_PR_TOKEN`

Used to open the auto-merged PR with the collected results. A 401/403 on the "Create PR with collected results" or "Enable auto-merge" step means this one expired.

1. Generate a new fine-grained PAT at `github.com/settings/personal-access-tokens/new`:
    - Resource owner: `fcefyn-testbed`
    - Repository access: only `fcefyn_testbed_utils`
    - Permissions: **Contents: Read and write** + **Pull requests: Read and write**
2. Update `BOT_PR_TOKEN` in the same secrets page

## Re-collecting results manually

To force an immediate pull (e.g. after a fresh CI run in `lime-packages`):

1. **Actions → Collect lime-packages test results**
2. **Run workflow** → branch `develop` → optionally set `runs` (default 10 — how many recent CI runs to scan)

The workflow is idempotent: it skips reports already present, so running it repeatedly is safe.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Cards show "Test details not yet published" | `report.xml` for that device/release hasn't been collected yet | Trigger `collect-lime-results.yml` manually, or wait for the cron |
| "Report ↗" link returns 404 | Either the report hasn't been collected yet, or `PAGES_BASE` in `dashboard.html` is pointing at the wrong host | Open the link and check the URL host — it must be `fcefyn-testbed.github.io/fcefyn_testbed_utils/` |
| Collect workflow fails with 401/403 on Download step | `LIME_PACKAGES_TOKEN` expired | Rotate (see above) |
| Collect workflow fails with 401/403 on Create PR step | `BOT_PR_TOKEN` expired | Rotate (see above) |
| Collect workflow fails with "GitHub Actions is not permitted to create or approve pull requests" | Org-level Actions setting disabled | Use a PAT (`BOT_PR_TOKEN`) — already the default; if blocked, check **Settings → Actions → General → Workflow permissions** at the org level |
| Collect workflow fails with "Auto merge is not allowed for this repository" | Repo setting disabled | **Settings → General → Pull Requests → Allow auto-merge** |
| Bot PR fails to merge with "Commits must have verified signatures" | `develop` branch protection has signed-commits required | Disable it: the PR is opened with the user PAT and not signed by GitHub — `gh api -X DELETE repos/fcefyn-testbed/fcefyn_testbed_utils/branches/develop/protection/required_signatures` |
| Dashboard shows no cards at all | GitHub API rate limit hit (60 req/h, unauthenticated) | Wait ~1 hour and reload |
| Old results not refreshing | Cron runs every 6h; no new CI runs in `lime-packages` since last pull | Trigger manually if needed |

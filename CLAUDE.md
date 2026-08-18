# jupyter-b2 project guidance

Repo-local rules for `backblaze-labs/jupyter-b2`. These add to the
workspace-level and global `CLAUDE.md` files. When rules overlap, the most
specific one wins.

## CI must never run on Dependabot PRs

Dependabot pull requests must not trigger any CI, ever. This is enforced by a
job-level guard on every job in every `pull_request`-triggered workflow:

```yaml
if: ${{ github.actor != 'dependabot[bot]' && github.event.pull_request.user.login != 'dependabot[bot]' }}
```

Both clauses are intentional:

* `github.actor != 'dependabot[bot]'` blocks the initial Dependabot-triggered
  run.
* `github.event.pull_request.user.login != 'dependabot[bot]'` keeps the jobs
  skipped even if a human later re-runs the workflow or pushes to the Dependabot
  branch.

Rules to keep this true going forward:

* Any new job added to `.github/workflows/ci.yml` must carry the guard.
* Any new workflow that runs on `pull_request` must add the guard to each of its
  jobs.
* `publish.yml` is exempt: it only triggers on `v*` tags, which Dependabot never
  creates.

Branch-protection caveat: if a guarded job is a required status check, skipped
Dependabot PRs will never report success and cannot merge (auto-merge included).
If Dependabot auto-merge is wanted, keep those checks non-required or gate merges
behind a single always-running status job.

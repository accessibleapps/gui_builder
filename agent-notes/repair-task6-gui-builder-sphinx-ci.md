# GUI Builder PR #9: Sphinx floor 8.1.3

## Goal

Preserve this dependency PR and supported Python while wiring the actual tracked tests, package build and real Sphinx autodoc build. No product/accessibility behavior, release workflow, dependency refresh, settings or external model calls.

## State

- Current local successor genuinely rebased from published 90c33a8b03cb489460929251d2151fb8054b5fa3 onto merged GUI #5 default 5a7ae5f7443e30ab05ad9c01f42d8984962954fb with --no-update-refs. Retain the exact wxPython Python 3.8 compatibility markers and original Sphinx >=8.1.3 proposal; no dependency/support/product/test policy change.
- Separate archive/task6-gui-builder-9-published-before-wx-rebase and -local-before-wx-rebase retain 90c33a8; archive/task6-gui-builder-canonical-before-wx-rebase preserves 32eb2671. Existing stacks, review worktrees, canonical experiments and other refs remain untouched. Remote PR #9 remains at 90c33a8; no publication.
- Replay produced add/add and historical-edit conflicts only in the generic living note. Preserve GUI #5's generic note at its original path and this branch's distinct Sphinx note. The later original rename removed the generic path during replay; restore exact default blob 0581bed9c0eb1ea61d0549f05ec18f184111aee1 before the final note commit. No note content was discarded; the old branch-note content below is retained as history.
- Return the complete fresh-default delta for root review before publication. No local CI, GUI execution, models, settings or description changes.

## Historical preparation state

- Current landed baseline: prerequisite #11 merged at 2026-10-21 02:35:30 UTC. Fresh authenticated master is 7a3c755e83b3f79f100560c73c3949cb1ec2f02c, independently read back from origin; its reviewed source was caa318f88aecdead2ba335413909d11a4bf69332 with all three hosted jobs green.
- Rebased this original feature branch from exact published/local 3c48385138ada5871b0acff8dc557c05bd775c19 onto actual master using git rebase --no-update-refs, not the earlier local merge stack. Both original feature commits were preserved. The rebase was clean; identical baseline CI/README were retained automatically.
- Exact published remote remains 3c48385138ada5871b0acff8dc557c05bd775c19; no push. The earlier local stack ca97cadbc52d211612e537ace44694ff0a9a5cf0 and its branch/worktree remain untouched. New backup/task6-gui-builder-9-{published,local,stacked}-before-master-rebase refs preserve those exact tips, alongside all original archives. Canonical dirty work and local master32eb2671 remain untouched.
- This current successor includes the landed config fix, complete seven tests and supported runtime/strict docs coverage; no source/test behavior changes. New final-head hosted/Claude gates remain pending. The following first-preparation state is historical.

- Fresh same-org origin is git@github.com:accessibleapps/gui_builder.git. Published PR #9 remains at cf3c623d5c89778fd4a0c6e0f0cb3dac6b136f10; preserved as backup/task6-gui-builder-9-published-before-repair. There was no local branch matching this Dependabot PR. Canonical master and all dirty/untracked experiments remain untouched.
- Local successor is based on current master 32eb2671a40eb3dc324e5628ef1544318adb6853, with only the original dependency commit replayed before this amendment. This carries current safe seven-test callback suite instead of inventing tests for an obsolete source tree. It is local and unpublished.
- Actions is enabled; existing default/release successes do not test this head. Hosted results and actual final-head Claude review are pending. No full local CI was run.

## Decisions and why

- Manifest/README Python floor is 3.8.6; RTD docs explicitly use 3.11. wxPython 4.2.4 primary PyPI metadata requires >=3.9 and supplies Windows wheels through CPython 3.14. The 3.8 wheel exists at 4.2.2. Python 3.14 is the latest demonstrated wheel leg, not a support-policy ceiling.
- Windows 3.8/3.14 installs the actual package graph with binary-only wxPython, imports wx and fields/forms without creating wx.App, runs the full unchanged tracked pytest suite (seven tests), and builds/verifies wheel/sdist. Compatible pytest pins are 8.3.5/9.1.1. Existing test stubs are not claimed as actual GUI/accessibility exercise.
- The docs job uses the actual RTD-selected Python 3.11 and real wxPython imports, not blanket autodoc mocks. Exact Sphinx 8.1.3/theme 3.1.0/typehints 3.0.0 meet the branch requirements (both typehints 3.0.0 and 3.0.1 require Sphinx >=8.1.3). Build runs from docs as its Makefile does; warnings are fatal and no links/services/examples are executed.
- Existing docs conf names absent _templates/_static directories. The strict hosted build may expose baseline documentation warnings; do not suppress or claim green. Classify actual failures against fresh default before a prerequisite fix.
- CI has ordinary PR/master events, verified pinned checkout/setup-uv, contents:read, no persisted credentials/cache, timeout/concurrency. No release workflow edits.

## Verification

Historical pre-rebase validation: source/manifest/test/docs authority read; actionlint1.7.12 (optional shellcheck/pyflakes disabled) and zizmor1.31.1 --offline --pedantic both passed, exit0, no findings. Fresh rebased-head hosted suite/build results remain pending. No local full CI, GUI windows, model calls, release or service calls.

## Next step

Return the complete actual-master-to-rebased-head diff and exact head to coordinator before publication. Keep remote feature unchanged; no push/merge/model or full local CI. Only concrete reviewed publication authority and subsequent final-head hosted/Claude gates may advance the PR.

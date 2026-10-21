# GUI Builder PR #5: wxPython floor 4.2.4

## Goal

Preserve this dependency PR and supported Python while wiring the actual tracked tests, package build and real Sphinx autodoc build. No product/accessibility behavior, release workflow, dependency refresh, settings or external model calls.

## State

- Fresh same-org origin is git@github.com:accessibleapps/gui_builder.git. Published PR #5 remains at 4626f870ac374a2dcdcaa81280f5d0737506fd64; preserved as backup/task6-gui-builder-5-published-before-repair. There was no local branch matching this Dependabot PR. Canonical master and all dirty/untracked experiments remain untouched.
- Local successor is based on current master 32eb2671a40eb3dc324e5628ef1544318adb6853, with only the original dependency commit replayed before this amendment. This carries current safe seven-test callback suite instead of inventing tests for an obsolete source tree. It is local and unpublished.
- Actions is enabled; existing default/release successes do not test this head. Hosted results and actual final-head Claude review are pending. No full local CI was run.

## Decisions and why

- Manifest/README Python floor is 3.8.6; RTD docs explicitly use 3.11. wxPython 4.2.4 primary PyPI metadata requires >=3.9 and supplies Windows wheels through CPython 3.14. The 3.8 wheel exists at 4.2.2. Python 3.14 is the latest demonstrated wheel leg, not a support-policy ceiling.
- Windows 3.8/3.14 installs the actual package graph with binary-only wxPython, imports wx and fields/forms without creating wx.App, runs the full unchanged tracked pytest suite (seven tests), and builds/verifies wheel/sdist. Compatible pytest pins are 8.3.5/9.1.1. Existing test stubs are not claimed as actual GUI/accessibility exercise.
- The docs job uses the actual RTD-selected Python 3.11 and real wxPython imports, not blanket autodoc mocks. Exact Sphinx 8.1.3/theme 3.1.0/typehints 3.0.0 meet the branch requirements (both typehints 3.0.0 and 3.0.1 require Sphinx >=8.1.3). Build runs from docs as its Makefile does; warnings are fatal and no links/services/examples are executed.
- Existing docs conf names absent _templates/_static directories. The strict hosted build may expose baseline documentation warnings; do not suppress or claim green. Classify actual failures against fresh default before a prerequisite fix.
- CI has ordinary PR/master events, verified pinned checkout/setup-uv, contents:read, no persisted credentials/cache, timeout/concurrency. No release workflow edits.

## Verification

The PR's unconditional wxPython >=4.2.4 cannot install at the declared Python 3.8 floor because that release requires >=3.9. This feature-only compatibility defect is fixed with two Python markers: retain original >=4.1.0 below 3.9, and apply >=4.2.4 from 3.9 onward. No source or support declaration changes.

Source/manifest/test/docs authority read. actionlint1.7.12 (optional shellcheck/pyflakes disabled) and zizmor1.31.1 --offline --pedantic both passed, exit0, no findings. Full hosted suite/build results are pending. No local full CI, GUI windows, model calls, release or service calls.

## Next step

Return exact local head and complete diff to coordinator before any publication. All published tips remain unchanged; review and actual hosted green are required before any merge.

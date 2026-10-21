# GUI Builder baseline: remove nonexistent custom static directory

## Goal

Fix the confirmed baseline documentation configuration failure before updating dependency PRs #5/#9/#10. Retain strict real docs, full seven runtime tests and supported Python coverage.

## State

- Fresh authenticated origin git@github.com:accessibleapps/gui_builder.git, master32eb2671a40eb3dc324e5628ef1544318adb6853. Isolated worktree gui-builder-docs-baseline / repair/task6-gui-builder-docs-baseline directly from that master.
- Canonical dirty work and all three published feature tips/archives remain unchanged. No feature dependency bump, source behavior change, warning suppression, model, hook, settings, merge or release call.
- Local prerequisite only; first new draft publication and final-head hosted/Claude gates pending coordinator approval. No full local CI ran.

## Evidence and decisions

- Actual pull_request attempt1 runs39530842757 (#5),39530857396 (#9),39530868038 (#10) all failed docs3.11 on exactly one warning: html_static_path entry '_static' does not exist. Actual HTML/autodoc processing completed but -W correctly made each job fail.
- Current master docs/conf.py line38 has the identical declaration; complete tracked docs tree has no _static directory/assets, and tracked grep finds no custom CSS/JS/static callers elsewhere in docs or RTD config. All three feature configs equal master. This is a confirmed baseline config defect, not three dependency failures.
- Remove only html_static_path=['_static']; Sphinx defaults to no custom static directories. Its theme assets are separate and remain. Do not add dummy assets or suppress warning categories.
- Add the same already-reviewed 77-line safe CI from #9, byte-for-byte: Windows3.8/3.14 real package+wx imports, seven unchanged callback tests, wheel/sdist; Windows3.11 real strict Sphinx HTML build with existing dependency floors. Both typehints3.0.0/3.0.1 already require Sphinx>=8.1.3, so pinning8.1.3 does not apply the feature's direct requirement bump.
- No dependency/support metadata or docs requirement changes. README commits the actual test/build authority; no generic framework or new test policy.

## Verification

- Original failing hosted evidence is above; all six feature runtime jobs succeeded, but that is not claimed as this new baseline head's hosted result.
- Static diff confirms only the unused config declaration is removed. Workflow Git blob10ee2ae4f0296bbec9b4cadb7a34500d136bd824 exactly equals the previously reviewed/audited #9 workflow (actionlint1.7.12 and zizmor1.31.1 --offline --pedantic both exit0, no findings). Source, seven tests, manifest, docs requirements and release workflow diffs are empty. No full local tests/docs/build rerun.

## Next step

Return full master-to-head diff and proposed prerequisite PR to coordinator before publication. Affected features remain at their published failing heads until this prerequisite is reviewed, hosted-green and explicitly allowed to land.

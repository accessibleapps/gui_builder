# Restore the stashed widget package

## Goal
Finish the interrupted stash application, fix the widget package, and merge the restored work.

## State
The checkout began with fields.py staged, wx_widgets.py unmerged, and an untracked
wx_widgets package. The newest stash contains the fields changes and empties the
old module; the package files were never included in that stash. No open PR existed.
The older stash is a separate autosizing experiment and is outside this task.
The conflict is resolved and focused native integration tests pass on a private
Windows desktop with wxPython 4.3.2. All original widget definitions are present;
concrete definitions are unchanged from master.

## Decisions and why
- Complete the already-applied newest stash rather than applying it a second time.
- Keep the shared widget contracts in base.py and concrete controls in widgets.py.
  Export the existing widget API from the package initializer.
- Preserve the merged label visibility, menu refresh, and responsive layout behavior.
  The untracked split predates those changes.
- Preserve unrelated untracked files and the older stash.

## Surprises
The package initializer was empty. The concrete module omitted runtime imports,
including generic type variables, sized_controls, callback helpers, and constants.
The native test also reproduced a TextCtrl assertion from SetLabel in
set_accessible_label. Use SetAccessibleName where available and SetName on older
wxPython; never replace editable text to assign its accessible name. Native
screen-reader output and the older wxPython provider behavior were not tested.

## Next step
Delivery is tracked in https://github.com/AccessibleApps/gui_builder/pull/21;
consult that PR for current CI and merge state. Tests and packaging passed on
Python 3.8 and 3.14 for the implementation. Documentation is checked in the same
workflow. Local verification ran only test_widget_package.py on a private desktop.
Remove only the newest stash after merge; preserve the older autosizing stash
and all unrelated untracked work.

# fix/hidden-label-13

## Goal
Fix accessibleapps/gui_builder#13: hiding a field leaves its label visible (and read by screen readers).

## State
Fixed in `gui_builder/widgets/wx_widgets.py` `WXWidget.hide()`/`show()`: they now also hide/show
`self.label_control` and call `Layout()` on the control's parent. Branch pushed; no PR opened
(coordinator opens it).

## Decisions and why
- `hidden=True` goes through `WXWidget.render()` -> `self.hide()`, and `GUIField.hide()/show()`
  (fields.py) delegate to the widget, so fixing the widget's hide/show covers every path.
- Layout: no code in the repo called Layout after hide/show. Measured on Windows (wx 4.3.2):
  without it, after `show()` the label and control both sat at (0,0) and the next field's label
  did not move. With `parent.Layout()` the label is at (3,3), the control at (3,25), and the next label at (3,69).

## Surprises
- No xvfb on this machine (Windows), so verification ran against real wx msw, not Linux.

## Next step
Coordinator: review, open PR closing #13.

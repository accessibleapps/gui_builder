# fix/hidden-label-13

## Goal
Fix accessibleapps/gui_builder#13: hiding a field leaves its label visible (and read by screen readers).

## State
Fixed in `gui_builder/widgets/wx_widgets.py` `WXWidget.hide()`/`show()`: they now also hide/show
`self.label_control` and call `Layout()` on every ancestor up to the top-level window. Branch pushed; no PR opened
(coordinator opens it).

## Decisions and why
- `hidden=True` goes through `WXWidget.render()` -> `self.hide()`, and `GUIField.hide()/show()`
  (fields.py) delegate to the widget, so fixing the widget's hide/show covers every path.
- Layout: no code in the repo called Layout after hide/show. Measured on Windows (wx 4.3.2):
  without it, after `show()` the label and control both sat at (0,0) and the next field's label
  did not move. With `parent.Layout()` the label is at (3,3), the control at (3,25), and the next label at (3,69).
- Nested panels (follow-up, Linux wx 4.2.1 gtk3 under Xvfb): parent-only `Layout()` is not enough.
  SizedFrame > SizedPanel > SizedPanel[Notes hidden, Kind] + After: on `show()` the inner panel stayed
  63px tall and Kind's label landed at y=66, height 0 (clipped). Laying out each ancestor fixes it
  (inner panel 131px, Kind at y=71, After below). Top-level `Layout()` alone is wrong: under a plain
  `wx.Frame` (no sizer) it only resizes the sole child to an unchanged size, so the panel never
  re-lays out and Kind stays at y=0 under Notes.

## Surprises
- No xvfb on this machine (Windows), so verification ran against real wx msw, not Linux.

## Next step
Coordinator: review, open PR closing #13.

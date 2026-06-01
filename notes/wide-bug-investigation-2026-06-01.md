# Wide bug investigation - 2026-06-01

Requested outcome: take notes on each reproduced bug, dig deeper into each, and figure out how to fix each one.

Verification interpreter:

- `uv run --python 3.12 python -c "import sys, wx; ..."` resolved to `C:\Users\Q\code\gui_builder\.venv\Scripts\python.exe`.
- Python: 3.12.5.
- wxPython: 4.2.3 msw, wxWidgets 3.2.7.

## 1. Pytest collects interactive examples and hangs

Evidence:

- `examples/test_link.py`, `examples/test_nested.py`, and `examples/test_radio_buttons.py` are named like pytest tests.
- Each creates `wx.App()` and enters `app.MainLoop()` at module import time.
- Full pytest under the wxPython interpreter blocked until the exact pytest process tree was stopped.

Current hypothesis:

- These files are demos, not pytest tests. Their names make pytest collect them.
- The import-time GUI startup is also hostile to reuse as examples because importing the module launches a GUI.

Fix direction:

- Rename example files so they do not match pytest discovery, or configure pytest to ignore `examples/`.
- Move GUI execution behind `if __name__ == "__main__":`.
- Keep examples runnable directly with `uv run --python 3.12 python examples/<name>.py`.

Open checks:

- Resolved: there is no `pytest.ini`, `setup.cfg`, or `tox.ini`; `pyproject.toml` has no pytest config.
- Best fix: rename the example files so they are no longer pytest candidates and move executable code behind `if __name__ == "__main__":`.
- Required doc updates: `README.md` names `examples/test_nested.py`; update it if examples are renamed.
- Verification gate: `uv run --python 3.12 --with pytest --group dev python -m pytest -q --ignore=test_dialog_lifetime.py` should no longer need `--ignore=examples`.

## 2. `forms.Frame.maximize()` / `restore()` / `minimize()` are broken

Evidence:

- `forms.BaseFrame.maximize()` delegates to `self.widget.maximize()`.
- `widgets.BaseFrame` implements `maximize`, `restore`, and `minimize`.
- `widgets.Frame` inherits `BaseContainer`, not `widgets.BaseFrame`.
- Runtime probe raised `AttributeError: 'Frame' object has no attribute 'maximize'`.

Current hypothesis:

- The widget-side `Frame` class should inherit `BaseFrame[FieldType, wx.Frame]`, not `BaseContainer[FieldType, wx.Frame]`.

Fix direction:

- Change `class Frame(BaseContainer[FieldType, wx.Frame])` to `class Frame(BaseFrame[FieldType, wx.Frame])`.
- Verify `forms.Frame.maximize()`, `restore()`, and `minimize()` against a rendered frame.
- Check `SizedFrame` already uses `BaseFrame`; MDI frame classes already use `BaseFrame`.

Open checks:

- Resolved: `widgets.BaseFrame.__init__` only records `maximized`, then delegates to `BaseContainer`; `widgets.BaseFrame.render` delegates then applies maximize. That is the behavior `forms.BaseFrame` already exposes.
- Best fix: make `widgets.Frame` inherit `widgets.BaseFrame[FieldType, wx.Frame]`.
- Verification gate: render `forms.Frame`, call `maximize`, `restore`, and `minimize`; each should complete without `AttributeError`.

## 3. `SectionHeader.wrap()` is broken

Evidence:

- Public field API calls `self.widget.wrap(width)`.
- Widget API calls `self.control.Wrap(width)`.
- `_SectionHeaderPanel` contains an inner `wx.StaticText` as `self._text`, but the panel itself has no `Wrap`.
- Runtime probe raised `AttributeError: '_SectionHeaderPanel' object has no attribute 'Wrap'`.

Current hypothesis:

- The wrapper panel needs to forward wrapping to its inner static text and relayout.

Fix direction:

- Add `_SectionHeaderPanel.Wrap(width)` that calls `self._text.Wrap(width)` and `self.Layout()`.
- Or change `SectionHeader.wrap` to call `self.control._text.Wrap(width)`, but a panel method is cleaner because it keeps the wrapper control API coherent.

Open checks:

- Resolved: `wx.StaticText` has `Wrap` in wxPython 4.2.3.
- Best fix: add `_SectionHeaderPanel.Wrap(width)` and delegate to `self._text.Wrap(width)`, then call `self.Layout()`.
- Verification gate: render `fields.SectionHeader`, call `wrap(120)`, assert no `AttributeError`.

## 4. `SectionHeader.is_ellipsized()` is broken

Evidence:

- Public field API calls `self.widget.is_ellipsized()`.
- Widget API calls `self.control.IsEllipsized()`.
- `_SectionHeaderPanel` has no `IsEllipsized`.
- Runtime probe raised `AttributeError: '_SectionHeaderPanel' object has no attribute 'IsEllipsized'`.

Current hypothesis:

- `IsEllipsized` belongs on the inner `wx.StaticText`, not the wrapper panel.

Fix direction:

- Add `_SectionHeaderPanel.IsEllipsized()` that delegates to `self._text.IsEllipsized()`.
- If the current wxPython static text lacks `IsEllipsized`, return `False` only after verifying that API absence on the supported wx versions.

Open checks:

- Resolved: `wx.StaticText` has `IsEllipsized` in wxPython 4.2.3.
- Best fix: add `_SectionHeaderPanel.IsEllipsized()` and delegate to `self._text.IsEllipsized()`.
- Verification gate: render `fields.SectionHeader`, call `is_ellipsized()`, assert a bool is returned.

## 5. `Text.get_x_y_from_insertion_point()` returns the wrong shape

Evidence:

- Field annotation promises `tuple[int, int]`.
- Widget implementation returns `self.control.PositionToXY(insertion_point)` directly.
- Runtime probe returned `(True, 0, 0)`, length 3.

Current hypothesis:

- wxPython `PositionToXY` returns `(success, x, y)`.
- The wrapper should translate this to `(x, y)` and define behavior for failed conversion.

Fix direction:

- Call `ok, x, y = self.control.PositionToXY(insertion_point)`.
- Return `(x, y)` when `ok` is true.
- Raise `ValueError` or return `(-1, -1)` when `ok` is false; prefer raising because the public API promises coordinates.

Open checks:

- Resolved: `PositionToXY(0)` returned `(True, 0, 0)`; `PositionToXY(9999)` returned `(False, 650, <garbage-looking int>)`.
- Best fix: unpack `ok, x, y`; return `(x, y)` only when `ok` is true; raise `ValueError` when false.
- Verification gate: valid insertion point returns a two-item tuple; invalid insertion point raises `ValueError`.

## 6. `RadioBox.set_items()` is a no-op

Evidence:

- Widget method converts and returns new items but does not mutate the control.
- Runtime probe: before `['Launch', 'Land']`; `set_items(['Dock', 'Abort'])` returned `['Dock', 'Abort']`; after still `['Launch', 'Land']`.

Current hypothesis:

- wx.RadioBox cannot be repopulated with `SetItems` like `wx.Choice`/`wx.ListBox`.
- A faithful implementation may need to recreate the control or explicitly reject runtime item changes.

Fix direction:

- First verify wx.RadioBox mutation API on wxPython 4.2.3.
- If no supported mutation API exists, change `RadioBox.set_items` to raise `NotImplementedError` instead of silently lying.
- If recreating is acceptable, implement a control replacement that preserves parent, label, style, selection where possible, and registered callbacks.

Open checks:

- Resolved: wxPython 4.2.3 `wx.RadioBox` has no `SetItems`, `Append`, or `Delete`, but does have `GetCount`, `GetString`, `GetStrings`, `SetString`, and `SetStringSelection`.
- Best fix: implement same-count relabeling with `SetString(index, item)` and raise `NotImplementedError` when the new list length differs from current count.
- Reason not to recreate the control by default: replacement would need to preserve parent sizer position, selection, callback bindings, enabled/hidden state, labels, and accessibility; that is a larger widget-lifecycle change.
- Verification gate: same-length `set_items` changes labels; different-length `set_items` raises instead of silently returning a lie.

## 7. `ListView.add_column(..., right=True)` ignores alignment

Evidence:

- `add_column` accepts `**format`.
- It calls `wx_attributes(format)` instead of `wx_attributes(**format)`.
- Runtime probe with `right=True` captured format `0`; `wx.ALIGN_RIGHT` was `512`.

Current hypothesis:

- This is a typo introduced by treating the kwargs dict as the first positional `prefix` argument.

Fix direction:

- Replace `format = wx_attributes(format)` with `format_kwargs = wx_attributes(**format)`.
- Extract `format_value = format_kwargs.get("style", wx.ALIGN_LEFT)` or adjust `wx_attributes` result key to match expected alignment constants.
- Add a direct unit probe for `right=True`, `center=True`, and default alignment.

Open checks:

- Resolved: wxPython exposes `wx.LIST_FORMAT_LEFT == 0`, `wx.LIST_FORMAT_RIGHT == 1`, `wx.LIST_FORMAT_CENTRE == 2`; `wx.ALIGN_RIGHT == 512`, so the current code is using the wrong constant family.
- Best fix: replace the generic `wx_attributes(format)` call with an explicit column-format resolver:
  - `format=<int>` uses that int.
  - `right=True` uses `wx.LIST_FORMAT_RIGHT`.
  - `center=True` or `centre=True` uses `wx.LIST_FORMAT_CENTRE`.
  - default uses `wx.LIST_FORMAT_LEFT`.
- Verification gate: probe `add_column(right=True)`, `add_column(center=True)`, and default; captured format values should be 1, 2, and 0.

## 8. `ChoiceWidget` indexing is misspelled

Evidence:

- Method is named `__getitem___`, with three trailing underscores.
- Runtime probe: `ListBox(...)[0]` raised `TypeError: 'ListBox' object is not subscriptable`.

Current hypothesis:

- Plain typo; intended method is `__getitem__`.

Fix direction:

- Rename to `__getitem__`.
- Add a focused test using a fake control or real ListBox to prove `widget[0]` delegates to `get_item`.

Open checks:

- Resolved: no intended production calls to `__getitem___` were found.
- Best fix: rename `__getitem___` to `__getitem__`.
- Verification gate: `widget[0]` returns the same value as `widget.get_item(0)`.

## 9. `Form.delete_child()` mutates the class field registry

Evidence:

- `Form.delete_child` removes entries from `self._unbound_fields`.
- `_unbound_fields` is cached on the form class by `FormMeta`.
- Runtime probe: deleting `first` from one instance changed class fields from `['first', 'second']` to `['second']`; a new instance then lacked `first`.

Current hypothesis:

- Instance deletion should remove from instance-owned `_fields`, attributes, and `_extra_fields`, but not from class-owned `_unbound_fields`.

Fix direction:

- Stop mutating `_unbound_fields` in instance `delete_child`.
- `__iter__` already filters names through `if name in self._fields`, so leaving class `_unbound_fields` intact should be safe.
- For class-level deletion of field definitions, rely on `FormMeta.__delattr__` invalidating the cache.

Open checks:

- Resolved by code inspection: `FormMeta.__delattr__` invalidates class `_unbound_fields` for class-level deletion; instance `delete_child` does not need to mutate the class cache.
- Best fix: remove the `_unbound_fields.remove(...)` block from `Form.delete_child`.
- Verification gate: deleting a declared child from one instance does not change fields on a new instance of the same class.

## 10. `ListView` coerces row tuples into strings

Evidence:

- `ChoiceField.__init__` stores `self.choices = [str(i) for i in choices]`.
- `forms.ListView` inherits `ChoiceField` and passes row tuples through that coercion.
- Runtime probe: `choices=[('name', 'value')]` became `["('name', 'value')"]`.
- Rendering then passed a string row into wx.ListCtrl and hit a wx column assertion.

Current hypothesis:

- Generic `ChoiceField` string coercion is wrong for `ListView`, whose rows are sequences.

Fix direction:

- Override `forms.ListView.__init__` to preserve row sequences after the `ChoiceField` initializer, or split choice normalization so only scalar choice widgets stringify values.
- Better target: change `ChoiceField` to let widgets convert input items, but that has wider behavior risk.
- Narrow fix: in `ListView.__init__`, keep an `original_choices` copy and assign `self.choices = original_choices` after `super().__init__`.

Open checks:

- Resolved by code inspection: `DataView.add_item` calls `AppendItem(item)` and expects a row-like item; it should not receive the stringified tuple either.
- Best narrow fix: in `forms.ListView.__init__`, preserve original row choices around `ChoiceField.__init__`, then restore `self.choices` to the row sequence after `super().__init__`.
- Better later cleanup: split scalar-choice normalization from row-choice normalization instead of making every `ChoiceField` stringify in `__init__`.
- Verification gate: `forms.ListView(parent=None, choices=[("name", "value")]).choices[0]` remains a tuple, and rendered ListView receives tuple rows.

## 11. `ListViewColumn.set_item()` treats a column index as a control

Evidence:

- `ListViewColumn.create_control()` stores `self.parent.add_column(...)`.
- `ListView.add_column()` returns the result of `InsertColumn`, an integer column index.
- `ListViewColumn.set_item()` calls `self.control.SetStringItem(...)`.
- Runtime probe printed `int 0`, then raised `AttributeError: 'int' object has no attribute 'SetStringItem'`.

Current hypothesis:

- `ListViewColumn` is a column descriptor, not a widget/control. It should store a column index and update through the parent ListView.

Fix direction:

- Rename internal storage to `column_index` or keep `control` only if larger refactor is avoided.
- Implement `set_item(index, item)` as `self.parent.set_item_column(index, self.column_index, str(item))`.
- Revisit the method signature: a column should probably set one subitem string, not enumerate a sequence as if it were a whole row.

Open checks:

- Resolved: no current docs/examples use `ListViewColumn`; only source defines it.
- Best fix: treat `ListViewColumn` as a column descriptor, not a window widget:
  - Store the returned column index as `self.column_index`.
  - Do not treat that integer as a wx control.
  - Implement `set_item(row_index, item)` by calling `self.parent.set_item_column(row_index, self.column_index, str(item))`.
  - Override `destroy` as a no-op or delete the column through the parent; do not call `Destroy()` on an int.
- Verification gate: rendering a `ListViewColumn` stores an integer column index; `set_item(0, "x")` calls the parent list view's `set_item_column`.

## 12. `Button.make_default()` contradicts its own contract

Evidence:

- Docstring says the method is called before rendering.
- Implementation immediately calls `self.widget.make_default()`.
- Runtime probe before render raised `AttributeError: 'Button' object has no attribute 'widget'`.

Current hypothesis:

- Widget `Button` already supports a constructor flag `default`; field API should set that flag before render.

Fix direction:

- Change field-level `make_default()` to set `self.widget_kwargs["default"] = True` before render.
- If already rendered, call `self.widget.make_default()` too.
- Or expose constructor parameter only and correct the docstring, but current method contract is explicit and should work.

Open checks:

- Resolved by code inspection: field `widget_kwargs` are passed to `self.widget_type(...)`; `widgets.Button.__init__(default=False, ...)` consumes `default` and applies it in `render`.
- Best fix: update field-level `Button.make_default()` to:
  - set `self.widget_kwargs["default"] = True`;
  - call `self.widget.make_default()` immediately when already rendered.
- Verification gate: calling `make_default()` before render does not raise, and after render the underlying button is default.

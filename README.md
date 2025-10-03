# GUI Builder

A declarative GUI framework for Python built on wxPython that makes creating desktop applications simple and maintainable.

## Features

- **Declarative Syntax**: Define your GUI layout using Python class attributes
- **Automatic Layout**: Framework handles widget positioning and sizing automatically
- **Flexible Event Binding**: Bind callbacks using decorators or direct assignment
- **Nested Forms**: Compose complex UIs from reusable form components
- **Cross-Platform**: Works on Windows, macOS, and Linux via wxPython

## Installation

```bash
pip install gui_builder
```

Requires Python 3.8.6 or higher.

## Quick Example

```python
import wx
from gui_builder import fields, forms

class SimpleForm(forms.Frame):
    # Define UI elements as class attributes
    name = fields.Text(label="Your Name")
    greeting = fields.Button(label="Say Hello")
    output = fields.Text(multiline=True, readonly=True)

    # Bind event handler with decorator
    @greeting.add_callback
    def on_greeting(self):
        self.output.set_value(f"Hello, {self.name.get_value()}!")

if __name__ == "__main__":
    app = wx.App()
    frame = SimpleForm(title="GUI Builder Demo", top_level_window=True)
    frame.display()
    app.MainLoop()
```

## Core Concepts

### Fields

Fields are declared as class attributes and represent UI controls:

```python
class MyForm(forms.Frame):
    text_input = fields.Text(label="Name")
    number = fields.IntText(label="Age", default_value=0)
    accept = fields.CheckBox(label="I agree")
    submit = fields.Button(label="Submit")
```

Available field types include: `Text`, `IntText`, `CheckBox`, `Button`, `ComboBox`, `ListBox`, `RadioButtonGroup`, `DatePicker`, `FilePicker`, `Slider`, `SpinBox`, `ProgressBar`, `TreeView`, `Link`, `StaticText`, `Image`, and more.

### Event Binding

Bind callbacks using the `@field.add_callback` decorator:

```python
class MyForm(forms.Frame):
    button = fields.Button(label="Click Me")

    @button.add_callback
    def on_click(self):
        print("Button clicked!")
```

Or use the `callback` parameter directly:

```python
class MyForm(forms.Frame):
    def handle_click(self):
        print("Button clicked!")

    button = fields.Button(label="Click Me", callback=handle_click)
```

### Nested Forms

Create reusable form components by nesting forms:

```python
class OptionsPanel(forms.Panel):
    option_a = fields.CheckBox(label="Enable Feature A")
    option_b = fields.CheckBox(label="Enable Feature B")

class MainFrame(forms.Frame):
    name = fields.Text(label="Name")
    options = OptionsPanel()
    submit = fields.Button(label="Submit")
```

### Container Types

- **Frame**: Top-level window
- **Dialog**: Modal or non-modal dialog window
- **Panel**: Container for grouping controls
- **SizedPanel**: Panel with automatic sizing
- **SizedFrame**: Frame with automatic sizing
- **SizedDialog**: Dialog with automatic sizing
- **Notebook**: Tabbed container

## Setting and Getting Values

```python
# Set a field value
self.name.set_value("John")

# Get a field value
name = self.name.get_value()

# Set multiple values using a dictionary
self.set_values({"name": "John", "age": 30})
```

## Examples

The `examples/` directory contains working demonstrations:

- **test_link.py**: Basic link field usage
- **test_nested.py**: Nested forms and panels
- **test_radio_buttons.py**: Radio button groups
- **text_conversion.py**: Text encoding/decoding with multiple controls

Run any example with:
```bash
python examples/test_nested.py
```

## Context Managers

Use `FreezeAndThaw` to optimize UI updates and prevent flickering:

```python
from gui_builder.context_managers import FreezeAndThaw

with FreezeAndThaw(self.text_field):
    # Multiple updates happen without visual flickering
    self.text_field.set_value(large_text)
    self.text_field.set_insertion_point(0)
```

## Development

Install development dependencies:
```bash
uv sync
```

The project uses:
- `hatchling` for build backend
- `uv` for dependency management
- `pyproject.toml` for configuration

## License

MIT License - see LICENSE.txt for details.

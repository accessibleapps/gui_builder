# GUI Builder

A declarative GUI framework for Python built on wxPython that makes creating complex interfaces simple and maintainable.

## Features

- **Declarative Syntax**: Define your GUI layout using Python classes with a clean, readable syntax
- **Automatic Layout**: Let the framework handle the positioning and sizing of your UI elements
- **Event Handling**: Easily bind callbacks to UI events with decorators or direct assignment
- **Form Management**: Automatic form validation and data binding
- **Cross-Platform**: Works on Windows, macOS, and Linux through wxPython

## Installation

```bash
pip install gui_builder
```

## Quick Example

```python
import wx
from gui_builder import fields, forms

class SimpleForm(forms.Frame):
    # Define UI elements as class attributes
    name = fields.Text(label="Your Name", min_size=(200, -1))
    greeting = fields.Button(label="Say Hello")
    output = fields.Text(multiline=True, read_only=True, min_size=(300, 100))
    
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

## More Examples

Check out the `examples` directory for more sample applications:

- Basic forms and dialogs
- Complex layouts
- Custom controls
- Data binding examples

## Context Managers

GUI Builder provides helpful context managers like `FreezeAndThaw` to optimize UI updates:

```python
from gui_builder.context_managers import FreezeAndThaw

with FreezeAndThaw(my_text_control):
    # Make multiple updates without flickering
    my_text_control.set_value(large_text)
    my_text_control.set_insertion_point(0)
```

## License

This project is licensed under the MIT License - see the LICENSE.txt file for details.

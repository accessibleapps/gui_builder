GUI_Builder
=======================

The GUI_builder library is a powerful tool for creating graphical user interfaces (GUIs) in Python with a declarative and clean syntax. It is built on top of wxPython, a cross-platform GUI toolkit for the Python language. GUI_builder simplifies the process of designing and implementing complex user interfaces by allowing developers to define the structure and behavior of a GUI in a high-level, readable format.

Features
--------
- Declarative syntax: Define your GUI layout and behavior in a structured and readable way.
- Reusable components: Create custom reusable GUI components for consistent and maintainable code.
- Event handling: Easily bind events to widget actions with clear callback definitions.
- Data binding: Synchronize your GUI with your application's data model seamlessly.

Installation
------------
To install the library, you can use pip:

```bash
pip install gui_builder
```

Getting Started
---------------
Here's a simple example of how to create a basic window with a button:

```python
import wx
from gui_builder import fields, forms

class MyFrame(forms.Frame):
    output = fields.Text(multiline=True, readonly=True, min_size=(300, 100))
    button = fields.Button(label="Click Me!")

    @button
    def click_me(self, event):
        self.output.append("Button clicked!\n")

app = wx.App()
frame = MyFrame()
frame.display()
app.MainLoop()
```

In the example above, we define a frame with a single button. When the button is clicked, it prints a message to the console. This is just a glimpse of what you can do with GUI_builder. The library supports a wide range of widgets and allows for complex layouts and interactions.

Documentation
-------------
For more detailed documentation, including a full list of available widgets and their properties, please refer to the `docs` directory in this repository.

License
-------
This library is released under the MIT License. See the `LICENSE.txt` file for more details.

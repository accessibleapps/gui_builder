GUI Builder Documentation
==========================

A declarative GUI framework for Python built on wxPython that makes creating complex interfaces simple and maintainable.

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   quickstart
   api
   examples

Features
--------

- **Declarative Syntax**: Define your GUI layout using Python classes with a clean, readable syntax
- **Automatic Layout**: Let the framework handle the positioning and sizing of your UI elements
- **Event Handling**: Easily bind callbacks to UI events with decorators or direct assignment
- **Form Management**: Automatic form validation and data binding
- **Cross-Platform**: Works on Windows, macOS, and Linux through wxPython

Installation
------------

.. code-block:: bash

   pip install gui_builder

Quick Example
-------------

.. code-block:: python

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

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
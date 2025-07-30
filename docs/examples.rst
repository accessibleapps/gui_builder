Examples
========

Text Conversion Tool
--------------------

This example demonstrates a practical text conversion utility using radio buttons and event handling:

.. literalinclude:: ../examples/text_conversion.py
   :language: python
   :linenos:

This example shows:

- **RadioButtonGroup**: For selecting conversion type
- **Multiline Text fields**: For input and output
- **Event handling**: Converting text based on selection
- **Dynamic UI updates**: Showing/hiding result field
- **Error handling**: Catching and displaying conversion errors

Key Features Demonstrated
~~~~~~~~~~~~~~~~~~~~~~~~~

1. **Declarative field definitions**: UI elements are defined as class attributes
2. **Event binding**: The ``on_convert`` method is bound to the Convert button
3. **Dynamic visibility**: The result field is hidden initially and shown after conversion
4. **Data validation**: Try/catch blocks handle conversion errors gracefully

More Examples
-------------

Check the ``examples/`` directory in the source code for additional examples:

- Basic forms and dialogs
- Complex layouts with nested panels  
- Custom field validation
- Data binding patterns
- Menu and toolbar integration
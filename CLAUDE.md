# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

GUI Builder is a declarative GUI framework for Python built on wxPython. It provides a clean, class-based approach to creating desktop applications with automatic layout management and event handling.

## Build System and Dependencies

This project uses modern Python packaging with:
- `pyproject.toml` for configuration using hatchling as the build backend
- `uv` for dependency management and virtual environments
- Core dependencies: wxPython (>=4.1.0) and six
- Supports Python 3.7-3.12

## Core Architecture

The framework is organized into three main layers:

### 1. Fields (`gui_builder/fields.py`)
- **UnboundField**: Template class that creates actual field instances when bound to forms
- Uses creation counter for field ordering in forms
- Supports callback binding via decorators (`@field.add_callback`)
- All GUI elements inherit from this pattern

### 2. Forms (`gui_builder/forms.py`) 
- **BaseForm**: Base class that manages collections of fields
- **Frame/Dialog**: Top-level window classes extending BaseForm
- Handles field binding, layout management, and value setting
- Supports nested forms and complex hierarchies

### 3. Widgets (`gui_builder/widgets/`)
- **widget.py**: Abstract base widget interface
- **wx_widgets.py**: wxPython-specific implementations
- Wraps wxPython controls with consistent API

## Key Design Patterns

**Declarative Syntax**: Define UI as class attributes:
```python
class MyForm(forms.Frame):
    name = fields.Text(label="Name")
    submit = fields.Button(label="Submit")
```

**Event Binding**: Use decorators for clean callback assignment:
```python
@submit.add_callback
def on_submit(self):
    # Handle button click
```

**Automatic Layout**: Framework handles positioning and sizing without manual layout code.

## Development Commands

### Installing for Development
```bash
uv sync
```

### Running Examples
```bash
python examples/test_link.py
python examples/test_nested.py
python examples/test_radio_buttons.py
python examples/text_conversion.py
```

### Building Package
```bash
uv build
```

## Testing

The project uses example scripts in `examples/` for testing rather than formal unit tests. Each example demonstrates specific functionality and serves as both documentation and validation.

## Context Managers

The framework provides `context_managers.py` with utilities like `FreezeAndThaw` for optimizing UI updates during bulk operations.

## Important Notes for Development

- Field creation order matters (uses creation_counter)
- Always test with actual GUI applications, not just imports
- The framework handles both Python 2/3 compatibility (uses six)
- Some examples require `logger_setup` (available on PyPI) for demonstration purposes
- wxPython dependency means platform-specific considerations for display
- No formal linting or testing configuration - examples serve as both documentation and validation

## wxPython Wrapper Development Guidelines

When adding methods that wrap wxPython functionality:

1. **Always check the wxPython API first**: Use `uv run python -c "import wx; help(wx.ControlName.method_name)"` to verify method signatures and parameters
2. **Check official documentation**: Reference https://docs.wxpython.org/ for complete parameter details and usage examples
3. **Include complete docstrings**: All field methods must have docstrings that document all parameters using Args format
4. **Match underlying API**: Wrapper methods should accept the same parameters as the underlying wx methods (with sensible defaults)
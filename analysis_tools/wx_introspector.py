#!/usr/bin/env python3
"""
wx Control Discovery and Analysis Tool

This script systematically discovers all wx controls and analyzes their
properties, methods, and characteristics to create a comprehensive inventory.
"""

import wx
import inspect
import json
import datetime
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional


def discover_wx_classes() -> List[type]:
    """
    Discover all wx classes that could be UI controls.
    
    Returns:
        List of wx classes that inherit from relevant base classes
    """
    print("🔍 Discovering wx classes...")
    
    # Base classes that indicate UI controls
    base_classes = (
        wx.Window,
        wx.Control, 
        wx.Dialog,
        wx.Frame,
        wx.Panel,
        wx.Sizer,
    )
    
    wx_classes = []
    
    # Get all attributes from wx module
    for attr_name in dir(wx):
        try:
            attr = getattr(wx, attr_name)
            
            # Check if it's a class
            if inspect.isclass(attr):
                # Check if it inherits from our base classes
                if issubclass(attr, base_classes):
                    # Skip abstract base classes and internal classes
                    if not attr_name.startswith('_') and attr_name != 'Object':
                        wx_classes.append(attr)
                        
        except (TypeError, AttributeError):
            # Some attributes might not be accessible
            continue
    
    print(f"✅ Found {len(wx_classes)} wx control classes")
    return wx_classes


def analyze_control_class(cls: type) -> Dict[str, Any]:
    """
    Analyze a single wx control class to extract its characteristics.
    
    Args:
        cls: The wx class to analyze
        
    Returns:
        Dictionary containing class analysis
    """
    analysis = {
        'name': cls.__name__,
        'module': cls.__module__,
        'doc': cls.__doc__,
        'mro': [base.__name__ for base in cls.__mro__],
        'constructor': {},
        'methods': [],
        'properties': [],
        'events': [],
        'style_constants': [],
    }
    
    # Analyze constructor
    try:
        sig = inspect.signature(cls.__init__)
        analysis['constructor'] = {
            'signature': str(sig),
            'parameters': []
        }
        
        for name, param in sig.parameters.items():
            if name != 'self':
                param_info = {
                    'name': name,
                    'annotation': str(param.annotation) if param.annotation != param.empty else None,
                    'default': str(param.default) if param.default != param.empty else None,
                }
                analysis['constructor']['parameters'].append(param_info)
                
    except (ValueError, TypeError):
        analysis['constructor']['error'] = 'Could not analyze constructor'
    
    # Analyze public methods
    for name in dir(cls):
        if not name.startswith('_'):
            try:
                attr = getattr(cls, name)
                if callable(attr):
                    method_info = {
                        'name': name,
                        'doc': getattr(attr, '__doc__', None),
                    }
                    
                    # Try to get method signature
                    try:
                        sig = inspect.signature(attr)
                        method_info['signature'] = str(sig)
                    except (ValueError, TypeError):
                        method_info['signature'] = 'Could not determine signature'
                    
                    analysis['methods'].append(method_info)
                    
            except (AttributeError, TypeError):
                continue
    
    # Look for properties (getters/setters)
    for name in dir(cls):
        if not name.startswith('_'):
            try:
                attr = getattr(cls, name)
                if isinstance(attr, property):
                    prop_info = {
                        'name': name,
                        'readable': attr.fget is not None,
                        'writable': attr.fset is not None,
                        'doc': attr.__doc__,
                    }
                    analysis['properties'].append(prop_info)
                    
            except (AttributeError, TypeError):
                continue
    
    # Look for common wx event types
    wx_events = [attr for attr in dir(wx) if attr.startswith('EVT_')]
    for event_name in wx_events:
        try:
            event = getattr(wx, event_name)
            # This is a very basic check - more sophisticated event analysis could be added
            if hasattr(event, 'typeId'):
                analysis['events'].append({
                    'name': event_name,
                    'type_id': getattr(event, 'typeId', None)
                })
        except (AttributeError, TypeError):
            continue
    
    # Look for style constants (basic approach)
    class_name_upper = cls.__name__.upper()
    style_constants = []
    for attr_name in dir(wx):
        if attr_name.startswith(class_name_upper) or f'_{class_name_upper}_' in attr_name:
            try:
                attr = getattr(wx, attr_name)
                if isinstance(attr, int):
                    style_constants.append({
                        'name': attr_name,
                        'value': attr
                    })
            except (AttributeError, TypeError):
                continue
    
    analysis['style_constants'] = style_constants[:10]  # Limit to avoid huge lists
    
    return analysis


def save_control_inventory(data: Dict[str, Any], filename: str) -> None:
    """
    Save the control inventory to a JSON file.
    
    Args:
        data: The inventory data to save
        filename: Output filename
    """
    output_path = Path(filename)
    
    print(f"💾 Saving inventory to {output_path}")
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)
    
    print(f"✅ Inventory saved successfully ({output_path.stat().st_size} bytes)")


def main():
    """Main function to run the wx introspection."""
    print("🚀 Starting wx Control Discovery Tool")
    print(f"📊 wx version: {wx.version()}")
    print(f"🐍 Python version: {sys.version}")
    print()
    
    # Create a minimal wx app (required for some introspection)
    app = wx.App(False)
    
    try:
        # Discover all wx control classes
        wx_classes = discover_wx_classes()
        
        # Analyze each class
        print("🔬 Analyzing control classes...")
        inventory = {
            'metadata': {
                'generated_at': datetime.datetime.now().isoformat(),
                'wx_version': wx.version(),
                'python_version': sys.version,
                'total_classes': len(wx_classes),
            },
            'controls': []
        }
        
        for i, cls in enumerate(wx_classes, 1):
            print(f"  📋 Analyzing {cls.__name__} ({i}/{len(wx_classes)})")
            
            try:
                analysis = analyze_control_class(cls)
                inventory['controls'].append(analysis)
            except Exception as e:
                print(f"    ⚠️ Error analyzing {cls.__name__}: {e}")
                # Still add basic info
                inventory['controls'].append({
                    'name': cls.__name__,
                    'module': cls.__module__,
                    'error': str(e)
                })
        
        # Save the inventory
        save_control_inventory(inventory, 'wx_controls_inventory.json')
        
        # Print summary
        print()
        print("📈 Summary:")
        print(f"  • Total classes discovered: {len(wx_classes)}")
        print(f"  • Successfully analyzed: {len([c for c in inventory['controls'] if 'error' not in c])}")
        print(f"  • Analysis errors: {len([c for c in inventory['controls'] if 'error' in c])}")
        print()
        
        # Show some examples
        print("🎯 Sample discoveries:")
        for control in inventory['controls'][:5]:
            if 'error' not in control:
                method_count = len(control.get('methods', []))
                prop_count = len(control.get('properties', []))
                print(f"  • {control['name']}: {method_count} methods, {prop_count} properties")
        
        print()
        print("✨ wx control discovery completed successfully!")
        
    finally:
        app.Destroy()


if __name__ == '__main__':
    main()
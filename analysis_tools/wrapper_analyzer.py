#!/usr/bin/env python3
"""
Wrapper Analysis Tool

This script analyzes the existing wrapper patterns in gui_builder to understand:
- Current wrapper architecture
- Mapping between wx controls and wrapper classes
- Field to Widget relationships
- Wrapper patterns and conventions
"""

import ast
import inspect
import json
import datetime
import sys
import re
from pathlib import Path
from typing import Dict, List, Any, Optional, Set


def parse_wx_widgets_file(file_path: str = "gui_builder/widgets/wx_widgets.py") -> Dict[str, Any]:
    """
    Parse the wx_widgets.py file to extract wrapper class information.
    
    Args:
        file_path: Path to the wx_widgets.py file
        
    Returns:
        Dictionary containing wrapper class analysis
    """
    print(f"📋 Parsing {file_path}...")
    
    analysis = {
        'widgets': {},
        'patterns': {
            'style_prefixes': set(),
            'event_prefixes': set(),
            'base_classes': set(),
            'control_types': set(),
        }
    }
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Parse the AST
        tree = ast.parse(content)
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                widget_info = analyze_widget_class(node, content)
                if widget_info:
                    analysis['widgets'][widget_info['name']] = widget_info
                    
                    # Extract patterns
                    if 'style_prefix' in widget_info:
                        analysis['patterns']['style_prefixes'].add(widget_info['style_prefix'])
                    if 'event_prefix' in widget_info:
                        analysis['patterns']['event_prefixes'].add(widget_info['event_prefix'])
                    if 'base_classes' in widget_info:
                        analysis['patterns']['base_classes'].update(widget_info['base_classes'])
                    if 'control_type' in widget_info:
                        analysis['patterns']['control_types'].add(widget_info['control_type'])
    
    except Exception as e:
        print(f"❌ Error parsing {file_path}: {e}")
        analysis['error'] = str(e)
    
    # Convert sets to lists for JSON serialization
    for key, value in analysis['patterns'].items():
        if isinstance(value, set):
            analysis['patterns'][key] = list(value)
    
    print(f"✅ Found {len(analysis['widgets'])} widget classes")
    return analysis


def analyze_widget_class(node: ast.ClassDef, content: str) -> Optional[Dict[str, Any]]:
    """
    Analyze a single widget class AST node.
    
    Args:
        node: AST ClassDef node
        content: Full file content for line extraction
        
    Returns:
        Dictionary with widget class analysis or None if not a widget
    """
    widget_info = {
        'name': node.name,
        'base_classes': [base.id if isinstance(base, ast.Name) else str(base) for base in node.bases],
        'attributes': {},
        'methods': [],
        'docstring': ast.get_docstring(node),
    }
    
    # Extract class-level attributes
    for item in node.body:
        if isinstance(item, ast.Assign):
            for target in item.targets:
                if isinstance(target, ast.Name):
                    attr_name = target.id
                    
                    # Try to extract the value
                    try:
                        if isinstance(item.value, ast.Constant):
                            widget_info['attributes'][attr_name] = item.value.value
                        elif isinstance(item.value, ast.Name):
                            widget_info['attributes'][attr_name] = item.value.id
                        elif isinstance(item.value, ast.Attribute):
                            # Handle wx.Something references
                            if isinstance(item.value.value, ast.Name) and item.value.value.id == 'wx':
                                widget_info['attributes'][attr_name] = f"wx.{item.value.attr}"
                        else:
                            widget_info['attributes'][attr_name] = str(item.value)
                    except:
                        widget_info['attributes'][attr_name] = "unknown"
        
        elif isinstance(item, ast.FunctionDef):
            method_info = {
                'name': item.name,
                'docstring': ast.get_docstring(item),
                'args': [arg.arg for arg in item.args.args],
            }
            widget_info['methods'].append(method_info)
    
    # Extract commonly used attributes
    attrs = widget_info['attributes']
    if 'control_type' in attrs:
        widget_info['control_type'] = attrs['control_type']
    if 'style_prefix' in attrs:
        widget_info['style_prefix'] = attrs['style_prefix']
    if 'event_prefix' in attrs:
        widget_info['event_prefix'] = attrs['event_prefix']
    if 'selflabeled' in attrs:
        widget_info['selflabeled'] = attrs['selflabeled']
    if 'unlabeled' in attrs:
        widget_info['unlabeled'] = attrs['unlabeled']
    if 'focusable' in attrs:
        widget_info['focusable'] = attrs['focusable']
    if 'default_callback_type' in attrs:
        widget_info['default_callback_type'] = attrs['default_callback_type']
    
    return widget_info


def parse_fields_file(file_path: str = "gui_builder/fields.py") -> Dict[str, Any]:
    """
    Parse the fields.py file to extract Field class information.
    
    Args:
        file_path: Path to the fields.py file
        
    Returns:
        Dictionary containing field class analysis
    """
    print(f"📋 Parsing {file_path}...")
    
    analysis = {
        'fields': {},
        'field_to_widget_mapping': {},
    }
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Parse the AST
        tree = ast.parse(content)
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                field_info = analyze_field_class(node)
                if field_info:
                    analysis['fields'][field_info['name']] = field_info
                    
                    # Map field to widget
                    if 'widget_type' in field_info:
                        analysis['field_to_widget_mapping'][field_info['name']] = field_info['widget_type']
    
    except Exception as e:
        print(f"❌ Error parsing {file_path}: {e}")
        analysis['error'] = str(e)
    
    print(f"✅ Found {len(analysis['fields'])} field classes")
    return analysis


def analyze_field_class(node: ast.ClassDef) -> Optional[Dict[str, Any]]:
    """
    Analyze a single field class AST node.
    
    Args:
        node: AST ClassDef node
        
    Returns:
        Dictionary with field class analysis or None if not a field
    """
    field_info = {
        'name': node.name,
        'base_classes': [base.id if isinstance(base, ast.Name) else str(base) for base in node.bases],
        'attributes': {},
        'docstring': ast.get_docstring(node),
    }
    
    # Extract class-level attributes
    for item in node.body:
        if isinstance(item, ast.Assign):
            for target in item.targets:
                if isinstance(target, ast.Name):
                    attr_name = target.id
                    
                    # Try to extract the value
                    try:
                        if isinstance(item.value, ast.Constant):
                            field_info['attributes'][attr_name] = item.value.value
                        elif isinstance(item.value, ast.Name):
                            field_info['attributes'][attr_name] = item.value.id
                        elif isinstance(item.value, ast.Attribute):
                            # Handle widgets.Something references
                            if isinstance(item.value.value, ast.Name) and item.value.value.id == 'widgets':
                                field_info['attributes'][attr_name] = f"widgets.{item.value.attr}"
                        else:
                            field_info['attributes'][attr_name] = str(item.value)
                    except:
                        field_info['attributes'][attr_name] = "unknown"
    
    # Extract widget_type specifically
    attrs = field_info['attributes']
    if 'widget_type' in attrs:
        field_info['widget_type'] = attrs['widget_type']
    
    return field_info


def analyze_wrapper_patterns(widgets_analysis: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze the wrapper patterns from the widget analysis.
    
    Args:
        widgets_analysis: Output from parse_wx_widgets_file
        
    Returns:
        Dictionary containing pattern analysis
    """
    print("🔍 Analyzing wrapper patterns...")
    
    patterns = {
        'inheritance_hierarchy': {},
        'common_attributes': {},
        'method_patterns': {},
        'style_patterns': {},
        'event_patterns': {},
    }
    
    widgets = widgets_analysis.get('widgets', {})
    
    # Analyze inheritance patterns
    for widget_name, widget_info in widgets.items():
        base_classes = widget_info.get('base_classes', [])
        if base_classes:
            primary_base = base_classes[0] if base_classes else None
            if primary_base not in patterns['inheritance_hierarchy']:
                patterns['inheritance_hierarchy'][primary_base] = []
            patterns['inheritance_hierarchy'][primary_base].append(widget_name)
    
    # Analyze common attributes
    all_attributes = {}
    for widget_name, widget_info in widgets.items():
        for attr_name, attr_value in widget_info.get('attributes', {}).items():
            if attr_name not in all_attributes:
                all_attributes[attr_name] = {}
            if str(attr_value) not in all_attributes[attr_name]:
                all_attributes[attr_name][str(attr_value)] = []
            all_attributes[attr_name][str(attr_value)].append(widget_name)
    
    patterns['common_attributes'] = all_attributes
    
    # Analyze method patterns
    all_methods = {}
    for widget_name, widget_info in widgets.items():
        for method in widget_info.get('methods', []):
            method_name = method['name']
            if method_name not in all_methods:
                all_methods[method_name] = []
            all_methods[method_name].append(widget_name)
    
    # Find common methods
    patterns['method_patterns'] = {
        name: widgets_list for name, widgets_list in all_methods.items() 
        if len(widgets_list) > 1
    }
    
    # Analyze style and event patterns
    style_prefixes = {}
    event_prefixes = {}
    
    for widget_name, widget_info in widgets.items():
        style_prefix = widget_info.get('style_prefix')
        if style_prefix:
            if style_prefix not in style_prefixes:
                style_prefixes[style_prefix] = []
            style_prefixes[style_prefix].append(widget_name)
        
        event_prefix = widget_info.get('event_prefix')
        if event_prefix:
            if event_prefix not in event_prefixes:
                event_prefixes[event_prefix] = []
            event_prefixes[event_prefix].append(widget_name)
    
    patterns['style_patterns'] = style_prefixes
    patterns['event_patterns'] = event_prefixes
    
    return patterns


def generate_coverage_matrix(widgets_analysis: Dict[str, Any], fields_analysis: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate a coverage matrix showing wx controls vs existing wrappers.
    
    Args:
        widgets_analysis: Widget analysis data
        fields_analysis: Field analysis data
        
    Returns:
        Coverage matrix analysis
    """
    print("📊 Generating coverage matrix...")
    
    # Get all wx control types from widgets
    wrapped_wx_controls = set()
    for widget_info in widgets_analysis.get('widgets', {}).values():
        control_type = widget_info.get('control_type')
        if control_type and control_type.startswith('wx.'):
            wrapped_wx_controls.add(control_type)
    
    # Get field to widget mappings
    field_to_widget = fields_analysis.get('field_to_widget_mapping', {})
    
    # Load wx controls inventory if available
    wx_controls = set()
    try:
        with open('wx_controls_inventory.json', 'r') as f:
            inventory = json.load(f)
            for control in inventory.get('controls', []):
                wx_controls.add(f"wx.{control['name']}")
    except FileNotFoundError:
        print("⚠️ wx_controls_inventory.json not found - run wx_introspector.py first")
    
    coverage = {
        'wrapped_controls': list(wrapped_wx_controls),
        'unwrapped_controls': list(wx_controls - wrapped_wx_controls),
        'field_widget_pairs': len(field_to_widget),
        'widget_only': [],  # Widgets without corresponding fields
        'field_only': [],   # Fields without corresponding widgets
        'complete_pairs': [], # Fields with widgets that have wx controls
    }
    
    # Analyze field-widget relationships
    widget_names = set(widgets_analysis.get('widgets', {}).keys())
    field_names = set(fields_analysis.get('fields', {}).keys())
    
    for field_name, widget_ref in field_to_widget.items():
        if widget_ref is None:
            continue
        widget_name = widget_ref.replace('widgets.', '') if widget_ref.startswith('widgets.') else widget_ref
        
        if widget_name in widget_names:
            widget_info = widgets_analysis['widgets'][widget_name]
            control_type = widget_info.get('control_type')
            if control_type:
                coverage['complete_pairs'].append({
                    'field': field_name,
                    'widget': widget_name,
                    'wx_control': control_type
                })
            else:
                coverage['field_only'].append(field_name)
        else:
            coverage['field_only'].append(field_name)
    
    # Find widgets without fields
    widgets_with_fields = {mapping.replace('widgets.', '') for mapping in field_to_widget.values() if mapping is not None}
    coverage['widget_only'] = list(widget_names - widgets_with_fields)
    
    return coverage


def save_analysis_results(data: Dict[str, Any], filename: str) -> None:
    """
    Save the analysis results to a JSON file.
    
    Args:
        data: Analysis data to save
        filename: Output filename
    """
    output_path = Path(filename)
    
    print(f"💾 Saving analysis to {output_path}")
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)
    
    print(f"✅ Analysis saved successfully ({output_path.stat().st_size} bytes)")


def main():
    """Main function to run the wrapper analysis."""
    print("🚀 Starting Wrapper Analysis Tool")
    print()
    
    # Parse wx_widgets.py
    widgets_analysis = parse_wx_widgets_file()
    
    # Parse fields.py  
    fields_analysis = parse_fields_file()
    
    # Analyze patterns
    patterns = analyze_wrapper_patterns(widgets_analysis)
    
    # Generate coverage matrix
    coverage = generate_coverage_matrix(widgets_analysis, fields_analysis)
    
    # Compile complete analysis
    complete_analysis = {
        'metadata': {
            'generated_at': datetime.datetime.now().isoformat(),
            'analyzer_version': '1.0.0',
        },
        'widgets_analysis': widgets_analysis,
        'fields_analysis': fields_analysis,
        'patterns': patterns,
        'coverage': coverage,
    }
    
    # Save results
    save_analysis_results(complete_analysis, 'current_wrapper_analysis.json')
    
    # Print summary
    print()
    print("📈 Analysis Summary:")
    print(f"  🎛️ Widget classes found: {len(widgets_analysis.get('widgets', {}))}")
    print(f"  📝 Field classes found: {len(fields_analysis.get('fields', {}))}")
    print(f"  🔗 Field-Widget pairs: {coverage['field_widget_pairs']}")
    print(f"  ✅ Complete pairs (Field->Widget->wx): {len(coverage['complete_pairs'])}")
    print(f"  🟡 Widgets without fields: {len(coverage['widget_only'])}")
    print(f"  🔴 Fields without widgets: {len(coverage['field_only'])}")
    print(f"  📦 Wrapped wx controls: {len(coverage['wrapped_controls'])}")
    print(f"  ❌ Unwrapped wx controls: {len(coverage['unwrapped_controls'])}")
    
    # Show patterns
    print()
    print("🎯 Common Patterns:")
    inheritance = patterns['inheritance_hierarchy']
    for base_class, derived in inheritance.items():
        if len(derived) > 1:
            print(f"  • {base_class}: {len(derived)} widgets ({', '.join(derived[:3])}{'...' if len(derived) > 3 else ''})")
    
    print()
    print("✨ Wrapper analysis completed successfully!")


if __name__ == '__main__':
    main()
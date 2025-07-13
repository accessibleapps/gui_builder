#!/usr/bin/env python3
"""
Gap Analysis and Prioritization Tool

This script analyzes the gaps between available wx controls and existing wrappers,
then prioritizes missing controls based on usage frequency, complexity, and importance.
"""

import json
import datetime
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional, Set


def load_inventory_data() -> Dict[str, Any]:
    """Load the wx controls inventory and wrapper analysis data."""
    print("📂 Loading analysis data...")
    
    data = {}
    
    # Load wx controls inventory
    try:
        with open('../wx_controls_inventory.json', 'r') as f:
            data['wx_inventory'] = json.load(f)
        print(f"  ✅ Loaded {len(data['wx_inventory']['controls'])} wx controls")
    except FileNotFoundError:
        print("  ❌ wx_controls_inventory.json not found - run wx_introspector.py first")
        data['wx_inventory'] = {'controls': []}
    
    # Load wrapper analysis
    try:
        with open('../current_wrapper_analysis.json', 'r') as f:
            data['wrapper_analysis'] = json.load(f)
        wrapped_count = len(data['wrapper_analysis']['coverage']['wrapped_controls'])
        print(f"  ✅ Loaded wrapper analysis ({wrapped_count} wrapped controls)")
    except FileNotFoundError:
        print("  ❌ current_wrapper_analysis.json not found - run wrapper_analyzer.py first")
        data['wrapper_analysis'] = {'coverage': {'wrapped_controls': [], 'unwrapped_controls': []}}
    
    return data


def categorize_controls(wx_controls: List[Dict[str, Any]]) -> Dict[str, List[str]]:
    """
    Categorize wx controls by their type and functionality.
    
    Args:
        wx_controls: List of wx control information
        
    Returns:
        Dictionary mapping categories to control names
    """
    print("🏷️ Categorizing wx controls...")
    
    categories = {
        'basic_controls': [],      # Button, Text, Label, CheckBox, etc.
        'container_controls': [],  # Panel, Frame, Dialog, Notebook, etc.
        'list_controls': [],       # ListBox, ListView, TreeCtrl, Grid, etc.
        'input_controls': [],      # Slider, SpinCtrl, DatePicker, etc.
        'graphics_controls': [],   # StaticBitmap, Canvas, etc.
        'layout_controls': [],     # Sizers, etc.
        'advanced_controls': [],   # PropertyGrid, AUI, RichText, etc.
        'dialog_controls': [],     # Various dialog types
        'uncategorized': []
    }
    
    # Define categorization rules
    basic_keywords = [
        'button', 'text', 'label', 'check', 'radio', 'static', 'gauge', 'hyperlink'
    ]
    container_keywords = [
        'panel', 'frame', 'window', 'notebook', 'book', 'splitter', 'scrolled'
    ]
    list_keywords = [
        'list', 'tree', 'grid', 'choice', 'combo'
    ]
    input_keywords = [
        'slider', 'spin', 'picker', 'ctrl', 'search'
    ]
    graphics_keywords = [
        'bitmap', 'image', 'canvas', 'draw', 'graphics'
    ]
    layout_keywords = [
        'sizer', 'box', 'flex', 'wrap'
    ]
    dialog_keywords = [
        'dialog', 'message', 'file', 'dir', 'colour', 'font', 'print'
    ]
    advanced_keywords = [
        'property', 'rich', 'aui', 'stc', 'media', 'web', 'gl', 'dataview', 'taskbar'
    ]
    
    for control in wx_controls:
        name = control['name'].lower()
        mro = [cls.lower() for cls in control.get('mro', [])]
        
        categorized = False
        
        # Check against keyword lists
        if any(keyword in name for keyword in basic_keywords):
            categories['basic_controls'].append(control['name'])
            categorized = True
        elif any(keyword in name for keyword in container_keywords):
            categories['container_controls'].append(control['name'])
            categorized = True
        elif any(keyword in name for keyword in list_keywords):
            categories['list_controls'].append(control['name'])
            categorized = True
        elif any(keyword in name for keyword in input_keywords):
            categories['input_controls'].append(control['name'])
            categorized = True
        elif any(keyword in name for keyword in graphics_keywords):
            categories['graphics_controls'].append(control['name'])
            categorized = True
        elif any(keyword in name for keyword in layout_keywords):
            categories['layout_controls'].append(control['name'])
            categorized = True
        elif any(keyword in name for keyword in dialog_keywords):
            categories['dialog_controls'].append(control['name'])
            categorized = True
        elif any(keyword in name for keyword in advanced_keywords):
            categories['advanced_controls'].append(control['name'])
            categorized = True
        
        # Check inheritance hierarchy for additional clues
        if not categorized:
            if any('dialog' in cls for cls in mro):
                categories['dialog_controls'].append(control['name'])
                categorized = True
            elif any('frame' in cls for cls in mro):
                categories['container_controls'].append(control['name'])
                categorized = True
            elif any('control' in cls for cls in mro):
                categories['basic_controls'].append(control['name'])
                categorized = True
            elif any('sizer' in cls for cls in mro):
                categories['layout_controls'].append(control['name'])
                categorized = True
        
        if not categorized:
            categories['uncategorized'].append(control['name'])
    
    # Print categorization summary
    for category, controls in categories.items():
        if controls:
            print(f"  {category}: {len(controls)} controls")
    
    return categories


def prioritize_missing_controls(
    categories: Dict[str, List[str]], 
    wrapped_controls: List[str], 
    unwrapped_controls: List[str]
) -> List[Dict[str, Any]]:
    """
    Prioritize missing controls based on various factors.
    
    Args:
        categories: Categorized controls
        wrapped_controls: List of already wrapped control names
        unwrapped_controls: List of unwrapped control names
        
    Returns:
        List of prioritized missing controls with scores
    """
    print("📊 Prioritizing missing controls...")
    
    # Define priority scores for each category
    category_scores = {
        'basic_controls': 5,      # Highest priority - fundamental UI elements
        'container_controls': 4,  # High priority - needed for layout
        'list_controls': 3,       # Medium-high - common in most apps
        'input_controls': 3,      # Medium-high - user interaction
        'dialog_controls': 2,     # Medium - useful but not essential
        'graphics_controls': 2,   # Medium - specialized use cases
        'layout_controls': 4,     # High - important for layouts
        'advanced_controls': 1,   # Low - complex, specialized
        'uncategorized': 2        # Medium - unknown complexity
    }
    
    # Define usage frequency estimates (higher = more commonly used)
    usage_frequency = {
        'Button': 5, 'TextCtrl': 5, 'StaticText': 5, 'Panel': 5, 'Frame': 5,
        'CheckBox': 4, 'RadioButton': 4, 'ComboBox': 4, 'ListBox': 4,
        'Slider': 3, 'SpinCtrl': 3, 'Gauge': 3, 'Dialog': 4,
        'MessageDialog': 4, 'FileDialog': 4, 'ColourDialog': 3,
        'TreeCtrl': 3, 'ListCtrl': 3, 'Notebook': 4, 'Splitter': 3,
        'MenuBar': 4, 'Menu': 4, 'StatusBar': 4, 'ToolBar': 4,
        'Grid': 2, 'PropertyGrid': 1, 'RichTextCtrl': 2, 'StyledTextCtrl': 1,
        'Calendar': 2, 'DatePickerCtrl': 3, 'TimePickerCtrl': 2,
        'SearchCtrl': 3, 'BitmapButton': 3, 'ToggleButton': 3,
        'ScrollBar': 2, 'StaticBitmap': 3, 'StaticBox': 3, 'StaticLine': 3,
    }
    
    # Create prioritized list
    prioritized = []
    
    # Convert wrapped controls to just names (remove wx. prefix)
    wrapped_names = {ctrl.replace('wx.', '') for ctrl in wrapped_controls}
    unwrapped_names = {ctrl.replace('wx.', '') for ctrl in unwrapped_controls}
    
    # Exclude base controls that shouldn't be wrapped directly
    base_controls_to_exclude = {'Control', 'Window', 'WindowBase', 'Object', 'EvtHandler'}
    unwrapped_names = unwrapped_names - base_controls_to_exclude
    
    for category, controls in categories.items():
        category_score = category_scores.get(category, 2)
        
        for control_name in controls:
            if control_name in unwrapped_names:
                # Calculate total score
                frequency_score = usage_frequency.get(control_name, 2)  # Default to medium
                
                # Implementation complexity estimate (1-5, where 5 is most complex)
                complexity_score = estimate_complexity(control_name, category)
                
                # Dependency score (some controls depend on others)
                dependency_score = estimate_dependencies(control_name)
                
                total_score = (
                    category_score * 0.4 +      # 40% category importance
                    frequency_score * 0.3 +     # 30% usage frequency  
                    (6 - complexity_score) * 0.2 + # 20% implementation ease (inverted)
                    dependency_score * 0.1      # 10% dependency weight
                )
                
                prioritized.append({
                    'name': control_name,
                    'category': category,
                    'total_score': round(total_score, 2),
                    'category_score': category_score,
                    'frequency_score': frequency_score,
                    'complexity_score': complexity_score,
                    'dependency_score': dependency_score,
                    'implementation_effort': get_effort_estimate(complexity_score),
                })
    
    # Sort by total score (highest first)
    prioritized.sort(key=lambda x: x['total_score'], reverse=True)
    
    print(f"  📈 Prioritized {len(prioritized)} missing controls")
    return prioritized


def estimate_complexity(control_name: str, category: str) -> int:
    """Estimate implementation complexity (1-5, where 5 is most complex)."""
    
    # High complexity controls
    if any(keyword in control_name.lower() for keyword in [
        'rich', 'styled', 'grid', 'property', 'media', 'web', 'gl', 'aui', 'dataview'
    ]):
        return 5
    
    # Medium-high complexity
    if any(keyword in control_name.lower() for keyword in [
        'tree', 'calendar', 'search', 'picker', 'generic'
    ]) or category == 'advanced_controls':
        return 4
    
    # Medium complexity
    if any(keyword in control_name.lower() for keyword in [
        'list', 'combo', 'notebook', 'splitter', 'toolbar', 'menu'
    ]) or category in ['list_controls', 'container_controls']:
        return 3
    
    # Low-medium complexity
    if any(keyword in control_name.lower() for keyword in [
        'slider', 'spin', 'gauge', 'scroll'
    ]) or category == 'input_controls':
        return 2
    
    # Low complexity - basic controls
    return 1


def estimate_dependencies(control_name: str) -> int:
    """Estimate dependency importance (1-5, where 5 means other controls depend on this)."""
    
    # High dependency - fundamental building blocks
    if control_name.lower() in ['panel', 'frame', 'window', 'control', 'sizer']:
        return 5
    
    # Medium-high dependency - common containers  
    if any(keyword in control_name.lower() for keyword in ['dialog', 'notebook', 'box']):
        return 4
    
    # Medium dependency - commonly used
    if any(keyword in control_name.lower() for keyword in ['button', 'text', 'static']):
        return 3
    
    # Low dependency - specialized
    return 2


def get_effort_estimate(complexity_score: int) -> str:
    """Convert complexity score to effort estimate."""
    if complexity_score <= 1:
        return "1-2 hours"
    elif complexity_score <= 2:
        return "2-4 hours"
    elif complexity_score <= 3:
        return "4-8 hours"
    elif complexity_score <= 4:
        return "1-2 days"
    else:
        return "2-5 days"


def generate_implementation_plan(prioritized_controls: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Generate an implementation plan based on prioritized controls."""
    
    plan = {
        'phases': {
            'phase_1_critical': [],
            'phase_2_important': [],
            'phase_3_useful': [],
            'phase_4_nice_to_have': []
        },
        'effort_estimates': {
            'phase_1_critical': "1-2 weeks",
            'phase_2_important': "2-3 weeks", 
            'phase_3_useful': "3-4 weeks",
            'phase_4_nice_to_have': "4+ weeks"
        },
        'statistics': {}
    }
    
    # Categorize by score ranges
    for control in prioritized_controls:
        score = control['total_score']
        
        if score >= 4.0:
            plan['phases']['phase_1_critical'].append(control)
        elif score >= 3.0:
            plan['phases']['phase_2_important'].append(control)
        elif score >= 2.0:
            plan['phases']['phase_3_useful'].append(control)
        else:
            plan['phases']['phase_4_nice_to_have'].append(control)
    
    # Calculate statistics
    for phase, controls in plan['phases'].items():
        plan['statistics'][phase] = {
            'count': len(controls),
            'avg_score': round(sum(c['total_score'] for c in controls) / len(controls), 2) if controls else 0,
            'categories': list(set(c['category'] for c in controls))
        }
    
    return plan


def save_gap_analysis(data: Dict[str, Any], filename: str) -> None:
    """Save gap analysis results to JSON file."""
    output_path = Path(filename)
    
    print(f"💾 Saving gap analysis to {output_path}")
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)
    
    print(f"✅ Gap analysis saved ({output_path.stat().st_size} bytes)")


def generate_markdown_report(gap_analysis: Dict[str, Any], filename: str) -> None:
    """Generate a human-readable markdown report."""
    
    print(f"📝 Generating markdown report: {filename}")
    
    plan = gap_analysis['implementation_plan']
    prioritized = gap_analysis['prioritized_controls']
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write("# wx Controls Gap Analysis Report\n\n")
        f.write(f"Generated: {gap_analysis['metadata']['generated_at']}\n\n")
        
        # Executive Summary
        f.write("## Executive Summary\n\n")
        total_missing = len(prioritized)
        f.write(f"- **Total missing controls:** {total_missing}\n")
        f.write(f"- **Critical priority:** {plan['statistics']['phase_1_critical']['count']}\n")
        f.write(f"- **Important priority:** {plan['statistics']['phase_2_important']['count']}\n")
        f.write(f"- **Useful priority:** {plan['statistics']['phase_3_useful']['count']}\n")
        f.write(f"- **Nice-to-have:** {plan['statistics']['phase_4_nice_to_have']['count']}\n\n")
        
        # Implementation Plan
        f.write("## Implementation Plan\n\n")
        
        for phase_key, phase_controls in plan['phases'].items():
            if not phase_controls:
                continue
                
            phase_name = phase_key.replace('_', ' ').title()
            effort = plan['effort_estimates'][phase_key]
            
            f.write(f"### {phase_name} ({effort})\n\n")
            f.write(f"**{len(phase_controls)} controls**\n\n")
            
            # Top controls in this phase
            for i, control in enumerate(phase_controls[:10], 1):
                f.write(f"{i}. **{control['name']}** (score: {control['total_score']})\n")
                f.write(f"   - Category: {control['category']}\n")
                f.write(f"   - Effort: {control['implementation_effort']}\n")
                f.write(f"   - Complexity: {control['complexity_score']}/5\n\n")
            
            if len(phase_controls) > 10:
                f.write(f"   ... and {len(phase_controls) - 10} more\n\n")
        
        # Top Priority Controls Detail
        f.write("## Top 20 Priority Controls\n\n")
        f.write("| Rank | Control | Score | Category | Effort | Complexity |\n")
        f.write("|------|---------|-------|----------|--------|-----------|\n")
        
        for i, control in enumerate(prioritized[:20], 1):
            f.write(f"| {i} | {control['name']} | {control['total_score']} | {control['category']} | {control['implementation_effort']} | {control['complexity_score']}/5 |\n")
        
        f.write(f"\n*Full prioritized list contains {len(prioritized)} controls*\n")

    print(f"✅ Markdown report generated")


def main():
    """Main function to run gap analysis and prioritization."""
    print("🚀 Starting Gap Analysis and Prioritization Tool")
    print()
    
    # Load data
    data = load_inventory_data()
    
    if not data['wx_inventory']['controls']:
        print("❌ No wx controls data found. Run wx_introspector.py first.")
        return
    
    # Categorize wx controls
    categories = categorize_controls(data['wx_inventory']['controls'])
    
    # Get wrapped and unwrapped controls
    wrapped_controls = data['wrapper_analysis']['coverage'].get('wrapped_controls', [])
    unwrapped_controls = data['wrapper_analysis']['coverage'].get('unwrapped_controls', [])
    
    print(f"📊 Found {len(wrapped_controls)} wrapped and {len(unwrapped_controls)} unwrapped controls")
    
    # Prioritize missing controls
    prioritized_controls = prioritize_missing_controls(categories, wrapped_controls, unwrapped_controls)
    
    # Generate implementation plan
    implementation_plan = generate_implementation_plan(prioritized_controls)
    
    # Compile complete analysis
    gap_analysis = {
        'metadata': {
            'generated_at': datetime.datetime.now().isoformat(),
            'total_wx_controls': len(data['wx_inventory']['controls']),
            'wrapped_controls': len(wrapped_controls),
            'unwrapped_controls': len(unwrapped_controls),
        },
        'categories': categories,
        'prioritized_controls': prioritized_controls,
        'implementation_plan': implementation_plan,
    }
    
    # Save results
    save_gap_analysis(gap_analysis, 'gap_analysis_report.json')
    generate_markdown_report(gap_analysis, 'gap_analysis_report.md')
    
    # Print summary
    print()
    print("📈 Gap Analysis Summary:")
    print(f"  🎯 Total wx controls: {gap_analysis['metadata']['total_wx_controls']}")
    print(f"  ✅ Already wrapped: {gap_analysis['metadata']['wrapped_controls']}")
    print(f"  ❌ Missing wrappers: {gap_analysis['metadata']['unwrapped_controls']}")
    print()
    print("🏆 Top 10 Priority Controls:")
    for i, control in enumerate(prioritized_controls[:10], 1):
        print(f"  {i:2d}. {control['name']:<20} (score: {control['total_score']}, {control['implementation_effort']})")
    
    print()
    print("📋 Implementation Plan:")
    for phase_key, stats in implementation_plan['statistics'].items():
        if stats['count'] > 0:
            phase_name = phase_key.replace('_', ' ').title()
            effort = implementation_plan['effort_estimates'][phase_key]
            print(f"  {phase_name}: {stats['count']} controls ({effort})")
    
    print()
    print("✨ Gap analysis completed successfully!")
    print(f"📄 See gap_analysis_report.md for detailed implementation plan")


if __name__ == '__main__':
    main()
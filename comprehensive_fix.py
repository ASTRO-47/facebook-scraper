#!/usr/bin/env python3
"""
Comprehensive fix for all indentation issues in profile.py
"""

import re

def fix_all_indentation():
    """Fix all indentation issues by rewriting the file with proper structure"""
    
    # Read the original file
    with open('scraper/profile.py', 'r') as f:
        content = f.read()
    
    # Fix basic indentation issues line by line
    lines = content.split('\n')
    fixed_lines = []
    
    in_class = False
    in_method = False
    method_indent = 4
    current_indent = 0
    
    for i, line in enumerate(lines):
        # Skip empty lines
        if not line.strip():
            fixed_lines.append('')
            continue
        
        # Get current line's content without leading whitespace
        stripped = line.lstrip()
        
        # Determine proper indentation based on context
        if stripped.startswith('class '):
            current_indent = 0
            in_class = True
        elif stripped.startswith('def ') or stripped.startswith('async def '):
            if in_class:
                current_indent = 4
                in_method = True
            else:
                current_indent = 0
        elif stripped.startswith('"""') and in_method:
            # Docstring in method
            current_indent = 8
        elif stripped.startswith('try:') or stripped.startswith('if ') or stripped.startswith('for ') or stripped.startswith('while ') or stripped.startswith('with '):
            if in_method:
                current_indent = 8 + (line.count('    ') - 2) * 4
                if current_indent < 8:
                    current_indent = 8
        elif stripped.startswith('except') or stripped.startswith('finally') or stripped.startswith('else:') or stripped.startswith('elif '):
            if in_method:
                current_indent = 8 + (line.count('    ') - 2) * 4
                if current_indent < 8:
                    current_indent = 8
        elif stripped.startswith('return ') or stripped.startswith('break') or stripped.startswith('continue') or stripped.startswith('pass'):
            if in_method:
                current_indent = 8 + (line.count('    ') - 2) * 4
                if current_indent < 8:
                    current_indent = 8
        elif stripped.startswith('#'):
            # Comments - keep relative indentation
            if in_method:
                current_indent = max(8, len(line) - len(stripped))
            else:
                current_indent = len(line) - len(stripped)
        elif in_method and stripped:
            # Regular code in method
            current_indent = 8 + (line.count('    ') - 2) * 4
            if current_indent < 8:
                current_indent = 8
        
        # Apply the indentation
        if stripped:
            fixed_line = ' ' * current_indent + stripped
            fixed_lines.append(fixed_line)
        else:
            fixed_lines.append('')
    
    # Join the lines back
    fixed_content = '\n'.join(fixed_lines)
    
    # Write the fixed content back
    with open('scraper/profile.py', 'w') as f:
        f.write(fixed_content)
    
    print("✅ Comprehensive indentation fix applied")

if __name__ == "__main__":
    fix_all_indentation() 
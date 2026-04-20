#!/usr/bin/env python
"""
Quick syntax check for Statistics API files
"""

import ast
import sys

files_to_check = [
    'apps/orders/apis/statistics/__init__.py',
    'apps/orders/apis/statistics/list.py',
    'apps/orders/apis/statistics/detail.py',
    'apps/orders/apis/statistics/shift.py',
    'apps/orders/apis/statistics/active_orders.py',
    'apps/orders/apis/statistics/urls.py',
    'apps/orders/apis/urls.py',
    'apps/orders/serializers/statistics.py',
]

def check_syntax(filepath):
    """Check Python file for syntax errors"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            code = f.read()
        ast.parse(code)
        print(f"✅ {filepath} - OK")
        return True
    except SyntaxError as e:
        print(f"❌ {filepath} - SYNTAX ERROR: {e}")
        return False
    except Exception as e:
        print(f"⚠️  {filepath} - ERROR: {e}")
        return False

def main():
    print("Checking Statistics API files for syntax errors...\n")
    all_ok = True
    
    for filepath in files_to_check:
        if not check_syntax(filepath):
            all_ok = False
    
    print("\n" + "="*50)
    if all_ok:
        print("✅ All files passed syntax check!")
        sys.exit(0)
    else:
        print("❌ Some files have errors!")
        sys.exit(1)

if __name__ == '__main__':
    main()

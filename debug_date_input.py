#!/usr/bin/env python3
"""
Debug script for testing manual date input parsing logic
"""

import os
import sys
from datetime import datetime

import django

# Setup Django environment
sys.path.append('/Users/kamranhacili/Projects/restuarant_backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

class TestDateParsing:
    """Test the date parsing logic from the bot"""
    
    def looks_like_date_input(self, text):
        """Check if text looks like a date input (current flawed version)"""
        parts = text.split()
        if len(parts) == 0 or len(parts) > 2:
            return False
        
        # Check if all parts look like dates (YYYY-MM-DD format)
        for part in parts:
            if not (len(part) == 10 and part.count('-') == 2):
                return False
            try:
                datetime.fromisoformat(part)
                return True  # BUG: This returns after first valid date
            except ValueError:
                pass
        
        return False
    
    def looks_like_date_input_fixed(self, text):
        """Fixed version of date input check"""
        parts = text.split()
        if len(parts) == 0 or len(parts) > 2:
            return False
        
        # Check if all parts look like dates (YYYY-MM-DD format)
        for part in parts:
            if not (len(part) == 10 and part.count('-') == 2):
                return False
            try:
                datetime.fromisoformat(part)
                # Don't return here - check all parts
            except ValueError:
                return False  # If any part is invalid, return False
        
        return True  # All parts are valid
    
    def test_date_inputs(self):
        """Test various date input scenarios"""
        test_cases = [
            "2025-01-15",
            "2025-01-15 2025-01-20",
            "invalid-date",
            "2025-01-15 invalid-date",
            "2025-13-45",  # Invalid date
            "2025-01-15 2025-13-45",  # One valid, one invalid
            "",
            "too many date inputs here",
            "20-01-15",  # Wrong format
            "2025/01/15"  # Wrong separator
        ]
        
        print("Testing date input parsing...")
        print("="*60)
        
        for test_input in test_cases:
            current_result = self.looks_like_date_input(test_input)
            fixed_result = self.looks_like_date_input_fixed(test_input)
            
            print(f"Input: '{test_input}'")
            print(f"  Current logic: {current_result}")
            print(f"  Fixed logic:   {fixed_result}")
            
            if current_result != fixed_result:
                print(f"  ❌ DIFFERENCE DETECTED!")
            else:
                print(f"  ✅ Same result")
            
            print()

if __name__ == "__main__":
    tester = TestDateParsing()
    tester.test_date_inputs()

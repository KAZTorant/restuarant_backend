#!/usr/bin/env python3
"""
Test script for the fixed manual date input functionality
"""

import os
import sys
from datetime import date, datetime

import django

# Setup Django environment
sys.path.append('/Users/kamranhacili/Projects/restuarant_backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.orders.telegram_bot.bot import RestaurantBot


class TestFixedDateParsing:
    def __init__(self):
        # Create a bot instance for testing
        self.bot = RestaurantBot("test_token")
    
    def test_date_recognition(self):
        """Test the looks_like_date_input method"""
        print("🔍 Testing Date Recognition Logic")
        print("="*60)
        
        test_cases = [
            # Valid single dates
            ("2025-01-15", True, "ISO format"),
            ("15.01.2025", True, "European format"),
            ("15/01/2025", True, "Slash format"),
            ("15-01-2025", True, "Dash format"),
            
            # Valid date ranges
            ("2025-01-15 2025-01-20", True, "ISO range"),
            ("15.01.2025 20.01.2025", True, "European range"),
            ("15/01/2025 20/01/2025", True, "Slash range"),
            ("15-01-2025 20-01-2025", True, "Dash range"),
            
            # Invalid dates
            ("invalid-date", False, "Invalid text"),
            ("2025-01-15 invalid-date", False, "Mixed valid/invalid"),
            ("2025-13-45", False, "Invalid date values"),
            ("2025-01-15 2025-13-45", False, "One valid, one invalid"),
            ("", False, "Empty string"),
            ("too many date inputs here", False, "Too many parts"),
            ("20-01-15", False, "Wrong year format"),
            ("2025/01/15", False, "Mixed separators"),
            ("random text", False, "Random text"),
        ]
        
        for test_input, expected, description in test_cases:
            result = self.bot.looks_like_date_input(test_input)
            status = "✅" if result == expected else "❌"
            
            print(f"{status} '{test_input}' -> {result} (expected: {expected}) - {description}")
    
    def test_date_parsing(self):
        """Test the date parsing functionality"""
        print("\n📅 Testing Date Parsing")
        print("="*60)
        
        test_cases = [
            ("2025-01-15", date(2025, 1, 15), "ISO format"),
            ("15.01.2025", date(2025, 1, 15), "European format"),
            ("15/01/2025", date(2025, 1, 15), "Slash format"),
            ("15-01-2025", date(2025, 1, 15), "Dash format"),
        ]
        
        for test_input, expected, description in test_cases:
            try:
                result = self.bot.parse_date_string(test_input)
                status = "✅" if result == expected else "❌"
                print(f"{status} '{test_input}' -> {result} (expected: {expected}) - {description}")
            except Exception as e:
                print(f"❌ '{test_input}' -> ERROR: {e} - {description}")
    
    def test_invalid_date_parsing(self):
        """Test that invalid dates raise proper errors"""
        print("\n⚠️  Testing Invalid Date Parsing")
        print("="*60)
        
        invalid_dates = [
            "invalid-date",
            "2025-13-45",
            "32/01/2025",
            "15.13.2025",
            "random text",
            "2025/13/45"
        ]
        
        for test_input in invalid_dates:
            try:
                result = self.bot.parse_date_string(test_input)
                print(f"❌ '{test_input}' -> {result} (Should have failed!)")
            except ValueError as e:
                print(f"✅ '{test_input}' -> Correctly failed: {e}")
            except Exception as e:
                print(f"⚠️  '{test_input}' -> Unexpected error: {e}")

def main():
    """Run all tests"""
    print("🧪 Testing Fixed Manual Date Input Functionality")
    print("="*80)
    
    tester = TestFixedDateParsing()
    
    tester.test_date_recognition()
    tester.test_date_parsing()
    tester.test_invalid_date_parsing()
    
    print("\n" + "="*80)
    print("🎯 Test Summary:")
    print("• Fixed the bug in looks_like_date_input where it returned True after first valid date")
    print("• Added support for multiple date formats (ISO, European, slash, dash)")
    print("• Improved error messages with format examples")
    print("• Enhanced date parsing robustness")

if __name__ == "__main__":
    main()

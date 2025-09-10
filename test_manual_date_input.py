#!/usr/bin/env python3
"""
Test script to verify the manual date input functionality in the Telegram bot.
This simulates the bot's manual date processing logic.
"""

from datetime import date, datetime

import requests


class ManualDateInputTester:
    def __init__(self):
        self.base_url = "http://127.0.0.1:8000"
    
    def looks_like_date_input(self, text):
        """Check if text looks like a date input"""
        parts = text.split()
        if len(parts) == 0 or len(parts) > 2:
            return False
        
        # Check if all parts look like dates (YYYY-MM-DD format)
        for part in parts:
            if not (len(part) == 10 and part.count('-') == 2):
                return False
            try:
                datetime.fromisoformat(part)
                return True
            except ValueError:
                pass
        
        return False
    
    def test_date_parsing(self, text):
        """Test date parsing logic"""
        print(f"\n🧪 Testing input: '{text}'")
        
        # First check if it looks like date input
        if not self.looks_like_date_input(text):
            print("❌ Does not look like date input")
            return False
        
        print("✅ Looks like date input")
        
        try:
            parts = text.split()
            
            if len(parts) == 1:
                # Single date
                try:
                    input_date = datetime.fromisoformat(parts[0]).date()
                    print(f"✅ Single date parsed: {input_date}")
                    return self.test_api_call_single(input_date)
                except ValueError as e:
                    print(f"❌ Invalid single date format: {e}")
                    return False
                    
            elif len(parts) == 2:
                # Date range
                try:
                    start_date = datetime.fromisoformat(parts[0]).date()
                    end_date = datetime.fromisoformat(parts[1]).date()
                    
                    print(f"✅ Date range parsed: {start_date} to {end_date}")
                    
                    if start_date > end_date:
                        print("❌ Start date is after end date")
                        return False
                    
                    return self.test_api_call_range(start_date, end_date)
                except ValueError as e:
                    print(f"❌ Invalid date range format: {e}")
                    return False
            else:
                print(f"❌ Wrong number of date parts: {len(parts)}")
                return False
                
        except Exception as e:
            print(f"❌ Error processing input: {e}")
            return False
    
    def test_api_call_single(self, target_date):
        """Test API call for single date"""
        try:
            api_url = f"{self.base_url}/orders/active-orders/?date={target_date.isoformat()}"
            print(f"📞 API call: {api_url}")
            
            response = requests.get(api_url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ API success: Paid {data['paid_total']:.2f} AZN, Unpaid {data['unpaid_total']:.2f} AZN")
                return True
            else:
                print(f"❌ API error: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Connection error: {e}")
            return False
    
    def test_api_call_range(self, start_date, end_date):
        """Test API call for date range"""
        try:
            start_datetime = f"{start_date.isoformat()}T00:00:00"
            end_datetime = f"{end_date.isoformat()}T23:59:59"
            api_url = f"{self.base_url}/orders/active-orders/?start_date={start_datetime}&end_date={end_datetime}"
            print(f"📞 API call: {api_url}")
            
            response = requests.get(api_url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ API success: Paid {data['paid_total']:.2f} AZN, Unpaid {data['unpaid_total']:.2f} AZN")
                return True
            else:
                print(f"❌ API error: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Connection error: {e}")
            return False


def main():
    print("🤖 Manual Date Input Testing for Telegram Bot")
    print("=" * 60)
    
    tester = ManualDateInputTester()
    
    # Test cases
    test_cases = [
        # Valid single dates
        "2025-09-10",
        "2025-09-05",
        
        # Valid date ranges
        "2025-09-05 2025-09-06",
        "2025-09-01 2025-09-10",
        
        # Invalid formats
        "invalid-date",
        "2025-13-45",
        "2025/09/10",
        "10-09-2025",
        
        # Wrong number of parts
        "2025-09-10 2025-09-11 2025-09-12",
        "",
        
        # Invalid ranges
        "2025-09-10 2025-09-05",  # start > end
        
        # Non-date text
        "hello world",
        "bugün",
        "today",
    ]
    
    results = []
    for test_case in test_cases:
        success = tester.test_date_parsing(test_case)
        results.append((test_case, success))
    
    print("\n" + "=" * 60)
    print("📊 Test Results Summary:")
    
    passed = 0
    failed = 0
    
    for test_case, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: '{test_case}'")
        if success:
            passed += 1
        else:
            failed += 1
    
    print(f"\n📈 Total: {len(results)} tests")
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    
    if failed == 0:
        print("🎉 All tests passed! Manual date input functionality is working correctly.")
    else:
        print("⚠️  Some tests failed. Check the error messages above.")


if __name__ == "__main__":
    main()

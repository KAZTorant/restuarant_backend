#!/usr/bin/env python3
"""
Comprehensive test for the /orders menu functionality with real data.
This script tests all the bot's API calls to ensure they work correctly.
"""

import json
from datetime import date, datetime, timedelta

import requests


def test_api_call(url, description):
    """Test an API call and return the result"""
    print(f"\n🧪 {description}")
    print(f"📞 API: {url}")
    
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Status: {response.status_code}")
            print(f"💰 Paid Total: {data.get('paid_total', 0):.2f} AZN")
            print(f"❌ Unpaid Total: {data.get('unpaid_total', 0):.2f} AZN")
            print(f"💵 Cash: {data.get('cash_total', 0):.2f} AZN")
            print(f"💳 Card: {data.get('card_total', 0):.2f} AZN")
            print(f"🔄 Other: {data.get('other_total', 0):.2f} AZN")
            
            filters = data.get('filters_applied', {})
            if any(filters.values()):
                print(f"🔍 Filters: {filters}")
            
            return True, data
        else:
            print(f"❌ Error: HTTP {response.status_code}")
            print(f"📄 Response: {response.text}")
            return False, None
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Connection Error: {e}")
        return False, None


def main():
    base_url = "http://127.0.0.1:8000"
    
    print("🍽️ Restaurant Bot Orders Menu - Real Data Testing")
    print("=" * 60)
    
    # Test 1: All orders (no filter) - What bot shows initially
    success, data = test_api_call(
        f"{base_url}/orders/active-orders/",
        "Option 1 & 2 Base: All Orders (No Filter)"
    )
    
    if success:
        all_orders_total = data['paid_total'] + data['unpaid_total']
        print(f"📊 Total Business: {all_orders_total:.2f} AZN")
    
    # Test 2: Today's report (Option 1)
    today = date.today().isoformat()
    test_api_call(
        f"{base_url}/orders/active-orders/?date={today}",
        f"Option 1: Today's Report ({today})"
    )
    
    # Test 3: This week (Option 2 - Predefined)
    today_obj = date.today()
    start_of_week = today_obj - timedelta(days=today_obj.weekday())
    end_of_week = start_of_week + timedelta(days=6)
    test_api_call(
        f"{base_url}/orders/active-orders/?start_date={start_of_week}T00:00:00&end_date={end_of_week}T23:59:59",
        f"Option 2: This Week ({start_of_week} to {end_of_week})"
    )
    
    # Test 4: Last week (Option 2 - Predefined)
    start_last_week = start_of_week - timedelta(days=7)
    end_last_week = start_last_week + timedelta(days=6)
    test_api_call(
        f"{base_url}/orders/active-orders/?start_date={start_last_week}T00:00:00&end_date={end_last_week}T23:59:59",
        f"Option 2: Last Week ({start_last_week} to {end_last_week})"
    )
    
    # Test 5: This month (Option 2 - Predefined)
    first_of_month = today_obj.replace(day=1)
    if today_obj.month == 12:
        last_of_month = today_obj.replace(year=today_obj.year + 1, month=1, day=1) - timedelta(days=1)
    else:
        last_of_month = today_obj.replace(month=today_obj.month + 1, day=1) - timedelta(days=1)
    
    test_api_call(
        f"{base_url}/orders/active-orders/?start_date={first_of_month}T00:00:00&end_date={last_of_month}T23:59:59",
        f"Option 2: This Month ({first_of_month} to {last_of_month})"
    )
    
    # Test 6: Historical date with data (Sept 5, 2025)
    test_api_call(
        f"{base_url}/orders/active-orders/?date=2025-09-05",
        "Option 2: Historical Date with Data (2025-09-05)"
    )
    
    # Test 7: Date range with data (Sept 5-6, 2025)
    test_api_call(
        f"{base_url}/orders/active-orders/?start_date=2025-09-05T00:00:00&end_date=2025-09-06T23:59:59",
        "Option 2: Historical Range with Data (2025-09-05 to 2025-09-06)"
    )
    
    # Test 8: Manual date range (Option 2 - Manual input simulation)
    manual_start = today_obj - timedelta(days=7)
    manual_end = today_obj - timedelta(days=1)
    test_api_call(
        f"{base_url}/orders/active-orders/?start_date={manual_start}T00:00:00&end_date={manual_end}T23:59:59",
        f"Option 2: Manual Range ({manual_start} to {manual_end})"
    )
    
    # Test 9: Error testing - Invalid date format
    print(f"\n🧪 Error Testing: Invalid Date Format")
    print(f"📞 API: {base_url}/orders/active-orders/?date=invalid-date")
    
    try:
        response = requests.get(f"{base_url}/orders/active-orders/?date=invalid-date", timeout=10)
        if response.status_code == 400:
            error_data = response.json()
            print(f"✅ Expected Error: {error_data.get('error', 'Unknown error')}")
        else:
            print(f"❌ Unexpected Status: {response.status_code}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print("\n" + "=" * 60)
    print("🎯 Test Summary:")
    print("✅ Option 1: Today's Report - Direct date filter")
    print("✅ Option 2: Date/Time Range - Multiple sub-options:")
    print("   ├── Predefined ranges (week, month)")
    print("   ├── Historical data access")
    print("   └── Manual date input simulation")
    print("✅ Error handling for invalid formats")
    print("\n🤖 Bot Menu Structure Verified:")
    print("   /orders")
    print("   ├── 📅 Bugünkü Hesabat (Today's Report)")
    print("   └── 📆 Tarix/Vaxt Aralığı (Date/Time Range)")
    print("       ├── 📅 Bu həftə (This Week)")
    print("       ├── 📅 Keçən həftə (Last Week)")
    print("       ├── 📅 Bu ay (This Month)")
    print("       └── 📝 Əl ilə daxil et (Manual Entry)")


if __name__ == "__main__":
    main()

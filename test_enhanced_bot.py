#!/usr/bin/env python3
"""
Test script for the enhanced Telegram bot functionality.

This script simulates the bot menu interactions and API calls to verify
that the date filtering works correctly with the new bot options.
"""

from datetime import date, datetime, timedelta

import requests


def test_bot_api_calls():
    """Test the API calls that the bot will make"""
    base_url = "http://127.0.0.1:8000"
    
    print("🤖 Testing Enhanced Telegram Bot API Calls\n")
    
    # Test 1: Today's Report (Option 1)
    print("1️⃣ Testing Option 1: Today's Report")
    today = date.today().isoformat()
    try:
        response = requests.get(f"{base_url}/orders/active-orders/?date={today}")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Today's Report Success")
            print(f"   📅 Date: {today}")
            print(f"   💰 Paid Total: {data.get('paid_total', 0):.2f} AZN")
            print(f"   ❌ Unpaid Total: {data.get('unpaid_total', 0):.2f} AZN")
        else:
            print(f"❌ Error: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"❌ Connection error: {e}")
    
    # Test 2: This Week's Report (Option 2 - Predefined)
    print("\n2️⃣ Testing Option 2: This Week's Report")
    today = date.today()
    start_date = today - timedelta(days=today.weekday())  # Monday
    end_date = start_date + timedelta(days=6)  # Sunday
    start_datetime = f"{start_date.isoformat()}T00:00:00"
    end_datetime = f"{end_date.isoformat()}T23:59:59"
    
    try:
        response = requests.get(
            f"{base_url}/orders/active-orders/?start_date={start_datetime}&end_date={end_datetime}"
        )
        if response.status_code == 200:
            data = response.json()
            print(f"✅ This Week's Report Success")
            print(f"   📅 Range: {start_date.strftime('%d.%m.%Y')} - {end_date.strftime('%d.%m.%Y')}")
            print(f"   💰 Paid Total: {data.get('paid_total', 0):.2f} AZN")
            print(f"   ❌ Unpaid Total: {data.get('unpaid_total', 0):.2f} AZN")
        else:
            print(f"❌ Error: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"❌ Connection error: {e}")
    
    # Test 3: Last Week's Report (Option 2 - Predefined)
    print("\n3️⃣ Testing Option 2: Last Week's Report")
    start_date = today - timedelta(days=today.weekday() + 7)  # Last Monday
    end_date = start_date + timedelta(days=6)  # Last Sunday
    start_datetime = f"{start_date.isoformat()}T00:00:00"
    end_datetime = f"{end_date.isoformat()}T23:59:59"
    
    try:
        response = requests.get(
            f"{base_url}/orders/active-orders/?start_date={start_datetime}&end_date={end_datetime}"
        )
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Last Week's Report Success")
            print(f"   📅 Range: {start_date.strftime('%d.%m.%Y')} - {end_date.strftime('%d.%m.%Y')}")
            print(f"   💰 Paid Total: {data.get('paid_total', 0):.2f} AZN")
            print(f"   ❌ Unpaid Total: {data.get('unpaid_total', 0):.2f} AZN")
        else:
            print(f"❌ Error: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"❌ Connection error: {e}")
    
    # Test 4: This Month's Report (Option 2 - Predefined)
    print("\n4️⃣ Testing Option 2: This Month's Report")
    start_date = today.replace(day=1)  # First day of month
    if today.month == 12:
        end_date = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
    else:
        end_date = today.replace(month=today.month + 1, day=1) - timedelta(days=1)
    
    start_datetime = f"{start_date.isoformat()}T00:00:00"
    end_datetime = f"{end_date.isoformat()}T23:59:59"
    
    try:
        response = requests.get(
            f"{base_url}/orders/active-orders/?start_date={start_datetime}&end_date={end_datetime}"
        )
        if response.status_code == 200:
            data = response.json()
            print(f"✅ This Month's Report Success")
            print(f"   📅 Range: {start_date.strftime('%d.%m.%Y')} - {end_date.strftime('%d.%m.%Y')}")
            print(f"   💰 Paid Total: {data.get('paid_total', 0):.2f} AZN")
            print(f"   ❌ Unpaid Total: {data.get('unpaid_total', 0):.2f} AZN")
        else:
            print(f"❌ Error: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"❌ Connection error: {e}")
    
    # Test 5: Manual Date Range (Option 2 - Manual)
    print("\n5️⃣ Testing Option 2: Manual Date Range")
    manual_start = today - timedelta(days=3)
    manual_end = today - timedelta(days=1)
    start_datetime = f"{manual_start.isoformat()}T00:00:00"
    end_datetime = f"{manual_end.isoformat()}T23:59:59"
    
    try:
        response = requests.get(
            f"{base_url}/orders/active-orders/?start_date={start_datetime}&end_date={end_datetime}"
        )
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Manual Date Range Success")
            print(f"   📅 Range: {manual_start.strftime('%d.%m.%Y')} - {manual_end.strftime('%d.%m.%Y')}")
            print(f"   💰 Paid Total: {data.get('paid_total', 0):.2f} AZN")
            print(f"   ❌ Unpaid Total: {data.get('unpaid_total', 0):.2f} AZN")
        else:
            print(f"❌ Error: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"❌ Connection error: {e}")
    
    print("\n🎉 Bot API Testing Completed!")
    print("\n📱 Bot Menu Flow:")
    print("   /orders")
    print("   ├── 📅 Bugünkü Hesabat (Option 1)")
    print("   └── 📆 Tarix/Vaxt Aralığı (Option 2)")
    print("       ├── 📅 Bu həftə")
    print("       ├── 📅 Keçən həftə") 
    print("       ├── 📅 Bu ay")
    print("       └── 📝 Əl ilə daxil et")


def simulate_manual_date_parsing():
    """Simulate the bot's manual date parsing functionality"""
    print("\n🔤 Testing Manual Date Input Parsing")
    
    test_inputs = [
        "2025-09-10",                    # Single date
        "2025-09-01 2025-09-10",         # Date range
        "invalid-date",                  # Invalid format
        "2025-09-10 2025-09-01",         # Start > End
        "2025-09-01 2025-09-10 2025-09-15"  # Too many dates
    ]
    
    for i, input_text in enumerate(test_inputs, 1):
        print(f"\n{i}️⃣ Testing input: '{input_text}'")
        
        try:
            parts = input_text.split()
            
            if len(parts) == 1:
                try:
                    input_date = datetime.fromisoformat(parts[0]).date()
                    print(f"   ✅ Single date parsed: {input_date}")
                except ValueError:
                    print(f"   ❌ Invalid date format")
                    
            elif len(parts) == 2:
                try:
                    start_date = datetime.fromisoformat(parts[0]).date()
                    end_date = datetime.fromisoformat(parts[1]).date()
                    
                    if start_date > end_date:
                        print(f"   ❌ Start date after end date")
                    else:
                        print(f"   ✅ Date range parsed: {start_date} to {end_date}")
                except ValueError:
                    print(f"   ❌ Invalid date format in range")
            else:
                print(f"   ❌ Wrong number of dates (expected 1 or 2)")
                
        except Exception as e:
            print(f"   ❌ Parsing error: {e}")


if __name__ == "__main__":
    test_bot_api_calls()
    simulate_manual_date_parsing()

#!/usr/bin/env python3
"""
Demonstration script for the new datetime filtering functionality
in the active_orders API endpoint.

Usage examples:

1. Get all active orders (no filters):
   GET /orders/active-orders/

2. Get orders for a specific date (today):
   GET /orders/active-orders/?date=2025-09-10

3. Get orders from a specific start datetime:
   GET /orders/active-orders/?start_date=2025-09-10T08:00:00

4. Get orders within a date range:
   GET /orders/active-orders/?start_date=2025-09-10T08:00:00&end_date=2025-09-10T18:00:00

The API now returns additional information:
- paid_total: Sum of all paid amounts
- filters_applied: Shows which filters were applied to the query

Bot Integration:
- Added "📅 Bugünkü Sifarişlər" button to show today's orders only
- Existing functionality remains unchanged for backward compatibility
"""

from datetime import date, datetime, timedelta

import requests


def test_api_endpoints():
    """Test the various datetime filtering options"""
    base_url = "http://127.0.0.1:8000"
    
    print("🧪 Testing Active Orders API with Datetime Filtering\n")
    
    # Test 1: No filters (all orders)
    print("1️⃣ Testing: All active orders (no filters)")
    try:
        response = requests.get(f"{base_url}/orders/active-orders/")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Success: Found orders with total paid: {data.get('paid_total', 0):.2f} AZN")
            print(f"   Filters applied: {data.get('filters_applied', {})}")
        else:
            print(f"❌ Error: {response.status_code} - {response.text}")
    except requests.exceptions.RequestException as e:
        print(f"❌ Connection error: {e}")
    
    # Test 2: Today's orders only
    print("\n2️⃣ Testing: Today's orders only")
    today = date.today().isoformat()
    try:
        response = requests.get(f"{base_url}/orders/active-orders/?date={today}")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Success: Today's orders total paid: {data.get('paid_total', 0):.2f} AZN")
            print(f"   Filters applied: {data.get('filters_applied', {})}")
        else:
            print(f"❌ Error: {response.status_code} - {response.text}")
    except requests.exceptions.RequestException as e:
        print(f"❌ Connection error: {e}")
    
    # Test 3: Orders from 8 AM today
    print("\n3️⃣ Testing: Orders from 8 AM today")
    start_time = datetime.combine(date.today(), datetime.min.time().replace(hour=8))
    try:
        response = requests.get(f"{base_url}/orders/active-orders/?start_date={start_time.isoformat()}")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Success: Orders from 8 AM total paid: {data.get('paid_total', 0):.2f} AZN")
            print(f"   Filters applied: {data.get('filters_applied', {})}")
        else:
            print(f"❌ Error: {response.status_code} - {response.text}")
    except requests.exceptions.RequestException as e:
        print(f"❌ Connection error: {e}")
    
    # Test 4: Invalid date format
    print("\n4️⃣ Testing: Invalid date format")
    try:
        response = requests.get(f"{base_url}/orders/active-orders/?date=invalid-date")
        if response.status_code == 400:
            print(f"✅ Expected error: {response.json().get('error', 'Unknown error')}")
        else:
            print(f"❌ Unexpected response: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"❌ Connection error: {e}")

    print("\n🎉 Testing completed!")
    print("\n📚 Available Query Parameters:")
    print("   • date: YYYY-MM-DD (e.g., '2025-09-10')")
    print("   • start_date: ISO datetime (e.g., '2025-09-10T08:00:00')")
    print("   • end_date: ISO datetime (e.g., '2025-09-10T18:00:00')")


if __name__ == "__main__":
    test_api_endpoints()

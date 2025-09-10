# Datetime Filtering for Active Orders API

## Overview

The `/orders/active-orders/` API endpoint now supports datetime filtering to retrieve order statistics for specific time periods.

## API Endpoint

```
GET /orders/active-orders/
```

## New Query Parameters

### 1. `date` - Filter by specific date

Filter orders for a specific date (00:00:00 to 23:59:59).

**Format:** `YYYY-MM-DD`

**Example:**

```
GET /orders/active-orders/?date=2025-09-10
```

### 2. `start_date` - Filter from specific datetime

Filter orders from a specific start datetime onwards.

**Format:** ISO datetime string `YYYY-MM-DDTHH:MM:SS`

**Example:**

```
GET /orders/active-orders/?start_date=2025-09-10T08:00:00
```

### 3. `end_date` - Filter until specific datetime

Filter orders up to a specific end datetime.

**Format:** ISO datetime string `YYYY-MM-DDTHH:MM:SS`

**Example:**

```
GET /orders/active-orders/?end_date=2025-09-10T18:00:00
```

### 4. Combined Filters

You can combine `start_date` and `end_date` for a specific time range:

```
GET /orders/active-orders/?start_date=2025-09-10T08:00:00&end_date=2025-09-10T18:00:00
```

**Note:** When using the `date` parameter, `start_date` and `end_date` are ignored.

## Response Format

The API response now includes:

```json
{
  "cash_total": 150.25,
  "card_total": 200.5,
  "other_total": 50.0,
  "unpaid_total": 75.0,
  "paid_total": 400.75,
  "filters_applied": {
    "start_date": "2025-09-10T08:00:00",
    "end_date": "2025-09-10T18:00:00",
    "date": null
  }
}
```

### New Fields:

- `paid_total`: Sum of all paid amounts (cash + card + other)
- `filters_applied`: Object showing which datetime filters were applied

## Error Handling

Invalid date/datetime formats return a 400 status code with error message:

```json
{
  "error": "Invalid date format. Use YYYY-MM-DD format."
}
```

```json
{
  "error": "Invalid start_date format. Use ISO format: YYYY-MM-DDTHH:MM:SS"
}
```

## Telegram Bot Integration

The bot now includes a new button for today's orders:

- **📅 Bugünkü Sifarişlər** - Shows orders for the current date only
- **📊 Aktiv Sifarişlər** - Shows all active orders (unchanged)

## Usage Examples

### Example 1: Get today's orders

```python
import requests
from datetime import date

today = date.today().isoformat()
response = requests.get(f"http://127.0.0.1:8000/orders/active-orders/?date={today}")
data = response.json()
print(f"Today's total: {data['paid_total']:.2f} AZN")
```

### Example 2: Get orders from morning shift (8 AM - 4 PM)

```python
import requests
from datetime import date, datetime

today = date.today()
start_time = datetime.combine(today, datetime.min.time().replace(hour=8))
end_time = datetime.combine(today, datetime.min.time().replace(hour=16))

url = f"http://127.0.0.1:8000/orders/active-orders/?start_date={start_time.isoformat()}&end_date={end_time.isoformat()}"
response = requests.get(url)
data = response.json()
print(f"Morning shift total: {data['paid_total']:.2f} AZN")
```

### Example 3: Get orders for a specific week

```python
import requests
from datetime import date, timedelta

today = date.today()
week_start = today - timedelta(days=today.weekday())  # Monday
week_end = week_start + timedelta(days=6)  # Sunday

start_datetime = f"{week_start.isoformat()}T00:00:00"
end_datetime = f"{week_end.isoformat()}T23:59:59"

url = f"http://127.0.0.1:8000/orders/active-orders/?start_date={start_datetime}&end_date={end_datetime}"
response = requests.get(url)
data = response.json()
print(f"This week's total: {data['paid_total']:.2f} AZN")
```

## Backward Compatibility

All existing functionality remains unchanged. The API works without any query parameters exactly as before.

## Testing

Run the test suite to verify datetime filtering:

```bash
python manage.py test apps.orders.tests.ActiveOrdersAPITestCase
```

Or use the demonstration script:

```bash
python test_datetime_filtering.py
```

# Telegram Bot Enhanced Functionality

## Overview

The Telegram bot now provides two main options for order reports:

1. **Today's Report** - Quick access to today's order statistics
2. **Date/Time Range** - Flexible date range selection with multiple options

## Menu Structure

### Main Orders Menu (`/orders`)

```
📋 Sifariş Hesabatları

Seçimlər:
📅 Bugünkü Hesabat - Bu günün sifarişləri
📆 Tarix/Vaxt Aralığı - Seçdiyiniz dövrün sifarişləri
```

## Option 1: Today's Report

**Callback:** `today_report`
**API Call:** `GET /orders/active-orders/?date=2025-09-10`

Shows comprehensive statistics for the current date including:

- Cash payments (💵 Nağd)
- Card payments (💳 Kart)
- Other payments (🔄 Digər)
- Unpaid orders (❌ Ödənilməmiş)
- Total paid and overall totals

## Option 2: Date/Time Range Selection

**Callback:** `date_range_menu`

Provides multiple sub-options:

### Predefined Ranges

1. **Bu həftə** (`date_range_this_week`)

   - Monday to Sunday of current week
   - API: `GET /orders/active-orders/?start_date=YYYY-MM-DDTHH:MM:SS&end_date=YYYY-MM-DDTHH:MM:SS`

2. **Keçən həftə** (`date_range_last_week`)

   - Monday to Sunday of previous week
   - API: Same format as above

3. **Bu ay** (`date_range_this_month`)
   - First day to last day of current month
   - API: Same format as above

### Manual Date Entry

4. **Əl ilə daxil et** (`date_range_manual`)
   - Allows users to type custom dates
   - Supports two formats:
     - Single date: `2025-09-10`
     - Date range: `2025-09-01 2025-09-10`

## API Integration Details

### Today's Report API Call

```python
response = requests.get(f"{base_url}/orders/active-orders/?date={today}")
```

### Date Range API Call

```python
response = requests.get(
    f"{base_url}/orders/active-orders/?start_date={start_datetime}&end_date={end_datetime}"
)
```

## User Flow Examples

### Flow 1: Today's Report

```
/orders → "📅 Bugünkü Hesabat" → Display today's statistics
```

### Flow 2: This Week's Report

```
/orders → "📆 Tarix/Vaxt Aralığı" → "📅 Bu həftə" → Display week's statistics
```

### Flow 3: Manual Date Range

```
/orders → "📆 Tarix/Vaxt Aralığı" → "📝 Əl ilə daxil et" →
User types: "2025-09-01 2025-09-10" → Display custom range statistics
```

## Report Format

All reports follow the same format:

```
📅/📆 [Report Title] ([Date Range])

💰 Ödəniş Statistikası:
├ 💵 Nağd: XXX.XX AZN
├ 💳 Kart: XXX.XX AZN
├ 🔄 Digər: XXX.XX AZN
└ ❌ Ödənilməmiş: XXX.XX AZN

📊 Ümumi:
├ Ödənilmiş: XXX.XX AZN
└ Toplam: XXX.XX AZN

🔄 Yenilənmə: HH:MM:SS
```

## Error Handling

### Invalid Date Formats

- Single date: "❌ Yanlış format! Doğru format: 2025-09-10"
- Date range: "❌ Yanlış format! Doğru format: 2025-09-01 2025-09-10"

### Date Logic Errors

- Start > End: "❌ Başlanğıc tarixi bitiş tarixindən böyük ola bilməz!"

### API Errors

- Connection issues: "❌ Serverlə əlaqə yaradılmadı."
- API errors: "❌ Məlumat alınarkən xəta baş verdi."

## Technical Implementation

### State Management

- Uses `context.user_data[user_id]` to track when users are inputting manual dates
- Clears state after processing input

### Date Calculations

- **Current week:** Monday of current week to Sunday
- **Last week:** Monday of previous week to Sunday
- **Current month:** 1st day to last day of current month

### API Date Formatting

- Single dates: `YYYY-MM-DD` format
- DateTime ranges: `YYYY-MM-DDTHH:MM:SS` format (00:00:00 to 23:59:59)

## Button Navigation

### Today's Report Buttons:

- 🔄 Yenilə (Refresh) - `today_report`
- ⬅️ Geri (Back) - `main_menu`

### Date Range Report Buttons:

- 🔄 Yenilə (Refresh) - Same callback as original selection
- 📆 Başqa dövrü (Other period) - `date_range_menu`
- ⬅️ Ana menyu (Main menu) - `main_menu`

### Date Range Menu Buttons:

- 📅 Bu həftə - `date_range_this_week`
- 📅 Keçən həftə - `date_range_last_week`
- 📅 Bu ay - `date_range_this_month`
- 📝 Əl ilə daxil et - `date_range_manual`
- ⬅️ Geri - `main_menu`

## Testing the Bot

1. **Start the bot:** `/start`
2. **Access orders:** `/orders`
3. **Test today's report:** Click "📅 Bugünkü Hesabat"
4. **Test predefined ranges:** Click "📆 Tarix/Vaxt Aralığı" → Select a predefined option
5. **Test manual input:** Click "📆 Tarix/Vaxt Aralığı" → "📝 Əl ilə daxil et" → Type dates

## Backward Compatibility

The bot maintains full backward compatibility while adding new functionality. All existing features continue to work as expected.

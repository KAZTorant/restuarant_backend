# Waiter Payment Calculation Feature

## Overview
Added functionality to track and display payment calculations grouped by waiters/waitresses in the Payment Calculation admin interface.

## Changes Made

### 1. Model Changes (`apps/payments/models/payment_calculation.py`)

#### New Method: `get_waiter_payments_summary()`
- Calculates payment summaries grouped by waiter
- Returns a list of dictionaries containing:
  - `waiter_id`: The waiter's user ID
  - `waiter_name`: The waiter's full name or username
  - `total_amount`: Total amount of orders served by this waiter
  - `payment_count`: Number of payments made for this waiter's orders
  - `order_count`: Number of orders served by this waiter
  - `cash_amount`: Total cash payments
  - `card_amount`: Total card payments
  - `other_amount`: Total other payment types

**Features:**
- Handles orders without assigned waiters (labeled as "Ofisiant təyin edilməyib")
- Supports multiple payment methods per order
- Includes deleted orders in calculations
- Sorted by total amount (highest first)

### 2. Admin Interface Changes (`apps/payments/admin/payment_calculation.py`)

#### New Display Method: `waiter_payments_display()`
- Shows a comprehensive table of payments grouped by waiter
- Displays:
  - Waiter name
  - Order count per waiter
  - Payment count per waiter
  - Total amount per waiter
  - Cash, Card, and Other payment breakdowns
  - Summary totals at the bottom

**Visual Features:**
- Professional table layout with borders
- Color-coded summary row (light blue background)
- Right-aligned numbers for better readability
- Bold formatting for totals

#### Updated Fields:
- Added `waiter_payments_display` to `readonly_fields`
- Added new fieldset "Ofisiantlar üzrə ödənişlər" (Payments by Waiters)

### 3. Fieldset Organization
The Payment Calculation detail page now shows information in this order:
1. **Date and Time Information**
2. **Payment Information** (totals, cash, card, other)
3. **Creation Information** (created by, created at)
4. **🆕 Payments by Waiters** - NEW SECTION
5. **All Payments** (collapsed by default)
6. **Products Sold**

## Usage

### Viewing Waiter Payment Summary

1. Go to Django Admin: `http://127.0.0.1:8000/admin/`
2. Navigate to: **Payments → Payment Calculations**
3. Click on any existing calculation or create a new one
4. Scroll to the **"Ofisiantlar üzrə ödənişlər"** section
5. View the table showing:
   - Each waiter's performance
   - Number of orders and payments
   - Total amounts by payment type
   - Overall totals

### Understanding the Data

The waiter payment calculation:
- **Associates orders with waiters** based on the `waitress` field in the Order model
- **Tracks payment methods** (cash, card, other) for each waiter
- **Handles edge cases**:
  - Orders without assigned waiters
  - Multiple orders in one payment
  - Mixed payment methods
  - Deleted orders

### Example Output

```
Ofisiantlar üzrə ödənişlər (3 ofisiant)

┌────────────────┬──────────────┬──────────────┬──────────────┬────────┬────────┬────────┐
│ Ofisiant       │ Sifariş sayı │ Ödəniş sayı  │ Ümumi məbləğ │ Nağd   │ Kart   │ Digər  │
├────────────────┼──────────────┼──────────────┼──────────────┼────────┼────────┼────────┤
│ Əli Məmmədov   │      15      │       8      │   450.00₼    │ 200.00 │ 250.00 │  0.00  │
│ Leyla Həsənova │      12      │       6      │   380.00₼    │ 150.00 │ 230.00 │  0.00  │
│ Vüsalə İsmayıl │       8      │       4      │   250.00₼    │ 100.00 │ 150.00 │  0.00  │
├────────────────┼──────────────┼──────────────┼──────────────┼────────┼────────┼────────┤
│ CƏMI           │      35      │      18      │  1080.00₼    │ 450.00 │ 630.00 │  0.00  │
└────────────────┴──────────────┴──────────────┴──────────────┴────────┴────────┴────────┘
```

## Technical Details

### Database Queries
- Uses `prefetch_related` to optimize database queries
- Accesses deleted orders through `all_orders()` manager
- Handles many-to-many relationships between payments and orders

### Payment Method Logic
- **Single payment method**: Full amount assigned to that method
- **Multiple payment methods**: Each method's amount tracked separately
- **Waiter attribution**: Based on order's assigned waiter

### Edge Cases Handled
1. **No waiter assigned**: Grouped under "Ofisiant təyin edilməyib"
2. **Multiple waiters per payment**: Attributed to first waiter (can be enhanced)
3. **Deleted orders**: Still included in calculations
4. **No payments in period**: Shows "Ofisiant məlumatı yoxdur"

## Future Enhancements (Optional)

Possible improvements:
1. **Split payments** between multiple waiters proportionally
2. **Export to Excel** for waiter performance reports
3. **Filter by specific waiter** in the calculation form
4. **Tips tracking** separate from regular payments
5. **Performance metrics** (average order value, etc.)
6. **Date range comparison** to show trends

## Testing

To test the feature:
1. Create orders with different waiters assigned
2. Make payments for those orders
3. Create a payment calculation for the date range
4. Verify waiter summaries are accurate
5. Check totals match overall payment totals

## Files Modified

1. `/apps/payments/models/payment_calculation.py`
   - Added `get_waiter_payments_summary()` method

2. `/apps/payments/admin/payment_calculation.py`
   - Added `waiter_payments_display()` method
   - Updated `readonly_fields`
   - Updated `fieldsets`

## Date
Created: March 3, 2026

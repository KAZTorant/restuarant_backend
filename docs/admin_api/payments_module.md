# 💳 Payments Module — Admin API Documentation

> **Base URL:** `http://<host>/api/admin/payments`  
> **Authentication:** All endpoints require `X-PIN` header  
> **Permission:** Only `admin` or `restaurant` type users can access these endpoints  
> **Pagination:** All list endpoints return paginated responses (`page_size: 20`)

---

## 📋 Table of Contents

- [Authentication](#authentication)
- [Models Overview](#models-overview)
- [Data Types & Enums](#data-types--enums)
- [1. Payments (Ödəmələr)](#1-payments-ödəmələr)
  - [1.1 List Payments](#11-list-payments)
  - [1.2 Get Payment Detail](#12-get-payment-detail)
- [2. Payment Calculations (Ödəniş Hesablamaları)](#2-payment-calculations-ödəniş-hesablamaları)
  - [2.1 List Calculations](#21-list-calculations)
  - [2.2 Create Calculation](#22-create-calculation)
  - [2.3 Get Calculation Detail](#23-get-calculation-detail)
  - [2.4 Delete Calculation](#24-delete-calculation)
- [Error Responses](#error-responses)
- [Quick Reference](#quick-reference)

---

## Authentication

Every request must include the following header:

```
X-PIN: <user_pin_code>
```

The PIN is the `username` field of the User model. If the PIN is invalid or the user does not have `admin`/`restaurant` role, the API returns `403 Forbidden`.

---

## Models Overview

```
Payment  ──────────────────────────────────────────────────────────────
  ├── table          → Table (Stol)
  │     └── room     → Room  (Zal)
  ├── paid_by        → User  (Operator)
  ├── payment_methods → PaymentMethod[] (cash/card/other breakdown)
  └── orders         → Order[] (M2M)

PaymentCalculation ────────────────────────────────────────────────────
  ├── payments       → Payment[] (M2M — tarix aralığında olan ödənişlər)
  └── created_by     → User
```

| Model                | Description                                                  |
| -------------------- | ------------------------------------------------------------ |
| `Payment`            | Bir stolun ödənilmiş hesabı — dəyişdirilə bilməz (read-only) |
| `PaymentMethod`      | Ödəniş növünün parçalanması (nağd + kart + digər)            |
| `PaymentCalculation` | Seçilmiş tarix/saat aralığı üçün toplanan hesablama qeydi    |

---

## Data Types & Enums

### `payment_type`

| Value   | Display |
| ------- | ------- |
| `cash`  | Nağd    |
| `card`  | Kart    |
| `other` | Digər   |

### Date / Time formats

| Field        | Format       | Example                |
| ------------ | ------------ | ---------------------- |
| `*_date`     | `YYYY-MM-DD` | `2026-03-30`           |
| `*_time`     | `HH:MM[:SS]` | `12:00`                |
| `paid_at`    | ISO 8601     | `2026-03-31T20:45:00Z` |
| `created_at` | ISO 8601     | `2026-04-08T10:00:00Z` |

---

## 1. Payments (Ödəmələr)

> ⚠️ Payments are **read-only**. They are created automatically when a table order is paid. No `POST`, `PUT`, `PATCH` or `DELETE`.

---

### 1.1 List Payments

```
GET /api/admin/payments/payments/
```

**Query Parameters:**

| Parameter      | Type   | Required | Description                                                        |
| -------------- | ------ | -------- | ------------------------------------------------------------------ |
| `page`         | int    | No       | Page number (default: 1, page size: 20)                            |
| `payment_type` | string | No       | Filter by type: `cash`, `card`, `other`                            |
| `paid_by`      | int    | No       | Filter by operator User ID                                         |
| `table_id`     | int    | No       | Filter by table ID                                                 |
| `start_date`   | date   | No       | Filter payments on or after this date (`YYYY-MM-DD`)               |
| `end_date`     | date   | No       | Filter payments on or before this date (`YYYY-MM-DD`)              |
| `search`       | string | No       | Search in `table.number`, `table.room.name`, `paid_by.username`    |
| `ordering`     | string | No       | Sort by: `id`, `final_price`, `paid_at`. Prefix `-` for descending |

**Success Response `200 OK`:**

```json
{
  "count": 172,
  "next": "http://<host>/api/admin/payments/payments/?page=2",
  "previous": null,
  "results": [
    {
      "id": 13019,
      "table": 5,
      "table_number": "KABINET 4",
      "room_name": "VIP",
      "total_price": "10.00",
      "discount_amount": "0.00",
      "discount_comment": "",
      "final_price": "10.00",
      "paid_amount": "10.00",
      "change": "0.00",
      "payment_type": "other",
      "payment_methods": [
        {
          "id": 1,
          "payment_type": "other",
          "payment_type_display": "Digər",
          "amount": "10.00"
        }
      ],
      "paid_by": 3,
      "paid_by_name": "Sehriyar Həsənov",
      "paid_by_username": "sehriyar",
      "paid_at": "2026-03-31T21:11:00Z"
    },
    {
      "id": 13018,
      "table": 1,
      "table_number": "KABINET 1",
      "room_name": "VIP",
      "total_price": "41.50",
      "discount_amount": "0.00",
      "discount_comment": "",
      "final_price": "41.50",
      "paid_amount": "41.50",
      "change": "0.00",
      "payment_type": "cash",
      "payment_methods": [
        {
          "id": 2,
          "payment_type": "cash",
          "payment_type_display": "Nağd",
          "amount": "41.50"
        }
      ],
      "paid_by": 3,
      "paid_by_name": "Sehriyar Həsənov",
      "paid_by_username": "sehriyar",
      "paid_at": "2026-03-31T21:11:00Z"
    }
  ]
}
```

**Field Descriptions:**

| Field              | Type     | Description                                                                                 |
| ------------------ | -------- | ------------------------------------------------------------------------------------------- |
| `id`               | int      | Ödəmə ID-si                                                                                 |
| `table`            | int      | Stol ID-si                                                                                  |
| `table_number`     | string   | Stol nömrəsi (e.g. `"STOL - 1"`)                                                            |
| `room_name`        | string   | Zalın adı (e.g. `"VIP"`)                                                                    |
| `total_price`      | decimal  | Sifarişin ilkin cəmi (endirimsiz)                                                           |
| `discount_amount`  | decimal  | Tətbiq edilən endirim məbləği                                                               |
| `discount_comment` | string   | Endirim səbəbi                                                                              |
| `final_price`      | decimal  | Son ödəniləcək məbləğ (`total_price - discount_amount`)                                     |
| `paid_amount`      | decimal  | Müştərinin faktiki ödədiyi məbləğ                                                           |
| `change`           | decimal  | Qaytarılacaq pul (`paid_amount - final_price`)                                              |
| `payment_type`     | string   | Köhnə tək növ sahə — `cash`/`card`/`other` (yeni ödənişlər `payment_methods` istifadə edir) |
| `payment_methods`  | array    | Ödəniş növlərinin parçalanması (birdən çox növ ola bilər)                                   |
| `paid_by`          | int      | Operatorun User ID-si                                                                       |
| `paid_by_name`     | string   | Operatorun tam adı                                                                          |
| `paid_by_username` | string   | Operatorun istifadəçi adı (PIN)                                                             |
| `paid_at`          | datetime | Ödənişin baş verdiyi vaxt (UTC)                                                             |

**Example Requests:**

```
# Yalnız nağd ödənişlər
GET /api/admin/payments/payments/?payment_type=cash

# Tarix aralığı üzrə
GET /api/admin/payments/payments/?start_date=2026-03-30&end_date=2026-03-31

# VIP zalındakı ödənişlər
GET /api/admin/payments/payments/?search=VIP

# Sehriyar operatorunun ödənişləri (user id=3)
GET /api/admin/payments/payments/?paid_by=3

# Ən böyük məbləğdən kiçiyə sırala
GET /api/admin/payments/payments/?ordering=-final_price

# Kombinasiya
GET /api/admin/payments/payments/?start_date=2026-03-31&payment_type=cash&ordering=-paid_at&page=1
```

---

### 1.2 Get Payment Detail

```
GET /api/admin/payments/payments/{id}/
```

**Path Parameters:**

| Parameter | Type | Description |
| --------- | ---- | ----------- |
| `id`      | int  | Ödəmə ID-si |

**Success Response `200 OK`:**

```json
{
  "id": 13010,
  "table": 2,
  "table_number": "STOL - 7",
  "room_name": "Zal1 1-20",
  "total_price": "18.50",
  "discount_amount": "0.00",
  "discount_comment": "",
  "final_price": "18.50",
  "paid_amount": "18.50",
  "change": "0.00",
  "payment_type": null,
  "payment_methods": [
    {
      "id": 10,
      "payment_type": "cash",
      "payment_type_display": "Nağd",
      "amount": "0.50"
    },
    {
      "id": 11,
      "payment_type": "card",
      "payment_type_display": "Kart",
      "amount": "18.00"
    }
  ],
  "paid_by": 3,
  "paid_by_name": "Sehriyar Həsənov",
  "paid_by_username": "sehriyar",
  "paid_at": "2026-03-31T18:22:00Z",
  "orders": [
    {
      "id": 13531,
      "total_price": "10.00",
      "waitress_id": 4,
      "waitress_name": "Aynur Məmmədova",
      "items": [
        {
          "id": 9801,
          "meal_id": 55,
          "meal_name": "Ekstra 10",
          "quantity": 1,
          "unit_price": "10.00",
          "total_price": "10.00",
          "comment": null
        }
      ]
    },
    {
      "id": 13532,
      "total_price": "8.50",
      "waitress_id": 4,
      "waitress_name": "Aynur Məmmədova",
      "items": [
        {
          "id": 9802,
          "meal_id": 12,
          "meal_name": "Çay",
          "quantity": 2,
          "unit_price": "2.00",
          "total_price": "4.00",
          "comment": null
        },
        {
          "id": 9803,
          "meal_id": 28,
          "meal_name": "Su 0.5L",
          "quantity": 3,
          "unit_price": "1.50",
          "total_price": "4.50",
          "comment": "Soyuq olsun"
        }
      ]
    }
  ]
}
```

**`orders` array field descriptions:**

| Field           | Type    | Description                              |
| --------------- | ------- | ---------------------------------------- |
| `id`            | int     | Sifariş ID-si                            |
| `total_price`   | decimal | Sifarişin ümumi məbləği                  |
| `waitress_id`   | int     | Ofisiantın User ID-si (`null` ola bilər) |
| `waitress_name` | string  | Ofisiantın adı (`null` ola bilər)        |
| `items`         | array   | Sifarişdəki məhsullar (aşağıya bax)      |

**`items` array field descriptions:**

| Field         | Type    | Description                                          |
| ------------- | ------- | ---------------------------------------------------- |
| `id`          | int     | OrderItem ID-si                                      |
| `meal_id`     | int     | Yeməyin ID-si                                        |
| `meal_name`   | string  | Yeməyin adı (e.g. `"Ekstra 10"`, `"Çay"`)            |
| `quantity`    | int     | Miqdar                                               |
| `unit_price`  | decimal | Vahid qiyməti (`total_price / quantity`)             |
| `total_price` | decimal | Bu maddənin ümumi qiyməti                            |
| `comment`     | string  | Xüsusi qeyd (`null` ola bilər, e.g. `"Soyuq olsun"`) |

---

## 2. Payment Calculations (Ödəniş Hesablamaları)

Müəyyən tarix və saat aralığındakı bütün ödənişləri toplayan hesablama qeydləri.

---

### 2.1 List Calculations

```
GET /api/admin/payments/calculations/
```

**Query Parameters:**

| Parameter    | Type | Required | Description                                                  |
| ------------ | ---- | -------- | ------------------------------------------------------------ |
| `page`       | int  | No       | Page number (default: 1, page size: 20)                      |
| `created_by` | int  | No       | Filter by creator User ID                                    |
| `start_date` | date | No       | Filter: hesablamanın `start_date` >= bu tarix (`YYYY-MM-DD`) |
| `end_date`   | date | No       | Filter: hesablamanın `end_date` <= bu tarix (`YYYY-MM-DD`)   |

**Success Response `200 OK`:**

```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 198,
      "start_date": "2026-03-30",
      "end_date": "2026-03-31",
      "start_time": "12:00:00",
      "end_time": "23:59:00",
      "date_range_display": "30.03.2026 - 31.03.2026",
      "time_range_display": "12:00 - 23:59",
      "total_amount": "2349.10",
      "total_paid": "2505.10",
      "payment_count": 172,
      "cash_amount": "1508.60",
      "card_amount": "697.00",
      "other_amount": "299.50",
      "extra_paid_amount": "156.00",
      "created_by": 1,
      "created_by_username": "devUser",
      "created_at": "2026-04-08T23:07:00Z"
    }
  ]
}
```

**Field Descriptions:**

| Field                 | Type     | Description                                                                    |
| --------------------- | -------- | ------------------------------------------------------------------------------ |
| `id`                  | int      | Hesablama ID-si                                                                |
| `start_date`          | date     | Aralığın başlanğıc tarixi                                                      |
| `end_date`            | date     | Aralığın son tarixi                                                            |
| `start_time`          | time     | Başlanğıc saatı                                                                |
| `end_time`            | time     | Son saatı                                                                      |
| `date_range_display`  | string   | İnsan oxunaqlı tarix aralığı (e.g. `"30.03.2026 - 31.03.2026"`)                |
| `time_range_display`  | string   | İnsan oxunaqlı saat aralığı (e.g. `"12:00 - 23:59"`)                           |
| `total_amount`        | decimal  | Sifarişlərin son qiyməti cəmi (`final_price` cəmi)                             |
| `total_paid`          | decimal  | Faktiki ödənilən cəm (`cash + card + other`)                                   |
| `payment_count`       | int      | Aralıqdakı ödəniş sayı                                                         |
| `cash_amount`         | decimal  | Nağd ödənişlər cəmi                                                            |
| `card_amount`         | decimal  | Kart ödənişlər cəmi                                                            |
| `other_amount`        | decimal  | Digər ödənişlər cəmi                                                           |
| `extra_paid_amount`   | decimal  | Əlavə ödənilən məbləğ — `total_paid - total_amount` (bahşiş, dəyişiklik və s.) |
| `created_by`          | int      | Yaradan istifadəçinin ID-si                                                    |
| `created_by_username` | string   | Yaradan istifadəçinin adı                                                      |
| `created_at`          | datetime | Hesablamanın yaradılma vaxtı                                                   |

---

### 2.2 Create Calculation

```
POST /api/admin/payments/calculations/
```

**Request Body:**

```json
{
  "start_date": "2026-03-30",
  "end_date": "2026-03-31",
  "start_time": "12:00",
  "end_time": "23:59"
}
```

| Field        | Type | Required | Description                                   |
| ------------ | ---- | -------- | --------------------------------------------- |
| `start_date` | date | ✅ Yes   | Aralığın başlanğıc tarixi (`YYYY-MM-DD`)      |
| `end_date`   | date | ✅ Yes   | Aralığın son tarixi (`YYYY-MM-DD`)            |
| `start_time` | time | No       | Başlanğıc saatı (`HH:MM`). Default: `"12:00"` |
| `end_time`   | time | No       | Son saatı (`HH:MM`). Default: `"23:59"`       |

> **Məntiqi:** Backend həmin tarix+saat aralığındakı bütün `Payment`-ləri tapır, `cash/card/other` cəmlərini hesablayır, `PaymentCalculation` qeydi yaradır və ödənişləri ona bağlayır. **Eyni aralıq üçün dəfələrlə yaratmaq olar.**

**Validation Qaydaları:**

| Şərt                                        | Xəta sahəsi | Mesaj                                              |
| ------------------------------------------- | ----------- | -------------------------------------------------- |
| `end_date` < `start_date`                   | `end_date`  | `"Son tarix başlanğıc tarixdən əvvəl ola bilməz."` |
| Eyni gün olduqda `end_time` <= `start_time` | `end_time`  | `"Son saat başlanğıc saatdan əvvəl ola bilməz."`   |

**Success Response `201 Created`:**

```json
{
  "id": 199,
  "start_date": "2026-03-30",
  "end_date": "2026-03-31",
  "start_time": "12:00:00",
  "end_time": "23:59:00",
  "date_range_display": "30.03.2026 - 31.03.2026",
  "time_range_display": "12:00 - 23:59",
  "total_amount": "2349.10",
  "total_paid": "2505.10",
  "payment_count": 172,
  "cash_amount": "1508.60",
  "card_amount": "697.00",
  "other_amount": "299.50",
  "extra_paid_amount": "156.00",
  "created_by": 1,
  "created_by_username": "devUser",
  "created_at": "2026-04-08T10:30:00Z"
}
```

**Validation Error `400 Bad Request`:**

```json
{
  "end_date": ["Son tarix başlanğıc tarixdən əvvəl ola bilməz."]
}
```

---

### 2.3 Get Calculation Detail

```
GET /api/admin/payments/calculations/{id}/
```

**Path Parameters:**

| Parameter | Type | Description     |
| --------- | ---- | --------------- |
| `id`      | int  | Hesablama ID-si |

**Success Response `200 OK`:**

```json
{
  "id": 199,
  "start_date": "2026-03-29",
  "end_date": "2026-03-31",
  "start_time": "12:00:00",
  "end_time": "23:59:00",
  "date_range_display": "29.03.2026 - 31.03.2026",
  "time_range_display": "12:00 - 23:59",
  "total_amount": "3571.60",
  "total_paid": "3852.60",
  "payment_count": 245,
  "cash_amount": "2202.60",
  "card_amount": "979.50",
  "other_amount": "670.50",
  "extra_paid_amount": "281.00",
  "created_by": 1,
  "created_by_username": "devUser",
  "created_at": "2026-04-08T23:32:00Z",

  "payments": [
    {
      "id": 12778,
      "table_number": "STOL - 36",
      "final_price": "15.50",
      "paid_amount": "15.50",
      "payment_methods": [
        {
          "payment_type": "cash",
          "payment_type_display": "Nağd",
          "amount": "15.50"
        }
      ],
      "operator_username": "5050",
      "paid_at": "29.03.2026 13:23"
    },
    {
      "id": 12782,
      "table_number": "STOL - 29",
      "final_price": "39.00",
      "paid_amount": "40.00",
      "payment_methods": [
        {
          "payment_type": "cash",
          "payment_type_display": "Nağd",
          "amount": "40.00"
        }
      ],
      "operator_username": "5050",
      "paid_at": "29.03.2026 14:32"
    }
  ],

  "waiter_summary": [
    {
      "waiter_id": 5,
      "waiter_name": "Elizamin",
      "order_count": 73,
      "payment_count": 73,
      "total_amount": "1083.50",
      "cash_amount": "847.50",
      "card_amount": "246.50",
      "other_amount": "174.50"
    },
    {
      "waiter_id": 7,
      "waiter_name": "Rusif .",
      "order_count": 40,
      "payment_count": 40,
      "total_amount": "677.00",
      "cash_amount": "253.50",
      "card_amount": "250.50",
      "other_amount": "210.50"
    }
  ],

  "product_summary": [
    {
      "meal_name": "SET 19",
      "quantity": 27,
      "total_amount": "513.00"
    },
    {
      "meal_name": "Yemek 5.5",
      "quantity": 84,
      "total_amount": "462.00"
    },
    {
      "meal_name": "CASKA 9",
      "quantity": 39,
      "total_amount": "351.00"
    }
  ]
}
```

---

#### `payments` array — field descriptions

| Field               | Type    | Description                                                                   |
| ------------------- | ------- | ----------------------------------------------------------------------------- |
| `id`                | int     | Ödəmə ID-si                                                                   |
| `table_number`      | string  | Stolun nömrəsi (e.g. `"STOL - 36"`)                                           |
| `final_price`       | decimal | Son məbləğ (endirimdən sonra)                                                 |
| `paid_amount`       | decimal | Müştərinin faktiki ödədiyi məbləğ                                             |
| `payment_methods`   | array   | Ödəniş növlərinin siyahısı (`payment_type`, `payment_type_display`, `amount`) |
| `operator_username` | string  | Əməliyyatı aparan operatorun adı                                              |
| `paid_at`           | string  | Ödəniş tarixi/saatı (format: `"DD.MM.YYYY HH:MM"`)                            |

---

#### `waiter_summary` array — field descriptions

| Field           | Type    | Description                              |
| --------------- | ------- | ---------------------------------------- |
| `waiter_id`     | int     | Ofisiantın User ID-si (`null` ola bilər) |
| `waiter_name`   | string  | Ofisiantın adı                           |
| `order_count`   | int     | Sifariş sayı                             |
| `payment_count` | int     | Ödəniş sayı                              |
| `total_amount`  | decimal | Ümumi məbləğ                             |
| `cash_amount`   | decimal | Nağd hissə                               |
| `card_amount`   | decimal | Kart hissə                               |
| `other_amount`  | decimal | Digər hissə                              |

> Sıralama: `total_amount` azalan sıra. Sonuncu sıra avtomatik olaraq bütün ofisiantların CƏMİ deyil — Flutter tərəfdə cəm hesablanmalıdır.

---

#### `product_summary` array — field descriptions

| Field          | Type    | Description                   |
| -------------- | ------- | ----------------------------- |
| `meal_name`    | string  | Yeməyin adı (e.g. `"SET 19"`) |
| `quantity`     | int     | Ümumi satış miqdarı           |
| `total_amount` | decimal | Ümumi satış məbləği           |

> Sıralama: `total_amount` azalan sıra (ən çox gəlir gətirən yemək birinci).

---

### 2.4 Delete Calculation

```
DELETE /api/admin/payments/calculations/{id}/
```

> ⚠️ **Yalnız `superuser` silə bilər.** Admin/restaurant rollu istifadəçilər `403` alacaq.

**Success Response `204 No Content`**

**Error — Not superuser `403 Forbidden`:**

```json
{
  "detail": "Yalnız superuser hesablamanı silə bilər."
}
```

**Error — Not found `404 Not Found`:**

```json
{
  "detail": "Hesablama tapılmadı."
}
```

---

## Error Responses

### Authentication Error `401`

```json
{
  "detail": "No such user"
}
```

### Permission Error `403`

```json
{
  "detail": "Bu endpointe girişiniz yoxdur. Admin, Restaurant, Superuser və ya Staff olmalısınız."
}
```

### Not Found `404`

```json
{
  "detail": "No Payment matches the given query."
}
```

### Validation Error `400`

```json
{
  "end_date": ["Son tarix başlanğıc tarixdən əvvəl ola bilməz."]
}
```

---

## Quick Reference

| Method   | Endpoint                                 | Permission         | Action                                              |
| -------- | ---------------------------------------- | ------------------ | --------------------------------------------------- |
| `GET`    | `/api/admin/payments/payments/`          | admin / restaurant | List payments (filter + search + pagination)        |
| `GET`    | `/api/admin/payments/payments/{id}/`     | admin / restaurant | Get payment detail (orders + items)                 |
| `GET`    | `/api/admin/payments/calculations/`      | admin / restaurant | List calculations (pagination + filter)             |
| `POST`   | `/api/admin/payments/calculations/`      | admin / restaurant | Create new calculation for date/time range          |
| `GET`    | `/api/admin/payments/calculations/{id}/` | admin / restaurant | Get calculation detail (payments + waiters + meals) |
| `DELETE` | `/api/admin/payments/calculations/{id}/` | **superuser only** | Delete calculation                                  |

---

## Flutter Integration Notes

### Decimal fields

Bütün pul sahələri (`total_price`, `final_price`, `cash_amount` və s.) **string** kimi gəlir.
Flutter-də parse edin:

```dart
final amount = double.parse(json['final_price']);
```

### Pagination loop

Bütün səhifələri yükləmək üçün:

```dart
while (nextUrl != null) {
  final response = await api.get(nextUrl);
  nextUrl = response['next'];
  items.addAll(response['results']);
}
```

### `payment_type` vs `payment_methods`

- Yeni ödənişlər həmişə `payment_methods` array-i dolduracaq, `payment_type` `null` ola bilər.
- Köhnə ödənişlər `payment_type` sahəsini istifadə edər, `payment_methods` boş ola bilər.
- **Tövsiyə:** Əvvəlcə `payment_methods.isNotEmpty` yoxlayın, boşdursa `payment_type`-a baxın.

```dart
String getPaymentDisplay(Payment p) {
  if (p.paymentMethods.isNotEmpty) {
    return p.paymentMethods
        .map((m) => '${m.paymentTypeDisplay}: ${m.amount}₼')
        .join(', ');
  }
  return '${p.paymentType}: ${p.paidAmount}₼';
}
```

### Calculation detail — 3 tab

`GET /api/admin/payments/calculations/{id}/` cavabında **3 ayrı blok** gəlir:

```dart
// Tab 1 — Ödənişlər
final payments = data['payments'] as List;

// Tab 2 — Ofisiantlar üzrə
final waiterSummary = data['waiter_summary'] as List;

// Tab 3 — Satılan məhsullar
final productSummary = data['product_summary'] as List;
```

### `waiter_summary` — CƏM sırası

Backend CƏM sırası göndərmir. Flutter tərəfdə hesabla:

```dart
final total = waiterSummary.fold(0.0,
  (sum, w) => sum + double.parse(w['total_amount']));
```

### `extra_paid_amount` (Əlavə ödənilmiş)

Müştərinin `final_price`-dan artıq ödədiyi məbləğ (bahşiş, dəyişiklik qalığı).

```dart
if (calculation.extraPaidAmount > 0) {
  // Göstər: "+281.00₼ Əlavə"
}
```

```
DELETE /api/admin/payments/calculations/{id}/
```

> ⚠️ **Yalnız `superuser` silə bilər.** Admin/restaurant rollu istifadəçilər `403` alacaq.

**Success Response `204 No Content`**

**Error — Not superuser `403 Forbidden`:**

```json
{
  "detail": "Yalnız superuser hesablamanı silə bilər."
}
```

**Error — Not found `404 Not Found`:**

```json
{
  "detail": "Hesablama tapılmadı."
}
```

---

## Error Responses

### Authentication Error `401`

```json
{
  "detail": "No such user"
}
```

### Permission Error `403`

```json
{
  "detail": "Bu endpointe girişiniz yoxdur. Admin, Restaurant, Superuser və ya Staff olmalısınız."
}
```

### Not Found `404`

```json
{
  "detail": "No Payment matches the given query."
}
```

### Validation Error `400`

```json
{
  "end_date": ["Son tarix başlanğıc tarixdən əvvəl ola bilməz."]
}
```

---

## Quick Reference

| Method   | Endpoint                                 | Permission         | Action                                       |
| -------- | ---------------------------------------- | ------------------ | -------------------------------------------- |
| `GET`    | `/api/admin/payments/payments/`          | admin / restaurant | List payments (filter + search + pagination) |
| `GET`    | `/api/admin/payments/payments/{id}/`     | admin / restaurant | Get payment detail (with `order_ids`)        |
| `GET`    | `/api/admin/payments/calculations/`      | admin / restaurant | List calculations (pagination + filter)      |
| `POST`   | `/api/admin/payments/calculations/`      | admin / restaurant | Create new calculation for date/time range   |
| `GET`    | `/api/admin/payments/calculations/{id}/` | admin / restaurant | Get calculation detail (with `payment_ids`)  |
| `DELETE` | `/api/admin/payments/calculations/{id}/` | **superuser only** | Delete calculation                           |

---

## Flutter Integration Notes

### Decimal fields

Bütün pul sahələri (`total_price`, `final_price`, `cash_amount` və s.) **string** kimi gəlir.  
Flutter-də parse edin:

```dart
final amount = double.parse(json['final_price']);
```

### Pagination loop

Bütün səhifələri yükləmək üçün:

```dart
while (nextUrl != null) {
  final response = await api.get(nextUrl);
  nextUrl = response['next'];
  items.addAll(response['results']);
}
```

### `payment_type` vs `payment_methods`

- Yeni ödənişlər həmişə `payment_methods` array-i dolduracaq, `payment_type` `null` ola bilər.
- Köhnə ödənişlər `payment_type` sahəsini istifadə edər, `payment_methods` boş ola bilər.
- **Tövsiyə:** Əvvəlcə `payment_methods.isNotEmpty` yoxlayın, boşdursa `payment_type`-a baxın.

```dart
String getPaymentDisplay(Payment p) {
  if (p.paymentMethods.isNotEmpty) {
    return p.paymentMethods
        .map((m) => '${m.paymentTypeDisplay}: ${m.amount}₼')
        .join(', ');
  }
  return '${p.paymentType}: ${p.paidAmount}₼';
}
```

### `extra_paid_amount` (Əlavə ödənilmiş)

Müştərinin `final_price`-dan artıq ödədiyi məbləğ (bahşiş, dəyişiklik qalığı). UI-da göstərmək üçün:

```dart
if (calculation.extraPaidAmount > 0) {
  // Göstər: "+156.00₼ Əlavə"
}
```

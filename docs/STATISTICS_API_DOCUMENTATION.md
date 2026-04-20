# Statistics/Hesabatlar API Documentation

Bu sənəd Statistics (Hesabatlar) modulu üçün mövcud olan bütün API endpoint-ləri təsvir edir. Bu API-lər Django admin panelində istifadə olunan funksionallığı təmin edir və Flutter tətbiqi üçün nəzərdə tutulub.

## Base URL

```
/api/orders/statistics/
```

## Authentication

Bütün endpoint-lər authentication tələb edir. Header-də Bearer token göndərilməlidir:

```
Authorization: Bearer <your_token>
```

---

## 1. Hesabatlar Siyahısı (Statistics List)

**Endpoint:** `GET /api/orders/statistics/`

**Təsvir:** Bütün shift-ləri/hesabatları siyahı şəklində göstərir. Filter və sort funksionallığı dəstəklənir.

### Query Parameters:

- `start_date` (optional): Başlanma tarixindən filter (YYYY-MM-DD)
- `end_date` (optional): Bitmə tarixinə qədər filter (YYYY-MM-DD)
- `is_closed` (optional): Bağlı/Açıq statusuna görə filter (true/false)
- `started_by` (optional): Növbəni açan istifadəçi adına görə filter
- `ordering` (optional): Sort parametri (-start_time, end_time, total, date)

### Request Example:

```http
GET /api/orders/statistics/?is_closed=false&ordering=-start_time
```

### Response Example:

```json
[
  {
    "id": 267,
    "started_by_username": "Sheriyar",
    "started_by_full_name": "Sheriyar AdminPanel",
    "start_time": "2026-03-30T19:01:00Z",
    "ended_by_username": "Sheriyar",
    "ended_by_full_name": "Sheriyar AdminPanel",
    "end_time": "2026-03-31T09:43:00Z",
    "shift_duration": 14.7,
    "total": "14534.14",
    "cash_total": "15240.14",
    "card_total": "0.00",
    "other_total": "0.00",
    "withdrawn_amount": "936.58",
    "withdrawn_from_card": "0.00",
    "withdrawn_from_other": "0.00",
    "remaining_cash": "11333.20",
    "remaining_card": "2970.36",
    "remaining_other": "0.00",
    "is_closed": true,
    "status": "Bağlandı",
    "date": "2026-03-31"
  }
]
```

### Response Fields:

- `id`: Hesabat ID-si
- `started_by_username`: Növbəni açan istifadəçinin username-i
- `started_by_full_name`: Növbəni açan istifadəçinin tam adı
- `start_time`: Növbənin başlanma vaxtı (ISO 8601)
- `ended_by_username`: Növbəni bağlayan istifadəçinin username-i
- `ended_by_full_name`: Növbəni bağlayan istifadəçinin tam adı
- `end_time`: Növbənin bitmə vaxtı (ISO 8601, null ola bilər)
- `shift_duration`: Növbənin müddəti (saat)
- `total`: Ümumi məbləğ
- `cash_total`: Növbə ərzində nağd qazanc
- `card_total`: Növbə ərzində kart qazancı
- `other_total`: Növbə ərzində digər ödənişlər
- `withdrawn_amount`: Çəkilən nağd məbləğ
- `withdrawn_from_card`: Kartdan çəkilən məbləğ
- `withdrawn_from_other`: Digər ödənişlərdən çəkilən məbləğ
- `remaining_cash`: Qalan nağd
- `remaining_card`: Qalan kart
- `remaining_other`: Qalan digər ödənişlər
- `is_closed`: Növbə bağlanıbmı (boolean)
- `status`: Status text (Açıq/Bağlandı)
- `date`: Tarix

### Performance Optimization:

- `select_related('started_by', 'ended_by')` istifadə olunur
- `prefetch_related('orders')` istifadə olunur
- Database query-lər minimal səviyyədədir

---

## 2. Hesabat Detalları (Statistics Detail)

**Endpoint:** `GET /api/orders/statistics/<shift_id>/`

**Təsvir:** Konkret hesabatın bütün tab-larındakı məlumatları göstərir. Django admin-də görünən bütün məlumatları ehtiva edir.

### Path Parameters:

- `shift_id`: Hesabat ID-si (integer)

### Request Example:

```http
GET /api/orders/statistics/267/
```

### Response Example:

```json
{
  "ümumi_məlumat": {
    "başlıq": "Hesabat",
    "ümumi_məbləğ": "14534.14",
    "tarix": "2026-03-31",
    "hesabat_təsdiqləndi": true
  },
  "mabləğlər": {
    "başlanğıc_nağd": "14534.14",
    "başlanğıc_kart": "0.00",
    "başlanğıc_digər": "0.00",
    "nağd_qazanılmış": "15240.14",
    "kart_ümumi": "0.00",
    "digər_ödənişlər": "0.00",
    "çıxarılan_nağd": "936.58",
    "çıxarılan_kart": "0.00",
    "çıxarılan_digər": "0.00",
    "qalan_nağd": "11333.20",
    "qalan_kart": "2970.36",
    "qalan_digər": "0.00",
    "ümumi_əldə_olan_nağd": "29774.28",
    "ümumi_çıxarılan": "936.58"
  },
  "növbə_detalları": {
    "növbəni_açan": {
      "istifadəçi_adı": "Sheriyar",
      "tam_ad": "Sheriyar AdminPanel"
    },
    "başlanma_vaxtı": "2026-03-30T19:01:00Z",
    "növbəni_bağlayan": {
      "istifadəçi_adı": "Sheriyar",
      "tam_ad": "Sheriyar AdminPanel"
    },
    "bitmə_vaxtı": "2026-03-31T09:43:00Z",
    "növbə_bağlandı": true,
    "növbə_müddəti_saat": 14.7,
    "başlanma_qeydi": "",
    "bağlanma_qeydi": "maas-35\nrasxod nəqd-91"
  },
  "qeydlər_və_hesabatlar": {
    "bağlanma_qeydi": {
      "bağlanma_qeydi": "maas-35\nrasxod nəqd-91",
      "başlanma_qeydi": "",
      "display_per_waitress": [
        {
          "ofisiant": "Aresh",
          "ümumi_məbləğ": "145.50 AZN",
          "sifariş_sayı": 3
        },
        {
          "ofisiant": "Elizamin",
          "ümumi_məbləğ": "56.00 AZN",
          "sifariş_sayı": 2
        },
        {
          "ofisiant": "Resad",
          "ümumi_məbləğ": "86.50 AZN",
          "sifariş_sayı": 4
        },
        {
          "ofisiant": "Sehriyar",
          "ümumi_məbləğ": "77.60 AZN",
          "sifariş_sayı": 5
        },
        {
          "ofisiant": "Togrul Gece",
          "ümumi_məbləğ": "168.50 AZN",
          "sifariş_sayı": 6
        }
      ]
    },
    "ofisiantların_xidməti": [
      {
        "ofisiant": "Aresh",
        "ümumi_məbləğ": "145.50 AZN",
        "sifariş_sayı": 3
      }
    ],
    "sifariş_məhsulları_xülasəsi": [
      {
        "yemək": "Çay",
        "say": 25,
        "vahid_qiymət": "2.00 AZN",
        "ümumi": "50.00 AZN"
      },
      {
        "yemək": "Qəhvə",
        "say": 15,
        "vahid_qiymət": "3.50 AZN",
        "ümumi": "52.50 AZN"
      }
    ]
  },
  "statistics_order_əlaqələri": [
    {
      "id": 13408,
      "stol": "STOL - 3 | Qrazi VIP",
      "məbləğ": "11.50 AZN",
      "ödənilib": true,
      "yaradılma_tarixi": "2026-03-30T21:39:55Z"
    },
    {
      "id": 13406,
      "stol": "STOL - 39 | Qrazi Zal2 20-40",
      "məbləğ": "21.00 AZN",
      "ödənilib": true,
      "yaradılma_tarixi": "2026-03-30T21:26:50Z"
    }
  ]
}
```

### Response Structure:

#### 1. `ümumi_məlumat` (General Information Tab)

Django admin-də "Ümumi Məlumat" tab-ının məlumatları.

#### 2. `mabləğlər` (Amounts Tab)

Django admin-də "Mabləğlər" tab-ının məlumatları. Bütün maliyyə məlumatları.

#### 3. `növbə_detalları` (Shift Details Tab)

Django admin-də "Nöbvə Detalları" tab-ının məlumatları. Kim açıb, kim bağlayıb, vaxtlar.

#### 4. `qeydlər_və_hesabatlar` (Notes and Reports Tab)

Django admin-də "Qeydlər və Hesabatlar" tab-ının məlumatları:

- Bağlanma qeydi
- Ofisiantların xidməti statistikası
- Sifariş məhsulları xülasəsi

#### 5. `statistics_order_əlaqələri` (Statistics-Order Relations Tab)

Django admin-də "Statistics-order əlaqələri" tab-ının məlumatları. Hesabata aid olan sifarişlər.

### Performance Optimization:

- Açıq shift üçün avtomatik olaraq `calculate_till_now` çağırılır
- Bütün əlaqəli məlumatlar bir query-də çəkilir:
  - `select_related('started_by', 'ended_by')`
  - `prefetch_related('orders', 'orders__table', 'orders__waitress', 'orders__order_items', 'orders__order_items__meal')`

---

## 3. Cari Növbə (Current Shift)

**Endpoint:** `GET /api/orders/statistics/current-shift/`

**Təsvir:** Cari istifadəçinin aktiv növbəsini qaytarır. Növbə məlumatlarını real-time olaraq yeniləyir.

### Request Example:

```http
GET /api/orders/statistics/current-shift/
```

### Response Example (Success):

```json
{
  "shift_id": 267,
  "cash_total": "15240.14",
  "card_total": "0.00",
  "other_total": "0.00",
  "total": "14534.14",
  "cash_in_hand": "29774.28",
  "card_in_hand": "0.00",
  "other_in_hand": "0.00",
  "initial_cash": "14534.14",
  "initial_card": "0.00",
  "initial_other": "0.00",
  "started_by": "Sheriyar",
  "start_time": "2026-03-30T19:01:00Z",
  "notes": ""
}
```

### Response Example (No Active Shift):

```json
{
  "error": "Aktiv növbə tapılmadı"
}
```

Status Code: 404

### Response Fields:

- `shift_id`: Cari növbənin ID-si
- `cash_total`: Növbə ərzində nağd qazanc
- `card_total`: Növbə ərzində kart qazancı
- `other_total`: Növbə ərzində digər ödənişlər
- `total`: Ümumi məbləğ
- `cash_in_hand`: Əldə olan ümumi nağd (başlanğıc + qazanc)
- `card_in_hand`: Əldə olan ümumi kart
- `other_in_hand`: Əldə olan ümumi digər ödənişlər
- `initial_cash`: Başlanğıc nağd
- `initial_card`: Başlanğıc kart
- `initial_other`: Başlanğıc digər ödənişlər
- `started_by`: Növbəni açan istifadəçi
- `start_time`: Başlanma vaxtı
- `notes`: Başlanma qeydi

### Auto-Refresh:

Bu endpoint çağırılanda avtomatik olaraq `calculate_till_now` işə düşür və məlumatlar yenilənir.

---

## 4. Növbə Başlatma Məlumatları (Start Shift Info)

**Endpoint:** `GET /api/orders/statistics/start-shift-info/`

**Təsvir:** Yeni növbə başlatmaq üçün təklif olunan başlanğıc məbləğləri göstərir. Son bağlanmış növbənin qalan məbləğlərini qaytarır.

### Request Example:

```http
GET /api/orders/statistics/start-shift-info/
```

### Response Example:

```json
{
  "initial_cash": "11333.20",
  "initial_card": "2970.36",
  "initial_other": "0.00"
}
```

### Response Fields:

- `initial_cash`: Təklif olunan başlanğıc nağd (son növbənin qalan nağdı)
- `initial_card`: Təklif olunan başlanğıc kart
- `initial_other`: Təklif olunan başlanğıc digər ödənişlər

### Use Case:

Yeni növbə açarkən, istifadəçiyə avtomatik olaraq öncəki növbənin qalan məbləğlərini göstərmək üçün istifadə olunur.

---

## 5. Növbə Başlatma (Start Shift)

**Endpoint:** `POST /api/orders/statistics/start-shift/`

**Təsvir:** Yeni növbə açır. Başlanğıc məbləğləri və qeydləri qəbul edir.

### Request Body:

```json
{
  "initial_cash": "11333.20",
  "initial_card": "2970.36",
  "initial_other": "0.00",
  "notes": "Səhər növbəsi"
}
```

### Request Fields:

- `initial_cash` (optional): Başlanğıc nağd məbləğ (default: 0)
- `initial_card` (optional): Başlanğıc kart məbləğ (default: 0)
- `initial_other` (optional): Başlanğıc digər ödəniş məbləği (default: 0)
- `notes` (optional): Başlanma qeydi

### Response Example (Success):

```json
{
  "message": "Növbə açıldı (Başlanğıc: Nağd 11333.20 AZN, Kart 2970.36 AZN, Digər 0.00 AZN)",
  "shift_id": 268,
  "initial_cash": "11333.20",
  "initial_card": "2970.36",
  "initial_other": "0.00",
  "start_time": "2026-04-20T10:00:00Z"
}
```

Status Code: 201

### Response Example (Error - Already Open Shift):

```json
{
  "error": "Açıq növbən var."
}
```

Status Code: 400

### Validation:

- İstifadəçinin artıq açıq növbəsi varsa, xəta qaytarır
- Başlanğıc məbləğlər mənfi ola bilməz

---

## 6. Növbə Bağlama (End Shift)

**Endpoint:** `POST /api/orders/statistics/<shift_id>/end-shift/`

**Təsvir:** Mövcud növbəni bağlayır. Çəkilən məbləğləri və qeydləri qəbul edir.

### Path Parameters:

- `shift_id`: Bağlanacaq növbənin ID-si

### Request Body:

```json
{
  "withdrawn_amount": "936.58",
  "withdrawn_from_card": "0.00",
  "withdrawn_from_other": "0.00",
  "withdrawn_notes": "maas-35\nrasxod nəqd-91"
}
```

### Request Fields:

- `withdrawn_amount` (optional): Çəkilən nağd məbləğ (default: 0)
- `withdrawn_from_card` (optional): Kartdan çəkilən məbləğ (default: 0)
- `withdrawn_from_other` (optional): Digər ödənişlərdən çəkilən məbləğ (default: 0)
- `withdrawn_notes` (optional): Bağlanma qeydi

### Response Example (Success):

```json
{
  "message": "Növbə bağlandı. Qalan nağd: 11333.20 AZN. Ümumi çəkilən: 936.58 AZN",
  "shift_id": 267,
  "remaining_cash": "11333.20",
  "remaining_card": "2970.36",
  "remaining_other": "0.00",
  "total_withdrawn": "936.58",
  "end_time": "2026-03-31T09:43:00Z"
}
```

Status Code: 200

### Response Example (Error - Not Found):

```json
{
  "error": "Növbə tapılmadı"
}
```

Status Code: 404

### Response Example (Error - Validation):

```json
{
  "error": "Çıxarılan nağd məbləğ mövcud nağd məbləği ötə bilməz. 1000.00 > 500.00"
}
```

Status Code: 400

### Validation:

- Növbəni yalnız açan istifadəçi bağlaya bilər
- Növbə artıq bağlanıbsa, xəta qaytarır
- Çəkilən məbləğ mövcud məbləğdən çox ola bilməz (hər ödəniş tipi üçün ayrıca)
- Növbə bağlananda bütün sifarişlər `is_deleted=True` olaraq işarələnir

---

## 7. Aktiv Sifarişlər Statistikası (Active Orders Stats)

**Endpoint:** `GET /api/orders/statistics/active-orders-stats/`

**Təsvir:** Ödənilmiş və ödənilməmiş sifarişlərin real-time statistikasını göstərir.

### Request Example:

```http
GET /api/orders/statistics/active-orders-stats/
```

### Response Example:

```json
{
  "total_paid": "15240.14",
  "total_unpaid": "385.50",
  "paid_count": 45,
  "unpaid_count": 8,
  "grand_total": "15625.64"
}
```

### Response Fields:

- `total_paid`: Ödənilmiş sifarişlərin ümumi məbləği
- `total_unpaid`: Ödənilməmiş sifarişlərin ümumi məbləği
- `paid_count`: Ödənilmiş sifarişlərin sayı
- `unpaid_count`: Ödənilməmiş sifarişlərin sayı
- `grand_total`: Ümumi məbləğ (ödənilmiş + ödənilməmiş)

### Use Case:

Dashboard və ya real-time monitoring üçün istifadə olunur.

---

## API İstifadə Ssenarisi

### Scenario 1: Növbə Açma

```
1. GET /api/orders/statistics/start-shift-info/
   → Təklif olunan başlanğıc məbləğləri əldə et

2. POST /api/orders/statistics/start-shift/
   Body: {
     "initial_cash": "11333.20",
     "initial_card": "2970.36",
     "initial_other": "0.00",
     "notes": "Səhər növbəsi"
   }
   → Növbəni başlat

3. GET /api/orders/statistics/current-shift/
   → Cari növbə məlumatlarını yoxla
```

### Scenario 2: Növbə Ərzində Monitoring

```
1. GET /api/orders/statistics/current-shift/
   → Cari növbə məlumatlarını al (auto-refresh)

2. GET /api/orders/statistics/active-orders-stats/
   → Aktiv sifarişlərin statistikasını al

3. GET /api/orders/statistics/<shift_id>/
   → Detallı məlumatları al (bütün tab-lar)
```

### Scenario 3: Növbə Bağlama

```
1. GET /api/orders/statistics/<shift_id>/
   → Son məlumatları yoxla

2. POST /api/orders/statistics/<shift_id>/end-shift/
   Body: {
     "withdrawn_amount": "936.58",
     "withdrawn_from_card": "0.00",
     "withdrawn_from_other": "0.00",
     "withdrawn_notes": "maas-35\nrasxod nəqd-91"
   }
   → Növbəni bağla

3. GET /api/orders/statistics/?is_closed=true&ordering=-end_time
   → Bağlanmış növbələri yoxla
```

### Scenario 4: Hesabatların Baxışı

```
1. GET /api/orders/statistics/?ordering=-start_time
   → Bütün hesabatları siyahı şəklində al

2. GET /api/orders/statistics/?start_date=2026-03-01&end_date=2026-03-31&is_closed=true
   → Mart ayının bağlanmış hesabatlarını al

3. GET /api/orders/statistics/<shift_id>/
   → Konkret hesabatın detallı məlumatlarını al (bütün tab-lar)
```

---

## Error Handling

Bütün API-lər aşağıdakı error code-ları qaytara bilər:

### 400 Bad Request

```json
{
  "error": "Validation error message"
}
```

### 401 Unauthorized

```json
{
  "detail": "Authentication credentials were not provided."
}
```

### 404 Not Found

```json
{
  "error": "Resource not found message"
}
```

### 500 Internal Server Error

```json
{
  "error": "Internal server error"
}
```

---

## Performance Considerations

### Database Optimization

1. **Select Related**: Bütün foreign key əlaqələr üçün `select_related` istifadə olunur
2. **Prefetch Related**: Many-to-Many və reverse foreign key əlaqələr üçün `prefetch_related` istifadə olunur
3. **Indexing**: `start_time`, `end_time`, `is_closed`, `started_by` field-ləri üzərində index-lər mövcuddur

### Caching Strategy

- Static data (bağlanmış hesabatlar) cache edilə bilər
- Active shift məlumatları real-time olduğundan cache edilmir

### Pagination

List endpoint-ləri pagination dəstəkləyir (DRF default pagination settings).

---

## Security

### Authentication

- Bütün endpoint-lər `IsAuthenticated` permission istifadə edir
- Token-based authentication tələb olunur

### Authorization

- İstifadəçi yalnız öz açdığı növbəni bağlaya bilər
- Current shift yalnız cari istifadəçinin növbəsini qaytarır

### Data Validation

- Bütün input-lar Decimal və string validation-dan keçir
- SQL injection-dan qorunma üçün Django ORM istifadə olunur

---

## Testing

### Postman Collection

Postman collection yaratmaq üçün nümunə:

```json
{
  "info": {
    "name": "Statistics API",
    "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
  },
  "item": [
    {
      "name": "List Statistics",
      "request": {
        "method": "GET",
        "header": [
          {
            "key": "Authorization",
            "value": "Bearer {{token}}"
          }
        ],
        "url": {
          "raw": "{{base_url}}/api/orders/statistics/",
          "host": ["{{base_url}}"],
          "path": ["api", "orders", "statistics", ""]
        }
      }
    }
  ]
}
```

---

## Əlavə Qeydlər

1. **Decimal Handling**: Bütün məbləğlər string olaraq qaytarılır (JSON-da Decimal precision qorunması üçün)
2. **Datetime Format**: Bütün tarix/vaxt məlumatları ISO 8601 formatındadır
3. **Null Values**: Bağlanmamış növbələr üçün `end_time` və `ended_by` null ola bilər
4. **Auto-calculation**: Açıq növbələr üçün məlumatlar real-time yenilənir

---

## API Versiyası

Cari versiya: **v1**

Son yenilənmə: **2026-04-20**

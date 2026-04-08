# Printer Module API Documentation

Printer modulunun tam CRUD API sənədləşməsi. Bu API-lər yeni UI application tərəfindən istifadə edilmək üçün hazırlanıb.

## Base URL
```
/api/printers/
```

## Autentifikasiya
Bütün endpoint-lər autentifikasiya tələb edir və yalnız admin panel istifadəçiləri (superuser, staff, admin, restaurant) girişi əldə edə bilər.

**Headers:**
```
Authorization: Bearer <token>
```

---

## 1. Printer API-ləri

### 1.1 Printer List (GET)
Bütün printerləri listələ

**Endpoint:** `GET /api/printers/printers/`

**Query Parameters:**
- `search` (optional): Printer adı, IP address və ya təsvir üzrə axtarış
- `is_main` (optional): Əsas printer (true/false)
- `ordering` (optional): Sıralama (id, name, -id, -name)

**Response: 200 OK**
```json
[
    {
        "id": 1,
        "name": "Qelyan Celal",
        "ip_address": "192.168.1.80",
        "port": 9100,
        "description": "Qelyan Celal printer",
        "is_main": true
    },
    {
        "id": 2,
        "name": "Dezgah printeri",
        "ip_address": "192.168.1.222",
        "port": 9100,
        "description": "",
        "is_main": false
    }
]
```

**Nümunə Request:**
```bash
curl -X GET "http://127.0.0.1:8000/api/printers/printers/?search=Celal" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

### 1.2 Printer Detail (GET)
Tək printerin detayını gətir

**Endpoint:** `GET /api/printers/printers/{id}/`

**Response: 200 OK**
```json
{
    "id": 1,
    "name": "Qelyan Celal",
    "ip_address": "192.168.1.80",
    "port": 9100,
    "description": "Qelyan Celal printer",
    "is_main": true
}
```

**Response: 404 Not Found**
```json
{
    "detail": "Not found."
}
```

---

### 1.3 Create Printer (POST)
Yeni printer yarat

**Endpoint:** `POST /api/printers/printers/`

**Request Body:**
```json
{
    "name": "Yeni Printer",
    "ip_address": "192.168.1.100",
    "port": 9100,
    "description": "Printer təsviri (optional)",
    "is_main": false
}
```

**Validation:**
- `name`: Məcburi field
- `ip_address`: Məcburi və unikal olmalıdır
- `port`: Default 9100
- `is_main`: Əgər true olarsa, digər printerlərin is_main-i avtomatik false olur

**Response: 201 Created**
```json
{
    "id": 3,
    "name": "Yeni Printer",
    "ip_address": "192.168.1.100",
    "port": 9100,
    "description": "Printer təsviri",
    "is_main": false
}
```

**Response: 400 Bad Request** (Duplikat IP)
```json
{
    "ip_address": [
        "Bu IP address artıq istifadə olunur."
    ]
}
```

**Nümunə Request:**
```bash
curl -X POST "http://127.0.0.1:8000/api/printers/printers/" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Kassa Printeri",
    "ip_address": "192.168.1.100",
    "port": 9100,
    "is_main": true
  }'
```

---

### 1.4 Update Printer (PUT)
Printeri tam yenilə

**Endpoint:** `PUT /api/printers/printers/{id}/`

**Request Body:**
```json
{
    "name": "Yenilənmiş Printer",
    "ip_address": "192.168.1.100",
    "port": 9100,
    "description": "Yenilənmiş təsvir",
    "is_main": true
}
```

**Response: 200 OK**
```json
{
    "id": 1,
    "name": "Yenilənmiş Printer",
    "ip_address": "192.168.1.100",
    "port": 9100,
    "description": "Yenilənmiş təsvir",
    "is_main": true
}
```

---

### 1.5 Partial Update Printer (PATCH)
Printeri qismən yenilə

**Endpoint:** `PATCH /api/printers/printers/{id}/`

**Request Body:**
```json
{
    "name": "Qismən yenilənmiş ad"
}
```

**Response: 200 OK**
```json
{
    "id": 1,
    "name": "Qismən yenilənmiş ad",
    "ip_address": "192.168.1.100",
    "port": 9100,
    "description": "Köhnə təsvir",
    "is_main": false
}
```

---

### 1.6 Delete Printer (DELETE)
Printeri sil

**Endpoint:** `DELETE /api/printers/printers/{id}/`

**Response: 204 No Content**
```json
{
    "message": "Printer uğurla silindi."
}
```

**Response: 400 Bad Request** (Printer hazırlanma yerində istifadə olunur)
```json
{
    "error": "Bu printer hazırlanma yerlərində istifadə olunur. Əvvəlcə hazırlanma yerlərindən silin."
}
```

---

### 1.7 Set Main Printer (POST - Custom Action)
Bu printeri əsas printer et

**Endpoint:** `POST /api/printers/printers/{id}/set-main/`

**Request Body:** (boş)

**Response: 200 OK**
```json
{
    "message": "Qelyan Celal əsas printer olaraq təyin edildi.",
    "data": {
        "id": 1,
        "name": "Qelyan Celal",
        "ip_address": "192.168.1.80",
        "port": 9100,
        "description": "",
        "is_main": true
    }
}
```

**Nümunə Request:**
```bash
curl -X POST "http://127.0.0.1:8000/api/printers/printers/1/set-main/" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

### 1.8 Get Main Printer (GET - Custom Action)
Əsas printeri gətir

**Endpoint:** `GET /api/printers/printers/main-printer/`

**Response: 200 OK**
```json
{
    "id": 1,
    "name": "Qelyan Celal",
    "ip_address": "192.168.1.80",
    "port": 9100,
    "description": "",
    "is_main": true
}
```

**Response: 404 Not Found**
```json
{
    "error": "Əsas printer tapılmadı."
}
```

---

## 2. Printer Actions API-ləri

### 2.1 Scan Network Printers (GET)
Şəbəkədəki printerləri scan et

**Endpoint:** `GET /api/printers/printers/scan/`

**Response: 200 OK**
```json
{
    "success": true,
    "message": "3 printer tapıldı.",
    "printers": [
        {
            "type": "network",
            "ip": "192.168.1.80",
            "name": "POS Printer"
        },
        {
            "type": "network",
            "ip": "192.168.1.100",
            "name": "POS Printer"
        },
        {
            "type": "network",
            "ip": "192.168.1.222",
            "name": "POS Printer"
        }
    ]
}
```

**Response: 500 Internal Server Error**
```json
{
    "success": false,
    "error": "Printer scan zamanı xəta baş verdi: ..."
}
```

**Nümunə Request:**
```bash
curl -X GET "http://127.0.0.1:8000/api/printers/printers/scan/" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

### 2.2 Test Print (POST)
Printerə test print göndər

**Endpoint:** `POST /api/printers/printers/test-print/`

**Request Body (Option 1 - Printer ID ilə):**
```json
{
    "printer_id": 1
}
```

**Request Body (Option 2 - IP Address ilə):**
```json
{
    "ip_address": "192.168.1.100",
    "port": 9100
}
```

**Response: 200 OK**
```json
{
    "success": true,
    "message": "✅ Receipt sent successfully over TCP."
}
```

**Response: 400 Bad Request** (Printer əlçatan deyil)
```json
{
    "success": false,
    "error": "❌ Failed to send receipt: [Errno 61] Connection refused"
}
```

**Response: 404 Not Found** (Printer tapılmadı)
```json
{
    "success": false,
    "error": "Printer tapılmadı."
}
```

**Nümunə Request:**
```bash
curl -X POST "http://127.0.0.1:8000/api/printers/printers/test-print/" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "printer_id": 1
  }'
```

---

## 3. Hazırlanma Yeri (Preparation Place) API-ləri

### 3.1 Preparation Place List (GET)
Bütün hazırlanma yerlərini listələ

**Endpoint:** `GET /api/printers/preparation-places/`

**Query Parameters:**
- `search` (optional): Hazırlanma yeri adı üzrə axtarış
- `printer` (optional): Printer ID-yə görə filter
- `ordering` (optional): Sıralama (id, name, -id, -name)

**Response: 200 OK**
```json
[
    {
        "id": 1,
        "name": "Mətbəx",
        "printer": 2,
        "printer_detail": {
            "id": 2,
            "name": "Dezgah printeri",
            "ip_address": "192.168.1.222",
            "port": 9100,
            "description": "",
            "is_main": false
        }
    },
    {
        "id": 2,
        "name": "Bar",
        "printer": null,
        "printer_detail": null
    }
]
```

---

### 3.2 Preparation Place Detail (GET)
Tək hazırlanma yerinin detayını gətir

**Endpoint:** `GET /api/printers/preparation-places/{id}/`

**Response: 200 OK**
```json
{
    "id": 1,
    "name": "Mətbəx",
    "printer": 2,
    "printer_detail": {
        "id": 2,
        "name": "Dezgah printeri",
        "ip_address": "192.168.1.222",
        "port": 9100,
        "description": "",
        "is_main": false
    }
}
```

---

### 3.3 Create Preparation Place (POST)
Yeni hazırlanma yeri yarat

**Endpoint:** `POST /api/printers/preparation-places/`

**Request Body:**
```json
{
    "name": "Qril",
    "printer": 2
}
```

**Validation:**
- `name`: Məcburi və unikal olmalıdır
- `printer`: Optional, printer ID

**Response: 201 Created**
```json
{
    "id": 3,
    "name": "Qril",
    "printer": 2,
    "printer_detail": {
        "id": 2,
        "name": "Dezgah printeri",
        "ip_address": "192.168.1.222",
        "port": 9100,
        "description": "",
        "is_main": false
    }
}
```

**Response: 400 Bad Request** (Duplikat ad)
```json
{
    "name": [
        "Bu adda hazırlanma yeri artıq mövcuddur."
    ]
}
```

---

### 3.4 Update Preparation Place (PUT)
Hazırlanma yerini tam yenilə

**Endpoint:** `PUT /api/printers/preparation-places/{id}/`

**Request Body:**
```json
{
    "name": "Yenilənmiş Mətbəx",
    "printer": 3
}
```

**Response: 200 OK**
```json
{
    "id": 1,
    "name": "Yenilənmiş Mətbəx",
    "printer": 3,
    "printer_detail": {
        "id": 3,
        "name": "Yeni Printer",
        "ip_address": "192.168.1.100",
        "port": 9100,
        "description": "",
        "is_main": false
    }
}
```

---

### 3.5 Partial Update Preparation Place (PATCH)
Hazırlanma yerini qismən yenilə

**Endpoint:** `PATCH /api/printers/preparation-places/{id}/`

**Request Body:**
```json
{
    "printer": null
}
```

**Response: 200 OK**

---

### 3.6 Delete Preparation Place (DELETE)
Hazırlanma yerini sil

**Endpoint:** `DELETE /api/printers/preparation-places/{id}/`

**Response: 204 No Content**
```json
{
    "message": "Hazırlanma yeri uğurla silindi."
}
```

---

## 4. Çek (Receipt) API-ləri (Read-Only)

Çeklər sistem tərəfindən avtomatik yaradılır, ona görə yalnız oxuma əməliyyatları mövcuddur.

### 4.1 Receipt List (GET)
Bütün çekləri listələ

**Endpoint:** `GET /api/printers/receipts/`

**Query Parameters:**
- `search` (optional): Çek mətni üzrə axtarış
- `type` (optional): Çek növü (customer, preperation_places, shift_summary, z_summary, order_summary)
- `printer_response_status_code` (optional): Printer cavab status kodu
- `date_from` (optional): Başlanğıc tarixi (YYYY-MM-DD)
- `date_to` (optional): Bitmə tarixi (YYYY-MM-DD)
- `ordering` (optional): Sıralama (id, created_at, -id, -created_at)

**Response: 200 OK**
```json
[
    {
        "id": 14393,
        "created_at": "2026-03-31T21:11:24.123456Z",
        "type": "customer",
        "type_display": "Müştəri üçün",
        "printer_response_status_code": 200,
        "orders_count": 1
    },
    {
        "id": 14392,
        "created_at": "2026-03-31T21:11:18.123456Z",
        "type": "customer",
        "type_display": "Müştəri üçün",
        "printer_response_status_code": 200,
        "orders_count": 1
    }
]
```

**Nümunə Request:**
```bash
curl -X GET "http://127.0.0.1:8000/api/printers/receipts/?type=customer&date_from=2026-03-01&date_to=2026-03-31" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

### 4.2 Receipt Detail (GET)
Tək çekin detayını gətir

**Endpoint:** `GET /api/printers/receipts/{id}/`

**Response: 200 OK**
```json
{
    "id": 14393,
    "created_at": "2026-03-31T21:11:24.123456Z",
    "type": "customer",
    "type_display": "Müştəri üçün",
    "text": "====================================\nQonaq Baku\n====================================\nTarix: 2026-03-31 21:11\nMasa: VIP - KABINET 4\nOfisiant: Sehriyar\n------------------------------------\nSifarış #13531\nAd Miqdar Qiymət Cəm\n------------------------------------\nEkstra 10 1 10.00 10.00 AZN\n...",
    "orders_list": [13531],
    "payment_detail": {
        "id": 1234,
        "amount": 10.0
    },
    "printer_response_status_code": 200
}
```

---

## Error Handling

Bütün API-lər aşağıdakı error format-ından istifadə edir:

**400 Bad Request:**
```json
{
    "field_name": [
        "Error message"
    ]
}
```

**401 Unauthorized:**
```json
{
    "detail": "Authentication credentials were not provided."
}
```

**403 Forbidden:**
```json
{
    "detail": "Bu endpointe girişiniz yoxdur."
}
```

**404 Not Found:**
```json
{
    "detail": "Not found."
}
```

**500 Internal Server Error:**
```json
{
    "error": "Internal server error message"
}
```

---

## Nümunə İstifadə Ssenariləri

### Ssenarilər 1: Yeni Printer Əlavə Et və Test Et

```bash
# 1. Şəbəkəni scan et
curl -X GET "http://127.0.0.1:8000/api/printers/printers/scan/" \
  -H "Authorization: Bearer YOUR_TOKEN"

# 2. Tapılan printerlərdən birini əlavə et
curl -X POST "http://127.0.0.1:8000/api/printers/printers/" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Mətbəx Printeri",
    "ip_address": "192.168.1.222",
    "port": 9100
  }'

# 3. Test print göndər
curl -X POST "http://127.0.0.1:8000/api/printers/printers/test-print/" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "printer_id": 3
  }'
```

### Ssenarilər 2: Hazırlanma Yeri Yarat və Printer Təyin Et

```bash
# 1. Printerləri listələ
curl -X GET "http://127.0.0.1:8000/api/printers/printers/" \
  -H "Authorization: Bearer YOUR_TOKEN"

# 2. Yeni hazırlanma yeri yarat
curl -X POST "http://127.0.0.1:8000/api/printers/preparation-places/" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Mətbəx",
    "printer": 2
  }'
```

### Ssenarilər 3: Çekləri Tarixi Aralıqda Filter Et

```bash
curl -X GET "http://127.0.0.1:8000/api/printers/receipts/?type=customer&date_from=2026-03-01&date_to=2026-03-31&ordering=-created_at" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## Əlavə Qeydlər

1. **Pagination**: API-lər pagination support edir (əgər settings-də konfiqurasiya olubsa)
2. **Permissions**: Bütün endpoint-lər admin panel istifadəçiləri üçündür (IsAdminPanelUser)
3. **Tarix Format**: ISO 8601 (YYYY-MM-DDTHH:MM:SS.ffffffZ)
4. **Main Printer**: Yalnız bir printer is_main=True ola bilər, sistem avtomatik idarə edir

---

**Son yenilənmə:** 8 Aprel 2026
**API Version:** 1.0

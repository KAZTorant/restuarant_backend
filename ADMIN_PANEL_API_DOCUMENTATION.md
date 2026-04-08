# Admin Panel API Documentation

**Base URL:** `http://localhost:8000`  
**Authentication:** Bearer Token

---

## 📋 Table of Contents

1. [Authentication APIs](#authentication-apis)
2. [Meals Management APIs](#meals-management-apis)
   - [Preparation Places](#preparation-places)
   - [Meal Groups](#meal-groups)
   - [Meal Categories](#meal-categories)
   - [Meals](#meals)
   - [Bulk Operations](#bulk-operations)

---

## 🔐 Authentication APIs

### 1. Login

**POST** `/api/admin/auth/login/`

Login admin panelə daxil olmaq üçün. Token qaytarır (30 gün etibarlıdır).

#### Request Body:

```json
{
  "username": "devUser",
  "password": "banm1234"
}
```

#### Success Response (200 OK):

```json
{
  "token": "8bb3e744478e0407f82d80d815c6187c914320eb808ad7ffdfd190afde13f289",
  "expires_at": "2026-05-08T11:41:27.489051Z",
  "user": {
    "id": 25,
    "username": "devUser",
    "full_name": "",
    "first_name": "",
    "last_name": "",
    "email": "",
    "type": null,
    "is_active": true,
    "is_superuser": true,
    "is_staff": true
  }
}
```

#### Error Response (400 Bad Request):

```json
{
  "username": ["İstifadəçi adı yanlışdır."]
}
```

```json
{
  "password": ["Şifrə yanlışdır."]
}
```

```json
{
  "username": ["Bu hesabın admin panelinə girişi yoxdur."]
}
```

---

### 2. Get Current User (Me)

**GET** `/api/admin/auth/me/`

Cari daxil olmuş admin istifadəçinin məlumatlarını qaytarır.

#### Headers:

```
Authorization: Bearer {token}
```

#### Success Response (200 OK):

```json
{
  "id": 25,
  "username": "devUser",
  "full_name": "",
  "first_name": "",
  "last_name": "",
  "email": "",
  "type": null,
  "is_active": true,
  "is_superuser": true,
  "is_staff": true
}
```

#### Error Response (401 Unauthorized):

```json
{
  "detail": "Yanlış və ya etibarsız token."
}
```

---

### 3. Refresh Token

**POST** `/api/admin/auth/refresh/`

Token-in bitmə müddətini 30 gün uzadır.

#### Headers:

```
Authorization: Bearer {token}
```

#### Success Response (200 OK):

```json
{
  "token": "8bb3e744478e0407f82d80d815c6187c914320eb808ad7ffdfd190afde13f289",
  "expires_at": "2026-05-08T11:41:42.973619Z"
}
```

---

### 4. Logout

**POST** `/api/admin/auth/logout/`

Aktiv token-i ləğv edir və sistemdən çıxış edir.

#### Headers:

```
Authorization: Bearer {token}
```

#### Success Response (200 OK):

```json
{
  "message": "Uğurla çıxış edildi."
}
```

---

## 🍽️ Meals Management APIs

### Preparation Places

#### 1. Get All Preparation Places

**GET** `/api/admin/meals/preparation-places/`

Bütün hazırlanma yerlərinin siyahısını qaytarır.

##### Headers:

```
Authorization: Bearer {token}
```

##### Query Parameters (Optional):

- `search` - Axtarış (name)
- `ordering` - Sıralama (`id`, `name`, `-id`, `-name`)

##### Success Response (200 OK):

```json
[
  {
    "id": 1,
    "name": "Kassa",
    "printer": 2,
    "printer_name": "Kassa"
  },
  {
    "id": 2,
    "name": "Dezgah",
    "printer": 3,
    "printer_name": "Dezgah printeri"
  },
  {
    "id": 3,
    "name": "Qelyan printeri",
    "printer": 4,
    "printer_name": "Qelyan Celal"
  }
]
```

---

#### 2. Create Preparation Place

**POST** `/api/admin/meals/preparation-places/`

Yeni hazırlanma yeri yaradır.

##### Headers:

```
Authorization: Bearer {token}
Content-Type: application/json
```

##### Request Body:

```json
{
  "name": "Mətbəx",
  "printer": 1
}
```

**Note:** `printer` field-i optional-dır (null ola bilər).

##### Success Response (201 Created):

```json
{
  "id": 5,
  "name": "Mətbəx",
  "printer": 1,
  "printer_name": "Ana Printer"
}
```

##### Error Response (400 Bad Request):

```json
{
  "name": ["Bu sahə boş ola bilməz."]
}
```

---

#### 3. Get Single Preparation Place

**GET** `/api/admin/meals/preparation-places/{id}/`

Bir hazırlanma yerinin detallarını qaytarır.

##### Headers:

```
Authorization: Bearer {token}
```

##### Success Response (200 OK):

```json
{
  "id": 1,
  "name": "Kassa",
  "printer": 2,
  "printer_name": "Kassa"
}
```

##### Error Response (404 Not Found):

```json
{
  "detail": "Tapılmadı."
}
```

---

#### 4. Update Preparation Place (Full)

**PUT** `/api/admin/meals/preparation-places/{id}/`

Hazırlanma yerini tam yeniləyir (bütün field-lər tələb olunur).

##### Headers:

```
Authorization: Bearer {token}
Content-Type: application/json
```

##### Request Body:

```json
{
  "name": "Yenilənmiş Ad",
  "printer": 3
}
```

##### Success Response (200 OK):

```json
{
  "id": 1,
  "name": "Yenilənmiş Ad",
  "printer": 3,
  "printer_name": "Dezgah printeri"
}
```

---

#### 5. Update Preparation Place (Partial)

**PATCH** `/api/admin/meals/preparation-places/{id}/`

Hazırlanma yerini qismən yeniləyir (yalnız göndərilən field-lər).

##### Headers:

```
Authorization: Bearer {token}
Content-Type: application/json
```

##### Request Body:

```json
{
  "name": "Yalnız ad yenilənir"
}
```

##### Success Response (200 OK):

```json
{
  "id": 1,
  "name": "Yalnız ad yenilənir",
  "printer": 2,
  "printer_name": "Kassa"
}
```

---

#### 6. Delete Preparation Place

**DELETE** `/api/admin/meals/preparation-places/{id}/`

Hazırlanma yerini silir (əgər yeməkdə istifadə edilmirsə).

##### Headers:

```
Authorization: Bearer {token}
```

##### Success Response (204 No Content):

```
(Body boş)
```

##### Error Response (400 Bad Request):

```json
{
  "error": "Bu hazırlanma yerinin 15 yeməyi var. Əvvəlcə yeməklərdən çıxarın."
}
```

---

### Meal Groups

#### 1. Get All Meal Groups

**GET** `/api/admin/meals/groups/`

Bütün meal group-ların siyahısını qaytarır.

##### Headers:

```
Authorization: Bearer {token}
```

##### Query Parameters (Optional):

- `search` - Axtarış (name, description)
- `ordering` - Sıralama (`id`, `name`, `created_at`, `-id`, `-name`)

##### Success Response (200 OK):

```json
[
  {
    "id": 1,
    "name": "İçkilər",
    "description": "",
    "created_at": "2025-11-02T04:01:27.358634+04:00",
    "updated_at": "2025-11-02T04:01:27.358661+04:00"
  },
  {
    "id": 2,
    "name": "Yeməklər",
    "description": "",
    "created_at": "2025-11-02T04:01:34.756025+04:00",
    "updated_at": "2025-11-02T04:01:34.756045+04:00"
  },
  {
    "id": 3,
    "name": "Əlavələr",
    "description": "",
    "created_at": "2025-11-02T04:04:06.700958+04:00",
    "updated_at": "2025-11-02T04:04:06.700992+04:00"
  }
]
```

---

#### 2. Create Meal Group

**POST** `/api/admin/meals/groups/`

Yeni meal group yaradır.

##### Headers:

```
Authorization: Bearer {token}
Content-Type: application/json
```

##### Request Body:

```json
{
  "name": "Test Qrup",
  "description": "Test üçün yaradılmış qrup"
}
```

##### Success Response (201 Created):

```json
{
  "id": 6,
  "name": "Test Qrup",
  "description": "Test üçün yaradılmış qrup",
  "created_at": "2026-04-08T15:45:09.887223+04:00",
  "updated_at": "2026-04-08T15:45:09.887228+04:00"
}
```

##### Error Response (400 Bad Request):

```json
{
  "name": ["Bu sahə boş ola bilməz."]
}
```

---

#### 3. Get Single Meal Group

**GET** `/api/admin/meals/groups/{id}/`

Bir meal group-un detallarını qaytarır (kateqoriya sayı ilə).

##### Headers:

```
Authorization: Bearer {token}
```

##### Success Response (200 OK):

```json
{
  "id": 1,
  "name": "İçkilər",
  "description": "",
  "categories_count": 2,
  "created_at": "2025-11-02T04:01:27.358634+04:00",
  "updated_at": "2025-11-02T04:01:27.358661+04:00"
}
```

##### Error Response (404 Not Found):

```json
{
  "detail": "Tapılmadı."
}
```

---

#### 4. Update Meal Group (Full)

**PUT** `/api/admin/meals/groups/{id}/`

Meal group-u tam yeniləyir (bütün field-lər tələb olunur).

##### Headers:

```
Authorization: Bearer {token}
Content-Type: application/json
```

##### Request Body:

```json
{
  "name": "Yenilənmiş Ad",
  "description": "Yenilənmiş təsvir"
}
```

##### Success Response (200 OK):

```json
{
  "id": 1,
  "name": "Yenilənmiş Ad",
  "description": "Yenilənmiş təsvir",
  "created_at": "2025-11-02T04:01:27.358634+04:00",
  "updated_at": "2026-04-08T15:50:00.123456+04:00"
}
```

---

#### 5. Update Meal Group (Partial)

**PATCH** `/api/admin/meals/groups/{id}/`

Meal group-u qismən yeniləyir (yalnız göndərilən field-lər).

##### Headers:

```
Authorization: Bearer {token}
Content-Type: application/json
```

##### Request Body:

```json
{
  "description": "Yalnız təsvir yenilənir"
}
```

##### Success Response (200 OK):

```json
{
  "id": 1,
  "name": "İçkilər",
  "description": "Yalnız təsvir yenilənir",
  "created_at": "2025-11-02T04:01:27.358634+04:00",
  "updated_at": "2026-04-08T15:52:00.123456+04:00"
}
```

---

#### 6. Delete Meal Group

**DELETE** `/api/admin/meals/groups/{id}/`

Meal group-u silir (əgər kateqoriyası yoxdursa).

##### Headers:

```
Authorization: Bearer {token}
```

##### Success Response (204 No Content):

```
(Body boş)
```

##### Error Response (400 Bad Request):

```json
{
  "error": "Bu qrupun 5 kateqoriyası var. Əvvəlcə kateqoriyaları silin və ya başqa qrupa köçürün."
}
```

---

### Meal Categories

#### 1. Get All Meal Categories

**GET** `/api/admin/meals/categories/`

Bütün meal category-lərin siyahısını qaytarır.

##### Headers:

```
Authorization: Bearer {token}
```

##### Query Parameters (Optional):

- `search` - Axtarış (name, description)
- `ordering` - Sıralama (`id`, `name`, `created_at`)
- `group_id` - Group-a görə filtr (məs: `?group_id=1`)
- `is_extra` - Extra olub-olmadığına görə filtr (`?is_extra=true`)

##### Success Response (200 OK):

```json
[
  {
    "id": 20,
    "name": "Sular",
    "description": "A variety of beverages and drinks",
    "group": 1,
    "group_name": "İçkilər",
    "is_extra": false,
    "created_at": null,
    "updated_at": "2025-11-02T04:03:42.773523+04:00"
  },
  {
    "id": 21,
    "name": "Shorbalar",
    "description": "A selection of soups",
    "group": 2,
    "group_name": "Yeməklər",
    "is_extra": false,
    "created_at": null,
    "updated_at": "2025-11-02T04:03:34.208359+04:00"
  }
]
```

---

#### 2. Create Meal Category

**POST** `/api/admin/meals/categories/`

Yeni meal category yaradır.

##### Headers:

```
Authorization: Bearer {token}
Content-Type: application/json
```

##### Request Body:

```json
{
  "name": "Desertlər",
  "description": "Şirin yeməklər və desertlər",
  "group": 2,
  "is_extra": false
}
```

##### Success Response (201 Created):

```json
{
  "id": 35,
  "name": "Desertlər",
  "description": "Şirin yeməklər və desertlər",
  "group": 2,
  "group_name": "Yeməklər",
  "is_extra": false,
  "created_at": "2026-04-08T16:00:00.123456+04:00",
  "updated_at": "2026-04-08T16:00:00.123456+04:00"
}
```

---

#### 3. Get Single Meal Category

**GET** `/api/admin/meals/categories/{id}/`

Bir meal category-nin detallarını qaytarır (yemək sayı ilə).

##### Headers:

```
Authorization: Bearer {token}
```

##### Success Response (200 OK):

```json
{
  "id": 20,
  "name": "Sular",
  "description": "A variety of beverages and drinks",
  "group": 1,
  "group_name": "İçkilər",
  "is_extra": false,
  "meals_count": 15,
  "created_at": null,
  "updated_at": "2025-11-02T04:03:42.773523+04:00"
}
```

---

#### 4. Update Meal Category

**PUT** `/api/admin/meals/categories/{id}/` - Tam yeniləmə  
**PATCH** `/api/admin/meals/categories/{id}/` - Qismən yeniləmə

##### Headers:

```
Authorization: Bearer {token}
Content-Type: application/json
```

##### Request Body (PATCH example):

```json
{
  "name": "Yenilənmiş Ad"
}
```

##### Success Response (200 OK):

```json
{
  "id": 20,
  "name": "Yenilənmiş Ad",
  "description": "A variety of beverages and drinks",
  "group": 1,
  "group_name": "İçkilər",
  "is_extra": false,
  "created_at": null,
  "updated_at": "2026-04-08T16:05:00.123456+04:00"
}
```

---

#### 5. Delete Meal Category

**DELETE** `/api/admin/meals/categories/{id}/`

Meal category-ni silir (əgər yeməyi yoxdursa).

##### Headers:

```
Authorization: Bearer {token}
```

##### Success Response (204 No Content):

```
(Body boş)
```

##### Error Response (400 Bad Request):

```json
{
  "error": "Bu kateqoriyanın 12 yeməyi var. Əvvəlcə yeməkləri silin və ya başqa kateqoriyaya köçürün."
}
```

---

### Meals

#### 1. Get All Meals

**GET** `/api/admin/meals/meals/`

Bütün yeməklərin siyahısını qaytarır.

##### Headers:

```
Authorization: Bearer {token}
```

##### Query Parameters (Optional):

- `search` - Axtarış (name, description, category name)
- `ordering` - Sıralama (`id`, `name`, `price`, `created_at`)
- `category_id` - Category-ə görə filtr (`?category_id=20`)
- `group_id` - Group-a görə filtr (`?group_id=1`)
- `is_extra` - Extra olub-olmadığına görə filtr (`?is_extra=false`)

##### Success Response (200 OK):

```json
[
  {
    "id": 1,
    "name": "0.50 QEPIK",
    "description": "",
    "price": "0.50",
    "category": 25,
    "category_name": "1Yemekler",
    "group_name": "Yeməklər",
    "preparation_places": [],
    "is_extra": false,
    "cost_price": 0.0,
    "marja_amount": 0.5,
    "marja_percentage": 100.0,
    "created_at": null,
    "updated_at": "2025-12-07T06:07:26.987436+04:00"
  },
  {
    "id": 2,
    "name": "BALLI CAY",
    "description": "",
    "price": "1.00",
    "category": 27,
    "category_name": "Cay sufresi",
    "group_name": "İçkilər",
    "preparation_places": [
      {
        "id": 1,
        "name": "Bar"
      }
    ],
    "is_extra": false,
    "cost_price": 0.25,
    "marja_amount": 0.75,
    "marja_percentage": 75.0,
    "created_at": null,
    "updated_at": "2025-12-07T05:51:16.800656+04:00"
  }
]
```

---

#### 2. Create Meal

**POST** `/api/admin/meals/meals/`

Yeni yemək yaradır.

##### Headers:

```
Authorization: Bearer {token}
Content-Type: application/json
```

##### Request Body:

```json
{
  "name": "Lahmacun",
  "description": "Ənənəvi türk mətbəxindən",
  "price": "3.50",
  "category": 29,
  "preparation_place_ids": [1, 2]
}
```

**Note:** `preparation_place_ids` optional-dır.

##### Success Response (201 Created):

```json
{
  "id": 125,
  "name": "Lahmacun",
  "description": "Ənənəvi türk mətbəxindən",
  "price": "3.50",
  "category": 29,
  "category_name": "Fast Food",
  "group_name": "Yeməklər",
  "preparation_places": [
    {
      "id": 1,
      "name": "Mətbəx"
    },
    {
      "id": 2,
      "name": "Pizza sexi"
    }
  ],
  "is_extra": false,
  "cost_price": 0.0,
  "marja_amount": 3.5,
  "marja_percentage": 100.0,
  "created_at": "2026-04-08T16:15:00.123456+04:00",
  "updated_at": "2026-04-08T16:15:00.123456+04:00"
}
```

---

#### 3. Get Single Meal

**GET** `/api/admin/meals/meals/{id}/`

Bir yeməyin detallarını qaytarır.

##### Headers:

```
Authorization: Bearer {token}
```

##### Success Response (200 OK):

```json
{
  "id": 2,
  "name": "BALLI CAY",
  "description": "",
  "price": "1.00",
  "category": 27,
  "category_name": "Cay sufresi",
  "group_name": "İçkilər",
  "preparation_places": [
    {
      "id": 1,
      "name": "Bar"
    }
  ],
  "is_extra": false,
  "cost_price": 0.25,
  "marja_amount": 0.75,
  "marja_percentage": 75.0,
  "created_at": null,
  "updated_at": "2025-12-07T05:51:16.800656+04:00"
}
```

---

#### 4. Update Meal

**PUT** `/api/admin/meals/meals/{id}/` - Tam yeniləmə  
**PATCH** `/api/admin/meals/meals/{id}/` - Qismən yeniləmə

##### Headers:

```
Authorization: Bearer {token}
Content-Type: application/json
```

##### Request Body (PATCH - yalnız qiymət):

```json
{
  "price": "4.50"
}
```

##### Request Body (PATCH - preparation places):

```json
{
  "preparation_place_ids": [1, 3]
}
```

##### Success Response (200 OK):

```json
{
  "id": 2,
  "name": "BALLI CAY",
  "description": "",
  "price": "4.50",
  "category": 27,
  "category_name": "Cay sufresi",
  "group_name": "İçkilər",
  "preparation_places": [
    {
      "id": 1,
      "name": "Bar"
    }
  ],
  "is_extra": false,
  "cost_price": 0.25,
  "marja_amount": 4.25,
  "marja_percentage": 94.4,
  "created_at": null,
  "updated_at": "2026-04-08T16:20:00.123456+04:00"
}
```

---

#### 5. Delete Meal

**DELETE** `/api/admin/meals/meals/{id}/`

Yeməyi silir (əgər aktiv sifarişdə yoxdursa).

##### Headers:

```
Authorization: Bearer {token}
```

##### Success Response (204 No Content):

```
(Body boş)
```

##### Error Response (400 Bad Request):

```json
{
  "error": "Bu yemək aktiv sifarişdə var. Silinə bilməz."
}
```

---

### Bulk Operations

#### 1. Bulk Update Price

**POST** `/api/admin/meals/meals/bulk/update-price/`

Bir neçə yeməyin qiymətini eyni anda yenilə.

##### Headers:

```
Authorization: Bearer {token}
Content-Type: application/json
```

##### Request Body:

```json
{
  "meals": [
    {
      "id": 1,
      "price": 5.5
    },
    {
      "id": 2,
      "price": 8.0
    },
    {
      "id": 3,
      "price": 12.5
    }
  ]
}
```

##### Success Response (200 OK):

```json
{
  "updated": [
    {
      "id": 1,
      "price": 5.5
    },
    {
      "id": 2,
      "price": 8.0
    },
    {
      "id": 3,
      "price": 12.5
    }
  ],
  "errors": []
}
```

##### Partial Success Response (200 OK):

```json
{
  "updated": [
    {
      "id": 1,
      "price": 5.5
    }
  ],
  "errors": [
    {
      "id": 999,
      "error": "Yemək tapılmadı."
    }
  ]
}
```

---

#### 2. Bulk Update Category

**POST** `/api/admin/meals/meals/bulk/update-category/`

Bir neçə yeməyin kateqoriyasını eyni anda dəyiş.

##### Headers:

```
Authorization: Bearer {token}
Content-Type: application/json
```

##### Request Body:

```json
{
  "meal_ids": [1, 2, 3, 5, 6],
  "category_id": 25
}
```

##### Success Response (200 OK):

```json
{
  "updated_count": 5,
  "category_id": 25,
  "category_name": "1Yemekler"
}
```

##### Error Response (400 Bad Request):

```json
{
  "error": "meal_ids siyahısı boş ola bilməz."
}
```

##### Error Response (404 Not Found):

```json
{
  "detail": "Tapılmadı."
}
```

---

#### 3. Bulk Update Preparation Places

**POST** `/api/admin/meals/meals/bulk/update-preparation-places/`

Bir neçə yeməyin hazırlanma yerlərini eyni anda dəyiş.

##### Headers:

```
Authorization: Bearer {token}
Content-Type: application/json
```

##### Request Body:

```json
{
  "meal_ids": [1, 2, 3, 5, 6],
  "preparation_place_ids": [1, 2]
}
```

##### Success Response (200 OK):

```json
{
  "updated_meal_ids": [1, 2, 3, 5, 6],
  "preparation_place_ids": [1, 2]
}
```

##### Error Response (400 Bad Request):

```json
{
  "error": "meal_ids siyahısı boş ola bilməz."
}
```

---

## 📝 Notes

### Authentication

- Bütün API-lər (login xaric) Bearer token tələb edir
- Token 30 gün etibarlıdır
- Token-i refresh etməklə müddəti uzatmaq olar
- Logout edildikdə token bazadan silinir və artıq işləmir

### Authorization

- Admin panel API-lərinə yalnız bu istifadəçilər daxil ola bilər:
  - `is_superuser=True` (Django superuser)
  - `is_staff=True` (Django staff)
  - `type='admin'` (App admin)
  - `type='restaurant'` (Restaurant owner)

### Pagination

- Hazırda pagination yoxdur (lazım olsa əlavə edilə bilər)

### Error Codes

- `200` - Success (GET, PATCH, PUT, bulk operations)
- `201` - Created (POST)
- `204` - No Content (DELETE success)
- `400` - Bad Request (validation error)
- `401` - Unauthorized (token yoxdur və ya etibarsızdır)
- `403` - Forbidden (icazə yoxdur)
- `404` - Not Found (resurs tapılmadı)

### Field Types

- `price` - Decimal (məs: "5.50")
- `cost_price`, `marja_amount`, `marja_percentage` - Hesablanır (read-only)
- `is_extra` - Boolean (category-dən gəlir, read-only)
- `preparation_places` - Read için array of objects, write için `preparation_place_ids`

---

## 🧪 Test Credentials

```
Username: devUser
Password: banm1234
```

---

## 📌 cURL Examples

### Login və Token Almaq:

```bash
curl -X POST http://localhost:8000/api/admin/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username": "devUser", "password": "banm1234"}'
```

### Yeməkləri Görmək:

```bash
curl -X GET http://localhost:8000/api/admin/meals/meals/ \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

### Yeni Yemək Yaratmaq:

```bash
curl -X POST http://localhost:8000/api/admin/meals/meals/ \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Pizza Margarita",
    "description": "Classic Italian pizza",
    "price": "8.50",
    "category": 29
  }'
```

### Qiymət Yeniləmək:

```bash
curl -X PATCH http://localhost:8000/api/admin/meals/meals/1/ \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{"price": "6.00"}'
```

---

**Document Version:** 1.0  
**Last Updated:** 2026-04-08  
**Contact:** Backend Team

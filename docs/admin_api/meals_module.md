# 🍽️ Meals Module — Admin API Documentation

> **Base URL:** `http://<host>/api/admin/meals`  
> **Authentication:** All endpoints require `X-PIN` header  
> **Permission:** Only `admin` or `restaurant` type users can access these endpoints

---

## 📋 Table of Contents

- [Authentication](#authentication)
- [Models Overview](#models-overview)
- [1. Meal Groups](#1-meal-groups-yemək-kateqoriyası-qrupları)
- [2. Meal Categories](#2-meal-categories-yemək-kateqoriyaları)
- [3. Meals](#3-meals-yeməklər)
- [4. Bulk Actions](#4-bulk-actions-toplu-əməliyyatlar)
- [Error Responses](#error-responses)

---

## Authentication

Every request must include the following header:

```
X-PIN: <user_pin_code>
```

The PIN is the `username` field of the User model. If the PIN is invalid or the user is not `admin`/`restaurant` type, the API returns `403 Forbidden`.

---

## Models Overview

```
MealGroup
  └── MealCategory (group → FK)
        └── Meal (category → FK)
              └── preparation_places (M2M → PreparationPlace)
```

| Model              | Description                                                    |
| ------------------ | -------------------------------------------------------------- |
| `MealGroup`        | Top-level grouping (e.g. "İçkilər", "Əsas Xörəklər")           |
| `MealCategory`     | Category inside a group (e.g. "Soyuq İçkilər")                 |
| `Meal`             | Individual menu item with price, cost, and margin              |
| `PreparationPlace` | Kitchen station where a meal is prepared (linked to a printer) |

---

## 1. Meal Groups (Yemək kateqoriyası qrupları)

### 1.1 List All Groups

```
GET /api/admin/meals/groups/
```

**Query Parameters:**

| Parameter  | Type   | Required | Description                                                                         |
| ---------- | ------ | -------- | ----------------------------------------------------------------------------------- |
| `search`   | string | No       | Search in `name`, `description`                                                     |
| `ordering` | string | No       | Sort by: `id`, `name`, `created_at`. Prefix `-` for descending (e.g. `-created_at`) |

**Success Response `200 OK`:**

```json
[
  {
    "id": 1,
    "name": "İçkilər",
    "description": "Bütün içki növləri",
    "created_at": "2026-01-15T10:30:00Z",
    "updated_at": "2026-01-15T10:30:00Z"
  },
  {
    "id": 2,
    "name": "Əsas Xörəklər",
    "description": null,
    "created_at": "2026-01-15T10:31:00Z",
    "updated_at": "2026-01-15T10:31:00Z"
  }
]
```

---

### 1.2 Create Group

```
POST /api/admin/meals/groups/
```

**Request Body:**

```json
{
  "name": "Desertlər",
  "description": "Şirin yeməklər"
}
```

| Field         | Type   | Required | Description                |
| ------------- | ------ | -------- | -------------------------- |
| `name`        | string | ✅ Yes   | Group name (max 100 chars) |
| `description` | string | No       | Optional description       |

**Success Response `201 Created`:**

```json
{
  "id": 3,
  "name": "Desertlər",
  "description": "Şirin yeməklər",
  "created_at": "2026-04-03T09:00:00Z",
  "updated_at": "2026-04-03T09:00:00Z"
}
```

---

### 1.3 Get Group Detail

```
GET /api/admin/meals/groups/{id}/
```

**Path Parameters:**

| Parameter | Type    | Description |
| --------- | ------- | ----------- |
| `id`      | integer | Group ID    |

**Success Response `200 OK`:**

```json
{
  "id": 1,
  "name": "İçkilər",
  "description": "Bütün içki növləri",
  "categories_count": 3,
  "created_at": "2026-01-15T10:30:00Z",
  "updated_at": "2026-01-15T10:30:00Z"
}
```

> `categories_count` — bu qrupa aid kateqoriyaların sayı

---

### 1.4 Update Group (Full)

```
PUT /api/admin/meals/groups/{id}/
```

**Request Body:** _(all fields required)_

```json
{
  "name": "İçkilər (Yeniləndi)",
  "description": "Yenilənmiş açıqlama"
}
```

**Success Response `200 OK`:** _(same as Create response)_

---

### 1.5 Update Group (Partial)

```
PATCH /api/admin/meals/groups/{id}/
```

**Request Body:** _(only fields you want to change)_

```json
{
  "name": "Yeni Ad"
}
```

**Success Response `200 OK`:** _(same as Create response)_

---

### 1.6 Delete Group

```
DELETE /api/admin/meals/groups/{id}/
```

**Success Response `204 No Content`**

**Error — Group has categories `400 Bad Request`:**

```json
{
  "error": "Bu qrupun 3 kateqoriyası var. Əvvəlcə kateqoriyaları silin və ya başqa qrupa köçürün."
}
```

> ⚠️ A group cannot be deleted if it has categories. Reassign or delete categories first.

---

## 2. Meal Categories (Yemək kateqoriyaları)

### 2.1 List All Categories

```
GET /api/admin/meals/categories/
```

**Query Parameters:**

| Parameter  | Type    | Required | Description                                       |
| ---------- | ------- | -------- | ------------------------------------------------- |
| `search`   | string  | No       | Search in `name`, `description`                   |
| `ordering` | string  | No       | Sort by: `id`, `name`, `created_at`               |
| `group_id` | integer | No       | Filter by group ID                                |
| `is_extra` | boolean | No       | `true` or `false` — filter extra-price categories |

**Success Response `200 OK`:**

```json
[
  {
    "id": 1,
    "name": "Soyuq İçkilər",
    "description": null,
    "group": 1,
    "group_name": "İçkilər",
    "is_extra": false,
    "created_at": "2026-01-15T10:30:00Z",
    "updated_at": "2026-01-15T10:30:00Z"
  }
]
```

---

### 2.2 Create Category

```
POST /api/admin/meals/categories/
```

**Request Body:**

```json
{
  "name": "İsti İçkilər",
  "description": "Çay, qəhvə və s.",
  "group": 1,
  "is_extra": false
}
```

| Field         | Type    | Required | Description                                                    |
| ------------- | ------- | -------- | -------------------------------------------------------------- |
| `name`        | string  | ✅ Yes   | Category name (max 100 chars)                                  |
| `description` | string  | No       | Optional description                                           |
| `group`       | integer | No       | Group ID (FK to MealGroup)                                     |
| `is_extra`    | boolean | No       | Default `false`. If `true`, price is sent dynamically from API |

**Success Response `201 Created`:**

```json
{
  "id": 5,
  "name": "İsti İçkilər",
  "description": "Çay, qəhvə və s.",
  "group": 1,
  "group_name": "İçkilər",
  "is_extra": false,
  "created_at": "2026-04-03T09:00:00Z",
  "updated_at": "2026-04-03T09:00:00Z"
}
```

---

### 2.3 Get Category Detail

```
GET /api/admin/meals/categories/{id}/
```

**Success Response `200 OK`:**

```json
{
  "id": 1,
  "name": "Soyuq İçkilər",
  "description": null,
  "group": 1,
  "group_name": "İçkilər",
  "is_extra": false,
  "meals_count": 8,
  "created_at": "2026-01-15T10:30:00Z",
  "updated_at": "2026-01-15T10:30:00Z"
}
```

> `meals_count` — bu kateqoriyaya aid yeməklərin sayı

---

### 2.4 Update Category (Full)

```
PUT /api/admin/meals/categories/{id}/
```

**Request Body:** _(all fields required)_

```json
{
  "name": "Soyuq İçkilər",
  "description": "Yenilənmiş",
  "group": 1,
  "is_extra": false
}
```

---

### 2.5 Update Category (Partial)

```
PATCH /api/admin/meals/categories/{id}/
```

**Request Body:** _(only fields to change)_

```json
{
  "is_extra": true
}
```

---

### 2.6 Delete Category

```
DELETE /api/admin/meals/categories/{id}/
```

**Success Response `204 No Content`**

**Error — Category has meals `400 Bad Request`:**

```json
{
  "error": "Bu kateqoriyanın 12 yeməyi var. Əvvəlcə yeməkləri silin və ya başqa kateqoriyaya köçürün."
}
```

---

## 3. Meals (Yeməklər)

### 3.1 List All Meals

```
GET /api/admin/meals/meals/
```

**Query Parameters:**

| Parameter     | Type    | Required | Description                                       |
| ------------- | ------- | -------- | ------------------------------------------------- |
| `search`      | string  | No       | Search in `name`, `description`, `category__name` |
| `ordering`    | string  | No       | Sort by: `id`, `name`, `price`, `created_at`      |
| `category_id` | integer | No       | Filter by category ID                             |
| `group_id`    | integer | No       | Filter by group ID                                |
| `is_extra`    | boolean | No       | `true` or `false`                                 |

**Success Response `200 OK`:**

```json
[
  {
    "id": 1,
    "name": "Qutab Göy",
    "description": null,
    "price": "1.50",
    "category": 2,
    "category_name": "Qutablar",
    "group_name": "Əsas Xörəklər",
    "preparation_places": [{ "id": 1, "name": "Mətbəx" }],
    "is_extra": false,
    "cost_price": 0.6,
    "marja_amount": 0.9,
    "marja_percentage": 60.0,
    "created_at": "2026-01-15T10:30:00Z",
    "updated_at": "2026-01-15T10:30:00Z"
  }
]
```

| Field                | Type           | Description                                |
| -------------------- | -------------- | ------------------------------------------ |
| `price`              | decimal string | Satış qiyməti (AZN)                        |
| `cost_price`         | float          | İnventardan hesablanan xərc qiyməti        |
| `marja_amount`       | float          | Marja məbləği (`price - cost_price`)       |
| `marja_percentage`   | float          | Marja faizi (`marja_amount / price * 100`) |
| `preparation_places` | array          | Hazırlanma yerləri (read-only)             |

---

### 3.2 Create Meal

```
POST /api/admin/meals/meals/
```

**Request Body:**

```json
{
  "name": "Qutab Ət",
  "description": "Əti qutab",
  "price": "2.00",
  "category": 2,
  "preparation_place_ids": [1, 2]
}
```

| Field                   | Type      | Required | Description                   |
| ----------------------- | --------- | -------- | ----------------------------- |
| `name`                  | string    | ✅ Yes   | Meal name (max 200 chars)     |
| `price`                 | decimal   | ✅ Yes   | Sale price in AZN             |
| `category`              | integer   | No       | Category ID (FK)              |
| `description`           | string    | No       | Optional description          |
| `preparation_place_ids` | integer[] | No       | Array of PreparationPlace IDs |

> ⚠️ Use `preparation_place_ids` (write-only) for setting places. The response returns `preparation_places` (read-only objects).

**Success Response `201 Created`:**

```json
{
  "id": 15,
  "name": "Qutab Ət",
  "description": "Əti qutab",
  "price": "2.00",
  "category": 2,
  "category_name": "Qutablar",
  "group_name": "Əsas Xörəklər",
  "preparation_places": [
    { "id": 1, "name": "Mətbəx" },
    { "id": 2, "name": "Bar" }
  ],
  "is_extra": false,
  "cost_price": 0.0,
  "marja_amount": 2.0,
  "marja_percentage": 100.0,
  "created_at": "2026-04-03T09:00:00Z",
  "updated_at": "2026-04-03T09:00:00Z"
}
```

---

### 3.3 Get Meal Detail

```
GET /api/admin/meals/meals/{id}/
```

**Success Response `200 OK`:** _(same structure as list item)_

---

### 3.4 Update Meal (Full)

```
PUT /api/admin/meals/meals/{id}/
```

**Request Body:** _(all required fields must be present)_

```json
{
  "name": "Qutab Ət",
  "price": "2.50",
  "category": 2,
  "preparation_place_ids": [1]
}
```

**Success Response `200 OK`:** _(same as create response)_

---

### 3.5 Update Meal (Partial)

```
PATCH /api/admin/meals/meals/{id}/
```

**Example — Update price only:**

```json
{
  "price": "3.00"
}
```

**Example — Update preparation places only:**

```json
{
  "preparation_place_ids": [1, 3]
}
```

**Success Response `200 OK`:** _(same as create response)_

---

### 3.6 Delete Meal

```
DELETE /api/admin/meals/meals/{id}/
```

**Success Response `204 No Content`**

**Error — Meal is in an active order `400 Bad Request`:**

```json
{
  "error": "Bu yemək aktiv sifarişdə var. Silinə bilməz."
}
```

---

## 4. Bulk Actions (Toplu Əməliyyatlar)

### 4.1 Bulk Update Prices

```
POST /api/admin/meals/meals/bulk/update-price/
```

Update multiple meal prices in a single request.

**Request Body:**

```json
{
  "meals": [
    { "id": 1, "price": 1.5 },
    { "id": 2, "price": 2.0 },
    { "id": 3, "price": 3.5 }
  ]
}
```

**Success Response `200 OK`:**

```json
{
  "updated": [
    { "id": 1, "price": 1.5 },
    { "id": 2, "price": 2.0 },
    { "id": 3, "price": 3.5 }
  ],
  "errors": []
}
```

**Partial failure example:**

```json
{
  "updated": [{ "id": 1, "price": 1.5 }],
  "errors": [{ "id": 999, "error": "Yemək tapılmadı." }]
}
```

---

### 4.2 Bulk Update Category

```
POST /api/admin/meals/meals/bulk/update-category/
```

Move multiple meals to a different category at once.

**Request Body:**

```json
{
  "meal_ids": [1, 2, 3],
  "category_id": 5
}
```

| Field         | Type      | Required | Description                 |
| ------------- | --------- | -------- | --------------------------- |
| `meal_ids`    | integer[] | ✅ Yes   | Array of Meal IDs to update |
| `category_id` | integer   | ✅ Yes   | Target Category ID          |

**Success Response `200 OK`:**

```json
{
  "updated_count": 3,
  "category_id": 5,
  "category_name": "İsti İçkilər"
}
```

---

### 4.3 Bulk Update Preparation Places

```
POST /api/admin/meals/meals/bulk/update-preparation-places/
```

Assign preparation places to multiple meals at once.

**Request Body:**

```json
{
  "meal_ids": [1, 2, 3],
  "preparation_place_ids": [1, 2]
}
```

| Field                   | Type      | Required | Description                                       |
| ----------------------- | --------- | -------- | ------------------------------------------------- |
| `meal_ids`              | integer[] | ✅ Yes   | Array of Meal IDs to update                       |
| `preparation_place_ids` | integer[] | ✅ Yes   | Array of PreparationPlace IDs (replaces existing) |

> ⚠️ This **replaces** all existing preparation places for each meal. To keep existing ones, include them in the array.

**Success Response `200 OK`:**

```json
{
  "updated_meal_ids": [1, 2, 3],
  "preparation_place_ids": [1, 2]
}
```

---

## Error Responses

### Common HTTP Status Codes

| Code               | Meaning                                     |
| ------------------ | ------------------------------------------- |
| `200 OK`           | Request successful                          |
| `201 Created`      | Resource created successfully               |
| `204 No Content`   | Resource deleted successfully               |
| `400 Bad Request`  | Validation error or business rule violation |
| `401 Unauthorized` | Missing or invalid `X-PIN` header           |
| `403 Forbidden`    | User is not `admin` or `restaurant` type    |
| `404 Not Found`    | Resource not found                          |

### Validation Error Format `400`

```json
{
  "field_name": ["This field is required."]
}
```

### Authentication Error `401`

```json
{
  "detail": "No such user"
}
```

### Permission Error `403`

```json
{
  "detail": "You must be an admin to access this endpoint."
}
```

---

## Quick Reference

| Method   | Endpoint                                                 | Action                         |
| -------- | -------------------------------------------------------- | ------------------------------ |
| `GET`    | `/api/admin/meals/groups/`                               | List all groups                |
| `POST`   | `/api/admin/meals/groups/`                               | Create group                   |
| `GET`    | `/api/admin/meals/groups/{id}/`                          | Get group detail               |
| `PUT`    | `/api/admin/meals/groups/{id}/`                          | Full update group              |
| `PATCH`  | `/api/admin/meals/groups/{id}/`                          | Partial update group           |
| `DELETE` | `/api/admin/meals/groups/{id}/`                          | Delete group                   |
| `GET`    | `/api/admin/meals/categories/`                           | List all categories            |
| `POST`   | `/api/admin/meals/categories/`                           | Create category                |
| `GET`    | `/api/admin/meals/categories/{id}/`                      | Get category detail            |
| `PUT`    | `/api/admin/meals/categories/{id}/`                      | Full update category           |
| `PATCH`  | `/api/admin/meals/categories/{id}/`                      | Partial update category        |
| `DELETE` | `/api/admin/meals/categories/{id}/`                      | Delete category                |
| `GET`    | `/api/admin/meals/meals/`                                | List all meals                 |
| `POST`   | `/api/admin/meals/meals/`                                | Create meal                    |
| `GET`    | `/api/admin/meals/meals/{id}/`                           | Get meal detail                |
| `PUT`    | `/api/admin/meals/meals/{id}/`                           | Full update meal               |
| `PATCH`  | `/api/admin/meals/meals/{id}/`                           | Partial update meal            |
| `DELETE` | `/api/admin/meals/meals/{id}/`                           | Delete meal                    |
| `POST`   | `/api/admin/meals/meals/bulk/update-price/`              | Bulk update prices             |
| `POST`   | `/api/admin/meals/meals/bulk/update-category/`           | Bulk update category           |
| `POST`   | `/api/admin/meals/meals/bulk/update-preparation-places/` | Bulk update preparation places |

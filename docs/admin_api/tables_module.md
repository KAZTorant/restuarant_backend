# 🪑 Tables Module — Admin API Documentation

> **Base URL:** `http://<host>/api/admin/tables`  
> **Authentication:** All endpoints require `X-PIN` header  
> **Permission:** Only `admin` or `restaurant` type users can access these endpoints

---

## 📋 Table of Contents

- [Authentication](#authentication)
- [Models Overview](#models-overview)
- [1. Rooms (Zallar)](#1-rooms-zallar)
- [2. Tables (Stollar)](#2-tables-stollar)
- [Error Responses](#error-responses)
- [Quick Reference](#quick-reference)

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
Room (Zal)
  └── Table (Stol) (room → FK)
```

| Model   | Description                                             |
| ------- | ------------------------------------------------------- |
| `Room`  | Restaurant section / hall (e.g. "VIP", "Terras", "Zal") |
| `Table` | Individual table inside a room with number and capacity |

---

## 1. Rooms (Zallar)

### 1.1 List All Rooms

```
GET /api/admin/tables/rooms/
```

**Query Parameters:**

| Parameter  | Type   | Required | Description                                                                         |
| ---------- | ------ | -------- | ----------------------------------------------------------------------------------- |
| `search`   | string | No       | Search in `name`, `description`                                                     |
| `ordering` | string | No       | Sort by: `id`, `name`, `created_at`. Prefix `-` for descending (e.g. `-created_at`) |
| `page`     | int    | No       | Page number (default: 1, page size: 20)                                             |

**Success Response `200 OK`:**

```json
{
  "count": 8,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "name": "Zal1 1-20",
      "description": null,
      "is_active": true,
      "tables_count": 20,
      "created_at": "2026-01-10T08:00:00Z",
      "updated_at": "2026-01-10T08:00:00Z"
    },
    {
      "id": 2,
      "name": "Zal2 20-40",
      "description": null,
      "is_active": true,
      "tables_count": 20,
      "created_at": "2026-01-10T08:01:00Z",
      "updated_at": "2026-01-10T08:01:00Z"
    }
  ]
}
```

> `tables_count` — həmin zala aid ümumi stol sayı

---

### 1.2 Create Room

```
POST /api/admin/tables/rooms/
```

**Request Body:**

```json
{
  "name": "VIP",
  "description": "VIP otağı",
  "is_active": true
}
```

| Field         | Type    | Required | Description                         |
| ------------- | ------- | -------- | ----------------------------------- |
| `name`        | string  | ✅ Yes   | Room name (max 100 chars)           |
| `description` | string  | No       | Optional description                |
| `is_active`   | boolean | No       | Default `true`. Hides room if false |

**Success Response `201 Created`:**

```json
{
  "id": 9,
  "name": "VIP",
  "description": "VIP otağı",
  "is_active": true,
  "created_at": "2026-04-08T10:00:00Z",
  "updated_at": "2026-04-08T10:00:00Z"
}
```

---

### 1.3 Get Room Detail

```
GET /api/admin/tables/rooms/{id}/
```

**Path Parameters:**

| Parameter | Type    | Description |
| --------- | ------- | ----------- |
| `id`      | integer | Room ID     |

**Success Response `200 OK`:**

```json
{
  "id": 1,
  "name": "Zal1 1-20",
  "description": null,
  "is_active": true,
  "tables_count": 20,
  "created_at": "2026-01-10T08:00:00Z",
  "updated_at": "2026-01-10T08:00:00Z"
}
```

> `tables_count` — bu zaldakı ümumi stol sayı

---

### 1.4 Update Room (Full)

```
PUT /api/admin/tables/rooms/{id}/
```

**Request Body:** _(all fields required)_

```json
{
  "name": "VIP Salon",
  "description": "Yenilənmiş VIP otağı",
  "is_active": true
}
```

**Success Response `200 OK`:**

```json
{
  "id": 9,
  "name": "VIP Salon",
  "description": "Yenilənmiş VIP otağı",
  "is_active": true,
  "created_at": "2026-04-08T10:00:00Z",
  "updated_at": "2026-04-08T11:00:00Z"
}
```

---

### 1.5 Update Room (Partial)

```
PATCH /api/admin/tables/rooms/{id}/
```

**Request Body:** _(only fields you want to change)_

```json
{
  "is_active": false
}
```

**Success Response `200 OK`:** _(same as Full Update response)_

---

### 1.6 Delete Room

```
DELETE /api/admin/tables/rooms/{id}/
```

**Success Response `204 No Content`**

**Error — Room has tables `400 Bad Request`:**

```json
{
  "error": "Bu zalda 20 stol var. Əvvəlcə stolları silin və ya başqa zala köçürün."
}
```

> ⚠️ A room cannot be deleted if it still has tables. Reassign or delete all tables first.

---

## 2. Tables (Stollar)

### 2.1 List All Tables

```
GET /api/admin/tables/tables/
```

**Query Parameters:**

| Parameter  | Type    | Required | Description                                                                  |
| ---------- | ------- | -------- | ---------------------------------------------------------------------------- |
| `room_id`  | integer | No       | Filter tables by room ID                                                     |
| `search`   | string  | No       | Search in `number`, `room__name`                                             |
| `ordering` | string  | No       | Sort by: `id`, `number`, `capacity`, `created_at`. Prefix `-` for descending |
| `page`     | int     | No       | Page number (default: 1, page size: 20)                                      |

**Success Response `200 OK`:**

```json
{
  "count": 100,
  "next": "http://<host>/api/admin/tables/tables/?page=2",
  "previous": null,
  "results": [
    {
      "id": 1,
      "number": "STOL - 1",
      "capacity": null,
      "room": 1,
      "room_name": "Zal1 1-20",
      "is_occupied": false,
      "total_price": 0,
      "created_at": "2026-01-10T08:00:00Z",
      "updated_at": "2026-01-10T08:00:00Z"
    },
    {
      "id": 2,
      "number": "STOL - 2",
      "capacity": 4,
      "room": 1,
      "room_name": "Zal1 1-20",
      "is_occupied": true,
      "total_price": 45.5,
      "created_at": "2026-01-10T08:00:00Z",
      "updated_at": "2026-01-10T08:00:00Z"
    }
  ]
}
```

> `is_occupied` — `true` olduqda stolda aktiv ödənilməmiş sifariş var  
> `total_price` — stolun cari bütün sifarişlərinin ümumi məbləği  
> `room` — Room-un ID-si (write üçün istifadə olunur)  
> `room_name` — Room-un adı (read-only)

**Filter by room example:**

```
GET /api/admin/tables/tables/?room_id=1
```

---

### 2.2 Create Table

```
POST /api/admin/tables/tables/
```

**Request Body:**

```json
{
  "number": "STOL - 21",
  "capacity": 4,
  "room": 2
}
```

| Field      | Type    | Required | Description                       |
| ---------- | ------- | -------- | --------------------------------- |
| `number`   | string  | No       | Table label/number (max 10 chars) |
| `capacity` | integer | No       | How many people the table seats   |
| `room`     | integer | No       | Room ID (FK to Room)              |

**Success Response `201 Created`:**

```json
{
  "id": 101,
  "number": "STOL - 21",
  "capacity": 4,
  "room": 2,
  "room_name": "Zal2 20-40",
  "created_at": "2026-04-08T10:00:00Z",
  "updated_at": "2026-04-08T10:00:00Z"
}
```

---

### 2.3 Get Table Detail

```
GET /api/admin/tables/tables/{id}/
```

**Path Parameters:**

| Parameter | Type    | Description |
| --------- | ------- | ----------- |
| `id`      | integer | Table ID    |

**Success Response `200 OK`:**

```json
{
  "id": 2,
  "number": "STOL - 2",
  "capacity": 4,
  "room": 1,
  "room_name": "Zal1 1-20",
  "is_occupied": true,
  "total_price": 45.5,
  "created_at": "2026-01-10T08:00:00Z",
  "updated_at": "2026-01-10T08:00:00Z"
}
```

---

### 2.4 Update Table (Full)

```
PUT /api/admin/tables/tables/{id}/
```

**Request Body:** _(all fields required)_

```json
{
  "number": "STOL - 2",
  "capacity": 6,
  "room": 1
}
```

**Success Response `200 OK`:**

```json
{
  "id": 2,
  "number": "STOL - 2",
  "capacity": 6,
  "room": 1,
  "room_name": "Zal1 1-20",
  "created_at": "2026-01-10T08:00:00Z",
  "updated_at": "2026-04-08T11:30:00Z"
}
```

---

### 2.5 Update Table (Partial)

```
PATCH /api/admin/tables/tables/{id}/
```

**Request Body:** _(only fields you want to change)_

```json
{
  "capacity": 8
}
```

**Success Response `200 OK`:** _(same as Full Update response)_

---

### 2.6 Delete Table

```
DELETE /api/admin/tables/tables/{id}/
```

**Success Response `204 No Content`**

**Error — Table has active order `400 Bad Request`:**

```json
{
  "error": "Bu stolun aktiv sifarişi var. Əvvəlcə sifarişi bağlayın."
}
```

> ⚠️ A table cannot be deleted while it has an active (unpaid) order.

---

## Error Responses

### Not Found `404`

```json
{
  "detail": "No Room matches the given query."
}
```

```json
{
  "detail": "No Table matches the given query."
}
```

### Validation Error `400`

```json
{
  "name": ["This field is required."]
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
  "detail": "Bu endpointe girişiniz yoxdur. Admin, Restaurant, Superuser və ya Staff olmalısınız."
}
```

---

## Quick Reference

| Method   | Endpoint                         | Action                               |
| -------- | -------------------------------- | ------------------------------------ |
| `GET`    | `/api/admin/tables/rooms/`       | List all rooms (with `tables_count`) |
| `POST`   | `/api/admin/tables/rooms/`       | Create room                          |
| `GET`    | `/api/admin/tables/rooms/{id}/`  | Get room detail                      |
| `PUT`    | `/api/admin/tables/rooms/{id}/`  | Full update room                     |
| `PATCH`  | `/api/admin/tables/rooms/{id}/`  | Partial update room                  |
| `DELETE` | `/api/admin/tables/rooms/{id}/`  | Delete room (fails if tables exist)  |
| `GET`    | `/api/admin/tables/tables/`      | List all tables (`?room_id=` filter) |
| `POST`   | `/api/admin/tables/tables/`      | Create table                         |
| `GET`    | `/api/admin/tables/tables/{id}/` | Get table detail                     |
| `PUT`    | `/api/admin/tables/tables/{id}/` | Full update table                    |
| `PATCH`  | `/api/admin/tables/tables/{id}/` | Partial update table                 |
| `DELETE` | `/api/admin/tables/tables/{id}/` | Delete table (fails if order active) |

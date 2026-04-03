# 🔐 Authentication Module — Admin API Documentation

> **Base URL:** `http://<host>/api/admin/auth`  
> **Authentication:** Bu modul token-based `Bearer` sistemindən istifadə edir  
> **Permission:** `admin`, `restaurant`, `is_superuser=True` və ya `is_staff=True` olan hesablar daxil ola bilər

---

## 📋 Table of Contents

- [Who Can Login](#who-can-login)
- [How Authentication Works](#how-authentication-works)
- [1. Login](#1-login)
- [2. Logout](#2-logout)
- [3. Get Current User (Me)](#3-get-current-user-me)
- [4. Refresh Token](#4-refresh-token)
- [Error Responses](#error-responses)

---

## Who Can Login

Bu API-yə aşağıdakı **4 növ hesab** daxil ola bilər:

| Hesab Növü           | Şərt                  | Məkan                                   |
| -------------------- | --------------------- | --------------------------------------- |
| **Django Superuser** | `is_superuser = true` | Django Admin → Users → Superuser status |
| **Django Staff**     | `is_staff = true`     | Django Admin → Users → Staff status     |
| **App Admin**        | `type = "admin"`      | Ofisiant və Menecerlər bölməsi          |
| **Restaurant Owner** | `type = "restaurant"` | Ofisiant və Menecerlər bölməsi          |

> ⚠️ **Şifrə tələbi:** Hesabın Django şifrəsi set olunmuş olmalıdır.  
> PIN ilə yaradılmış hesablarda şifrə olmaya bilər. Django Admin-dən:  
> `Users → [hesabı seç] → Password → Set Password`

---

## How Authentication Works

### Login Flow

```
1. POST /api/admin/auth/login/  →  { token: "abc123..." }
2. Hər sonrakı sorğuda header əlavə et:
   Authorization: Bearer abc123...
```

### Token Lifecycle

- Token **30 gün** etibarlıdır
- Hər istifadədə `last_used_at` avtomatik yenilənir
- `POST /refresh/` ilə müddəti uzadıla bilər
- `POST /logout/` ilə token DB-dən silinir
- Yenidən login edəndə əvvəlki token silinir, yeni token yaradılır

---

## 1. Login

```
POST /api/admin/auth/login/
```

> 🔓 Bu endpoint **authentication tələb etmir** — açıqdır.

**Request Headers:**

```
Content-Type: application/json
```

**Request Body:**

```json
{
  "username": "admin_user",
  "password": "secret123"
}
```

| Field      | Type   | Required | Description    |
| ---------- | ------ | -------- | -------------- |
| `username` | string | ✅ Yes   | İstifadəçi adı |
| `password` | string | ✅ Yes   | Şifrə          |

**Success Response `200 OK`:**

```json
{
  "token": "a3f8c2d1e4b7...(64 hex chars)",
  "expires_at": "2026-05-03T09:00:00Z",
  "user": {
    "id": 1,
    "username": "admin_user",
    "full_name": "Kamran Hacili",
    "first_name": "Kamran",
    "last_name": "Hacili",
    "email": "kamran@kazza.az",
    "type": "admin",
    "is_active": true,
    "is_superuser": false,
    "is_staff": false
  }
}
```

| Field               | Type                | Description                                                                                 |
| ------------------- | ------------------- | ------------------------------------------------------------------------------------------- |
| `token`             | string              | 64 simvolluq hex token — bütün sorğularda istifadə olunur                                   |
| `expires_at`        | datetime (ISO 8601) | Token-in bitmə tarixi (UTC)                                                                 |
| `user.type`         | string \| null      | `"admin"`, `"restaurant"`, `"waitress"`, `"captain_waitress"` və ya `null` (superuser üçün) |
| `user.is_superuser` | boolean             | Django superadmin hesabıdır?                                                                |
| `user.is_staff`     | boolean             | Django staff hesabıdır?                                                                     |

> 💡 Flutter tərəfdə `is_superuser` və ya `is_staff` `true` olarsa — tam səlahiyyətli hesabdır.  
> `type` field-i `null` ola bilər (Django superuser-lərdə `type` set edilmir).

**Error — Wrong password `400 Bad Request`:**

```json
{
  "password": ["Şifrə yanlışdır."]
}
```

**Error — User not found `400 Bad Request`:**

```json
{
  "username": ["İstifadəçi adı yanlışdır."]
}
```

**Error — Not admin `400 Bad Request`:**

```json
{
  "username": [
    "Bu hesabın admin panelinə girişi yoxdur. (admin, restaurant, superuser və ya staff olmalıdır)"
  ]
}
```

**Error — Inactive account `400 Bad Request`:**

```json
{
  "username": ["Bu hesab deaktivdir."]
}
```

---

## 2. Logout

```
POST /api/admin/auth/logout/
```

> 🔒 **Authentication tələb olunur** — `Authorization: Bearer <token>`

**Request Headers:**

```
Authorization: Bearer a3f8c2d1e4b7...
```

**Request Body:** _(boş — body tələb olunmur)_

**Success Response `200 OK`:**

```json
{
  "message": "Uğurla çıxış edildi."
}
```

> Token DB-dən silinir. Həmin token artıq heç bir sorğu üçün keçərli deyil.

**Error — Invalid token `401 Unauthorized`:**

```json
{
  "detail": "Yanlış və ya etibarsız token."
}
```

---

## 3. Get Current User (Me)

```
GET /api/admin/auth/me/
```

> 🔒 **Authentication tələb olunur** — `Authorization: Bearer <token>`

**Request Headers:**

```
Authorization: Bearer a3f8c2d1e4b7...
```

**Success Response `200 OK`:**

```json
{
  "id": 1,
  "username": "admin_user",
  "full_name": "Kamran Hacili",
  "first_name": "Kamran",
  "last_name": "Hacili",
  "email": "kamran@kazza.az",
  "type": "admin",
  "is_active": true,
  "is_superuser": false,
  "is_staff": false
}
```

| Field          | Type           | Description                                           |
| -------------- | -------------- | ----------------------------------------------------- |
| `id`           | integer        | İstifadəçi ID-si                                      |
| `username`     | string         | Login adı                                             |
| `full_name`    | string         | Ad + Soyad                                            |
| `type`         | string \| null | `"admin"` \| `"restaurant"` \| `"waitress"` \| `null` |
| `is_active`    | boolean        | Hesab aktivdir?                                       |
| `is_superuser` | boolean        | Django superadmin?                                    |
| `is_staff`     | boolean        | Django staff?                                         |

> 💡 Bu endpoint app açıldığında token-in hələ də keçərli olub-olmadığını yoxlamaq üçün istifadə edilir.

---

## 4. Refresh Token

```
POST /api/admin/auth/refresh/
```

> 🔒 **Authentication tələb olunur** — `Authorization: Bearer <token>`

Token-in bitmə müddətini **30 gün** uzadır. Token dəyişmir, yalnız `expires_at` yenilənir.

**Request Headers:**

```
Authorization: Bearer a3f8c2d1e4b7...
```

**Request Body:** _(boş — body tələb olunmur)_

**Success Response `200 OK`:**

```json
{
  "token": "a3f8c2d1e4b7...",
  "expires_at": "2026-06-03T09:00:00Z"
}
```

> 💡 App hər açıldığında bu endpoint-i çağırmaq tövsiyə olunur — beləliklə aktiv istifadəçinin token-i heç vaxt bitmir.

---

## Error Responses

### Authentication Errors

**Token yoxdur `401 Unauthorized`:**

```json
{
  "detail": "Authentication credentials were not provided."
}
```

**Token etibarsızdır `401 Unauthorized`:**

```json
{
  "detail": "Yanlış və ya etibarsız token."
}
```

**Token-in müddəti bitib `401 Unauthorized`:**

```json
{
  "detail": "Token-in müddəti bitib. Yenidən daxil olun."
}
```

**İstifadəçi admin deyil `403 Forbidden`:**

```json
{
  "detail": "Bu endpointe girişiniz yoxdur. Admin, Restaurant, Superuser və ya Staff olmalısınız."
}
```

---

## Flutter Implementation Guide

### Token saxlama

```dart
// Login olduqda token-i saxla
final prefs = await SharedPreferences.getInstance();
await prefs.setString('admin_token', response['token']);
await prefs.setString('token_expires_at', response['expires_at']);
```

### İstifadəçi tipini yoxla (kim daxil olub?)

```dart
final user = response['user'];

final bool isSuperAdmin = user['is_superuser'] == true;
final bool isStaff      = user['is_staff'] == true;
final String? type      = user['type'];

// Tam səlahiyyətli admin:
final bool isFullAdmin = isSuperAdmin || isStaff || type == 'restaurant';

// App admin:
final bool isAppAdmin = type == 'admin' || type == 'restaurant';
```

### Hər sorğuya header əlavə et

```dart
final token = prefs.getString('admin_token');

final response = await http.get(
  Uri.parse('$baseUrl/api/admin/meals/meals/'),
  headers: {
    'Content-Type': 'application/json',
    'Authorization': 'Bearer $token',
  },
);
```

### Token bitib-bitmədiyini yoxla

```dart
final expiresAt = DateTime.parse(prefs.getString('token_expires_at')!);
final isExpired = DateTime.now().isAfter(expiresAt);

if (isExpired) {
  // Login səhifəsinə yönləndir
  Navigator.pushReplacementNamed(context, '/login');
}
```

### App açılışında token yoxla

```dart
// App başladığında /me endpoint-i çağır
try {
  final res = await dio.get('/api/admin/auth/me/');
  // Token hələ keçərlidir → dashboard-a get
  await dio.post('/api/admin/auth/refresh/'); // müddəti uzat
} on DioException catch (e) {
  if (e.response?.statusCode == 401) {
    // Token bitib → login səhifəsi
  }
}
```

---

## Quick Reference

| Method | Endpoint                   | Auth Required | Action                                  |
| ------ | -------------------------- | ------------- | --------------------------------------- |
| `POST` | `/api/admin/auth/login/`   | ❌ No         | Username + password ilə giriş, token al |
| `POST` | `/api/admin/auth/logout/`  | ✅ Yes        | Token-i ləğv et, çıxış et               |
| `GET`  | `/api/admin/auth/me/`      | ✅ Yes        | Cari istifadəçi məlumatları             |
| `POST` | `/api/admin/auth/refresh/` | ✅ Yes        | Token müddətini 30 gün uzat             |

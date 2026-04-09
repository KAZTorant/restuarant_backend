# 👤 Users & Groups Module — Admin API Documentation

> **Base URL:** `http://<host>/api/admin/users`  
> **Authentication:** `Authorization: Bearer <token>` (admin login-dən alınan token)  
> **Permission:** `admin`, `restaurant`, `is_staff` və ya `is_superuser` tələb olunur  
> **Pagination:** Bütün list endpointlər `page_size: 20` ilə paginate edilir

---

## 📋 Table of Contents

- [Authentication](#authentication)
- [Models Overview](#models-overview)
- [Data Types & Enums](#data-types--enums)
- [1. Users (İstifadəçilər)](#1-users-istifadəçilər)
  - [1.1 List Users](#11-list-users)
  - [1.2 Create User](#12-create-user)
  - [1.3 Get User Detail](#13-get-user-detail)
  - [1.4 Update User](#14-update-user)
  - [1.5 Delete User](#15-delete-user)
  - [1.6 Set Password](#16-set-password)
- [2. Groups (Qruplar)](#2-groups-qruplar)
  - [2.1 List Groups](#21-list-groups)
  - [2.2 Create Group](#22-create-group)
  - [2.3 Get Group Detail](#23-get-group-detail)
  - [2.4 Update Group](#24-update-group)
  - [2.5 Delete Group](#25-delete-group)
- [3. Permissions (İcazələr)](#3-permissions-icazələr)
  - [3.1 List Permissions](#31-list-permissions)
- [Error Responses](#error-responses)
- [Quick Reference](#quick-reference)
- [Flutter Integration Notes](#flutter-integration-notes)
- [Curl Examples (tez nümunələr)](#curl-examples-tez-nümunələr)
- [Testing notes](#testing-notes)
- [Validation & Edge Cases (qısa xülasə)](#validation--edge-cases-qısa-xülasə)
- [Admin UI parity notes](#admin-ui-parity-notes)
- [Changelog (qısa)](#changelog-qısa)
- [Support / Contact](#support--contact)

---

## Authentication

Bütün endpointlər `Authorization` header-i tələb edir:

```
Authorization: Bearer <token>
```

Token `POST /api/admin/auth/login/` endpoint-indən alınır.

---

## Models Overview

```
User  ─────────────────────────────────────────────
  ├── groups        → Group[]  (M2M)
  └── user_permissions → Permission[] (M2M, nadir hallarda)

Group ─────────────────────────────────────────────
  └── permissions   → Permission[] (M2M)

Permission ────────────────────────────────────────
  └── content_type  → ContentType (app_label + model)
```

| Model        | Description                                                           |
| ------------ | --------------------------------------------------------------------- |
| `User`       | Ofisiant, Kapitan, Admin, Restaurant sahibi                           |
| `Group`      | İcazə qrupu — istifadəçilərə toplu icazə vermək üçün                  |
| `Permission` | Django-nun standart model icazəsi (`add`, `change`, `delete`, `view`) |

---

## Data Types & Enums

### `user.type`

| Value              | Display           |
| ------------------ | ----------------- |
| `waitress`         | Ofisiant          |
| `captain_waitress` | Kapitan Ofisiant  |
| `admin`            | Administrator     |
| `restaurant`       | Restaurant Sahibi |
| `null`             | Təyin edilməyib   |

---

## 1. Users (İstifadəçilər)

---

### 1.1 List Users

```
GET /api/admin/users/users/
```

**Query Parameters:**

| Parameter   | Type   | Required | Description                                                       |
| ----------- | ------ | -------- | ----------------------------------------------------------------- |
| `page`      | int    | No       | Səhifə nömrəsi (default: 1, page_size: 20)                        |
| `type`      | string | No       | Filter: `waitress`, `captain_waitress`, `admin`, `restaurant`     |
| `is_active` | bool   | No       | Filter: `true` / `false`                                          |
| `is_staff`  | bool   | No       | Filter: `true` / `false`                                          |
| `group_id`  | int    | No       | Filter: həmin qrupa aid istifadəçilər                             |
| `search`    | string | No       | `username`, `first_name`, `last_name`, `email` üzrə axtarış       |
| `ordering`  | string | No       | Sırala: `id`, `username`, `date_joined`. Azalan üçün `-` prefiksi |

**Success Response `200 OK`:**

```json
{
  "count": 18,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "username": "0001",
      "full_name": "Resad",
      "first_name": "Resad",
      "last_name": "",
      "type": "waitress",
      "is_staff": false,
      "is_active": true,
      "groups": [{ "id": 1, "name": "Adminstrator Selahiyyetleri" }],
      "date_joined": "2025-12-01T10:00:00Z"
    }
  ]
}
```

**Field Descriptions:**

| Field         | Type     | Description                           |
| ------------- | -------- | ------------------------------------- |
| `id`          | int      | İstifadəçi ID-si                      |
| `username`    | string   | PIN kodu (login üçün istifadə olunur) |
| `full_name`   | string   | Ad + Soyad birləşmiş                  |
| `first_name`  | string   | Ad                                    |
| `last_name`   | string   | Soyad                                 |
| `type`        | string   | İstifadəçi rolu (`null` ola bilər)    |
| `is_staff`    | bool     | Admin panelə girişi var?              |
| `is_active`   | bool     | Aktiv/Deaktiv                         |
| `groups`      | array    | Təyin edilmiş qruplar (`id`, `name`)  |
| `date_joined` | datetime | Qeydiyyat tarixi (UTC)                |

---

### 1.2 Create User

```
POST /api/admin/users/users/
```

**Request Body:**

```json
{
  "username": "2323",
  "first_name": "Yeni",
  "last_name": "Ofisiant",
  "password": "StrongPass123!",
  "password2": "StrongPass123!",
  "type": "waitress",
  "is_staff": false,
  "is_active": true,
  "groups": [1]
}
```

| Field        | Type   | Required | Description                                           |
| ------------ | ------ | -------- | ----------------------------------------------------- |
| `username`   | string | ✅ Yes   | PIN kodu — unikal olmalıdır                           |
| `first_name` | string | No       | Ad                                                    |
| `last_name`  | string | No       | Soyad                                                 |
| `password`   | string | ✅ Yes   | Şifrə (min 8 simvol)                                  |
| `password2`  | string | ✅ Yes   | Şifrə təsdiqi                                         |
| `type`       | string | No       | `waitress`, `captain_waitress`, `admin`, `restaurant` |
| `is_staff`   | bool   | No       | Default: `false`                                      |
| `is_active`  | bool   | No       | Default: `true`                                       |
| `groups`     | array  | No       | Qrup ID-lərinin siyahısı                              |

**Validation Qaydaları:**

| Şərt                       | Xəta sahəsi | Mesaj                                        |
| -------------------------- | ----------- | -------------------------------------------- |
| `username` artıq mövcuddur | `username`  | `"Bu istifadəçi adı artıq istifadə edilir."` |
| `password != password2`    | `password2` | `"Şifrələr uyğun deyil."`                    |
| Zəif şifrə                 | `password`  | Django şifrə validasiya mesajları            |

**Success Response `201 Created`:** — `AdminUserDetailSerializer` formatında (bax 1.3)

---

### 1.3 Get User Detail

```
GET /api/admin/users/users/{id}/
```

**Success Response `200 OK`:**

```json
{
  "id": 46,
  "username": "2323",
  "full_name": "Yeni Ofisiant",
  "first_name": "Yeni",
  "last_name": "Ofisiant",
  "type": "waitress",
  "is_staff": false,
  "is_active": true,
  "groups": [{ "id": 1, "name": "Adminstrator Selahiyyetleri" }],
  "date_joined": "2026-04-09T10:00:00Z",
  "email": "",
  "is_superuser": false,
  "user_permissions": [],
  "last_login": null
}
```

**Əlavə fields (detail-only):**

| Field              | Type     | Description                         |
| ------------------ | -------- | ----------------------------------- |
| `email`            | string   | E-poçt (boş ola bilər)              |
| `is_superuser`     | bool     | Django superuser statusu            |
| `user_permissions` | array    | Birbaşa verilmiş icazələr (nadir)   |
| `last_login`       | datetime | Son giriş tarixi (`null` ola bilər) |

---

### 1.4 Update User

```
PUT   /api/admin/users/users/{id}/   ← tam yeniləmə
PATCH /api/admin/users/users/{id}/   ← qismən yeniləmə (tövsiyə olunur)
```

**Request Body (PATCH nümunəsi):**

```json
{
  "first_name": "Dəyişdirilmiş Ad",
  "type": "captain_waitress",
  "is_active": false,
  "groups": [1, 2]
}
```

> 📝 `password` və `password2` göndərilsə şifrə dəyişdirilir. Göndərilməsə dəyişdirilmir.  
> 📝 `groups` göndərilsə mövcud qruplar tam əvəzlənir.  
> 📝 `groups: []` göndərilsə istifadəçi bütün qruplardan çıxarılır.

**Success Response `200 OK`:** — `AdminUserDetailSerializer` formatında (bax 1.3)

---

### 1.5 Delete User

```
DELETE /api/admin/users/users/{id}/
```

**Success Response `204 No Content`**

**Bloklanan hallar:**

| Hal                           | Status | Mesaj                                   |
| ----------------------------- | ------ | --------------------------------------- |
| `is_superuser = true`         | `400`  | `"Superuser istifadəçi silinə bilməz."` |
| Özünü silmək (`request.user`) | `400`  | `"Özünüzü silə bilməzsiniz."`           |

---

### 1.6 Set Password

```
POST /api/admin/users/users/{id}/set-password/
```

> Yalnız `superuser` başqa istifadəçinin şifrəsini dəyişə bilər.  
> Admin/restaurant öz şifrəsini dəyişə bilər.

**Request Body:**

```json
{
  "password": "NewStrongPass123!",
  "password2": "NewStrongPass123!"
}
```

**Success Response `200 OK`:**

```json
{
  "detail": "Şifrə uğurla dəyişdirildi."
}
```

**Error `403 Forbidden`:**

```json
{
  "detail": "Yalnız superuser başqa istifadəçinin şifrəsini dəyişə bilər."
}
```

---

## 2. Groups (Qruplar)

---

### 2.1 List Groups

```
GET /api/admin/users/groups/
```

**Query Parameters:**

| Parameter  | Type   | Required | Description                            |
| ---------- | ------ | -------- | -------------------------------------- |
| `page`     | int    | No       | Səhifə nömrəsi (default: 1)            |
| `search`   | string | No       | `name` üzrə axtarış                    |
| `ordering` | string | No       | Sırala: `id`, `name`. `-` prefiksi ilə |

**Success Response `200 OK`:**

```json
{
  "count": 2,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "name": "Adminstrator Selahiyyetleri",
      "permissions_count": 45
    },
    {
      "id": 2,
      "name": "Ruslan Mudriyyet",
      "permissions_count": 12
    }
  ]
}
```

---

### 2.2 Create Group

```
POST /api/admin/users/groups/
```

**Request Body:**

```json
{
  "name": "Yeni Qrup",
  "permissions": [1, 5, 12, 48]
}
```

| Field         | Type   | Required | Description                              |
| ------------- | ------ | -------- | ---------------------------------------- |
| `name`        | string | ✅ Yes   | Qrup adı — unikal olmalıdır              |
| `permissions` | array  | No       | Permission ID-lərinin siyahısı (bax 3.1) |

**Success Response `201 Created`:** — `AdminGroupDetailSerializer` formatında (bax 2.3)

**Validation Error `400`:**

```json
{
  "name": ["Bu adda qrup artıq mövcuddur."]
}
```

---

### 2.3 Get Group Detail

```
GET /api/admin/users/groups/{id}/
```

**Success Response `200 OK`:**

```json
{
  "id": 1,
  "name": "Adminstrator Selahiyyetleri",
  "permissions": [
    {
      "id": 5,
      "name": "Can add user",
      "codename": "add_user",
      "content_type_label": "users",
      "content_type_model": "user"
    },
    {
      "id": 6,
      "name": "Can change user",
      "codename": "change_user",
      "content_type_label": "users",
      "content_type_model": "user"
    }
  ]
}
```

---

### 2.4 Update Group

```
PUT   /api/admin/users/groups/{id}/
PATCH /api/admin/users/groups/{id}/
```

**Request Body (PATCH nümunəsi):**

```json
{
  "name": "Yenilənmiş Qrup Adı",
  "permissions": [1, 2, 5]
}
```

> 📝 `permissions` göndərilsə mövcud icazələr tam əvəzlənir.

**Success Response `200 OK`:** — `AdminGroupDetailSerializer` formatında (bax 2.3)

---

### 2.5 Delete Group

```
DELETE /api/admin/users/groups/{id}/
```

**Success Response `204 No Content`**

**Bloklanan hal:**

| Hal                      | Status | Mesaj                                                           |
| ------------------------ | ------ | --------------------------------------------------------------- |
| Qrupda istifadəçilər var | `400`  | `"Bu qrupda N istifadəçi var. Əvvəlcə istifadəçiləri çıxarın."` |

---

## 3. Permissions (İcazələr)

> ⚠️ Read-only. Yalnız qrup yaradarkən / yenilərkən seçim üçün istifadə olunur.

---

### 3.1 List Permissions

```
GET /api/admin/users/permissions/
```

> Pagination yoxdur — hamısı bir anda qaytarılır (cəmi ~152 icazə).

**Query Parameters:**

| Parameter   | Type   | Required | Description                                                                                                              |
| ----------- | ------ | -------- | ------------------------------------------------------------------------------------------------------------------------ |
| `search`    | string | No       | `name`, `codename`, `app_label`, `model` üzrə axtar                                                                      |
| `app_label` | string | No       | App-a görə filtr: `auth`, `users`, `orders`, `payments`, `meals`, `tables`, `printers`, `finance`, `inventory_connector` |

**Success Response `200 OK`:**

```json
[
  {
    "id": 1,
    "name": "Can add log entry",
    "codename": "add_logentry",
    "content_type_label": "admin",
    "content_type_model": "logentry"
  },
  {
    "id": 5,
    "name": "Can add user",
    "codename": "add_user",
    "content_type_label": "users",
    "content_type_model": "user"
  }
]
```

**Field Descriptions:**

| Field                | Type   | Description                                         |
| -------------------- | ------ | --------------------------------------------------- |
| `id`                 | int    | Permission ID-si (qrup assign üçün istifadə edilir) |
| `name`               | string | İnsan oxunaqlı ad (e.g. `"Can add user"`)           |
| `codename`           | string | Kod adı (e.g. `"add_user"`)                         |
| `content_type_label` | string | App adı (e.g. `"users"`, `"orders"`, `"payments"`)  |
| `content_type_model` | string | Model adı (e.g. `"user"`, `"order"`, `"payment"`)   |

**Nümunə filterlər:**

```
# Yalnız auth icazələri
GET /api/admin/users/permissions/?app_label=auth

# orders app icazələri
GET /api/admin/users/permissions/?app_label=orders

# Axtarış
GET /api/admin/users/permissions/?search=payment
```

---

## Error Responses

### Authentication Error `401`

```json
{ "detail": "Yanlış və ya etibarsız token." }
```

### Permission Error `403`

```json
{
  "detail": "Bu endpointe girişiniz yoxdur. Admin, Restaurant, Superuser və ya Staff olmalısınız."
}
```

### Not Found `404`

```json
{ "detail": "No User matches the given query." }
```

### Validation Error `400`

```json
{
  "username": ["Bu istifadəçi adı artıq istifadə edilir."],
  "password2": ["Şifrələr uyğun deyil."]
}
```

---

## Quick Reference

| Method   | Endpoint                                    | Description                                             |
| -------- | ------------------------------------------- | ------------------------------------------------------- |
| `GET`    | `/api/admin/users/users/`                   | İstifadəçilərin siyahısı (filter + search + pagination) |
| `POST`   | `/api/admin/users/users/`                   | Yeni istifadəçi yarat                                   |
| `GET`    | `/api/admin/users/users/{id}/`              | İstifadəçi detalları (groups + permissions)             |
| `PUT`    | `/api/admin/users/users/{id}/`              | Tam yeniləmə                                            |
| `PATCH`  | `/api/admin/users/users/{id}/`              | Qismən yeniləmə (tövsiyə olunur)                        |
| `DELETE` | `/api/admin/users/users/{id}/`              | Sil (superuser və özü bloklanır)                        |
| `POST`   | `/api/admin/users/users/{id}/set-password/` | Şifrəni dəyişdir                                        |
| `GET`    | `/api/admin/users/groups/`                  | Qrupların siyahısı                                      |
| `POST`   | `/api/admin/users/groups/`                  | Yeni qrup yarat                                         |
| `GET`    | `/api/admin/users/groups/{id}/`             | Qrup detalları (tam icazə siyahısı)                     |
| `PUT`    | `/api/admin/users/groups/{id}/`             | Tam yeniləmə                                            |
| `PATCH`  | `/api/admin/users/groups/{id}/`             | Qismən yeniləmə                                         |
| `DELETE` | `/api/admin/users/groups/{id}/`             | Sil (üzvlər varsa bloklanır)                            |
| `GET`    | `/api/admin/users/permissions/`             | Bütün icazələr (qrup assign üçün)                       |

---

## Flutter Integration Notes

### User type dropdown

```dart
const userTypes = [
  {'value': 'waitress',         'label': 'Ofisiant'},
  {'value': 'captain_waitress', 'label': 'Kapitan Ofisiant'},
  {'value': 'admin',            'label': 'Administrator'},
  {'value': 'restaurant',       'label': 'Restaurant Sahibi'},
];
```

### Create user

```dart
final body = {
  'username': pinController.text,
  'password': passController.text,
  'password2': pass2Controller.text,
  'type': selectedType,        // 'waitress', 'admin', ...
  'is_active': true,
  'groups': selectedGroupIds,  // List<int>
};
final resp = await api.post('/api/admin/users/users/', body);
```

### Update user (PATCH — yalnız dəyişənlər göndər)

```dart
final body = <String, dynamic>{};
if (nameChanged)   body['first_name'] = firstName;
if (typeChanged)   body['type'] = selectedType;
if (activeChanged) body['is_active'] = isActive;
if (groupsChanged) body['groups'] = selectedGroupIds;
if (passChanged) {
  body['password'] = newPass;
  body['password2'] = newPass2;
}
await api.patch('/api/admin/users/users/$userId/', body);
```

### Load permissions for group create/edit

```dart
// Bütün icazələri app_label-a görə qruplaşdır
final perms = await api.get('/api/admin/users/permissions/');
final grouped = <String, List>{};
for (final p in perms) {
  grouped.putIfAbsent(p['content_type_label'], () => []).add(p);
}
// grouped['users'], grouped['orders'], grouped['payments'], ...
```

### `is_staff` vs `type`

| Sahə       | Məna                                                              |
| ---------- | ----------------------------------------------------------------- |
| `is_staff` | Django admin panelə giriş (`true` = admin panelə daxil ola bilər) |
| `type`     | App-a məxsus rol (ofisiant, admin, restaurant sahibi)             |

> Admin panelə giriş üçün `is_staff: true` **VƏ ya** `type: admin/restaurant` lazımdır.

### Delete guard

```dart
Future<void> deleteUser(int userId) async {
  try {
    await api.delete('/api/admin/users/users/$userId/');
    // 204 — uğurlu
  } on ApiException catch (e) {
    if (e.statusCode == 400) {
      showSnackbar(e.body['error']); // superuser və ya özünü silmə
    }
  }
}
```

---

## Curl Examples (tez nümunələr)

> Qısa nümunələr API-ni sürətlə yoxlamaq üçün.

- Login (token alınması)

```
POST /api/admin/auth/login/
Body: { "username": "admin", "password": "TopSecret" }
Response: { "access": "<token>", "refresh": "..." }
```

- List users

```
GET /api/admin/users/users/?page=1
Headers: Authorization: Bearer <token>
```

- Create user

```
POST /api/admin/users/users/
Headers: Authorization: Bearer <token>
Body: {
  "username": "2323",
  "password": "StrongPass123!",
  "password2": "StrongPass123!",
  "type": "waitress",
  "is_staff": false,
  "is_active": true,
  "groups": [1]
}
```

- Update user (PATCH)

```
PATCH /api/admin/users/users/46/
Headers: Authorization: Bearer <token>
Body: { "first_name": "Yeni", "groups": [1,2] }
```

- Set password

```
POST /api/admin/users/users/46/set-password/
Headers: Authorization: Bearer <token>
Body: { "password": "NewPass123!", "password2": "NewPass123!" }
```

- List groups

```
GET /api/admin/users/groups/
Headers: Authorization: Bearer <token>
```

- Create group

```
POST /api/admin/users/groups/
Headers: Authorization: Bearer <token>
Body: { "name": "Yeni Qrup", "permissions": [5,6,30] }
```

---

## Testing notes

- Test suite: unit və integration testlər `apps/users` içində yerləşən test faylları ilə təmin olunub. Testlər aşağıdakıları əhatə edir:
  - İstifadəçi yaratma, yeniləmə, silmə, parol dəyişmə
  - Qrupların CRUD əməliyyatları və icazə assign/unalter
  - Filtrlər, axtarış, sıralama və pagination edge-case-ləri
  - Məhdudlaşdırılmış əməliyyatlar: superuser silmə, özünü silmək, qrupa üzvlük varsa qrup silmə

- Testləri icra etmək üçün Django test runner istifadə edin (məsələn: `python manage.py test`). Test fayllarını işə salarkən müvafiq test bazası yaradılacaq və sonra silinəcək.

---

## Validation & Edge Cases (qısa xülasə)

- Username unikal olmalıdır — duplikat halında `400` qaytarılır. Mesaj: `"Bu istifadəçi adı artıq istifadə edilir."`.
- Şifrələr uyğun gəlmirsə (`password != password2`) `400` qaytarılır və sahə `password2`-də xəta göstərilir.
- Zəif şifrə Django-nun built-in validasiyası ilə rədd edilir (müvafiq səbəblər `400` içində açıqlanır).
- Superuser silinməsinə icazə verilmir — `400` ilə uyğun mesaj.
- Özünü silmək qadağandır — `400`.
- Qrup silinməyə çalışıldığında əgər o qrupa istifadəçilər bağlıdırsa `400` qaytarılır və istifadəçi sayı mesajda göstərilir.
- `permissions` və `groups` kimi M2M sahələr göndərilirsə onlar tam şəkildə əvəz olunur. Boş array (`[]`) göndərilməsi sahəni sıfırlayır.

---

## Admin UI parity notes

API-lar Django admin UI-nin davranışını reproduksiya edir:

- `is_staff` flag və `type` kombinasiyası UI-də olduğu kimi admin girişi məntiqini təyin edir.
- Qruplar panelində seçilən icazələr və istifadəçi səhifəsində qrupların təyini admin ilə paralel işləyir.
- Form davranışları: yeni istifadəçi yaradarkən şifrənin mütləq göstərilməsi, mövcud istifadəçi üçün şifrə yalnız göndərildikdə dəyişir.
- Pagination, search və ordering admin siyahısının ümumi istifadə təcrübəsinə uyğun konfiqurasiya edilib.

---

## Changelog (qısa)

- v1.0.0 — Başlangıç: Full CRUD endpoints for Users, Groups and Permissions read-only list. Filters, pagination, ordering, and validation implemented. Tests included.

---

## Support / Contact

Hər hansı problem və ya əlavə istəyiniz olarsa, repository içində `README`-də göstərilən əlaqə vasitələri ilə və ya issue tracker vasitəsilə bildirin.

---

End of documentation.

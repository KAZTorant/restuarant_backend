# 📋 Log Entries Module — Admin API Documentation

> **Base URL:** `http://<host>/api/admin/users`  
> **Authentication:** `Authorization: Bearer <token>`  
> **Permission:** `is_staff` və ya `is_superuser` tələb olunur  
> **Pagination:** `page_size: 20` (sabit)  
> **Access:** Read-only — yazma/silmə yoxdur

---

## 📋 Table of Contents

- [Overview](#overview)
- [Endpoint](#endpoint)
- [Query Parameters](#query-parameters)
- [Response Format](#response-format)
- [Field Reference](#field-reference)
- [Filter Examples](#filter-examples)
- [Flutter Integration](#flutter-integration)
- [Quick Reference](#quick-reference)

---

## Overview

Django Admin Log Entries (`django.contrib.admin.models.LogEntry`) — admin paneldəki hər əməliyyatın avtomatik qeydini saxlayır.

| Əməliyyat  | `action_flag` | `action`   | `action_label` |
| ---------- | ------------- | ---------- | -------------- |
| Əlavəetmə  | `1`           | `addition` | `Əlavəetmə`    |
| Dəyişiklik | `2`           | `change`   | `Dəyişiklik`   |
| Silmə      | `3`           | `deletion` | `Silmə`        |

**Mövcud `app_label`-lər:**

| `app_label`           | Modellər                                                                                                               |
| --------------------- | ---------------------------------------------------------------------------------------------------------------------- |
| `users`               | `user`                                                                                                                 |
| `auth`                | `group`                                                                                                                |
| `orders`              | `order`, `orderitem`, `statistics`, `summary`, `report`, `workperiodconfig`, `orderitemdeletionlog`, `historicalorder` |
| `payments`            | `payment`, `paymentcalculation`                                                                                        |
| `meals`               | `meal`, `mealcategory`, `mealgroup`                                                                                    |
| `tables`              | `room`, `table`                                                                                                        |
| `printers`            | `printer`, `preparationplace`                                                                                          |
| `finance`             | `income`, `expense`                                                                                                    |
| `inventory`           | `category`, `inventoryitem`, `inventoryrecord`                                                                         |
| `inventory_connector` | `mealinventoryconnector`                                                                                               |

---

## Endpoint

```
GET /api/admin/users/log-entries/
```

---

## Query Parameters

| Parameter   | Type   | Required | Description                                                                                                                 |
| ----------- | ------ | -------- | --------------------------------------------------------------------------------------------------------------------------- |
| `page`      | int    | No       | Səhifə nömrəsi (default: 1, page_size: 20)                                                                                  |
| `action`    | string | No       | Filter: `addition` / `change` / `deletion`                                                                                  |
| `app_label` | string | No       | Filter: `users`, `orders`, `payments`, `meals`, `tables`, `printers`, `finance`, `inventory`, `inventory_connector`, `auth` |
| `model`     | string | No       | Filter: `user`, `order`, `payment`, `meal`, `table`, `printer` ...                                                          |
| `user_id`   | int    | No       | Filter: bu istifadəçi tərəfindən edilən əməliyyatlar                                                                        |
| `year`      | int    | No       | Filter: `2025` / `2026` ...                                                                                                 |
| `search`    | string | No       | `object_repr`, `username`, `first_name`, `last_name` üzrə axtarış                                                           |
| `ordering`  | string | No       | `id`, `action_time`, `action_flag`. Default: `-action_time` (ən yeni əvvəl)                                                 |

---

## Response Format

**Success `200 OK`:**

```json
{
  "count": 1768,
  "next": "http://localhost:8000/api/admin/users/log-entries/?page=2",
  "previous": null,
  "results": [
    {
      "id": 1768,
      "action_time": "2026-04-09T23:27:06.985029+04:00",
      "user_id": 25,
      "username": "devUser",
      "user_fullname": "Kamran Hacili",
      "app_label": "users",
      "model": "user",
      "object_id": "28",
      "object_repr": "Kamran Hacili Admin",
      "action": "change",
      "action_label": "Dəyişiklik",
      "action_flag": 2,
      "change_summary": [
        {
          "changed": {
            "fields": ["Username"]
          }
        }
      ],
      "change_message_display": "Username dəyişdirildi."
    }
  ]
}
```

---

## Field Reference

| Field                    | Type     | Description                                                                  |
| ------------------------ | -------- | ---------------------------------------------------------------------------- |
| `id`                     | int      | Log entry ID                                                                 |
| `action_time`            | datetime | Əməliyyat tarixi və vaxtı (timezone-aware, UTC+4 Bakı vaxtı)                 |
| `user_id`                | int      | Əməliyyatı edən istifadəçinin ID-si                                          |
| `username`               | string   | Əməliyyatı edən istifadəçinin `username`-i (PIN kodu)                        |
| `user_fullname`          | string   | Ad + Soyad (`username`-ə fallback edir)                                      |
| `app_label`              | string   | Hansı app-a aid model (`users`, `orders`, `payments`, ...)                   |
| `model`                  | string   | Model adı kiçik hərflə (`user`, `order`, `payment`, ...)                     |
| `object_id`              | string   | Dəyişdirilmiş/silinmiş obyektin PK-si (həmişə string)                        |
| `object_repr`            | string   | Obyektin `__str__()` təsviri (e.g. `"Kamran Hacili Admin"`)                  |
| `action`                 | string   | `"addition"` / `"change"` / `"deletion"`                                     |
| `action_label`           | string   | Azərbaycan dilində: `"Əlavəetmə"` / `"Dəyişiklik"` / `"Silmə"`               |
| `action_flag`            | int      | Raw Django dəyəri: `1` / `2` / `3`                                           |
| `change_summary`         | array    | JSON-parse edilmiş `change_message` — hansı field-lərin dəyişdiyini göstərir |
| `change_message_display` | string   | İnsan oxunaqlı, lokalizasiya edilmiş dəyişiklik mesajı                       |

### `change_summary` strukturu

**Dəyişiklik (`action=change`):**

```json
[{ "changed": { "fields": ["Username", "First name"] } }]
```

**Əlavəetmə (`action=addition`):**

```json
[{ "added": {} }]
```

**Silmə (`action=deletion`):**

```json
[]
```

**M2M dəyişiklik:**

```json
[{ "changed": { "fields": ["groups"] } }]
```

---

## Filter Examples

```
# Yalnız dəyişiklik əməliyyatları
GET /api/admin/users/log-entries/?action=change

# Yalnız silmə əməliyyatları
GET /api/admin/users/log-entries/?action=deletion

# users app-a aid bütün loglar
GET /api/admin/users/log-entries/?app_label=users

# payments app, yalnız silmə, 2026-cı il
GET /api/admin/users/log-entries/?app_label=payments&action=deletion&year=2026

# Konkret istifadəçinin əməliyyatları
GET /api/admin/users/log-entries/?user_id=25

# Axtarış (object_repr, username üzrə)
GET /api/admin/users/log-entries/?search=Kamran

# Ən köhnədən başla (cronoloji)
GET /api/admin/users/log-entries/?ordering=action_time

# Konkret model üzrə
GET /api/admin/users/log-entries/?app_label=orders&model=statistics

# 2025-ci il, əlavəetmə əməliyyatları
GET /api/admin/users/log-entries/?year=2025&action=addition
```

---

## Flutter Integration

### Model sinfi

```dart
enum LogAction { addition, change, deletion }

class LogEntry {
  final int id;
  final DateTime actionTime;
  final int userId;
  final String username;
  final String userFullname;
  final String appLabel;
  final String model;
  final String objectId;
  final String objectRepr;
  final LogAction action;
  final String actionLabel;
  final List<dynamic> changeSummary;
  final String changeMessageDisplay;

  LogEntry.fromJson(Map<String, dynamic> json)
      : id = json['id'],
        actionTime = DateTime.parse(json['action_time']),
        userId = json['user_id'],
        username = json['username'],
        userFullname = json['user_fullname'],
        appLabel = json['app_label'],
        model = json['model'],
        objectId = json['object_id'],
        objectRepr = json['object_repr'],
        action = LogAction.values.firstWhere(
          (e) => e.name == json['action'],
          orElse: () => LogAction.change,
        ),
        actionLabel = json['action_label'],
        changeSummary = json['change_summary'] ?? [],
        changeMessageDisplay = json['change_message_display'] ?? '';
}
```

### Action rəng kodu (UI üçün)

```dart
Color actionColor(LogAction action) {
  switch (action) {
    case LogAction.addition:  return Colors.green;
    case LogAction.change:    return Colors.blue;
    case LogAction.deletion:  return Colors.red;
  }
}

IconData actionIcon(LogAction action) {
  switch (action) {
    case LogAction.addition:  return Icons.add_circle_outline;
    case LogAction.change:    return Icons.edit_outlined;
    case LogAction.deletion:  return Icons.delete_outline;
  }
}
```

### List screen — paginated fetch

```dart
Future<Map<String, dynamic>> fetchLogs({
  int page = 1,
  String? action,       // 'addition' | 'change' | 'deletion'
  String? appLabel,
  String? model,
  int? userId,
  int? year,
  String? search,
  String ordering = '-action_time',
}) async {
  final params = <String, String>{
    'page': page.toString(),
    'ordering': ordering,
    if (action   != null) 'action':    action,
    if (appLabel != null) 'app_label': appLabel,
    if (model    != null) 'model':     model,
    if (userId   != null) 'user_id':   userId.toString(),
    if (year     != null) 'year':      year.toString(),
    if (search   != null && search.isNotEmpty) 'search': search,
  };
  final resp = await api.get('/api/admin/users/log-entries/', queryParams: params);
  return resp; // { count, next, previous, results }
}
```

### Log screen filter bar

```dart
// Django admin-dəki kimi: action + app_label + year + search
// Ekrandakı filter barı üçün:

const actionOptions = [
  {'value': null,         'label': 'Hamısı'},
  {'value': 'addition',  'label': 'Əlavəetmə'},
  {'value': 'change',    'label': 'Dəyişiklik'},
  {'value': 'deletion',  'label': 'Silmə'},
];

const appLabelOptions = [
  {'value': null,                   'label': 'Bütün bölmələr'},
  {'value': 'users',                'label': 'İstifadəçilər'},
  {'value': 'orders',               'label': 'Sifarişlər'},
  {'value': 'payments',             'label': 'Ödənişlər'},
  {'value': 'meals',                'label': 'Menyu'},
  {'value': 'tables',               'label': 'Masalar'},
  {'value': 'printers',             'label': 'Printerlər'},
  {'value': 'finance',              'label': 'Maliyyə'},
  {'value': 'inventory',            'label': 'Anbar'},
  {'value': 'inventory_connector',  'label': 'Anbar Əlaqələri'},
  {'value': 'auth',                 'label': 'Qruplar'},
];
```

### `change_summary` display helper

```dart
String formatChangeSummary(List<dynamic> summary) {
  if (summary.isEmpty) return '';
  final parts = <String>[];
  for (final item in summary) {
    if (item is Map) {
      if (item.containsKey('changed')) {
        final fields = (item['changed']['fields'] as List?)?.join(', ') ?? '';
        parts.add('Dəyişdi: $fields');
      } else if (item.containsKey('added')) {
        parts.add('Əlavə edildi');
      } else if (item.containsKey('deleted')) {
        parts.add('Silindi');
      }
    }
  }
  return parts.join(' • ');
}

// İstifadə:
// Text(logEntry.changeMessageDisplay)         ← lokalizasiya edilmiş
// Text(formatChangeSummary(logEntry.changeSummary))  ← manual
```

### Year filter (Django admin-dəki kimi)

```dart
// Action bar-da il seçici
final years = [2024, 2025, 2026]; // və ya serverdən dinamik al

// 2026 seçiləndə:
final logs = await fetchLogs(year: 2026);
```

---

## Quick Reference

| Method | Endpoint                        | Description                                       |
| ------ | ------------------------------- | ------------------------------------------------- |
| `GET`  | `/api/admin/users/log-entries/` | Bütün log yazıları (pagination + filter + search) |
| `GET`  | `?action=change`                | Yalnız dəyişiklik qeydləri                        |
| `GET`  | `?action=deletion`              | Yalnız silmə qeydləri                             |
| `GET`  | `?action=addition`              | Yalnız əlavəetmə qeydləri                         |
| `GET`  | `?app_label=users`              | Yalnız istifadəçi əməliyyatları                   |
| `GET`  | `?app_label=payments&year=2026` | Ödəniş əməliyyatları, 2026                        |
| `GET`  | `?user_id=25`                   | Konkret istifadəçinin bütün əməliyyatları         |
| `GET`  | `?search=Kamran`                | `object_repr` və ya `username` üzrə axtarış       |
| `GET`  | `?ordering=action_time`         | Ən köhnədən ən yeniyə sıralama                    |
| `GET`  | `?ordering=-action_time`        | Ən yenidən ən köhnəyə (default)                   |

> ⚠️ **Read-only:** Log entries yazmaq/silmək/dəyişmək mümkün deyil.  
> Log yazıları yalnız Django admin paneli vasitəsilə avtomatik yaradılır.

---

## Notes

- `object_id` həmişə **string** tipindədir (Django-nun özündən belədir), `int`-ə çevirə bilərsiniz.
- `action_time` timezone-aware-dir — `Asia/Baku` (UTC+4) ilə göstərilir.
- `change_summary` Deletion üçün həmişə `[]` qaytarır.
- `user_fullname` boş olduqda `username`-ə fallback edir.
- 1768 qeyd mövcuddur (10 aprel 2026 tarixi ilə); iri baza — pagination mütləqdir.

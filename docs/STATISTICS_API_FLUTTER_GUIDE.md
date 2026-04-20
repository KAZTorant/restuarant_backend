# Statistics (Hesabatlar) API - Flutter İnteqrasiyası üçün Qısa Təlimat

## Ümumi Məlumat

Bu API Django admin panelindəki Statistics (Hesabatlar) modulunun bütün funksionallığını təmin edir. Tables modulu ilə eyni struktur və optimizasiyalar istifadə edilib.

## Base URL
```
http://127.0.0.1:8000/api/orders/statistics/
```

## Authentication
Bütün API-lər token authentication tələb edir:
```dart
headers: {
  'Authorization': 'Bearer $token',
  'Content-Type': 'application/json',
}
```

---

## API Endpoint-ləri

### 1. 📋 Hesabatlar Siyahısı
```
GET /api/orders/statistics/
```

**Parametrlər:**
- `start_date`: Başlanma tarixi (YYYY-MM-DD)
- `end_date`: Bitmə tarixi (YYYY-MM-DD)
- `is_closed`: true/false (bağlı/açıq növbələr)
- `ordering`: -start_time, end_time, total

**Nümunə:**
```dart
final response = await http.get(
  Uri.parse('$baseUrl/api/orders/statistics/?is_closed=false&ordering=-start_time'),
  headers: headers,
);
```

**Response:** Hesabatlar siyahısı (ID, başlanma/bitmə vaxtı, məbləğlər, status)

---

### 2. 🔍 Hesabat Detalları (Bütün Tab-lar)
```
GET /api/orders/statistics/{shift_id}/
```

**Nümunə:**
```dart
final response = await http.get(
  Uri.parse('$baseUrl/api/orders/statistics/267/'),
  headers: headers,
);
```

**Response Tab-ları:**
- ✅ **ümumi_məlumat**: Başlıq, ümumi məbləğ, tarix
- 💰 **mabləğlər**: Bütün maliyyə məlumatları (başlanğıc, qazanc, çəkilən, qalan)
- 📅 **növbə_detalları**: Kim açıb/bağlayıb, vaxtlar, qeydlər, müddət
- 📊 **qeydlər_və_hesabatlar**: Bağlanma qeydi, ofisiantlar, məhsul xülasəsi
- 🔗 **statistics_order_əlaqələri**: Hesabata aid sifarişlər

---

### 3. ⏰ Cari Aktiv Növbə
```
GET /api/orders/statistics/current-shift/
```

**Nümunə:**
```dart
final response = await http.get(
  Uri.parse('$baseUrl/api/orders/statistics/current-shift/'),
  headers: headers,
);
```

**Response:** Cari növbənin real-time məlumatları (auto-refresh)

**404 Error:** Aktiv növbə yoxdursa

---

### 4. 💡 Növbə Başlatma Məlumatları
```
GET /api/orders/statistics/start-shift-info/
```

**Nümunə:**
```dart
final response = await http.get(
  Uri.parse('$baseUrl/api/orders/statistics/start-shift-info/'),
  headers: headers,
);
```

**Response:** Təklif olunan başlanğıc məbləğlər (öncəki növbənin qalan məbləği)

---

### 5. ▶️ Növbə Başlatma
```
POST /api/orders/statistics/start-shift/
```

**Request Body:**
```json
{
  "initial_cash": "11333.20",
  "initial_card": "2970.36",
  "initial_other": "0.00",
  "notes": "Səhər növbəsi"
}
```

**Nümunə:**
```dart
final response = await http.post(
  Uri.parse('$baseUrl/api/orders/statistics/start-shift/'),
  headers: headers,
  body: jsonEncode({
    'initial_cash': '11333.20',
    'initial_card': '2970.36',
    'initial_other': '0.00',
    'notes': 'Səhər növbəsi',
  }),
);
```

**Response (201):** Yeni növbənin ID-si və məlumatları

**Error (400):** "Açıq növbən var."

---

### 6. ⏹️ Növbə Bağlama
```
POST /api/orders/statistics/{shift_id}/end-shift/
```

**Request Body:**
```json
{
  "withdrawn_amount": "936.58",
  "withdrawn_from_card": "0.00",
  "withdrawn_from_other": "0.00",
  "withdrawn_notes": "maas-35\nrasxod nəqd-91"
}
```

**Nümunə:**
```dart
final response = await http.post(
  Uri.parse('$baseUrl/api/orders/statistics/267/end-shift/'),
  headers: headers,
  body: jsonEncode({
    'withdrawn_amount': '936.58',
    'withdrawn_from_card': '0.00',
    'withdrawn_from_other': '0.00',
    'withdrawn_notes': 'maas-35\nrasxod nəqd-91',
  }),
);
```

**Response (200):** Qalan məbləğlər və bağlanma məlumatları

**Error (400):** Validation xətası (məsələn, çox məbləğ çəkilməsi)

---

### 7. 📊 Aktiv Sifarişlər Statistikası
```
GET /api/orders/statistics/active-orders-stats/
```

**Nümunə:**
```dart
final response = await http.get(
  Uri.parse('$baseUrl/api/orders/statistics/active-orders-stats/'),
  headers: headers,
);
```

**Response:** Ödənilmiş və ödənilməmiş sifarişlərin statistikası

---

## UI Flow Təklifləri

### 1. Hesabatlar Səhifəsi (List)
```
┌─────────────────────────────────────┐
│  Hesabatlar 📊                      │
│  ─────────────────────────────────  │
│  🔍 Filter: [Açıq ▼] [Bu ay ▼]     │
│  ─────────────────────────────────  │
│  ✅ #267 - Sheriyar AdminPanel      │
│     Başlanma: 30 Mar 2026, 19:01    │
│     Bitmə: 31 Mar 2026, 09:43       │
│     Ümumi: 14534.14 AZN             │
│     Status: Bağlandı ✓              │
│  ─────────────────────────────────  │
│  🟢 #268 - Sheriyar AdminPanel      │
│     Başlanma: 31 Mar 2026, 10:00    │
│     Status: Açıq 🔄                 │
│     Ümumi: 2450.50 AZN              │
│  ─────────────────────────────────  │
│  [+ Yeni Növbə]                     │
└─────────────────────────────────────┘
```

**API:** `GET /api/orders/statistics/?ordering=-start_time`

---

### 2. Hesabat Detalları (Detail)
```
┌─────────────────────────────────────┐
│  ← Hesabat #267                     │
│  ─────────────────────────────────  │
│  📑 Tabs:                           │
│  [Ümumi] [Məbləğlər] [Detaylar]    │
│  ─────────────────────────────────  │
│  Ümumi Məlumat:                     │
│  • Tarix: 31 Mar 2026               │
│  • Ümumi: 14534.14 AZN              │
│  • Status: Bağlandı ✓               │
│  ─────────────────────────────────  │
│  Məbləğlər:                         │
│  💵 Nağd: 15240.14 AZN              │
│  💳 Kart: 0.00 AZN                  │
│  🔄 Digər: 0.00 AZN                 │
│  ─────────────────────────────────  │
│  [Ofisiantlar] [Məhsullar] [...]   │
└─────────────────────────────────────┘
```

**API:** `GET /api/orders/statistics/267/`

---

### 3. Növbə Başlatma
```
┌─────────────────────────────────────┐
│  Yeni Növbə Başlat                  │
│  ─────────────────────────────────  │
│  Başlanğıc məbləğlər:               │
│  (Təklif olunan)                    │
│  ─────────────────────────────────  │
│  💵 Nağd:     [11333.20] AZN        │
│  💳 Kart:     [2970.36] AZN         │
│  🔄 Digər:    [0.00] AZN            │
│  ─────────────────────────────────  │
│  📝 Qeyd:                           │
│  [Səhər növbəsi...]                 │
│  ─────────────────────────────────  │
│  [İmtina]          [Növbə Başlat]   │
└─────────────────────────────────────┘
```

**API Sequence:**
1. `GET /api/orders/statistics/start-shift-info/` → Təklif olunan məbləğləri əldə et
2. `POST /api/orders/statistics/start-shift/` → Növbəni başlat

---

### 4. Növbə Bağlama
```
┌─────────────────────────────────────┐
│  Növbə Bağlama                      │
│  ─────────────────────────────────  │
│  Əldə olan:                         │
│  💵 Nağd: 15240.14 AZN              │
│  💳 Kart: 2970.36 AZN               │
│  🔄 Digər: 0.00 AZN                 │
│  ─────────────────────────────────  │
│  Çəkilən məbləğlər:                 │
│  💵 Nağd:     [936.58] AZN          │
│  💳 Kart:     [0.00] AZN            │
│  🔄 Digər:    [0.00] AZN            │
│  ─────────────────────────────────  │
│  📝 Bağlanma qeydi:                 │
│  [maas-35                           │
│   rasxod nəqd-91]                   │
│  ─────────────────────────────────  │
│  Qalan məbləğ: 11333.20 AZN         │
│  ─────────────────────────────────  │
│  [İmtina]          [Növbə Bağla]    │
└─────────────────────────────────────┘
```

**API Sequence:**
1. `GET /api/orders/statistics/267/` → Cari məlumatları al
2. `POST /api/orders/statistics/267/end-shift/` → Növbəni bağla

---

### 5. Dashboard Widget (Cari Növbə)
```
┌─────────────────────────────────────┐
│  Cari Növbə 🟢                      │
│  ─────────────────────────────────  │
│  Başlanma: Bu gün, 10:00            │
│  Müddət: 4 saat 23 dəq              │
│  ─────────────────────────────────  │
│  💵 Nağd: 2,450.50 AZN              │
│  💳 Kart: 850.00 AZN                │
│  Ümumi: 3,300.50 AZN                │
│  ─────────────────────────────────  │
│  [Detallar]         [Növbə Bağla]   │
└─────────────────────────────────────┘
```

**API (Auto-refresh hər 30 saniyə):**
```dart
Timer.periodic(Duration(seconds: 30), (timer) async {
  final response = await http.get(
    Uri.parse('$baseUrl/api/orders/statistics/current-shift/'),
    headers: headers,
  );
  if (response.statusCode == 200) {
    updateUI(jsonDecode(response.body));
  }
});
```

---

## Model Nümunələri (Dart)

### Statistics Model
```dart
class Statistics {
  final int id;
  final String startedByUsername;
  final String startedByFullName;
  final DateTime startTime;
  final String? endedByUsername;
  final String? endedByFullName;
  final DateTime? endTime;
  final double? shiftDuration;
  final String total;
  final String cashTotal;
  final String cardTotal;
  final String otherTotal;
  final String withdrawnAmount;
  final String withdrawnFromCard;
  final String withdrawnFromOther;
  final String remainingCash;
  final String remainingCard;
  final String remainingOther;
  final bool isClosed;
  final String status;
  final String date;

  Statistics({
    required this.id,
    required this.startedByUsername,
    required this.startedByFullName,
    required this.startTime,
    this.endedByUsername,
    this.endedByFullName,
    this.endTime,
    this.shiftDuration,
    required this.total,
    required this.cashTotal,
    required this.cardTotal,
    required this.otherTotal,
    required this.withdrawnAmount,
    required this.withdrawnFromCard,
    required this.withdrawnFromOther,
    required this.remainingCash,
    required this.remainingCard,
    required this.remainingOther,
    required this.isClosed,
    required this.status,
    required this.date,
  });

  factory Statistics.fromJson(Map<String, dynamic> json) {
    return Statistics(
      id: json['id'],
      startedByUsername: json['started_by_username'],
      startedByFullName: json['started_by_full_name'],
      startTime: DateTime.parse(json['start_time']),
      endedByUsername: json['ended_by_username'],
      endedByFullName: json['ended_by_full_name'],
      endTime: json['end_time'] != null ? DateTime.parse(json['end_time']) : null,
      shiftDuration: json['shift_duration']?.toDouble(),
      total: json['total'],
      cashTotal: json['cash_total'],
      cardTotal: json['card_total'],
      otherTotal: json['other_total'],
      withdrawnAmount: json['withdrawn_amount'],
      withdrawnFromCard: json['withdrawn_from_card'],
      withdrawnFromOther: json['withdrawn_from_other'],
      remainingCash: json['remaining_cash'],
      remainingCard: json['remaining_card'],
      remainingOther: json['remaining_other'],
      isClosed: json['is_closed'],
      status: json['status'],
      date: json['date'],
    );
  }
}
```

### Statistics Detail Model
```dart
class StatisticsDetail {
  final GeneralInfo generalInfo;
  final Amounts amounts;
  final ShiftDetails shiftDetails;
  final NotesAndReports notesAndReports;
  final List<StatisticsOrder> statisticsOrders;

  StatisticsDetail({
    required this.generalInfo,
    required this.amounts,
    required this.shiftDetails,
    required this.notesAndReports,
    required this.statisticsOrders,
  });

  factory StatisticsDetail.fromJson(Map<String, dynamic> json) {
    return StatisticsDetail(
      generalInfo: GeneralInfo.fromJson(json['ümumi_məlumat']),
      amounts: Amounts.fromJson(json['mabləğlər']),
      shiftDetails: ShiftDetails.fromJson(json['növbə_detalları']),
      notesAndReports: NotesAndReports.fromJson(json['qeydlər_və_hesabatlar']),
      statisticsOrders: (json['statistics_order_əlaqələri'] as List)
          .map((e) => StatisticsOrder.fromJson(e))
          .toList(),
    );
  }
}
```

---

## API Service Nümunəsi (Dart)

```dart
class StatisticsApiService {
  final String baseUrl;
  final String token;

  StatisticsApiService({required this.baseUrl, required this.token});

  Map<String, String> get _headers => {
    'Authorization': 'Bearer $token',
    'Content-Type': 'application/json',
  };

  // List statistics
  Future<List<Statistics>> getStatisticsList({
    String? startDate,
    String? endDate,
    bool? isClosed,
    String? ordering = '-start_time',
  }) async {
    final queryParams = <String, String>{};
    if (startDate != null) queryParams['start_date'] = startDate;
    if (endDate != null) queryParams['end_date'] = endDate;
    if (isClosed != null) queryParams['is_closed'] = isClosed.toString();
    if (ordering != null) queryParams['ordering'] = ordering;

    final uri = Uri.parse('$baseUrl/api/orders/statistics/')
        .replace(queryParameters: queryParams);
    
    final response = await http.get(uri, headers: _headers);
    
    if (response.statusCode == 200) {
      final List<dynamic> data = jsonDecode(response.body);
      return data.map((e) => Statistics.fromJson(e)).toList();
    } else {
      throw Exception('Failed to load statistics');
    }
  }

  // Get statistics detail
  Future<StatisticsDetail> getStatisticsDetail(int shiftId) async {
    final response = await http.get(
      Uri.parse('$baseUrl/api/orders/statistics/$shiftId/'),
      headers: _headers,
    );
    
    if (response.statusCode == 200) {
      return StatisticsDetail.fromJson(jsonDecode(response.body));
    } else {
      throw Exception('Failed to load statistics detail');
    }
  }

  // Get current shift
  Future<CurrentShift?> getCurrentShift() async {
    final response = await http.get(
      Uri.parse('$baseUrl/api/orders/statistics/current-shift/'),
      headers: _headers,
    );
    
    if (response.statusCode == 200) {
      return CurrentShift.fromJson(jsonDecode(response.body));
    } else if (response.statusCode == 404) {
      return null; // No active shift
    } else {
      throw Exception('Failed to load current shift');
    }
  }

  // Get start shift info
  Future<StartShiftInfo> getStartShiftInfo() async {
    final response = await http.get(
      Uri.parse('$baseUrl/api/orders/statistics/start-shift-info/'),
      headers: _headers,
    );
    
    if (response.statusCode == 200) {
      return StartShiftInfo.fromJson(jsonDecode(response.body));
    } else {
      throw Exception('Failed to load start shift info');
    }
  }

  // Start shift
  Future<StartShiftResponse> startShift({
    required String initialCash,
    required String initialCard,
    required String initialOther,
    String? notes,
  }) async {
    final response = await http.post(
      Uri.parse('$baseUrl/api/orders/statistics/start-shift/'),
      headers: _headers,
      body: jsonEncode({
        'initial_cash': initialCash,
        'initial_card': initialCard,
        'initial_other': initialOther,
        'notes': notes ?? '',
      }),
    );
    
    if (response.statusCode == 201) {
      return StartShiftResponse.fromJson(jsonDecode(response.body));
    } else {
      final error = jsonDecode(response.body)['error'];
      throw Exception(error);
    }
  }

  // End shift
  Future<EndShiftResponse> endShift({
    required int shiftId,
    required String withdrawnAmount,
    required String withdrawnFromCard,
    required String withdrawnFromOther,
    String? withdrawnNotes,
  }) async {
    final response = await http.post(
      Uri.parse('$baseUrl/api/orders/statistics/$shiftId/end-shift/'),
      headers: _headers,
      body: jsonEncode({
        'withdrawn_amount': withdrawnAmount,
        'withdrawn_from_card': withdrawnFromCard,
        'withdrawn_from_other': withdrawnFromOther,
        'withdrawn_notes': withdrawnNotes ?? '',
      }),
    );
    
    if (response.statusCode == 200) {
      return EndShiftResponse.fromJson(jsonDecode(response.body));
    } else {
      final error = jsonDecode(response.body)['error'];
      throw Exception(error);
    }
  }

  // Get active orders stats
  Future<ActiveOrdersStats> getActiveOrdersStats() async {
    final response = await http.get(
      Uri.parse('$baseUrl/api/orders/statistics/active-orders-stats/'),
      headers: _headers,
    );
    
    if (response.statusCode == 200) {
      return ActiveOrdersStats.fromJson(jsonDecode(response.body));
    } else {
      throw Exception('Failed to load active orders stats');
    }
  }
}
```

---

## Testing

### Postman-da Test Etmək

1. **Environment yaradın:**
```
base_url: http://127.0.0.1:8000
token: your_auth_token_here
```

2. **Collection yaradın və test edin:**
```
✅ List Statistics
✅ Get Statistics Detail
✅ Get Current Shift
✅ Get Start Shift Info
✅ Start Shift
✅ End Shift
✅ Active Orders Stats
```

---

## Əlavə Qeydlər

### ✨ Optimizasyonlar
- ✅ `select_related` və `prefetch_related` istifadə olunub
- ✅ Minimal database query-lər
- ✅ Tables modulu ilə eyni struktur

### 🔒 Security
- ✅ Authentication tələb olunur
- ✅ İstifadəçi yalnız öz növbəsini bağlaya bilər
- ✅ Input validation

### 📱 Real-time
- ✅ Current shift auto-refresh dəstəkləyir
- ✅ Active orders stats real-time

### 📚 Tam Dokumentasiya
Ətraflı məlumat üçün bax: `docs/STATISTICS_API_DOCUMENTATION.md`

---

## Suallar və Dəstək

Suallarınız varsa və ya köməyə ehtiyacınız varsa, backend developer ilə əlaqə saxlayın.

**Uğurlar! 🚀**

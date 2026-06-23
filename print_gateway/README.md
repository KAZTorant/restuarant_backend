# Print Gateway Service (Node.js)

> **Məqsəd:** Remote Django serverdən gələn çap sorğularını restoranın lokal şəbəkəsində (LAN/kabel) quraşdırılmış **XPrinter** termal printerlərə çatdırmaq.

---

## Problem

Hal-hazırda `apps/printers/utils/service_v2.py` birbaşa TCP socket ilə printerə qoşulur:

```
Django (remote server) --X--> XPrinter (192.168.x.x:9100)
```

Remote server lokal IP-yə çata bilmir. Ona görə çap yalnız server eyni LAN-da olanda işləyir.

**Həll:** Restoranda kiçik Node.js agent işləyir. O, LAN-da printerlərə çatır; remote server isə bu agenta HTTP/WebSocket ilə sorğu göndərir.

```
┌─────────────────┐         HTTPS/WSS          ┌──────────────────────┐
│  Django Backend │  ───────────────────────►  │  Print Gateway       │
│  (remote cloud) │   çap sorğusu + mətn       │  (Node.js, LAN-da)   │
└─────────────────┘                            └──────────┬───────────┘
        ▲                                                  │ TCP :9100
        │                                                  ▼
   Frontend / Admin                               ┌──────────────────────┐
   (API çağırır)                                  │  XPrinter (main)     │
                                                  │  XPrinter (worker)   │
                                                  └──────────────────────┘
```

---

## Dəstəklənməli çap ssenariləri

Mövcud `PrinterService` funksionallığı tam əhatə olunmalıdır:

| Mənbə | Ssenari | Printer | Django metodu |
|-------|---------|---------|---------------|
| **Frontend** | Hesab çeki (masa) | Main | `print_orders_for_table()` |
| **Frontend** | Ödəniş sonrası çek | Main | `print_orders_for_table(is_paid=True)` |
| **Frontend** | Mətbəx/hazırlanma çeki | Worker | `send_to_worker_printer()` |
| **Admin** | Çek yenidən çap | Main / Worker | `ReceiptAdmin.reprint` |
| **Admin** | Növbə yekunu | Main | `print_shift_summary()` |
| **Admin** | Z-hesabat | Main | `print_z_hesabat()` |
| **Admin** | Satılmış məhsullar | Main | `print_order_items_summary()` |
| **Admin** | Ödəniş hesablaması | Main | `print_payment_calculation()` |
| **Admin** | Silinmə çeki | Worker | `send_deletion_receipt()` |
| **Admin** | Test səhifəsi | Seçilmiş | `send_raw_receipt()` |

---

## Texniki protokol (XPrinter / ESC-POS)

Gateway aşağıdakı qaydalarla uyğun olmalıdır (mövcud Python kodu ilə eyni):

| Parametr | Dəyər |
|----------|-------|
| Protokol | Raw TCP |
| Port | `9100` (default) |
| Encoding | `cp857` |
| Simvol mapping | AZ hərfləri → ASCII (`ə→e`, `ş→s`, `ç→c`, ...) |
| Kəsmə | `\x1D\x56\x00` (ESC/POS full cut) |
| Səs | `\x1B\x42\x03\x02` (3 beep) |
| Timeout | 5 saniyə |

```javascript
// src/printer/escpos.js (nümunə)
const ESC_CUT = Buffer.from([0x1d, 0x56, 0x00]);
const BEEP    = Buffer.from([0x1b, 0x42, 0x03, 0x02]);

const AZ_MAP = {
  'ə':'e','Ə':'E','ı':'i','İ':'I','ö':'o','Ö':'O',
  'ü':'u','Ü':'U','ğ':'g','Ğ':'G','ş':'s','Ş':'S','ç':'c','Ç':'C',
};

function mapAzChars(text) {
  return text.replace(/[əƏıİöÖüÜğĞşŞçÇ]/g, ch => AZ_MAP[ch] ?? ch);
}

async function sendToPrinter(text, ip, port = 9100) {
  const net = require('net');
  const mapped = mapAzChars(text);
  const payload = Buffer.concat([
    Buffer.from(mapped, 'cp857'),
    ESC_CUT,
    BEEP,
  ]);

  return new Promise((resolve, reject) => {
    const socket = net.createConnection({ host: ip, port, timeout: 5000 }, () => {
      socket.write(payload, err => {
        socket.end();
        err ? reject(err) : resolve({ status: 200 });
      });
    });
    socket.on('error', reject);
    socket.on('timeout', () => { socket.destroy(); reject(new Error('timeout')); });
  });
}
```

> **Qeyd:** Çek formatlaşdırması Django-da qalır. Gateway yalnız hazır `text` alır və printerə göndərir. Beləliklə frontend/admin-də eyni görünüş saxlanılır.

---

## Əlaqə modeli (remote → local)

Remote server lokal IP-yə birbaşa çata bilmədiyi üçün 3 variant:

### Variant A — Outbound WebSocket (tövsiyə olunur)

Gateway serverə **özü qoşulur**. Port forwarding lazım deyil.

```
Gateway ──WSS──► Django (/ws/print-jobs/)
Django job queue-ya yazır → Gateway çəkir → LAN printerə göndərir → nəticəni geri bildirir
```

**Üstünlüklər:** Firewall-friendly, NAT arxasında işləyir, restoran internet kəsilsə retry edilir.

### Variant B — Inbound HTTP (tunnel ilə)

Cloudflare Tunnel / ngrok vasitəsilə gateway expose edilir.

```
Django ──POST──► https://print-restoran1.example.com/print
```

### Variant C — VPN

Site-to-site VPN (WireGuard). Django birbaşa `http://192.168.1.50:3000/print` çağırır.

**MVP üçün:** Variant A (WebSocket) və ya Variant B (HTTP + API key).

---

## API spesifikasiyası

### `POST /api/v1/print`

Hazır formatlanmış mətni printerə göndərir.

**Headers:**
```
Authorization: Bearer <PRINT_GATEWAY_API_KEY>
Content-Type: application/json
X-Request-Id: <uuid>   // idempotency / log
```

**Body:**
```json
{
  "text": "================================\n        Qonaq Baku\n...",
  "target": {
    "type": "main"
  },
  "meta": {
    "receipt_type": "customer",
    "table_id": 12,
    "order_ids": [101, 102],
    "source": "frontend"
  }
}
```

**Target növləri:**

| `target.type` | Təsvir |
|---------------|--------|
| `main` | Config-dəki əsas printer |
| `ip` | `{ "type": "ip", "ip": "192.168.1.50", "port": 9100 }` |
| `name` | `{ "type": "name", "name": "Mətbəx printer" }` |

**Cavab (200):**
```json
{
  "success": true,
  "message": "Çek uğurla çap edildi.",
  "printer": { "ip": "192.168.1.50", "port": 9100 },
  "duration_ms": 142
}
```

**Cavab (502 — printer offline):**
```json
{
  "success": false,
  "message": "Printerə qoşulmaq mümkün olmadı.",
  "error": "ECONNREFUSED"
}
```

---

### `POST /api/v1/print/batch`

Bir sorğuda bir neçə worker printerə (mətbəx çeki ssenarisi).

```json
{
  "jobs": [
    {
      "text": "...",
      "target": { "type": "ip", "ip": "192.168.1.51", "port": 9100 },
      "meta": { "receipt_type": "preparation", "preparation_place": "Mətbəx" }
    },
    {
      "text": "...",
      "target": { "type": "ip", "ip": "192.168.1.52", "port": 9100 },
      "meta": { "receipt_type": "preparation", "preparation_place": "Bar" }
    }
  ]
}
```

---

### `GET /api/v1/health`

```json
{
  "status": "ok",
  "uptime_sec": 86400,
  "printers": {
    "main": { "ip": "192.168.1.50", "reachable": true },
    "workers": [
      { "name": "Mətbəx", "ip": "192.168.1.51", "reachable": true },
      { "name": "Bar", "ip": "192.168.1.52", "reachable": false }
    ]
  }
}
```

---

### `GET /api/v1/printers/scan`

LAN-da port `9100` scan (admin panel üçün).

```json
{
  "found": [
    { "ip": "192.168.1.50", "port": 9100, "name": "POS Printer" },
    { "ip": "192.168.1.51", "port": 9100, "name": "POS Printer" }
  ],
  "subnet": "192.168.1.",
  "scan_duration_ms": 3200
}
```

---

### `POST /api/v1/test`

Test səhifəsi göndərir (admin `send_test_page_action` ekvivalenti).

```json
{
  "target": { "type": "ip", "ip": "192.168.1.50", "port": 9100 }
}
```

---

## WebSocket protokolu (Variant A)

**Gateway → Server qoşulma:**
```
wss://api.example.com/ws/print-gateway/?token=<GATEWAY_TOKEN>&location_id=1
```

**Server → Gateway (job):**
```json
{
  "type": "print_job",
  "job_id": "uuid",
  "payload": {
    "text": "...",
    "target": { "type": "main" },
    "meta": { "receipt_type": "customer", "table_id": 5 }
  }
}
```

**Gateway → Server (nəticə):**
```json
{
  "type": "print_result",
  "job_id": "uuid",
  "success": true,
  "status_code": 200,
  "message": "Çek uğurla çap edildi."
}
```

**Gateway → Server (heartbeat, hər 30s):**
```json
{
  "type": "heartbeat",
  "printers_status": { "main": true, "workers": [...] }
}
```

---

## Layihə strukturu

```
print_gateway/
├── package.json
├── .env.example
├── README.md
├── src/
│   ├── index.js                 # entrypoint
│   ├── config.js                # env, printer config
│   ├── server/
│   │   ├── http.js              # Express/Fastify REST API
│   │   └── ws-client.js         # outbound WebSocket (optional)
│   ├── printer/
│   │   ├── escpos.js            # encoding, cut, beep
│   │   ├── tcp-sender.js        # socket göndərmə
│   │   └── scanner.js           # LAN scan (9100)
│   ├── middleware/
│   │   ├── auth.js              # API key yoxlama
│   │   └── logger.js
│   └── jobs/
│       ├── queue.js             # retry / offline buffer
│       └── processor.js
├── config/
│   └── printers.json            # lokal printer siyahısı
└── scripts/
    ├── install-service.sh       # systemd / pm2
    └── discover-printers.js
```

---

## Konfiqurasiya

### `.env.example`

```env
# Server
PORT=3000
NODE_ENV=production
PRINT_GATEWAY_API_KEY=change-me-long-random-string

# Django backend (WebSocket mode)
BACKEND_WS_URL=wss://api.qonaqbaku.az/ws/print-gateway/
GATEWAY_TOKEN=location-specific-token
LOCATION_ID=1

# Connection mode: "http" | "websocket" | "both"
MODE=both

# Printer defaults
MAIN_PRINTER_IP=192.168.1.50
MAIN_PRINTER_PORT=9100

# Network scan
SCAN_SUBNET=192.168.1.
SCAN_PORT=9100

# Retry
PRINT_RETRY_COUNT=3
PRINT_RETRY_DELAY_MS=2000
```

### `config/printers.json`

```json
{
  "main": {
    "name": "Kassa printer",
    "ip": "192.168.1.50",
    "port": 9100
  },
  "workers": [
    { "name": "Mətbəx", "ip": "192.168.1.51", "port": 9100 },
    { "name": "Bar", "ip": "192.168.1.52", "port": 9100 }
  ]
}
```

---

## Django inteqrasiyası

### Settings (`config/settings.py`)

```python
PRINT_GATEWAY_ENABLED = env.bool("PRINT_GATEWAY_ENABLED", default=False)
PRINT_GATEWAY_URL = env("PRINT_GATEWAY_URL", default="http://127.0.0.1:3000")
PRINT_GATEWAY_API_KEY = env("PRINT_GATEWAY_API_KEY", default="")
PRINT_GATEWAY_MODE = env("PRINT_GATEWAY_MODE", default="http")  # http | websocket
PRINT_GATEWAY_TIMEOUT = env.int("PRINT_GATEWAY_TIMEOUT", default=10)
```

### Adapter (`apps/printers/utils/gateway_client.py`)

```python
import requests
from django.conf import settings

class PrintGatewayClient:
    @staticmethod
    def send(text, target=None, meta=None):
        if not settings.PRINT_GATEWAY_ENABLED:
            return None  # fallback: direct socket

        payload = {
            "text": text,
            "target": target or {"type": "main"},
            "meta": meta or {},
        }
        resp = requests.post(
            f"{settings.PRINT_GATEWAY_URL}/api/v1/print",
            json=payload,
            headers={"Authorization": f"Bearer {settings.PRINT_GATEWAY_API_KEY}"},
            timeout=settings.PRINT_GATEWAY_TIMEOUT,
        )
        return resp
```

### `service_v2.py` dəyişikliyi (minimal)

`_send_text_to_printer` metodunda:

```python
@staticmethod
def _send_text_to_printer(text, ip_address, port):
    from apps.printers.utils.gateway_client import PrintGatewayClient
    from django.conf import settings

    if settings.PRINT_GATEWAY_ENABLED:
        resp = PrintGatewayClient.send(
            text=text,
            target={"type": "ip", "ip": ip_address, "port": port},
        )
        code = resp.status_code if resp.ok else 500
        return DummyResponse(code)

    # mövcud socket kodu (fallback / lokal dev)
    ...
```

> Frontend və Admin kodu **dəyişmir** — eyni API endpoint-lər qalır, yalnız arxa planda çap gateway-ə gedir.

---

## Frontend axını (dəyişiklik yoxdur)

```
Frontend (actions.js)
  └─ POST /api/orders/{tableId}/print-check/
       └─ PrintCheckAPIView
            └─ PrinterService.print_orders_for_table()
                 └─ _format_customer_receipt()
                 └─ PrintGatewayClient.send()  ← yeni
```

Mövcud frontend çağırışları:
- `KazzaAPI.printCheck(tableId)` → hesab çeki
- `KazzaAPI.deleteCheck(tableId)` → çek statusunu sıfırlayır (çap etmir)

---

## Admin axını

| Admin əməliyyat | Django yolu | Gateway target |
|-----------------|-------------|----------------|
| Receipt reprint | `/admin/printers/receipt/reprint/<id>/` | main və ya worker IP |
| Test page | Printer admin action | seçilmiş printer |
| Növbə yekunu / Z / Məhsul xülasəsi | Summary admin | main |
| Confirm → worker | `ConfirmOrderItemsToWorkerPrintersAPIView` | batch worker jobs |

---

## package.json (tövsiyə)

```json
{
  "name": "print-gateway",
  "version": "1.0.0",
  "description": "Local print relay for XPrinter thermal printers",
  "main": "src/index.js",
  "scripts": {
    "start": "node src/index.js",
    "dev": "nodemon src/index.js",
    "scan": "node scripts/discover-printers.js"
  },
  "dependencies": {
    "dotenv": "^16.4.0",
    "express": "^4.21.0",
    "iconv-lite": "^0.6.3",
    "ws": "^8.18.0",
    "pino": "^9.0.0",
    "uuid": "^10.0.0"
  },
  "devDependencies": {
    "nodemon": "^3.1.0"
  },
  "engines": {
    "node": ">=18"
  }
}
```

`iconv-lite` — Node.js-də `cp857` encoding üçün (Python `encode('cp857')` ekvivalenti).

---

## Deployment (restoran PC / mini PC)

1. Node.js 18+ quraşdır
2. Repo klonla / `print_gateway` qovluğunu kopyala
3. `npm install && cp .env.example .env` — printer IP-lərini doldur
4. PM2 və ya systemd ilə avtomatik start:

```bash
# PM2
npm install -g pm2
pm2 start src/index.js --name print-gateway
pm2 save && pm2 startup
```

5. PC eyni LAN-da olmalıdır (kabel/WiFi — printer subnet-i ilə)
6. Firewall: daxili trafik üçün port `9100` outbound açıq olmalıdır

---

## Təhlükəsizlik

| Tələb | Həll |
|-------|------|
| Sorğu autentifikasiyası | `Bearer` API key (hər lokasiya üçün unikal) |
| HTTPS | Gateway REST yalnız localhost/tunnel üzərindən; WSS TLS ilə |
| IP whitelist | Optional: yalnız Django server IP-sindən HTTP qəbul et |
| Rate limit | Dəqiqədə max 60 print sorğusu |
| Log | `text` logda saxlanmır (yalnız meta: table_id, receipt_type) |
| Idempotency | `X-Request-Id` ilə təkrar çapın qarşısı |

---

## MVP planı

### Faza 1 — Core (1-2 gün)
- [ ] TCP sender (`cp857`, cut, beep, AZ mapping)
- [ ] `POST /api/v1/print` + auth
- [ ] `GET /api/v1/health`
- [ ] `printers.json` config
- [ ] Django `PrintGatewayClient` + `PRINT_GATEWAY_ENABLED` flag

### Faza 2 — Tam inteqrasiya (1 gün)
- [ ] `POST /api/v1/print/batch` (worker printers)
- [ ] Bütün `PrinterService` metodlarını gateway-ə yönləndir
- [ ] Frontend print-check test
- [ ] Admin reprint + test page test

### Faza 3 — Etibarlılıq (1 gün)
- [ ] Retry queue (printer offline olanda)
- [ ] WebSocket outbound mode
- [ ] LAN scanner endpoint
- [ ] PM2/systemd deploy script

### Faza 4 — Monitorinq (optional)
- [ ] Printer status dashboard
- [ ] Telegram/Slack alert (printer offline)
- [ ] Print job history (lokal SQLite)

---

## Test planı

```bash
# 1. Health
curl http://localhost:3000/api/v1/health

# 2. Test çap
curl -X POST http://localhost:3000/api/v1/test \
  -H "Authorization: Bearer $PRINT_GATEWAY_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"target":{"type":"main"}}'

# 3. Real çek mətni
curl -X POST http://localhost:3000/api/v1/print \
  -H "Authorization: Bearer $PRINT_GATEWAY_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"text":"================================\n        Qonaq Baku\n================================\n\n\n\n","target":{"type":"main"}}'

# 4. Django-dan (frontend simulyasiya)
curl -X POST https://api.example.com/api/orders/5/print-check/ \
  -H "Authorization: Bearer <user-jwt>"
```

**Yoxlanılacaq ssenarilər:**
- [ ] Frontend: masa çeki çap
- [ ] Frontend: ödəniş + çek
- [ ] Frontend: confirm → mətbəx printerləri
- [ ] Admin: receipt reprint
- [ ] Admin: növbə yekunu / Z-hesabat
- [ ] Printer söndürülüb → düzgün error mesajı
- [ ] Gateway restart → pending job-lar retry

---

## Qeydlər

- **XPrinter** modelləri adətən port `9100`-də raw ESC/POS qəbul edir; driver lazım deyil.
- Çek eni: **48 simvol** (mövcud formatlaşdırmada sabit).
- Worker çeklərində ESC/POS font ölçüsü komandaları (`\x1D!`) mətnin içində gəlir — gateway onları olduğu kimi ötürməlidir.
- Development-da `PRINT_GATEWAY_ENABLED=false` saxla, birbaşa socket fallback işləsin.

---

## Əlaqəli fayllar (mövcud backend)

| Fayl | Rol |
|------|-----|
| `apps/printers/utils/service_v2.py` | Çek formatlaşdırma + çap |
| `apps/printers/apis.py` | Frontend print-check API |
| `apps/orders/apis/orders/confirm.py` | Worker printer çap |
| `apps/payments/apis/pay_table_orders.py` | Ödəniş çeki |
| `apps/printers/admin.py` | Admin reprint, scan, test |
| `apps/printers/models/printer.py` | Printer model (IP, port, is_main) |
| `frontend/static/frontend/js/actions.js` | Frontend "Hesab Çeki" düyməsi |

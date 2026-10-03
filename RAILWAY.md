# Railway Deploy

## 1. Layihəni Railway-ə qoş

1. [railway.app](https://railway.app) hesabına daxil olun.
2. **New Project** → **Deploy from GitHub repo** → `restuarant_backend` reposunu seçin.
3. **Add Service** → **Database** → **PostgreSQL** əlavə edin.
4. Django servisində **Variables** bölməsində PostgreSQL servisini reference edin (`DATABASE_URL` avtomatik gəlir).

## 2. Environment variables

| Dəyişən | Məcburi | Təsvir |
|---------|---------|--------|
| `SECRET_KEY` | Bəli | Uzun təsadüfi string |
| `DEBUG` | Bəli | Production-da `False` |
| `DATABASE_URL` | Bəli | PostgreSQL (Railway avtomatik verir) |
| `ALLOWED_HOSTS` | Xeyr | Default: `*` |
| `CSRF_TRUSTED_ORIGINS` | Tövsiyə | `https://<your-domain>.up.railway.app` |
| `CUSTOM_DOMAINS` | Xeyr | Əlavə domainlər (default: `kazza.qr-menu.cc`) |
| `WHATSAPP_SERVICE_URL` | Xeyr | WhatsApp Node servisinin URL-i (private domain) |
| `WHATSAPP_API_KEY` | Tövsiyə | Django və WhatsApp servisində eyni gizli açar |
| `PRINTER_URL` | Xeyr | Print gateway URL-i |

Tam siyahı üçün `.env.example` faylına baxın.

## 3. Deploy axını

Build zamanı yalnız `requirements.txt` install olunur (Node.js / npm lazım deyil).

Deploy əvvəl avtomatik işləyir:

```bash
python manage.py ensure_superuser
```

Migration və static fayllar lazım olanda əl ilə:

```bash
python manage.py migrate --noinput
python manage.py collectstatic --noinput
```

Restoran məlumatlarını (məs. **Qonaq-Baku**) bir dəfəlik import etmək üçün deploy-dan sonra əl ilə:

```bash
python manage.py ensure_qonaq_baku
```

Admin panel `/panel/` ünvanında adi HTML/JS/CSS ilə işləyir (`admin-frontend/` qovluğu).

`ensure_superuser` superuser yoxdursa yaradır (default: `admin` / `admin123`).

Sonra Gunicorn başlayır (`bin/start.sh`).

## 4. Domain

Railway dashboard-da **Settings → Networking → Generate Domain** ilə public URL alın.

`CSRF_TRUSTED_ORIGINS` dəyişəninə həmin URL-i əlavə edin (məs: `https://restuarant-backend-production.up.railway.app`).

Xüsusi domain (məs: `kazza.qr-menu.cc`) üçün Railway **Settings → Networking → Custom Domain** bölməsində domaini backend servisinə yönəldin. Kod tərəfində `https://kazza.qr-menu.cc` avtomatik `CSRF_TRUSTED_ORIGINS`-ə əlavə olunur; əlavə domainlər üçün `CUSTOM_DOMAINS` env dəyişənindən istifadə edin.

## 5. Admin istifadəçisi

Deploy zamanı avtomatik yaradılır:

- **Username:** `admin`
- **Password:** `admin123`

Dəyişmək üçün Railway Variables:

- `SUPERUSER_USERNAME`
- `SUPERUSER_PASSWORD`
- `SUPERUSER_EMAIL`

Superuser artıq varsa, command onu toxunmur.

## 6. Qeydlər

- `pycups` cloud serverdə CUPS printer discovery üçün işləmir; network printer discovery işləyir.
- WhatsApp servisi (`whatsapp_service/`) ayrıca deploy edilməlidir. Chromium + QR sessiyası Django konteynerində işləmir; lokal `localhost` URL-i cloud-da boşdur.

## 7. WhatsApp (QR login)

Eyni repodan ikinci Railway servisi:

1. **New Service** → eyni GitHub reposu.
2. **Settings → Root Directory** = `whatsapp_service` (öz `Dockerfile` və `railway.toml` istifadə olunur).
3. **Volume** əlavə edin, mount path: `/data`. Sessiya burda qalır; volume olmasa hər restart-da QR yenidən lazımdır.
4. WhatsApp servisində dəyişənlər:
   - `WHATSAPP_SESSION_PATH=/data/session`
   - `CHROME_PATH=/usr/bin/chromium`
   - `WHATSAPP_API_KEY` — uzun təsadüfi string
5. RAM ən azı **1 GB** bir qoşulmuş restoran üçün (Chromium). Hər əlavə qoşulmuş restoran öz brauzerini açır. 512 MB-da brauzer düşür.
6. Django servisində:
   - `WHATSAPP_SERVICE_URL=http://${{WhatsApp.RAILWAY_PRIVATE_DOMAIN}}:${{WhatsApp.PORT}}`
     (servis adı dashboard-dakı adla eyni olsun)
   - `WHATSAPP_API_KEY` — WhatsApp servisindəki ilə eyni
7. Admin → **WhatsApp Konfiqurasiyaları** → **Restoran nömrəsini qoş**. Sessiya restoran slug-una görə ayrılır (`session-<slug>`). QR çıxanda həmin restoranın telefonundan Linked Devices ilə skan edin. Başqa restoranın nömrəsi bu səhifədə görünmür.
8. Həmin siyahıya müdir/sahib nömrələrini `994...` formatında yazın və aktiv saxlayın.
9. Göndərilən mesajlar **WhatsApp mesajları** siyahısında qalır (alıcı, göndərən, çatdı, oxundu).

Axın: hər restoran öz nömrəsi ilə QR login olur (göndərən). Hazırlanmış sifariş məhsulu silinəndə mesaj həmin restoranın nömrəsindən yalnız onun müdir nömrələrinə gedir. Mövcud `session` qovluğu Qonaq-Baku-ya aiddir və deploy onu köçürmür, silmir.
- Print gateway (`print_gateway/`) restoran şəbəkəsində ayrıca işləməlidir.

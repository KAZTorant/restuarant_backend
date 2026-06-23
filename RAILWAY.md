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
| `WHATSAPP_SERVICE_URL` | Xeyr | WhatsApp servis URL-i |
| `PRINTER_URL` | Xeyr | Print gateway URL-i |

Tam siyahı üçün `.env.example` faylına baxın.

## 3. Deploy axını

Build zamanı `requirements.txt` install olunur.

Deploy əvvəl avtomatik işləyir:

```bash
python manage.py migrate --noinput
python manage.py collectstatic --noinput
python manage.py ensure_superuser
```

`ensure_superuser` superuser yoxdursa yaradır (default: `admin` / `admin123`).

Sonra Gunicorn başlayır (`bin/start.sh`).

## 4. Domain

Railway dashboard-da **Settings → Networking → Generate Domain** ilə public URL alın.

`CSRF_TRUSTED_ORIGINS` dəyişəninə həmin URL-i əlavə edin (məs: `https://restuarant-backend-production.up.railway.app`).

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
- WhatsApp servisi (`whatsapp_service/`) ayrıca deploy edilməlidir.
- Print gateway (`print_gateway/`) restoran şəbəkəsində ayrıca işləməlidir.

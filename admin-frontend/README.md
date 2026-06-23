# KAZZA Admin Panel

Adi HTML/JS/CSS admin panel (`frontend/` qovluğu ilə eyni yanaşma).

## Struktur

```
admin-frontend/
  templates/admin_panel/   # Django template-lər
  static/admin_panel/      # CSS + JS
```

## URL-lər

| URL | Təsvir |
|-----|--------|
| `/panel/` | Dashboard |
| `/panel/login/` | Giriş |
| `/panel/models/<app>/<model>/` | Model siyahısı |
| `/panel/statistics/` | Növbə idarəetməsi |
| `/admin-api/` | Backend API |

Build lazım deyil — `collectstatic` ilə deploy olunur.

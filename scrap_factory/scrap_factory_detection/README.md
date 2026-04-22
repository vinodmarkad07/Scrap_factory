# scrap Factory Safety Detection System

Real-time belt & person safety detection using YOLOv8, Django, and Django-Ninja REST API.

---

## Quick Start

### Step 1 — Install dependencies
```bash
pip install -r requirements.txt
# OR double-click install.bat on Windows
```

### Step 2 — Create MySQL database
```sql
CREATE DATABASE scrap_factory CHARACTER SET utf8mb4;
```

### Step 3 — Configure .env
Edit `.env` file — set DB_PASSWORD, MODEL_PATH, VIDEO_PATH or RTSP_URL, and email credentials.

### Step 4 — Run migrations
```bash
python manage.py migrate
```

### Step 5 — Create admin user
```bash
python manage.py createsuperuser
```

### Step 6 — Place your model file
Copy `best.pt` to the path set in `MODEL_PATH` in your `.env`.

### Step 7 — Start server
```bash
python manage.py runserver 0.0.0.0:8000
```

---

## URLs

| URL | Description |
|---|---|
| `http://127.0.0.1:8000/api/docs` | Swagger API docs |
| `http://127.0.0.1:8000/admin/` | Django Admin |
| `http://127.0.0.1:8000/api/stream` | Live MJPEG stream |
| `http://127.0.0.1:8000/api/events/` | All safety events |
| `http://127.0.0.1:8000/api/dashboard?filter_type=today` | Dashboard stats |

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/auth/login` | Login |
| POST | `/api/detection/toggle` | Start or stop detection |
| GET | `/api/detection/status` | Detection status |
| GET | `/api/stream` | Live video stream |
| GET | `/api/events/` | List all events |
| GET | `/api/events/latest` | Latest event |
| GET | `/api/events/{id}` | Single event |
| DELETE | `/api/events/{id}` | Delete event |
| GET | `/api/dashboard` | Stats + graph data |

---

## Switching from Video to RTSP

When your RTSP link is ready, update `.env`:
```env
RTSP_URL=rtsp://admin:password@192.168.x.x:554/Streaming/channels/101
VIDEO_PATH=   # leave empty
```

No code changes needed — the detector auto-switches.

---

## Detection Logic

- Belt detected ONCE and region is locked
- Background subtractor (MOG2) checks belt motion every frame
- Person boxes shrunk by 15% to reduce false overlaps
- Person inside belt ROI = DANGER → email alert + screenshot saved
- Events saved to DB every 5 seconds (throttled to avoid flooding)
- MJPEG stream updated every 50ms

import os
os.environ["KMP_DUPLICATE_LIB_OK"]         = "TRUE"
os.environ["OPENCV_LOG_LEVEL"]              = "SILENT"
os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = (
    "rtsp_transport;tcp"
    "|stimeout;10000000"
    "|max_delay;1000000"
    "|threads;1"
    "|fflags;nobuffer"
)

import cv2
channels = [101,102,201,202,301,302,401,402,501,502]

for ch in channels:
    url = f"rtsp://admin:cctv%40321@182.79.56.146:554/Streaming/Channels/{ch}"
    cap = cv2.VideoCapture(url)

    if cap.isOpened():
        print("✅ WORKING:", url)
    else:        
        print("❌ NOT WORKING:", url)

    cap.release()
import numpy as np
import time 
import smtplib
import torch
import threading
from ultralytics import YOLO
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# ================= CONFIG =================
MODEL_PATH = "yolov8x.pt"

CAMERA_CONFIGS = [
    {"id": 1, "rtsp": "rtsp://admin:cctv%40321@182.79.56.146:554/Streaming/Channels/102"},
   {"id": 2, "rtsp": "rtsp://admin:cctv%40321@182.79.56.146:554/Streaming/Channels/701"},
    {"id": 3, "rtsp": "rtsp://admin:cctv%40321@182.79.56.146:554/Streaming/Channels/802"},
    {"id": 4, "rtsp": "rtsp://admin:cctv%40321@182.79.56.146:554/Streaming/Channels/502"},
    {"id": 5, "rtsp": "rtsp://admin:cctv%40321@182.79.56.146:554/Streaming/Channels/602"},
]

PERSON_CLASS_ID  = 0
CONF_THRESHOLD   = 0.30
IOU_THRESHOLD    = 0.45
MOTION_THRESHOLD = 0.0728
RECONNECT_DELAY  = 15
CONFIRM_FRAMES   = 2
BOX_SHRINK_X     = 0.10
BOX_SHRINK_Y     = 0.05

SMTP_SERVER     = "smtp.gmail.com"
SMTP_PORT       = 587
SENDER_EMAIL    = "vinodmarkad04@gmail.com"
SENDER_PASSWORD = "obgpkzuamhonjtha"
RECEIVER_EMAIL  = "autadeshekhar1@gmail.com"
ALERT_COOLDOWN  = 60
last_alert_time = 0

# ================= HELPERS =================
def shrink_box(x1, y1, x2, y2, fw, fh):
    pw, ph = x2 - x1, y2 - y1
    sx, sy = int(pw * BOX_SHRINK_X), int(ph * BOX_SHRINK_Y)
    return max(0, x1+sx), max(0, y1+sy), min(fw, x2-sx), min(fh, y2-sy)

def send_alert_email():
    global last_alert_time
    if time.time() - last_alert_time < ALERT_COOLDOWN:
        return
    last_alert_time = time.time()
    msg = MIMEMultipart()
    msg["From"]    = SENDER_EMAIL
    msg["To"]      = RECEIVER_EMAIL
    msg["Subject"] = "🚨 DANGER ALERT"
    msg.attach(MIMEText("Person detected near moving belt!", "plain"))
    try:
        s = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        s.starttls()
        s.login(SENDER_EMAIL, SENDER_PASSWORD)
        s.send_message(msg)
        s.quit()
        print("📧 Alert sent")
    except Exception as e:
        print(f"❌ Email error: {e}")

def handle_alert(cam_id, is_moving, track_id):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] ⚠️  Person in zone — Cam {cam_id} | ID {track_id}")
    if is_moving:
        print(f"[{ts}] 🚨 DANGER — belt MOVING!")
        send_alert_email()
    else:
        print(f"[{ts}] ✅ SAFE — belt stopped")

# ================= THREADED CAMERA READER =================
class CameraStream:
    def __init__(self, cam_id, rtsp_url):
        self.cam_id   = cam_id
        self.rtsp_url = rtsp_url
        self.frame    = None
        self.ok       = False
        self.running  = True
        self.lock     = threading.Lock()
        self.cap      = None
        self._open()
        threading.Thread(target=self._reader, daemon=True).start()

    def _open(self):
        try:
            if self.cap:
                self.cap.release()
        except Exception:
            pass
        self.cap = cv2.VideoCapture(self.rtsp_url, cv2.CAP_FFMPEG)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    def _reader(self):
        fail_count = 0
        while self.running:
            try:
                ret, frame = self.cap.read()
            except Exception:
                ret, frame = False, None

            if not ret or frame is None or frame.size == 0:
                fail_count += 1
                with self.lock:
                    self.ok = False
                if fail_count == 1:
                    print(f"⚠️  Camera {self.cam_id}: lost — retrying in {RECONNECT_DELAY}s")
                time.sleep(RECONNECT_DELAY)
                self._open()
                continue

            fail_count = 0
            with self.lock:
                self.frame = frame
                self.ok    = True

    def read(self):
        with self.lock:
            if self.frame is None:
                return False, None
            return self.ok, self.frame.copy()

    def stop(self):
        self.running = False
        try:
            if self.cap:
                self.cap.release()
        except Exception:
            pass

# ================= ROI =================
BELT_ROIS = {
    1: np.array([[505,0],[500,530],[600,530],[575,0]]),
    2: np.array([[585,0],[600,320],[700,320],[670,0]]),
    3: np.array([[375,120],[315,505],[515,525],[527,140]]),
    4: np.array([[560,240],[590,520],[680,520],[610,240]]),
    5: np.array([[415,410],[410,540],[470,540],[485,405]]),
}
def get_belt_polygon(cam_id):
    return BELT_ROIS.get(cam_id, np.array([[0,0],[100,0],[100,100],[0,100]]))

# =================================================
# ✅ STEP 1 — Start camera streams FIRST
#    so cameras stay alive while models load
# =================================================
print("Starting camera streams first...")
streams = {}
for cam in CAMERA_CONFIGS:
    streams[cam["id"]] = CameraStream(cam["id"], cam["rtsp"])
    print(f"  📷 Cam {cam['id']} stream started")

# Pre-create windows immediately so user sees something
for cam in CAMERA_CONFIGS:
    cv2.namedWindow(f"Camera {cam['id']}", cv2.WINDOW_NORMAL)
    cv2.resizeWindow(f"Camera {cam['id']}", 960, 540)
    blank = np.zeros((540, 960, 3), dtype=np.uint8)
    cv2.putText(blank, f"CAM {cam['id']}  |  Loading model...",
                (20, 270), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 200, 200), 2)
    cv2.imshow(f"Camera {cam['id']}", blank)
cv2.waitKey(1)

# =================================================
# ✅ STEP 2 — Now load ONE shared model
#    (not 5 separate models — saves memory and load time)
# =================================================
print("\nLoading model...")
DEVICE = 0 if torch.cuda.is_available() else "cpu"
print("🚀 GPU" if torch.cuda.is_available() else "⚠  CPU")

model = YOLO(MODEL_PATH)
if torch.cuda.is_available():
    model.to("cuda")
print("✅ Model loaded\n")

# Per-camera state (separate tracker state via predict+sort manually)
states = {}
for cam in CAMERA_CONFIGS:
    states[cam["id"]] = {
        "prev_gray":      None,
        "motion_history": [],
        "last_frame":     None,
        "person_hits":    {},
        "person_boxes":   {},
        "track_model":    YOLO(MODEL_PATH),  # own tracker per cam
    }
    if torch.cuda.is_available():
        states[cam["id"]]["track_model"].to("cuda")
    print(f"  ✅ Cam {cam['id']} tracker ready")

print("\n🟢 Running — press ESC to quit\n")

# ================= MAIN LOOP =================
try:
    while True:
        for cam in CAMERA_CONFIGS:
            cam_id = cam["id"]
            ret, frame = streams[cam_id].read()

            if not ret or frame is None:
                last = states[cam_id]["last_frame"]
                d = last.copy() if last is not None else np.zeros((540, 960, 3), dtype=np.uint8)
                cv2.putText(d, f"CAM {cam_id}  |  NO SIGNAL",
                            (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.1, (0, 0, 255), 2)
                cv2.imshow(f"Camera {cam_id}", d)
                continue

            frame = cv2.resize(frame, (960, 540))
            fh, fw = frame.shape[:2]
            state  = states[cam_id]
            state["last_frame"] = frame.copy()
            belt_polygon = get_belt_polygon(cam_id)
            track_model  = state["track_model"]

            # ===== PERSON DETECTION =====
            raw = {}
            try:
                results = track_model.track(
                    frame,
                    conf=CONF_THRESHOLD,
                    iou=IOU_THRESHOLD,
                    tracker="bytetrack.yaml",
                    persist=True,
                    device=DEVICE,
                    verbose=False,
                    imgsz=960,
                    agnostic_nms=True,
                )[0]

                if results.boxes is not None:
                    for i in range(len(results.boxes)):
                        if int(results.boxes.cls[i]) != PERSON_CLASS_ID:
                            continue
                        x1, y1, x2, y2 = map(int, results.boxes.xyxy[i])
                        x1, y1, x2, y2 = shrink_box(x1, y1, x2, y2, fw, fh)
                        tid = int(results.boxes.id[i]) if results.boxes.id is not None else -(i+1)
                        raw[tid] = (x1, y1, x2, y2)

            except Exception as e:
                print(f"⚠️  Cam {cam_id} detection error: {e}")

            # ===== HIT COUNTER =====
            new_hits, new_boxes = {}, {}
            for tid, box in raw.items():
                new_hits[tid]  = state["person_hits"].get(tid, 0) + 1
                new_boxes[tid] = box
            state["person_hits"]  = new_hits
            state["person_boxes"] = new_boxes

            confirmed = [
                (tid, new_boxes[tid])
                for tid, hits in new_hits.items()
                if hits >= CONFIRM_FRAMES
            ]

            # ===== MOTION DETECTION =====
            mask = np.zeros(frame.shape[:2], dtype=np.uint8)
            cv2.fillPoly(mask, [belt_polygon], 255)
            mask = cv2.erode(mask, np.ones((15,15), np.uint8))

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            bx, by, bw, bh = cv2.boundingRect(belt_polygon)
            roi      = gray[by:by+bh, bx:bx+bw]
            roi_mask = mask[by:by+bh, bx:bx+bw]

            is_moving = False
            if roi.size > 0 and roi_mask.size > 0:
                roi_g = cv2.bitwise_and(roi, roi, mask=roi_mask)
                roi_g = cv2.resize(roi_g, (0,0), fx=0.5, fy=0.5)
                rm_s  = cv2.resize(roi_mask,
                                   (roi_g.shape[1], roi_g.shape[0]),
                                   interpolation=cv2.INTER_NEAREST)
                prev = state["prev_gray"]
                if prev is not None and prev.shape == roi_g.shape:
                    flow = cv2.calcOpticalFlowFarneback(
                        prev, roi_g, None, 0.5, 2, 9, 2, 3, 1.1, 0)
                    mag, _ = cv2.cartToPolar(flow[...,0], flow[...,1])
                    valid  = mag[rm_s > 0]
                    mp     = np.percentile(valid, 75) if len(valid) > 0 else 0
                    mh = state["motion_history"]
                    mh.append(mp)
                    if len(mh) > 5:
                        mh.pop(0)
                    is_moving = (sum(mh)/len(mh)) > MOTION_THRESHOLD
                state["prev_gray"] = roi_g

            # ===== DRAW =====
            bcol = (0,0,255) if is_moving else (0,255,0)
            cv2.polylines(frame, [belt_polygon], True, bcol, 2)
            cv2.putText(frame, "BELT: MOVING" if is_moving else "BELT: STOPPED",
                        (10,35), cv2.FONT_HERSHEY_SIMPLEX, 0.85, bcol, 2)
            cv2.putText(frame, f"CAM {cam_id}",
                        (855,35), cv2.FONT_HERSHEY_SIMPLEX, 0.85, (255,255,255), 2)
            cv2.putText(frame, f"Persons: {len(confirmed)}",
                        (10,65), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0,220,220), 2)

            for tid, (px1, py1, px2, py2) in confirmed:
                cx = (px1+px2)//2
                cy = (py1+py2)//2
                in_roi = cv2.pointPolygonTest(
                    belt_polygon.astype(np.float32),
                    (float(cx), float(cy)), False) >= 0
                danger = False
                if in_roi:
                    handle_alert(cam_id, is_moving, tid)
                    danger = is_moving

                col   = (0,0,255) if danger else (0,165,255) if in_roi else (0,255,255)
                label = f"DANGER #{tid}" if danger else f"IN ZONE #{tid}" if in_roi else f"Person #{tid}"

                cv2.rectangle(frame, (px1,py1), (px2,py2), col, 2)
                (tw,th),_ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 1)
                cv2.rectangle(frame, (px1, max(0,py1-th-10)), (px1+tw+6, py1), col, -1)
                cv2.putText(frame, label, (px1+3, py1-5),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0,0,0), 1)
                cv2.circle(frame, (cx,cy), 4, col, -1)

            cv2.imshow(f"Camera {cam_id}", frame)

        if cv2.waitKey(1) & 0xFF == 27:
            break

except Exception:
    import traceback
    print("\n❌ CRASH:")
    traceback.print_exc()

finally:
    print("\nShutting down...")
    for s in streams.values():
        s.stop()
    cv2.destroyAllWindows()
    print("✅ Done.")
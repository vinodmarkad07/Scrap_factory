"""
API — scrap Factory Safety Detection
=====================================
All routes mounted under /api/

Endpoints:
  POST   /api/auth/login
  POST   /api/detection/toggle
  GET    /api/detection/status
  GET    /api/stream
  POST   /api/events/
  GET    /api/events/
  GET    /api/events/latest
  GET    /api/events/{id}
  DELETE /api/events/{id}
  GET    /api/dashboard
"""

import logging
from typing import Optional
from datetime import datetime, timedelta

from django.http import HttpRequest, StreamingHttpResponse
from django.shortcuts import get_object_or_404
from django.contrib.auth import authenticate
from django.utils import timezone as dj_timezone
from django.db.models import Sum, Count
from ninja import NinjaAPI
from ninja.errors import HttpError
from ninja import NinjaAPI, File, Form
from ninja.files import UploadedFile

from .models import SafetyEvent
from .process_manager import process_manager
from .schemas import (
    SafetyEventOut, SafetyEventIn, SafetyEventUpdateIn,
    ToggleIn, DetectionStatusOut, MessageOut,
    LoginIn, LoginOut, EventsListOut
)

logger = logging.getLogger(__name__)

api = NinjaAPI(
    title="scrap Factory Safety API",
    version="1.0.0",
    description="Belt & Person detection backend for scrap Factory.",
)


# ── Auth ──────────────────────────────────────────────────────────────────────

@api.post("/auth/login", response=LoginOut, tags=["Auth"], summary="Login")
def login(request: HttpRequest, payload: LoginIn):
    user = authenticate(request, username=payload.username, password=payload.password)
    if user:
        return {"status": True, "message": "Login successful", "username": user.username}
    return {"status": False, "message": "Invalid username or password", "username": None}


# ── Detection Control ─────────────────────────────────────────────────────────

@api.post(
    "/detection/toggle",
    response={200: DetectionStatusOut, 400: MessageOut, 409: MessageOut},
    tags=["Detection"],
    summary="Start or stop detection",
)
def toggle_detection(request: HttpRequest, payload: ToggleIn):
    try:
        if payload.action == "start":
            result = process_manager.start()
        else:
            result = process_manager.stop()
        return 200, result
    except RuntimeError as exc:
        return 409, {"message": str(exc)}
    except Exception as exc:
        return 400, {"message": str(exc)}


@api.get(
    "/detection/status",
    response=DetectionStatusOut,
    tags=["Detection"],
    summary="Get detection running/stopped status",
)
def detection_status(request: HttpRequest):
    return process_manager.status


# ── Live Stream ───────────────────────────────────────────────────────────────

@api.get("/stream", tags=["Stream"], summary="Live MJPEG stream")
def live_stream(request: HttpRequest):
    """
    Open this URL in a browser or Flutter to view the live detection feed.
    URL: http://127.0.0.1:8000/api/stream
    """
    from belt_detector.detector import generate_stream
    return StreamingHttpResponse(
        generate_stream(),
        content_type="multipart/x-mixed-replace; boundary=frame",
    )


# ── Safety Events ─────────────────────────────────────────────────────────────

@api.get(
    "/events/",
    response=EventsListOut,
    tags=["Events"],
    summary="List all safety events",
)
def list_events(
    request: HttpRequest,
    event_type: Optional[str] = None,
    danger: Optional[bool] = None,
    belt_status: Optional[str] = None,
):
    qs = SafetyEvent.objects.all()
    if event_type:
        qs = qs.filter(event_type=event_type)
    if danger is not None:
        qs = qs.filter(danger=danger)
    if belt_status:
        qs = qs.filter(belt_status=belt_status)
    results = list(qs)
    return {"total": len(results), "results": results}

@api.post(
    "/events/",
    response={201: SafetyEventOut, 422: MessageOut},
    tags=["Events"],
    summary="Create a new safety event manually",
)
def create_event(
    request: HttpRequest,
    # Form fields so screenshot file can be attached in same request
    event_type:      Form[Optional[str]] = "safe",
    belt_status:     Form[Optional[str]] = "unknown",
    person_detected: Form[Optional[bool]] = False,
    danger:          Form[Optional[bool]] = False,
    email_sent:      Form[Optional[bool]] = False,
    notes:           Form[Optional[str]] = None,
    screenshot:      File[Optional[UploadedFile]] = None,
):
    """
    Create a safety event manually.
    Accepts multipart/form-data so a screenshot can be attached.

    - event_type: danger / safe / belt_moving / belt_stationary
    - belt_status: moving / stationary / unknown
    - person_detected: true / false
    - danger: true / false
    - screenshot: optional image file (JPEG/PNG)
    """
    try:
        event = SafetyEvent.objects.create(
            event_type=event_type or "safe",
            belt_status=belt_status or "unknown",
            person_detected=person_detected or False,
            danger=danger or False,
            email_sent=email_sent or False,
            notes=notes,
            screenshot=screenshot,
        )
        logger.info("SafetyEvent created manually: id=%d type=%s", event.id, event_type)
        return 201, event
    except Exception as exc:
        logger.exception("Failed to create SafetyEvent: %s", exc)
        return 422, {"message": f"Could not save event: {exc}"}

@api.get(
    "/events/latest",
    response={200: SafetyEventOut, 404: MessageOut},
    tags=["Events"],
    summary="Get latest safety event",
)
def get_latest_event(request: HttpRequest):
    event = SafetyEvent.objects.first()
    if event is None:
        return 404, {"message": "No events recorded yet."}
    return 200, event


@api.get(
    "/events/{event_id}",
    response={200: SafetyEventOut, 404: MessageOut},
    tags=["Events"],
    summary="Get single event by ID",
)
def get_event(request: HttpRequest, event_id: int):
    event = get_object_or_404(SafetyEvent, id=event_id)
    return 200, event


@api.delete(
    "/events/{event_id}",
    response={200: MessageOut, 404: MessageOut},
    tags=["Events"],
    summary="Delete a safety event",
)
def delete_event(request: HttpRequest, event_id: int):
    event = get_object_or_404(SafetyEvent, id=event_id)
    event.delete()
    return 200, {"message": f"Event {event_id} deleted."}

from django.http import JsonResponse
from detection.models import SafetyEvent
from django.utils import timezone
from datetime import timedelta

def detection_status(request):
    now = timezone.now()
    start = now - timedelta(hours=1)

    qs = SafetyEvent.objects.filter(timestamp__range=[start, now])

    return JsonResponse({
        "total": qs.count(),
        "moving": qs.filter(belt_status="moving").count(),
        "stationary": qs.filter(belt_status="stationary").count()
    })
def event_list(request):
    events = SafetyEvent.objects.order_by('-timestamp')[:10]

    data = []
    for e in events:
        data.append({
            "id": e.id,
            "area": e.area_type,
            "belt": e.belt_status,
            "time": e.timestamp.strftime("%H:%M:%S")
        })

    return JsonResponse(data, safe=False)
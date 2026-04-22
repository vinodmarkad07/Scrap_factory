from datetime import datetime
from typing import Optional, Literal
from ninja import Schema
from django.conf import settings

class SafetyEventIn(Schema):
    event_type:      str = "safe"        # danger / safe / belt_moving / belt_stationary
    belt_status:     str = "unknown"     # moving / stationary / unknown
    person_detected: bool = False
    danger:          bool = False
    email_sent:      bool = False
    notes:           Optional[str] = None

class SafetyEventOut(Schema):
    id:          int
    area_type:   Optional[str]
    belt_status: str
    timestamp:   datetime
    screenshot:  Optional[str]

    @staticmethod
    def resolve_screenshot(obj) -> Optional[str]:
        if not obj.screenshot:
            return None
        return f"{settings.SITE_URL}{obj.screenshot.url}"
    

class SafetyEventUpdateIn(Schema):
    notes: Optional[str] = None


class ToggleIn(Schema):
    action: Literal["start", "stop"]


class DetectionStatusOut(Schema):
    status:    Literal["running", "stopped"]
    pid:       Optional[int] = None
    timestamp: Optional[str] = None


class MessageOut(Schema):
    message: str


class LoginIn(Schema):
    username: str
    password: str


class LoginOut(Schema):
    status:   bool
    message:  str
    username: Optional[str] = None


class EventsListOut(Schema):
    total:   int
    results: list[SafetyEventOut]


class DashboardOut(Schema):
    filter_type:     str
    total_events:    int
    danger_count:    int
    safe_count:      int
    belt_moving:     int
    belt_stationary: int
    email_alerts:    int
    graph:           list[dict]


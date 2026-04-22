from django.db import models


class SafetyEvent(models.Model):

    BELT_STATUS = [
        ("moving", "Moving"),
        ("stationary", "Stationary"),
        ("unknown", "Unknown"),
    ]

    AREA_TYPES = [
        ("area1", "Area 1"),
        ("area2", "Area 2"),
        ("area3", "Area 3"),
      
    ]

    belt_status = models.CharField(max_length=20, choices=BELT_STATUS, default="unknown")
    area_type   = models.CharField(max_length=20, choices=AREA_TYPES, blank=True, null=True)
    screenshot  = models.ImageField(upload_to="screenshots/", blank=True, null=True)
    timestamp   = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "safety_events"
        ordering = ["-timestamp"]

    def __str__(self):
        return f"[{self.timestamp}] belt={self.belt_status} | area={self.area_type}"
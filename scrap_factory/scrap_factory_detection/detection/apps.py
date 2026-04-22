from django.apps import AppConfig


class DetectionConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "detection"

    def ready(self):
        import detection.signals  # noqa: F101

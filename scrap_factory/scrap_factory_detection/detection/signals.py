import logging
import os
from django.db.models.signals import pre_delete, post_delete
from django.dispatch import receiver
from .models import SafetyEvent

logger = logging.getLogger(__name__)


@receiver(pre_delete, sender=SafetyEvent)
def cache_screenshot_path(sender, instance, **kwargs):
    try:
        instance._cached_ss_path = instance.screenshot.path if instance.screenshot else None
    except Exception:
        instance._cached_ss_path = None


@receiver(post_delete, sender=SafetyEvent)
def delete_screenshot_file(sender, instance, **kwargs):
    path = getattr(instance, "_cached_ss_path", None)
    if path and os.path.isfile(path):
        try:
            os.remove(path)
            logger.info("Deleted screenshot: %s", path)
        except Exception as exc:
            logger.warning("Could not delete screenshot %s: %s", path, exc)

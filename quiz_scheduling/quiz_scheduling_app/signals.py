from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Vote
from .services.notification_service import NotificationService

@receiver(post_save, sender=Vote)
def handle_vote_notifications(sender, instance, created, **kwargs):
    if created:
        NotificationService.send_vote_created_notification(instance)
    elif not instance.is_active and instance.room:
        NotificationService.send_vote_completed_notification(instance)
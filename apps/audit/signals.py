"""Auto-log Talk changes and auth events via Django signals."""
from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver

from apps.talks.models import Talk

from .service import log_event

_TRACKED_FIELDS = (
    'conference_id',
    'talk_title',
    'type',
    'docdb_number',
    'plenary',
    'parallel',
    'assigned_to_id',
    'practice_talk_date',
    'practice_talk_complete',
    'final_approval',
    'complete_given',
    'comments',
    'status',
)


@receiver(pre_save, sender=Talk)
def _talk_snapshot(sender, instance, **kwargs):
    if instance.pk:
        try:
            old = Talk.objects.get(pk=instance.pk)
            instance._audit_old = {field: str(getattr(old, field)) for field in _TRACKED_FIELDS}
        except Talk.DoesNotExist:
            instance._audit_old = {}
    else:
        instance._audit_old = {}


@receiver(post_save, sender=Talk)
def _talk_saved(sender, instance, created, **kwargs):
    if created:
        log_event(action='create', obj=instance)
        return

    old = getattr(instance, '_audit_old', {})
    changes = {}
    for field in _TRACKED_FIELDS:
        new_val = str(getattr(instance, field))
        if old.get(field) != new_val:
            changes[field] = {'old': old.get(field), 'new': new_val}
    if changes:
        log_event(action='update', obj=instance, changes=changes)


@receiver(post_delete, sender=Talk)
def _talk_deleted(sender, instance, **kwargs):
    log_event(action='delete', obj=instance)


@receiver(user_logged_in)
def _user_logged_in(sender, request, user, **kwargs):
    log_event(action='login', actor=user, request=request)


@receiver(user_logged_out)
def _user_logged_out(sender, request, user, **kwargs):
    log_event(action='logout', actor=user, request=request)

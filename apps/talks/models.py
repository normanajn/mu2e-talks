from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class Conference(models.Model):
    title = models.CharField(max_length=255, db_index=True)
    start_date = models.DateField(null=True, blank=True, db_index=True)
    end_date = models.DateField(null=True, blank=True, db_index=True)
    url = models.URLField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-start_date', 'title']
        indexes = [
            models.Index(fields=['start_date', 'end_date']),
            models.Index(fields=['title']),
        ]
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(start_date__isnull=True)
                    | models.Q(end_date__isnull=True)
                    | models.Q(end_date__gte=models.F('start_date'))
                ),
                name='talks_conference_end_gte_start',
            )
        ]

    def clean(self):
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValidationError({'end_date': 'Conference end date must be on or after start date.'})

    def __str__(self):
        return self.title


class Talk(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        ACTIVE = 'active', 'Active'

    class Type(models.TextChoices):
        OVERVIEW = 'overview', 'Overview'
        CONFERENCE = 'conference', 'Conference'
        SEMINAR = 'seminar', 'Seminar'
        COLLOQUIUM = 'colloquium', 'Colloquium'
        JOB_TALK = 'job_talk', 'Job Talk'
        OTHER = 'other', 'Other'

    conference = models.ForeignKey(
        Conference,
        null=True, blank=True,
        on_delete=models.PROTECT,
        related_name='talks',
    )
    talk_title = models.CharField(max_length=255, db_index=True)
    type = models.CharField(max_length=16, choices=Type.choices, default=Type.OTHER, db_index=True)
    docdb_number = models.CharField('DocDB Number', max_length=64, blank=True, db_index=True)
    plenary = models.BooleanField('Plenary', default=False, db_index=True)
    parallel = models.BooleanField('Parallel', default=False, db_index=True)
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.PROTECT,
        related_name='assigned_talks',
    )
    practice_talk_date = models.DateField(null=True, blank=True, db_index=True)
    practice_talk_complete = models.BooleanField(default=False, db_index=True)
    final_approval = models.BooleanField(default=False, db_index=True)
    complete_given = models.BooleanField('Complete/Given', default=False, db_index=True)
    comments = models.TextField(blank=True)
    status = models.CharField(
        max_length=12,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='created_talks',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['status', '-conference__start_date', 'talk_title']
        indexes = [
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['assigned_to', 'status']),
            models.Index(fields=['practice_talk_date']),
        ]

    def clean(self):
        conference = getattr(self, 'conference', None)
        if self.status == self.Status.ACTIVE and not conference:
            raise ValidationError({'conference': 'Active talks require a conference.'})
        if self.status == self.Status.ACTIVE and not conference.title:
            raise ValidationError({'conference': 'Active talks require a conference title.'})

    @property
    def title(self):
        return self.talk_title

    def __str__(self):
        return self.talk_title

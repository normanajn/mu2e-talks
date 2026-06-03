import re

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class Conference(models.Model):
    inspire_id = models.CharField('INSPIRE ID', max_length=32, null=True, blank=True, unique=True)
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
    presentation_date = models.DateField(null=True, blank=True, db_index=True)
    type = models.CharField(max_length=16, choices=Type.choices, default=Type.OTHER, db_index=True)
    spreadsheet_type_raw = models.CharField('Spreadsheet Type', max_length=128, blank=True)
    docdb_number = models.CharField('DocDB Number', max_length=64, blank=True, db_index=True)
    docdb_password_number = models.CharField('DocDB Password Number', max_length=64, blank=True)
    docdb_certificate_number = models.CharField('DocDB Certificate Number', max_length=64, blank=True)
    plenary = models.BooleanField('Plenary', default=False, db_index=True)
    parallel = models.BooleanField('Parallel', default=False, db_index=True)
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.PROTECT,
        related_name='assigned_talks',
    )
    speaker_first_name = models.CharField(max_length=128, blank=True)
    speaker_last_name = models.CharField(max_length=128, blank=True)
    speaker_home_institution_raw = models.CharField(max_length=255, blank=True)
    speaker_institution = models.ForeignKey(
        'accounts.Institution',
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='talk_speaker_records',
    )
    duration_minutes = models.PositiveIntegerField(null=True, blank=True)
    duration_raw = models.CharField(max_length=64, blank=True)
    practice_talk_date = models.DateField(null=True, blank=True, db_index=True)
    practice_talk_complete = models.BooleanField(default=False, db_index=True)
    final_approval = models.BooleanField(default=False, db_index=True)
    committee_approved_raw = models.CharField('Committee Approval', max_length=64, blank=True)
    complete_given = models.BooleanField('Complete/Given', default=False, db_index=True)
    mu2e_program = models.CharField('Mu2e/Mu2e-II', max_length=64, blank=True, db_index=True)
    proceedings_url = models.URLField(blank=True)
    arxiv_url = models.URLField(blank=True)
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
    source_spreadsheet = models.CharField(max_length=255, blank=True)
    source_sheet = models.CharField(max_length=128, blank=True)
    source_row = models.PositiveIntegerField(null=True, blank=True)
    spreadsheet_import_notes = models.TextField(blank=True)

    class Meta:
        ordering = ['status', '-conference__start_date', 'talk_title']
        indexes = [
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['assigned_to', 'status']),
            models.Index(fields=['practice_talk_date']),
            models.Index(fields=['presentation_date']),
            models.Index(fields=['source_spreadsheet', 'source_sheet', 'source_row']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['source_spreadsheet', 'source_sheet', 'source_row'],
                name='talks_talk_unique_spreadsheet_row',
                condition=models.Q(source_spreadsheet__gt='', source_sheet__gt='', source_row__isnull=False),
            ),
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

    @property
    def docdb_url(self):
        match = re.search(r'\d+', self.docdb_number)
        if not match:
            return ''
        return f'https://mu2e-docdb.fnal.gov/cgi-bin/sso/ShowDocument?docid={match.group()}'

    def __str__(self):
        return self.talk_title

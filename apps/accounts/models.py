import re

from django.contrib.auth.models import AbstractUser
from django.db import models


def normalize_institution_alias(value):
    value = str(value or '').strip().lower()
    value = value.replace('&', ' and ')
    return re.sub(r'[^a-z0-9]+', ' ', value).strip()


def normalize_user_alias_name(first_name='', last_name='', full_name=''):
    if full_name:
        value = full_name
    else:
        value = f'{first_name or ""} {last_name or ""}'
    return normalize_institution_alias(value)


class Institution(models.Model):
    name = models.CharField(max_length=160, unique=True)
    url = models.URLField(blank=True)
    collaboration_number = models.CharField(max_length=32, blank=True)
    collaboration_code = models.CharField(max_length=32, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    sort_order = models.PositiveIntegerField(default=0, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['sort_order', 'name']

    def __str__(self):
        return self.name


class InstitutionAlias(models.Model):
    alias = models.CharField(max_length=160, unique=True)
    normalized_alias = models.CharField(max_length=160, unique=True, db_index=True, editable=False)
    institution = models.ForeignKey(
        Institution,
        on_delete=models.CASCADE,
        related_name='aliases',
    )
    notes = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['alias']
        verbose_name_plural = 'Institution aliases'

    def save(self, *args, **kwargs):
        self.normalized_alias = normalize_institution_alias(self.alias)
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.alias} -> {self.institution}'


class User(AbstractUser):
    class CollaborationPosition(models.TextChoices):
        LAB_STAFF = 'PL', 'Lab Staff (PL)'
        POST_DOC = 'PD', 'Post Doc (PD)'
        RESEARCH_SCIENTIST = 'RS', 'Research Scientist (RS)'
        GRADUATE_STUDENT = 'SG', 'Graduate Student (SG)'
        UNDERGRADUATE_STUDENT = 'SU', 'Undergraduate Student (SU)'
        UNIVERSITY_PROFESSOR = 'PU', 'Univ. Professor (PU)'
        ENGINEER = 'E', 'Engineer (E)'
        TECHNICAL = 'T', 'Technical (T)'
        PRIVATE_INSTITUTION = 'PI', 'Private Inst. (PI)'

    class Role(models.TextChoices):
        USER = 'user', 'User'
        IB_REP = 'ib_rep', 'IB Rep'
        SPOKESPERSON = 'spokesperson', 'Spokesperson'
        ADMIN = 'admin', 'Administrator'

    role = models.CharField(
        max_length=16,
        choices=Role.choices,
        default=Role.USER,
        db_index=True,
    )
    email = models.EmailField('Login Email', blank=True)
    contact_email = models.EmailField('Contact Email', blank=True)
    display_name = models.CharField(max_length=128, blank=True)
    collaboration_member_number = models.CharField(max_length=32, blank=True, db_index=True)
    collaboration_start_date = models.DateField(null=True, blank=True)
    collaboration_position = models.CharField(
        max_length=32,
        choices=CollaborationPosition.choices,
        blank=True,
    )
    collaboration_international = models.CharField(max_length=32, blank=True)
    office_phone = models.CharField(max_length=64, blank=True)
    mobile_phone = models.CharField(max_length=64, blank=True)
    other_phone = models.CharField(max_length=64, blank=True)
    collaboration_status = models.CharField(max_length=32, blank=True)
    orcid = models.CharField(max_length=32, blank=True)
    inspire_id = models.CharField(max_length=64, blank=True)
    fnal_username = models.CharField(max_length=64, blank=True, db_index=True)
    github_username = models.CharField(max_length=64, blank=True)
    collaboration_flag = models.CharField(max_length=32, blank=True)
    minority_serving = models.CharField(max_length=64, blank=True)
    roster_comments = models.TextField(blank=True)
    is_collaboration_member = models.BooleanField(default=False, db_index=True)
    roster_merge_completed = models.BooleanField(default=False, db_index=True)
    group = models.ForeignKey(
        'taxonomy.WorkGroup',
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='members',
    )
    institution = models.ForeignKey(
        Institution,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='members',
    )
    managed_groups = models.ManyToManyField(
        'taxonomy.WorkGroup',
        blank=True,
        related_name='division_heads',
    )
    managed_projects = models.ManyToManyField(
        'taxonomy.Project',
        blank=True,
        related_name='functional_leads',
    )

    class Meta:
        constraints = [
            models.CheckConstraint(
                name='accounts_user_valid_collaboration_position',
                condition=(
                    models.Q(collaboration_position='')
                    | models.Q(collaboration_position__in=[
                        'PL', 'PD', 'RS', 'SG', 'SU', 'PU', 'E', 'T', 'PI',
                    ])
                ),
            ),
        ]

    def __str__(self):
        return self.display_name or self.email or self.username

    @property
    def is_mu2e_admin(self):
        return self.role == self.Role.ADMIN

    @property
    def is_scd_admin(self):
        return self.is_mu2e_admin

    @property
    def is_ib_rep(self):
        return self.role == self.Role.IB_REP

    @property
    def is_spokesperson(self):
        return self.role == self.Role.SPOKESPERSON

    @property
    def can_manage_talks(self):
        return self.is_mu2e_admin or self.is_ib_rep or self.is_spokesperson

    @property
    def can_delete_talks(self):
        return self.is_mu2e_admin or self.is_spokesperson


class UserAlias(models.Model):
    first_name_alias = models.CharField(max_length=128, blank=True)
    last_name_alias = models.CharField(max_length=128, blank=True)
    full_name_alias = models.CharField(max_length=255, blank=True)
    normalized_alias = models.CharField(max_length=255, unique=True, db_index=True, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='aliases',
    )
    institution = models.ForeignKey(
        Institution,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='user_aliases',
    )
    notes = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['last_name_alias', 'first_name_alias', 'full_name_alias']
        verbose_name_plural = 'User aliases'

    def save(self, *args, **kwargs):
        self.normalized_alias = normalize_user_alias_name(
            self.first_name_alias,
            self.last_name_alias,
            self.full_name_alias,
        )
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.full_name_alias or f"{self.first_name_alias} {self.last_name_alias}".strip()} -> {self.user}'


class SiteSettings(models.Model):
    allow_signup = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'Site Settings'

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(pk=1, defaults={'allow_signup': False})
        return obj

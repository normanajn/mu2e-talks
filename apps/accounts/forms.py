from django import forms
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import models

from .models import Institution, InstitutionAlias, User, UserAlias


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = [
            'display_name', 'contact_email', 'institution',
            'collaboration_member_number', 'collaboration_start_date',
            'collaboration_position', 'collaboration_international',
            'office_phone', 'mobile_phone', 'other_phone', 'collaboration_status',
            'orcid', 'inspire_id', 'fnal_username', 'github_username',
            'collaboration_flag', 'minority_serving', 'roster_comments',
            'is_collaboration_member',
        ]
        widgets = {
            'collaboration_start_date': forms.DateInput(attrs={'type': 'date'}),
            'roster_comments': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['institution'].queryset = Institution.objects.filter(is_active=True)
        self.fields['institution'].required = False
        self.fields['institution'].empty_label = '- No institution -'
        self.fields['contact_email'].required = False


class AdminCreateUserForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput, label='Password')
    password2 = forms.CharField(widget=forms.PasswordInput, label='Confirm password')

    class Meta:
        model = User
        fields = ['email', 'display_name', 'institution', 'role']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['institution'].queryset = Institution.objects.filter(is_active=True)
        self.fields['institution'].required = False
        self.fields['institution'].empty_label = '- No institution -'
        self.fields['display_name'].required = False

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip()
        if User.objects.filter(username=email).exists() or User.objects.filter(email=email).exists():
            raise forms.ValidationError('A user with this email already exists.')
        return email

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get('password')
        p2 = cleaned.get('password2')
        if p1 and p2 and p1 != p2:
            self.add_error('password2', 'Passwords do not match.')
        elif p1:
            # Build an unsaved user so validators can check similarity to email etc.
            user = User(email=cleaned.get('email', ''), username=cleaned.get('email', ''))
            try:
                validate_password(p1, user=user)
            except ValidationError as e:
                self.add_error('password', e)
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = self.cleaned_data['email']
        if commit:
            user.save()
        return user


class InstitutionForm(forms.ModelForm):
    class Meta:
        model = Institution
        fields = [
            'name', 'url', 'collaboration_number', 'collaboration_code',
            'sort_order', 'is_active',
        ]


class InstitutionAliasForm(forms.ModelForm):
    class Meta:
        model = InstitutionAlias
        fields = ['alias', 'institution', 'notes', 'is_active']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['institution'].queryset = Institution.objects.all()


class InstitutionAliasImportForm(forms.Form):
    csv_file = forms.FileField(
        label='Alias CSV file',
        help_text='Upload CSV with alias and institution_name columns.',
    )


class UserAliasForm(forms.ModelForm):
    class Meta:
        model = UserAlias
        fields = [
            'first_name_alias', 'last_name_alias', 'full_name_alias',
            'user', 'institution', 'notes', 'is_active',
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['user'].queryset = User.objects.order_by('display_name', 'email', 'username')
        self.fields['institution'].queryset = Institution.objects.all()
        self.fields['institution'].required = False


class UserAliasImportForm(forms.Form):
    csv_file = forms.FileField(
        label='Alias CSV file',
        help_text='Upload CSV with first_name_alias/last_name_alias or full_name_alias plus user_email, username, or user_display_name.',
    )


class AdminEditUserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = [
            'email', 'contact_email', 'display_name', 'institution', 'role',
            'collaboration_member_number', 'collaboration_start_date',
            'collaboration_position', 'collaboration_international',
            'office_phone', 'mobile_phone', 'other_phone', 'collaboration_status',
            'orcid', 'inspire_id', 'fnal_username', 'github_username',
            'collaboration_flag', 'minority_serving', 'roster_comments',
            'is_collaboration_member', 'is_active',
        ]
        widgets = {
            'collaboration_start_date': forms.DateInput(attrs={'type': 'date'}),
            'roster_comments': forms.Textarea(attrs={'rows': 3}),
        }


class RosterImportForm(forms.Form):
    class ImportType(models.TextChoices):
        INSTITUTIONS = 'institutions', 'Institutions'
        MEMBERS = 'members', 'Members'

    import_type = forms.ChoiceField(choices=ImportType.choices)
    csv_file = forms.FileField(
        label='CSV file',
        help_text='Upload a UTF-8 CSV generated from the Mu2e collaboration workbook.',
    )

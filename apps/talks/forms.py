from django import forms

from .models import Conference, Talk


class ConferenceForm(forms.ModelForm):
    class Meta:
        model = Conference
        fields = ['title', 'start_date', 'end_date', 'url']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
        }


class TalkForm(forms.ModelForm):
    conference_title = forms.CharField(max_length=255, required=False, label='Conference Title')
    conference_start_date = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    conference_end_date = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    conference_url = forms.URLField(required=False, label='Conference URL')

    class Meta:
        model = Talk
        fields = [
            'conference',
            'talk_title',
            'type',
            'docdb_number',
            'plenary',
            'parallel',
            'assigned_to',
            'practice_talk_date',
            'practice_talk_complete',
            'final_approval',
            'complete_given',
            'comments',
            'status',
        ]
        widgets = {
            'practice_talk_date': forms.DateInput(attrs={'type': 'date'}),
            'comments': forms.Textarea(attrs={'rows': 8}),
        }

    def __init__(self, *args, user=None, allow_status=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.allow_status = allow_status
        self.fields['conference'].queryset = Conference.objects.order_by('-start_date', 'title')
        self.fields['conference'].required = False
        self.fields['type'].required = False
        self.fields['assigned_to'].required = False
        self.fields['practice_talk_date'].required = False
        if not allow_status:
            self.fields['status'].widget = forms.HiddenInput()
        if self.instance and self.instance.conference_id:
            conf = self.instance.conference
            self.fields['conference_title'].initial = conf.title
            self.fields['conference_start_date'].initial = conf.start_date
            self.fields['conference_end_date'].initial = conf.end_date
            self.fields['conference_url'].initial = conf.url

    def clean(self):
        cleaned = super().clean()
        cleaned['type'] = cleaned.get('type') or Talk.Type.OTHER
        status = cleaned.get('status') or Talk.Status.DRAFT
        if not self.allow_status:
            status = Talk.Status.DRAFT
            cleaned['status'] = Talk.Status.DRAFT
        conference = cleaned.get('conference')
        title = cleaned.get('conference_title', '').strip()
        start = cleaned.get('conference_start_date')
        end = cleaned.get('conference_end_date')
        url = cleaned.get('conference_url', '').strip()

        if start and end and end < start:
            self.add_error('conference_end_date', 'Conference end date must be on or after start date.')

        has_inline_conference = bool(title or start or end or url)
        if has_inline_conference:
            conference = conference or Conference()
            conference.title = title or conference.title
            conference.start_date = start
            conference.end_date = end
            conference.url = url
            cleaned['conference'] = conference

        if status == Talk.Status.ACTIVE and not (conference and conference.title):
            self.add_error('conference_title', 'Active talks require a conference title.')
        return cleaned

    def save(self, commit=True):
        instance = super().save(commit=False)
        title = self.cleaned_data.get('conference_title', '').strip()
        start = self.cleaned_data.get('conference_start_date')
        end = self.cleaned_data.get('conference_end_date')
        url = self.cleaned_data.get('conference_url', '').strip()
        if title or start or end or url:
            conference = instance.conference
            if conference is None:
                conference = Conference()
            conference.title = title or conference.title
            conference.start_date = start
            conference.end_date = end
            conference.url = url
            if commit:
                conference.full_clean()
                conference.save()
            instance.conference = conference
        if commit:
            instance.full_clean()
            instance.save()
            self.save_m2m()
        return instance

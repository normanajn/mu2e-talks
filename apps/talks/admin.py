from django.contrib import admin

from .models import Conference, Talk


@admin.register(Conference)
class ConferenceAdmin(admin.ModelAdmin):
    list_display = ('title', 'inspire_id', 'start_date', 'end_date', 'url')
    search_fields = ('title', 'inspire_id', 'url')
    list_filter = ('start_date',)


@admin.register(Talk)
class TalkAdmin(admin.ModelAdmin):
    list_display = (
        'talk_title',
        'conference',
        'presentation_date',
        'type',
        'assigned_to',
        'speaker_last_name',
        'speaker_first_name',
        'plenary',
        'parallel',
        'status',
        'practice_talk_date',
        'practice_talk_complete',
        'final_approval',
        'complete_given',
    )
    search_fields = (
        'talk_title', 'docdb_number', 'comments', 'conference__title', 'assigned_to__email',
        'speaker_first_name', 'speaker_last_name', 'speaker_home_institution_raw',
    )
    list_filter = ('status', 'type', 'plenary', 'parallel', 'practice_talk_complete', 'final_approval', 'complete_given', 'mu2e_program')
    autocomplete_fields = ('conference', 'assigned_to', 'speaker_institution', 'created_by')

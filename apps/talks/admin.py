from django.contrib import admin

from .models import Conference, Talk


@admin.register(Conference)
class ConferenceAdmin(admin.ModelAdmin):
    list_display = ('title', 'start_date', 'end_date', 'url')
    search_fields = ('title', 'url')
    list_filter = ('start_date',)


@admin.register(Talk)
class TalkAdmin(admin.ModelAdmin):
    list_display = (
        'talk_title',
        'conference',
        'type',
        'assigned_to',
        'plenary',
        'parallel',
        'status',
        'practice_talk_date',
        'practice_talk_complete',
        'final_approval',
        'complete_given',
    )
    search_fields = ('talk_title', 'docdb_number', 'comments', 'conference__title', 'assigned_to__email')
    list_filter = ('status', 'type', 'plenary', 'parallel', 'practice_talk_complete', 'final_approval', 'complete_given')
    autocomplete_fields = ('conference', 'assigned_to', 'created_by')

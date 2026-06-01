import shlex

import django_filters
from django import forms
from django.db.models import Q

from apps.accounts.models import User
from apps.talks.models import Talk


class TalkFilter(django_filters.FilterSet):
    search = django_filters.CharFilter(method='filter_search', label='Search')
    conference_title = django_filters.CharFilter(
        field_name='conference__title',
        lookup_expr='icontains',
        label='Conference title',
    )
    talk_title = django_filters.CharFilter(lookup_expr='icontains', label='Talk title')
    type = django_filters.ChoiceFilter(choices=Talk.Type.choices, empty_label='All types', label='Type')
    conference_after = django_filters.DateFilter(
        field_name='conference__start_date',
        lookup_expr='gte',
        label='Conference starts on/after',
    )
    conference_before = django_filters.DateFilter(
        field_name='conference__end_date',
        lookup_expr='lte',
        label='Conference ends on/before',
    )
    conference_url = django_filters.CharFilter(
        field_name='conference__url',
        lookup_expr='icontains',
        label='Conference URL',
    )
    docdb_number = django_filters.CharFilter(lookup_expr='icontains', label='DocDB Number')
    plenary = django_filters.BooleanFilter(label='Plenary')
    parallel = django_filters.BooleanFilter(label='Parallel')
    assigned_to = django_filters.ModelChoiceFilter(
        queryset=User.objects.order_by('email'),
        empty_label='All users',
        label='Assigned person',
    )
    practice_talk_date = django_filters.DateFilter(label='Practice talk date')
    practice_talk_complete = django_filters.BooleanFilter(label='Practice complete')
    final_approval = django_filters.BooleanFilter(label='Final approval')
    complete_given = django_filters.BooleanFilter(label='Complete/Given')
    status = django_filters.ChoiceFilter(choices=Talk.Status.choices, empty_label='All statuses')

    def filter_search(self, queryset, name, value):
        try:
            tokens = shlex.split(value)
        except ValueError:
            tokens = value.split()

        operators = {'AND', 'OR', 'XOR'}
        normalized = []
        prev_was_term = False
        for token in tokens:
            if token.upper() in operators:
                if prev_was_term:
                    normalized.append(token.upper())
                    prev_was_term = False
            else:
                if prev_was_term:
                    normalized.append('OR')
                normalized.append(token)
                prev_was_term = True

        if not normalized:
            return queryset

        def term_q(term):
            return (
                Q(talk_title__icontains=term)
                | Q(conference__title__icontains=term)
                | Q(conference__url__icontains=term)
                | Q(docdb_number__icontains=term)
                | Q(assigned_to__email__icontains=term)
                | Q(assigned_to__display_name__icontains=term)
                | Q(comments__icontains=term)
            )

        result = term_q(normalized[0])
        i = 1
        while i < len(normalized) - 1:
            op = normalized[i]
            next_q = term_q(normalized[i + 1])
            if op == 'AND':
                result = result & next_q
            elif op == 'XOR':
                result = (result | next_q) & ~(result & next_q)
            else:
                result = result | next_q
            i += 2

        return queryset.filter(result)

    class Meta:
        model = Talk
        fields = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in ('conference_after', 'conference_before', 'practice_talk_date'):
            self.filters[name].field.widget = forms.DateInput(attrs={'type': 'date'})

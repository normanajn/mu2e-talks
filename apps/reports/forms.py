from django import forms

from .models import AIPromptConfig


class AIPromptConfigForm(forms.ModelForm):
    class Meta:
        model = AIPromptConfig
        fields = ['system_prompt', 'user_template']
        widgets = {
            'system_prompt': forms.Textarea(attrs={'rows': 5, 'class': 'font-mono text-xs'}),
            'user_template': forms.Textarea(attrs={'rows': 12, 'class': 'font-mono text-xs'}),
        }
        labels = {
            'system_prompt': 'System prompt',
            'user_template': 'User template',
        }
        help_texts = {
            'user_template': (
                'Supported placeholders: '
                '{talks} — filtered talk data, '
                '{query} — user question, '
                '{institutions} — full institution list, '
                '{users} — full member list.'
            ),
        }

    _KNOWN_PLACEHOLDERS = {'talks', 'query', 'institutions', 'users'}

    def clean_user_template(self):
        template = self.cleaned_data.get('user_template', '')
        if '{talks}' not in template:
            raise forms.ValidationError('The template must contain {talks} as a placeholder.')
        try:
            template.format_map({k: '' for k in self._KNOWN_PLACEHOLDERS})
        except KeyError as exc:
            known = ', '.join(f'{{{k}}}' for k in sorted(self._KNOWN_PLACEHOLDERS))
            raise forms.ValidationError(
                f'Unknown placeholder {{{exc.args[0]}}} — supported: {known}.'
            ) from exc
        except ValueError as exc:
            raise forms.ValidationError(f'Invalid template syntax: {exc}') from exc
        return template

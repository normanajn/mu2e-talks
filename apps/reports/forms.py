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
                'Use {talks} where talk data is inserted. '
                'Use {query} where the user query is inserted.'
            ),
        }

    def clean_user_template(self):
        template = self.cleaned_data.get('user_template', '')
        if '{talks}' not in template:
            raise forms.ValidationError('The template must contain {talks} as a placeholder.')
        try:
            template.format(talks='', query='')
        except KeyError as exc:
            raise forms.ValidationError(
                f'Unknown placeholder {{{exc.args[0]}}} — only {{talks}} and {{query}} are supported.'
            ) from exc
        except ValueError as exc:
            raise forms.ValidationError(f'Invalid template syntax: {exc}') from exc
        return template

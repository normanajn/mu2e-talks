from django.conf import settings
from django.db import models

DEFAULT_SYSTEM = (
    "You are an analyst writing structured summaries of talks and presentations "
    "by members of the Mu2e particle physics collaboration at Fermilab. "
    "Your summaries are factual, professional, and well-organised. "
    "Use Markdown headings and bullet points. Do not invent information beyond what is provided."
)

DEFAULT_USER_TMPL = """\
{query}

## Talks (filtered selection)

{talks}

---

## Mu2e Collaboration Institutions

{institutions}

---

## Mu2e Collaboration Members

{users}
"""

DEFAULT_QUERY = (
    "Please provide a concise narrative summary of these Mu2e talks, including:\n\n"
    "1. **Overview** – date range covered, total talks, conferences, and speakers involved.\n"
    "2. **Key Themes** – the main talk types (plenary, parallel, seminar, etc.) and programs represented.\n"
    "3. **Notable Presentations** – standout contributions, especially approved and completed talks.\n"
    "4. **Summary Table** – a compact Markdown table with columns: Speaker | Conference | Date | Type | Title."
)


class AIPromptConfig(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.CASCADE,
        related_name='ai_prompt_config',
    )
    system_prompt = models.TextField(default=DEFAULT_SYSTEM)
    user_template = models.TextField(default=DEFAULT_USER_TMPL)

    class Meta:
        verbose_name = 'AI Prompt Configuration'

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(
            pk=1,
            defaults={
                'user': None,
                'system_prompt': DEFAULT_SYSTEM,
                'user_template': DEFAULT_USER_TMPL,
            },
        )
        return obj

    @classmethod
    def for_user(cls, user):
        try:
            return user.ai_prompt_config
        except cls.DoesNotExist:
            return cls.get_solo()

    @classmethod
    def get_or_create_for_user(cls, user):
        global_config = cls.get_solo()
        obj, _ = cls.objects.get_or_create(
            user=user,
            defaults={
                'system_prompt': global_config.system_prompt,
                'user_template': global_config.user_template,
            },
        )
        return obj

from django.db import migrations

# Templates that are known old defaults — update them; leave customised templates alone.
_OLD_TEMPLATES = [
    # Original template before institutions/users were added
    "{query}\n\nBelow is the Mu2e talks data matching the selected filters:\n\n{talks}\n",
    # Intermediate template with section header but no roster sections
    "{query}\n\n## Talks (filtered selection)\n\n{talks}\n",
]

_NEW_TEMPLATE = """\
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


def update_template(apps, schema_editor):
    AIPromptConfig = apps.get_model('reports', 'AIPromptConfig')
    for config in AIPromptConfig.objects.all():
        if config.user_template.strip() in [t.strip() for t in _OLD_TEMPLATES]:
            config.user_template = _NEW_TEMPLATE
            config.save(update_fields=['user_template'])


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0002_add_user_to_aipromptconfig'),
    ]

    operations = [
        migrations.RunPython(update_template, migrations.RunPython.noop),
    ]

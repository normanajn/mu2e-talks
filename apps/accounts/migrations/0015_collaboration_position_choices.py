from django.db import migrations, models


VALID_POSITIONS = {'PL', 'PD', 'RS', 'SG', 'SU', 'PU', 'E', 'T', 'PI'}


def normalize_positions(apps, schema_editor):
    User = apps.get_model('accounts', 'User')
    aliases = {
        'pl': 'PL',
        'lab staff': 'PL',
        'lab staff pl': 'PL',
        'pd': 'PD',
        'post doc': 'PD',
        'post doc pd': 'PD',
        'postdoc': 'PD',
        'rs': 'RS',
        'research scientist': 'RS',
        'research scientist rs': 'RS',
        'sg': 'SG',
        'graduate student': 'SG',
        'graduate student sg': 'SG',
        'su': 'SU',
        'undergraduate student': 'SU',
        'undergraduate student su': 'SU',
        'pu': 'PU',
        'univ professor': 'PU',
        'univ professor pu': 'PU',
        'university professor': 'PU',
        'university professor pu': 'PU',
        'e': 'E',
        'engineer': 'E',
        'engineer e': 'E',
        't': 'T',
        'technical': 'T',
        'technical t': 'T',
        'pi': 'PI',
        'private inst': 'PI',
        'private inst pi': 'PI',
        'private institution': 'PI',
        'private institution pi': 'PI',
    }
    for user in User.objects.exclude(collaboration_position=''):
        value = str(user.collaboration_position or '').strip()
        normalized = value.lower().replace('.', '').replace('(', ' ').replace(')', ' ')
        normalized = ' '.join(normalized.split())
        mapped = aliases.get(normalized)
        if value in VALID_POSITIONS:
            mapped = value
        if mapped is None:
            mapped = ''
        if user.collaboration_position != mapped:
            user.collaboration_position = mapped
            user.save(update_fields=['collaboration_position'])


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0014_useralias'),
    ]

    operations = [
        migrations.RunPython(normalize_positions, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='user',
            name='collaboration_position',
            field=models.CharField(
                blank=True,
                choices=[
                    ('PL', 'Lab Staff (PL)'),
                    ('PD', 'Post Doc (PD)'),
                    ('RS', 'Research Scientist (RS)'),
                    ('SG', 'Graduate Student (SG)'),
                    ('SU', 'Undergraduate Student (SU)'),
                    ('PU', 'Univ. Professor (PU)'),
                    ('E', 'Engineer (E)'),
                    ('T', 'Technical (T)'),
                    ('PI', 'Private Inst. (PI)'),
                ],
                max_length=32,
            ),
        ),
        migrations.AddConstraint(
            model_name='user',
            constraint=models.CheckConstraint(
                name='accounts_user_valid_collaboration_position',
                condition=(
                    models.Q(('collaboration_position', ''))
                    | models.Q(('collaboration_position__in', ['PL', 'PD', 'RS', 'SG', 'SU', 'PU', 'E', 'T', 'PI']))
                ),
            ),
        ),
    ]

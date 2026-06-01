from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Conference',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(db_index=True, max_length=255)),
                ('start_date', models.DateField(blank=True, db_index=True, null=True)),
                ('end_date', models.DateField(blank=True, db_index=True, null=True)),
                ('url', models.URLField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'ordering': ['-start_date', 'title'],
                'indexes': [
                    models.Index(fields=['start_date', 'end_date'], name='talks_confe_start_d_68017c_idx'),
                    models.Index(fields=['title'], name='talks_confe_title_00609f_idx'),
                ],
            },
        ),
        migrations.CreateModel(
            name='Talk',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('talk_title', models.CharField(db_index=True, max_length=255)),
                ('docdb_number', models.CharField(blank=True, db_index=True, max_length=64, verbose_name='DocDB Number')),
                ('practice_talk_date', models.DateField(blank=True, db_index=True, null=True)),
                ('practice_talk_complete', models.BooleanField(db_index=True, default=False)),
                ('final_approval', models.BooleanField(db_index=True, default=False)),
                ('complete_given', models.BooleanField(db_index=True, default=False, verbose_name='Complete/Given')),
                ('comments', models.TextField(blank=True)),
                ('status', models.CharField(choices=[('draft', 'Draft'), ('active', 'Active')], db_index=True, default='draft', max_length=12)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('assigned_to', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='assigned_talks', to=settings.AUTH_USER_MODEL)),
                ('conference', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='talks', to='talks.conference')),
                ('created_by', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='created_talks', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['status', '-conference__start_date', 'talk_title'],
                'indexes': [
                    models.Index(fields=['status', '-created_at'], name='talks_talk_status_a2ffe1_idx'),
                    models.Index(fields=['assigned_to', 'status'], name='talks_talk_assigne_1a0961_idx'),
                    models.Index(fields=['practice_talk_date'], name='talks_talk_practic_c4b7be_idx'),
                ],
            },
        ),
        migrations.AddConstraint(
            model_name='conference',
            constraint=models.CheckConstraint(
                condition=(
                    models.Q(('start_date__isnull', True))
                    | models.Q(('end_date__isnull', True))
                    | models.Q(('end_date__gte', models.F('start_date')))
                ),
                name='talks_conference_end_gte_start',
            ),
        ),
    ]

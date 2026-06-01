from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0007_alter_user_role'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='role',
            field=models.CharField(
                choices=[
                    ('user', 'User'),
                    ('ib_rep', 'IB Rep'),
                    ('spokesperson', 'Spokesperson'),
                    ('admin', 'Administrator'),
                ],
                db_index=True,
                default='user',
                max_length=16,
            ),
        ),
    ]

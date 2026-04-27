from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('communications', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='emailthread',
            name='thread_type',
            field=models.CharField(
                choices=[
                    ('intro', 'Intro'),
                    ('documents', 'Documents'),
                    ('requirements', 'Requirements'),
                    ('pricing', 'Pricing'),
                    ('followup', 'Follow-Up on Pricing'),
                    ('meeting', 'Meeting'),
                    ('deal', 'Deal'),
                    ('negotiation', 'Negotiation'),
                ],
                max_length=20,
            ),
        ),
    ]

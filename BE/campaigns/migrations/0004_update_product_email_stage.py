from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('campaigns', '0003_add_product_stage_config'),
    ]

    operations = [
        migrations.AlterField(
            model_name='productstageconfig',
            name='stage',
            field=models.CharField(
                choices=[
                    ('intro', 'Intro'),
                    ('documents', 'Documents'),
                    ('requirements', 'Requirements'),
                    ('pricing', 'Pricing'),
                    ('followup', 'Follow-Up on Pricing'),
                    ('meeting', 'Meeting'),
                    ('deal', 'Deal'),
                ],
                max_length=20,
            ),
        ),
    ]

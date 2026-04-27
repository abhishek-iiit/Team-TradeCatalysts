from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_add_smtp_password'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='cc_emails',
            field=models.JSONField(blank=True, default=list, help_text='List of email addresses to CC on all outbound emails'),
        ),
    ]

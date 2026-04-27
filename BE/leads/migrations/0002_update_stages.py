from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('leads', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='lead',
            name='stage',
            field=models.CharField(
                choices=[
                    ('discovered', 'Discovered'),
                    ('intro_sent', 'Intro Sent'),
                    ('documents_sent', 'Documents Sent'),
                    ('requirements_asked', 'Requirements Asked'),
                    ('pricing_sent', 'Pricing Sent'),
                    ('pricing_followup', 'Pricing Follow-Up'),
                    ('meeting_sent', 'Meeting Sent'),
                    ('deal_sent', 'Deal Sent'),
                    ('closed_won', 'Closed Won'),
                    ('closed_lost', 'Closed Lost'),
                ],
                default='discovered',
                max_length=30,
            ),
        ),
        migrations.AlterField(
            model_name='leadaction',
            name='action_type',
            field=models.CharField(
                choices=[
                    ('intro_email', 'Intro Email'),
                    ('intro_sms', 'Intro SMS'),
                    ('documents_email', 'Documents Email'),
                    ('documents_sms', 'Documents SMS'),
                    ('requirements_email', 'Requirements Email'),
                    ('requirements_sms', 'Requirements SMS'),
                    ('pricing_email', 'Pricing Email'),
                    ('pricing_sms', 'Pricing SMS'),
                    ('pricing_followup_email', 'Pricing Follow-Up Email'),
                    ('pricing_followup_sms', 'Pricing Follow-Up SMS'),
                    ('meeting_email', 'Meeting Email'),
                    ('meeting_sms', 'Meeting SMS'),
                    ('deal_email', 'Deal Email'),
                    ('deal_sms', 'Deal SMS'),
                    ('follow_up_call', 'Follow Up Call'),
                    ('meeting_scheduled', 'Meeting Scheduled'),
                    ('note', 'Note'),
                    ('ai_draft_generated', 'AI Draft Generated'),
                    ('ai_draft_approved', 'AI Draft Approved'),
                    ('ai_draft_rejected', 'AI Draft Rejected'),
                    ('deal_closed', 'Deal Closed'),
                    ('manual_takeover', 'Manual Takeover'),
                ],
                max_length=50,
            ),
        ),
    ]

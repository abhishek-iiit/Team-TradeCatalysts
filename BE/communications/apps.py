from django.apps import AppConfig


class CommunicationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'communications'

    def ready(self):
        from django.db.models.signals import post_migrate
        post_migrate.connect(_setup_gmail_poll_schedule, sender=self)


def _setup_gmail_poll_schedule(sender, **kwargs):
    try:
        from django_q.models import Schedule
        if not Schedule.objects.filter(func='communications.tasks.poll_gmail_inbox').exists():
            Schedule.objects.create(
                func='communications.tasks.poll_gmail_inbox',
                minutes=15,
                schedule_type=Schedule.MINUTES,
                repeats=-1,
            )
    except Exception:
        pass

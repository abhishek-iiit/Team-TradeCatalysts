import uuid
from datetime import timedelta

from django.conf import settings


class CalendarInviteService:
    """Builds RFC 5545 iCalendar invites and emails them to contacts via SMTP."""

    def create_event(self, lead, contact, scheduled_at, meeting_link: str = '') -> str:
        """
        Generate an event UID, build an iCal payload, and send it to the contact.
        Always returns a UID (stored as calendar_event_id). Send failures are silent.

        Returns:
            str: UUID event identifier
        """
        event_uid = str(uuid.uuid4())

        if not contact.email:
            return event_uid

        ics_content = self._build_ics(event_uid, lead, contact, scheduled_at, meeting_link)
        try:
            self._send_invite(contact, lead, ics_content, meeting_link=meeting_link)
        except Exception:
            pass

        return event_uid

    def _build_ics(self, uid, lead, contact, scheduled_at, meeting_link) -> str:
        end_at = scheduled_at + timedelta(hours=1)
        fmt = '%Y%m%dT%H%M%SZ'
        company = getattr(settings, 'SENDER_COMPANY_NAME', 'Elchemy')

        description = (
            f'Meeting with {company} regarding {lead.company_name}.'
            + (f'\\nJoin: {meeting_link}' if meeting_link else '')
        )

        lines = [
            'BEGIN:VCALENDAR',
            'VERSION:2.0',
            'PRODID:-//SalesCatalyst//EN',
            'METHOD:REQUEST',
            'BEGIN:VEVENT',
            f'UID:{uid}',
            f'SUMMARY:Meeting with {lead.company_name} — {company}',
            f'DESCRIPTION:{description}',
            f'DTSTART:{scheduled_at.strftime(fmt)}',
            f'DTEND:{end_at.strftime(fmt)}',
            f'ORGANIZER:MAILTO:{settings.EMAIL_HOST_USER}',
            (
                f'ATTENDEE;CN={contact.first_name} {contact.last_name}'
                f':MAILTO:{contact.email}'
            ),
            'STATUS:CONFIRMED',
            'SEQUENCE:0',
        ]
        if meeting_link:
            lines.append(f'LOCATION:{meeting_link}')
            lines.append(f'URL:{meeting_link}')
        lines += ['END:VEVENT', 'END:VCALENDAR']
        return '\r\n'.join(lines) + '\r\n'

    def _send_invite(self, contact, lead, ics_content: str, meeting_link: str = '') -> None:
        from django.core.mail import EmailMessage as DjangoEmailMessage

        company = getattr(settings, 'SENDER_COMPANY_NAME', 'Elchemy')
        join_line = f'\nJoin the meeting: {meeting_link}\n' if meeting_link else ''
        msg = DjangoEmailMessage(
            subject=f'Meeting Invitation: {lead.company_name} × {company}',
            body=(
                f'Dear {contact.first_name},\n\n'
                f'You are invited to a meeting with {company} regarding {lead.company_name}.\n'
                f'{join_line}\n'
                'Please accept the calendar invitation attached to add this to your calendar.\n\n'
                f'Best regards,\n{settings.EMAIL_HOST_USER}'
            ),
            from_email=settings.EMAIL_HOST_USER,
            to=[contact.email],
        )
        msg.attach('invite.ics', ics_content.encode('utf-8'), 'text/calendar; method=REQUEST')
        msg.send(fail_silently=False)

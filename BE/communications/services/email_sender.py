import uuid
from django.conf import settings
from django.core.mail import EmailMessage as DjangoEmailMessage
from django.utils import timezone

from communications.models import EmailThread, EmailMessage, ThreadType, MessageDirection


_EMAIL_TEMPLATES = {
    'intro': {
        'subject': 'Introduction | {product_name}',
        'body': (
            'Dear {contact_name},\n\n'
            'I hope this email finds you well. We are {company}, a leading supplier of {product_name}.\n\n'
            'We noticed your company has been actively importing {product_name} and would love to '
            'explore how we can meet your requirements with our high-quality products.\n\n'
            '{brochure_note}'
            'We would welcome the opportunity to discuss your requirements further. '
            'Please feel free to reply to this email or reach out directly.\n\n'
            'Best regards,\n{sender_email}'
        ),
        'thread_type': ThreadType.INTRO,
    },
    'pricing': {
        'subject': 'Pricing Information | {product_name}',
        'body': (
            'Dear {contact_name},\n\n'
            'Thank you for your interest in {product_name}.\n\n'
            'We are pleased to share that we offer competitive pricing and flexible payment terms '
            'tailored to your purchase volume. Please let us know your quantity requirements so '
            'we can provide a detailed quotation.\n\n'
            'Best regards,\n{sender_email}'
        ),
        'thread_type': ThreadType.PRICING,
    },
    'followup': {
        'subject': 'Follow-Up | {product_name}',
        'body': (
            'Dear {contact_name},\n\n'
            'I wanted to follow up on our previous email regarding {product_name}.\n\n'
            'We understand you are busy, but we believe we can offer excellent value for your '
            'requirements. Please do not hesitate to reach out if you have any questions.\n\n'
            'Best regards,\n{sender_email}'
        ),
        'thread_type': ThreadType.FOLLOWUP,
    },
}


class GmailSMTPSender:
    """Sends outbound emails via Django SMTP and records them in EmailThread/EmailMessage."""

    def send_email(self, lead, contact, product, email_type: str) -> EmailThread:
        """
        Send an outbound email and persist the thread and message records.

        Args:
            lead: Lead instance
            contact: Contact instance (must have .email set)
            product: Product instance (brochure attached for 'intro' type if available)
            email_type: One of 'intro', 'pricing', 'followup'

        Returns:
            Created EmailThread instance
        """
        tmpl = _EMAIL_TEMPLATES[email_type]
        contact_name = f'{contact.first_name} {contact.last_name}'.strip() or contact.email
        company = getattr(settings, 'SENDER_COMPANY_NAME', 'Elchemy')
        sender_email = settings.EMAIL_HOST_USER

        has_brochure = email_type == 'intro' and bool(
            getattr(product, 'brochure_pdf', None) and product.brochure_pdf.name
        )
        brochure_note = (
            'Please find our product brochure attached for your reference.\n\n'
            if has_brochure
            else ''
        )

        subject = tmpl['subject'].format(product_name=product.name)
        body = tmpl['body'].format(
            contact_name=contact_name,
            product_name=product.name,
            company=company,
            brochure_note=brochure_note,
            sender_email=sender_email,
        )

        message_id = f'<{uuid.uuid4()}@salescatalyst>'

        thread = EmailThread.objects.create(
            lead=lead,
            contact=contact,
            subject=subject,
            thread_type=tmpl['thread_type'],
            gmail_thread_id='',
        )

        django_email = DjangoEmailMessage(
            subject=subject,
            body=body,
            from_email=sender_email,
            to=[contact.email],
            headers={'Message-ID': message_id},
        )

        if has_brochure:
            try:
                with product.brochure_pdf.open('rb') as f:
                    django_email.attach(
                        product.brochure_pdf.name.split('/')[-1],
                        f.read(),
                        'application/pdf',
                    )
            except (OSError, ValueError):
                pass

        django_email.send(fail_silently=False)

        EmailMessage.objects.create(
            thread=thread,
            direction=MessageDirection.OUTBOUND,
            body_text=body,
            sent_at=timezone.now(),
            gmail_message_id=message_id,
        )

        return thread

    def send_draft_reply(self, thread, contact, draft_content: str) -> None:
        """Send an approved AI draft as a reply in an existing thread."""
        message_id = f'<{uuid.uuid4()}@salescatalyst>'

        django_email = DjangoEmailMessage(
            subject=f'Re: {thread.subject}',
            body=draft_content,
            from_email=settings.EMAIL_HOST_USER,
            to=[contact.email],
            headers={'Message-ID': message_id},
        )
        django_email.send(fail_silently=False)

        EmailMessage.objects.create(
            thread=thread,
            direction=MessageDirection.OUTBOUND,
            body_text=draft_content,
            sent_at=timezone.now(),
            gmail_message_id=message_id,
        )

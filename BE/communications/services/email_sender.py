import uuid
from django.conf import settings
from django.core.mail import EmailMessage as DjangoEmailMessage, get_connection
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
    'documents': {
        'subject': 'Product Documents | {product_name}',
        'body': (
            'Dear {contact_name},\n\n'
            'Thank you for your interest in {product_name}. '
            'Please find attached our detailed product documentation for your review.\n\n'
            '{brochure_note}'
            'We hope this provides the information you need to evaluate our offering. '
            'Please do not hesitate to reach out with any questions.\n\n'
            'Best regards,\n{sender_email}'
        ),
        'thread_type': ThreadType.DOCUMENTS,
    },
    'requirements': {
        'subject': 'Understanding Your Requirements | {product_name}',
        'body': (
            'Dear {contact_name},\n\n'
            'We hope you had a chance to review our documentation for {product_name}. '
            'To prepare the most accurate quotation for you, we would appreciate your inputs:\n\n'
            '  - Quantity required (MT / month or per shipment)\n'
            '  - Preferred packing format\n'
            '  - Quality certifications needed (if any)\n'
            '  - Target delivery port / location\n\n'
            'Your responses will help us tailor our offer precisely to your needs.\n\n'
            'Best regards,\n{sender_email}'
        ),
        'thread_type': ThreadType.REQUIREMENTS,
    },
    'pricing': {
        'subject': 'Pricing Information | {product_name}',
        'body': (
            'Dear {contact_name},\n\n'
            'Thank you for sharing your requirements for {product_name}.\n\n'
            'We are pleased to offer competitive pricing tailored to your purchase volume. '
            'Please let us know your quantity so we can provide a detailed quotation.\n\n'
            'Best regards,\n{sender_email}'
        ),
        'thread_type': ThreadType.PRICING,
    },
    'followup': {
        'subject': 'Follow-Up on Pricing | {product_name}',
        'body': (
            'Dear {contact_name},\n\n'
            'I wanted to follow up on the pricing we shared for {product_name}.\n\n'
            'To help you plan ahead, here are our standard commercial terms:\n'
            '  - Payment Terms: 30% advance, 70% against BL copy (negotiable)\n'
            '  - Lead Time: 2–3 weeks from order confirmation\n\n'
            'We are flexible and happy to discuss terms that work best for you. '
            'Please feel free to reach out with any questions.\n\n'
            'Best regards,\n{sender_email}'
        ),
        'thread_type': ThreadType.FOLLOWUP,
    },
    'meeting': {
        'subject': 'Scheduling a Meeting | {product_name}',
        'body': (
            'Dear {contact_name},\n\n'
            'We have had a great exchange so far about {product_name} and believe we can offer '
            'excellent value for your business.\n\n'
            'We would love to schedule a brief call to discuss your requirements in detail and '
            'answer any remaining questions you may have.\n\n'
            'Please let us know your availability and we will arrange a meeting at your convenience.\n\n'
            'Best regards,\n{sender_email}'
        ),
        'thread_type': ThreadType.MEETING,
    },
    'deal': {
        'subject': 'Special Offer & Sample Request | {product_name}',
        'body': (
            'Dear {contact_name},\n\n'
            'Following our discussions, we are pleased to present our best commercial offer for {product_name}.\n\n'
            'We are committed to working with highly competitive margins to earn your business. '
            'Additionally, we would be happy to arrange a sample shipment so you can verify '
            'our quality firsthand before placing a formal order.\n\n'
            'Please let us know if you would like to proceed with:\n'
            '  (a) A sample request, or\n'
            '  (b) A formal purchase order discussion\n\n'
            'We look forward to a long-term partnership.\n\n'
            'Best regards,\n{sender_email}'
        ),
        'thread_type': ThreadType.DEAL,
    },
}


class GmailSMTPSender:
    """
    Sends outbound emails via SMTP.

    If a user with smtp_password is provided, their own Gmail account is used
    as the sender (from_email = user.email, credentials = user.smtp_password).
    Otherwise falls back to the global EMAIL_HOST_USER / EMAIL_HOST_PASSWORD.
    """

    def __init__(self, user=None):
        self._user = user

    @property
    def _from_email(self) -> str:
        if self._user and getattr(self._user, 'smtp_password', ''):
            return self._user.email
        return settings.EMAIL_HOST_USER

    @property
    def _cc(self) -> list:
        if self._user:
            return list(getattr(self._user, 'cc_emails', None) or [])
        return []

    def _get_connection(self):
        """Return an SMTP connection for this user, or None to use Django's default."""
        if self._user and getattr(self._user, 'smtp_password', ''):
            return get_connection(
                backend='django.core.mail.backends.smtp.EmailBackend',
                host=settings.EMAIL_HOST,
                port=settings.EMAIL_PORT,
                username=self._user.email,
                password=self._user.smtp_password,
                use_tls=getattr(settings, 'EMAIL_USE_TLS', True),
                fail_silently=False,
            )
        return None

    def send_email(self, lead, contact, product, email_type: str, stage_config=None) -> EmailThread:
        tmpl = _EMAIL_TEMPLATES[email_type]
        contact_name = f'{contact.first_name} {contact.last_name}'.strip() or contact.email
        company = getattr(settings, 'SENDER_COMPANY_NAME', 'Elchemy')
        sender_email = self._from_email

        # Determine attachment: stage_config doc takes priority over product brochure
        config_doc = stage_config.document if stage_config and stage_config.document and stage_config.document.name else None
        has_brochure = not config_doc and email_type == 'intro' and bool(
            getattr(product, 'brochure_pdf', None) and product.brochure_pdf.name
        )
        has_attachment = bool(config_doc or has_brochure)
        brochure_note = (
            'Please find our product brochure attached for your reference.\n\n'
            if has_attachment
            else ''
        )

        if stage_config and stage_config.subject_line:
            subject = stage_config.subject_line
        else:
            subject = tmpl['subject'].format(product_name=product.name)

        if stage_config and stage_config.email_content:
            body = stage_config.email_content
        else:
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
            cc=self._cc,
            headers={'Message-ID': message_id},
            connection=self._get_connection(),
        )

        if config_doc:
            try:
                with config_doc.open('rb') as f:
                    django_email.attach(
                        config_doc.name.split('/')[-1],
                        f.read(),
                        'application/octet-stream',
                    )
            except (OSError, ValueError):
                pass
        elif has_brochure:
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

    def send_draft_reply(self, thread, contact, draft_content: str, attachment=None) -> None:
        """Send a reply in an existing thread."""
        message_id = f'<{uuid.uuid4()}@salescatalyst>'

        django_email = DjangoEmailMessage(
            subject=f'Re: {thread.subject}',
            body=draft_content,
            from_email=self._from_email,
            to=[contact.email],
            cc=self._cc,
            headers={'Message-ID': message_id},
            connection=self._get_connection(),
        )
        if attachment:
            django_email.attach(attachment.name, attachment.read(), attachment.content_type)
        django_email.send(fail_silently=False)

        EmailMessage.objects.create(
            thread=thread,
            direction=MessageDirection.OUTBOUND,
            body_text=draft_content,
            sent_at=timezone.now(),
            gmail_message_id=message_id,
        )

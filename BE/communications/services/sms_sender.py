from django.conf import settings


class TwilioSMSSender:
    """
    Sends SMS via Twilio when a contact has no email.
    Falls back to console logging when TWILIO_ACCOUNT_SID is not configured.
    """

    def send_intro_sms(self, lead, contact, product) -> None:
        company = getattr(settings, 'SENDER_COMPANY_NAME', 'Elchemy')
        body = (
            f"Hi {contact.first_name}, this is {company}. "
            f"We supply {product.name} and would love to connect. "
            f"We will share our product catalogue and pricing shortly. "
            f"Reply to this message or call us to learn more."
        )
        self._send(contact.phone, body)

    def send_pricing_sms(self, lead, contact, product) -> None:
        company = getattr(settings, 'SENDER_COMPANY_NAME', 'Elchemy')
        body = (
            f"Hi {contact.first_name}, {company} here. "
            f"Following up on {product.name} — we have competitive pricing available. "
            f"Please reply with your required quantity and we will send a formal quote."
        )
        self._send(contact.phone, body)

    def send_documents_sms(self, lead, contact, product) -> None:
        company = getattr(settings, 'SENDER_COMPANY_NAME', 'Elchemy')
        body = (
            f"Hi {contact.first_name}, {company} here. "
            f"We have shared detailed documents for {product.name}. "
            f"Please reply and we will send them to your email or WhatsApp."
        )
        self._send(contact.phone, body)

    def send_requirements_sms(self, lead, contact, product) -> None:
        company = getattr(settings, 'SENDER_COMPANY_NAME', 'Elchemy')
        body = (
            f"Hi {contact.first_name}, {company} here regarding {product.name}. "
            f"To prepare your quotation, please share: quantity needed, packing preference, "
            f"and delivery location. Reply to this message."
        )
        self._send(contact.phone, body)

    def send_pricing_followup_sms(self, lead, contact, product) -> None:
        company = getattr(settings, 'SENDER_COMPANY_NAME', 'Elchemy')
        body = (
            f"Hi {contact.first_name}, {company} following up on {product.name} pricing. "
            f"Our standard terms: 30% advance, 70% against BL, 2-3 week lead time. "
            f"Happy to discuss — reply or call us."
        )
        self._send(contact.phone, body)

    def send_meeting_sms(self, lead, contact, product) -> None:
        company = getattr(settings, 'SENDER_COMPANY_NAME', 'Elchemy')
        body = (
            f"Hi {contact.first_name}, {company} here. "
            f"We would love to schedule a quick call about {product.name}. "
            f"Please reply with your availability."
        )
        self._send(contact.phone, body)

    def send_deal_sms(self, lead, contact, product) -> None:
        company = getattr(settings, 'SENDER_COMPANY_NAME', 'Elchemy')
        body = (
            f"Hi {contact.first_name}, {company} has a special offer for {product.name} "
            f"with best-in-market margins. We can also arrange a free sample. "
            f"Reply to discuss!"
        )
        self._send(contact.phone, body)

    def _send(self, to_number: str, body: str) -> None:
        sid = getattr(settings, 'TWILIO_ACCOUNT_SID', '')
        token = getattr(settings, 'TWILIO_AUTH_TOKEN', '')
        from_number = getattr(settings, 'TWILIO_FROM_NUMBER', '')

        if not sid or not token or not from_number:
            print(f"[TwilioSMSSender] DEMO — To: {to_number} | {body}")
            return

        try:
            from twilio.rest import Client
            client = Client(sid, token)
            client.messages.create(body=body, from_=from_number, to=to_number)
        except Exception as exc:
            print(f"[TwilioSMSSender] Send failed to {to_number}: {exc}")

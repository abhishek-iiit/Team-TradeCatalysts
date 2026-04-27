from django.conf import settings


class GeminiClient:
    """Wraps Gemini 2.0 Flash for context-aware email draft generation."""

    MODEL = 'gemini-2.0-flash'

    def generate_draft(self, lead, thread) -> tuple[str, str]:
        """
        Generate an email draft for the given lead + thread context.

        Returns:
            (draft_content, context_summary)
        """
        prompt = self._build_prompt(lead, thread)
        draft_content = self._call_gemini(prompt)
        context_summary = (
            f'Lead: {lead.company_name} ({lead.company_country}), '
            f'Thread: {thread.subject}, Stage: {lead.stage}'
        )
        return draft_content, context_summary

    def _call_gemini(self, prompt: str) -> str:
        try:
            import google.generativeai as genai
            genai.configure(api_key=settings.GEMINI_API_KEY)
            model = genai.GenerativeModel(self.MODEL)
            response = model.generate_content(prompt)
            return response.text.strip()
        except Exception:
            return (
                'Thank you for your interest. We would be happy to discuss how we can '
                'meet your requirements. Please let us know your specific needs and '
                'we will provide a detailed proposal.\n\n'
                f'Best regards,\n{getattr(settings, "EMAIL_HOST_USER", "")}'
            )

    def _build_prompt(self, lead, thread) -> str:
        messages = list(thread.messages.order_by('sent_at')[:10])
        messages_text = '\n\n'.join(
            f"[{'Received' if m.direction == 'inbound' else 'Sent'}]\n{m.body_text[:500]}"
            for m in messages
        ) or 'No messages yet.'

        company_name = getattr(settings, 'SENDER_COMPANY_NAME', 'Elchemy')
        contact_name = thread.contact.first_name

        return (
            f'You are a B2B chemical trading sales assistant for {company_name}.\n\n'
            f'LEAD: {lead.company_name} ({lead.company_country}), stage: {lead.stage}\n'
            f'THREAD: "{thread.subject}" ({thread.thread_type})\n'
            f'CONTACT: {thread.contact.first_name} {thread.contact.last_name}\n\n'
            f'CONVERSATION:\n{messages_text}\n\n'
            f'Write a professional 2-3 paragraph follow-up email body. '
            f'Address {contact_name} by name. Move the deal toward closing. '
            f'Output ONLY the email body text, no subject line.'
        )

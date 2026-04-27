"""
Django-Q2 background tasks for AI email draft generation.

Module-level async_task shim mirrors campaigns/tasks.py pattern for easy test patching.
"""

from ai_assistant.services.gemini_client import GeminiClient


def async_task(func_path: str, *args, **kwargs) -> None:
    """
    Thin shim that delegates to django_q.tasks.async_task.

    Defined at module level so tests can patch ``ai_assistant.tasks.async_task``
    without needing to patch the django_q import path directly.
    """
    from django_q.tasks import async_task as _async_task

    _async_task(func_path, *args, **kwargs)


def generate_ai_draft_task(lead_id: str, thread_id: str) -> None:
    """
    Django-Q2 task: call Gemini to generate an email draft, create AIDraft record,
    and log LeadAction(ai_draft_generated).

    Args:
        lead_id: String UUID of the Lead
        thread_id: String UUID of the EmailThread
    """
    from leads.models import Lead, LeadAction, ActionType
    from communications.models import EmailThread
    from ai_assistant.models import AIDraft, DraftStatus

    try:
        lead = (
            Lead.objects
            .select_related('campaign')
            .prefetch_related('campaign__products')
            .get(id=lead_id)
        )
        thread = (
            EmailThread.objects
            .select_related('contact')
            .prefetch_related('messages')
            .get(id=thread_id)
        )
    except (Lead.DoesNotExist, EmailThread.DoesNotExist):
        return

    client = GeminiClient()
    draft_content, context_summary = client.generate_draft(lead, thread)

    draft = AIDraft.objects.create(
        lead=lead,
        thread=thread,
        draft_content=draft_content,
        context_summary=context_summary,
        status=DraftStatus.PENDING_REVIEW,
    )

    LeadAction.objects.create(
        lead=lead,
        performed_by=None,
        action_type=ActionType.AI_DRAFT_GENERATED,
        notes=f'AI draft generated for thread: {thread.subject}',
        metadata={'draft_id': str(draft.id)},
    )

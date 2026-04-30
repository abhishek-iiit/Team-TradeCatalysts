import base64
import json
import logging
import os

from django.conf import settings

logger = logging.getLogger(__name__)

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
TOKEN_PATH = os.path.join(settings.BASE_DIR, 'gmail_token.json')


def _load_credentials():
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request

    if not os.path.exists(TOKEN_PATH):
        logger.error('gmail_token.json not found. Run: python manage.py setup_gmail_oauth')
        return None

    with open(TOKEN_PATH) as f:
        token_data = json.load(f)

    creds = Credentials(
        token=token_data.get('token'),
        refresh_token=token_data.get('refresh_token'),
        token_uri=token_data.get('token_uri', 'https://oauth2.googleapis.com/token'),
        client_id=token_data.get('client_id'),
        client_secret=token_data.get('client_secret'),
        scopes=token_data.get('scopes', SCOPES),
    )

    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        token_data['token'] = creds.token
        with open(TOKEN_PATH, 'w') as f:
            json.dump(token_data, f)

    return creds if creds.valid else None


def _extract_body_text(payload) -> str:
    if payload.get('mimeType') == 'text/plain':
        data = payload.get('body', {}).get('data', '')
        if data:
            return base64.urlsafe_b64decode(data + '==').decode('utf-8', errors='replace')

    for part in payload.get('parts', []):
        if part.get('mimeType') == 'text/plain':
            data = part.get('body', {}).get('data', '')
            if data:
                return base64.urlsafe_b64decode(data + '==').decode('utf-8', errors='replace')
        nested = _extract_body_text(part)
        if nested:
            return nested

    return ''


class GmailAPIPoller:
    """Polls Gmail via the Gmail API for replies to our outbound messages."""

    def poll_new_replies(self) -> list[dict]:
        from communications.models import EmailMessage, MessageDirection

        creds = _load_credentials()
        if not creds:
            return []

        try:
            from googleapiclient.discovery import build
            service = build('gmail', 'v1', credentials=creds)
        except Exception as e:
            logger.error('Failed to build Gmail API service: %s', e)
            return []

        outbound_ids = set(
            EmailMessage.objects
            .filter(direction=MessageDirection.OUTBOUND)
            .exclude(gmail_message_id='')
            .values_list('gmail_message_id', flat=True)
        )

        if not outbound_ids:
            return []

        results = []
        try:
            response = service.users().messages().list(
                userId='me',
                q='in:inbox',
                maxResults=100,
            ).execute()

            for msg_ref in response.get('messages', []):
                try:
                    msg = service.users().messages().get(
                        userId='me',
                        id=msg_ref['id'],
                        format='full',
                    ).execute()

                    headers = {
                        h['name']: h['value']
                        for h in msg['payload'].get('headers', [])
                    }
                    in_reply_to = headers.get('In-Reply-To', '').strip()

                    if in_reply_to not in outbound_ids:
                        continue

                    sender = headers.get('From', '')
                    if '<' in sender and '>' in sender:
                        sender = sender.split('<')[1].rstrip('>')
                    sender = sender.lower().strip()

                    results.append({
                        'uid': msg['id'],
                        'sender_email': sender,
                        'in_reply_to': in_reply_to,
                        'subject': headers.get('Subject', ''),
                        'body_text': _extract_body_text(msg['payload']),
                    })

                except Exception as e:
                    logger.warning('Error processing Gmail message %s: %s', msg_ref['id'], e)

        except Exception as e:
            logger.error('Gmail API polling error: %s', e)

        return results

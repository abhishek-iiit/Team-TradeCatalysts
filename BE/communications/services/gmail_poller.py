import imaplib
import email as email_lib
from email.header import decode_header as _decode_header

from django.conf import settings


def _decode(value) -> str:
    if value is None:
        return ''
    if isinstance(value, bytes):
        return value.decode('utf-8', errors='replace')
    return str(value)


class GmailIMAPPoller:
    """Polls Gmail INBOX via IMAP for unread replies from known contacts."""

    HOST = 'imap.gmail.com'
    PORT = 993

    def poll_new_replies(self) -> list[dict]:
        """
        Connect to Gmail IMAP SSL, fetch UNSEEN messages, return parsed results.

        Returns:
            List of dicts with keys: uid, sender_email, in_reply_to, subject, body_text.
            Returns [] on any connection or parsing failure.
        """
        results = []
        try:
            mail = imaplib.IMAP4_SSL(self.HOST, self.PORT)
            mail.login(settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD)
            mail.select('INBOX')

            _, uid_data = mail.uid('search', None, 'UNSEEN')
            uids = uid_data[0].split() if uid_data[0] else []

            for uid in uids:
                _, msg_data = mail.uid('fetch', uid, '(RFC822)')
                if not msg_data or not msg_data[0]:
                    continue
                raw = msg_data[0][1]
                msg = email_lib.message_from_bytes(raw)

                sender = msg.get('From', '')
                if '<' in sender and '>' in sender:
                    sender = sender.split('<')[1].rstrip('>')
                sender = sender.lower().strip()

                in_reply_to = (msg.get('In-Reply-To') or '').strip()

                subject_parts = _decode_header(msg.get('Subject', ''))
                subject = ''.join(
                    _decode(part) if enc is None else part.decode(enc, errors='replace')
                    for part, enc in subject_parts
                )

                body_text = ''
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == 'text/plain':
                            body_text = _decode(part.get_payload(decode=True))
                            break
                else:
                    body_text = _decode(msg.get_payload(decode=True))

                results.append({
                    'uid': _decode(uid),
                    'sender_email': sender,
                    'in_reply_to': in_reply_to,
                    'subject': subject,
                    'body_text': body_text,
                })

            mail.logout()
        except Exception:
            pass

        return results

import json
import os

from django.conf import settings
from django.core.management.base import BaseCommand

TOKEN_PATH = os.path.join(settings.BASE_DIR, 'gmail_token.json')
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']


class Command(BaseCommand):
    help = 'One-time Gmail OAuth setup — saves a refresh token for the inbox poller.'

    def handle(self, *args, **options):
        from google_auth_oauthlib.flow import Flow

        raw = getattr(settings, 'GMAIL_OAUTH_CREDENTIALS_JSON', None)
        if not raw:
            self.stderr.write(self.style.ERROR(
                'GMAIL_OAUTH_CREDENTIALS_JSON is not set in settings / .env'
            ))
            return

        creds_data = json.loads(raw) if isinstance(raw, str) else raw

        # The redirect URI must be registered in Google Cloud Console
        redirect_uri = 'http://127.0.0.1:8000/auth/google/callback/'

        flow = Flow.from_client_config(
            creds_data,
            scopes=SCOPES,
            redirect_uri=redirect_uri,
        )

        auth_url, _ = flow.authorization_url(
            access_type='offline',
            prompt='consent',
            include_granted_scopes='true',
        )

        self.stdout.write('\n' + '=' * 70)
        self.stdout.write('Step 1 — Open this URL in your browser and authorize access:')
        self.stdout.write('=' * 70)
        self.stdout.write(f'\n{auth_url}\n')
        self.stdout.write('=' * 70)
        self.stdout.write(
            '\nStep 2 — After authorizing, you will be redirected to:\n'
            f'  {redirect_uri}?code=<CODE>&...\n\n'
            'Copy only the "code" value from the URL and paste it below.\n'
        )

        code = input('Authorization code: ').strip()
        if not code:
            self.stderr.write(self.style.ERROR('No code provided. Aborting.'))
            return

        try:
            flow.fetch_token(code=code)
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'Token exchange failed: {e}'))
            return

        creds = flow.credentials
        token_data = {
            'token': creds.token,
            'refresh_token': creds.refresh_token,
            'token_uri': creds.token_uri,
            'client_id': creds.client_id,
            'client_secret': creds.client_secret,
            'scopes': list(creds.scopes or SCOPES),
        }

        with open(TOKEN_PATH, 'w') as f:
            json.dump(token_data, f, indent=2)

        self.stdout.write(self.style.SUCCESS(
            f'\nToken saved to {TOKEN_PATH}\n'
            'You can now run the inbox poller:\n'
            '  python manage.py shell -c "from communications.tasks import poll_gmail_inbox; poll_gmail_inbox()"'
        ))

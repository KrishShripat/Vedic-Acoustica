"""
api/emails.py — minimal transactional-email sender.

Sends over a provider's HTTPS API rather than SMTP so the app works behind
container networking that is unreliable on SMTP ports, and so the message
inherits the provider's authenticated sending domain (the main lever for
staying out of the spam folder).

Supported providers (``EMAIL_PROVIDER``):

* ``resend`` (default) — POST https://api.resend.com/emails
* ``brevo``            — POST https://api.brevo.com/v3/smtp/email

Configuration raises no errors when unset: :func:`email_configured` reports
whether a provider is usable so callers can degrade gracefully.
"""

import json
import logging
import os
import urllib.error
import urllib.request

logger = logging.getLogger(__name__)

_REQUEST_TIMEOUT = 10  # seconds


def _provider() -> str:
    return os.environ.get('EMAIL_PROVIDER', 'resend').strip().lower()


def _resend_api_key() -> str:
    return os.environ.get('RESEND_API_KEY', '').strip()


def _brevo_api_key() -> str:
    return os.environ.get('BREVO_API_KEY', '').strip()


def email_configured() -> bool:
    """True when the selected provider has the credentials it needs."""
    provider = _provider()
    if provider == 'brevo':
        return bool(_brevo_api_key())
    return bool(_resend_api_key())


def _parse_address(value: str) -> tuple[str, str]:
    """Split ``"Name <user@host>"`` into ``(name, email)``; bare email → ("", email)."""
    value = (value or '').strip()
    if '<' in value and '>' in value:
        name = value[:value.index('<')].strip().strip('"')
        email = value[value.index('<') + 1:value.index('>')].strip()
        return name, email
    return '', value


def _post_json(url: str, payload: dict, headers: dict) -> tuple[bool, str]:
    body = json.dumps(payload).encode('utf-8')
    request = urllib.request.Request(url, data=body, method='POST')
    request.add_header('Content-Type', 'application/json')
    for key, value in headers.items():
        request.add_header(key, value)
    try:
        with urllib.request.urlopen(request, timeout=_REQUEST_TIMEOUT) as response:
            response.read()
        return True, ''
    except urllib.error.HTTPError as exc:
        detail = ''
        try:
            detail = exc.read().decode('utf-8', 'replace')[:500]
        except Exception:  # pragma: no cover - best-effort diagnostics
            pass
        return False, f'HTTP {exc.code}: {detail}'
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return False, str(exc)


def send_email(to_email: str, subject: str, text_body: str, html_body: str = '') -> bool:
    """Send one email. Returns True on success; never raises."""
    to_email = (to_email or '').strip()
    if not to_email:
        return False
    if not email_configured():
        logger.warning('Email not sent (no provider configured): %s', subject)
        return False

    provider = _provider()
    default_from = os.environ.get('DEFAULT_FROM_EMAIL', 'onboarding@resend.dev')
    default_name = os.environ.get('DEFAULT_FROM_NAME', 'Vedic Acoustica')

    try:
        if provider == 'brevo':
            from_name, from_email = _parse_address(
                os.environ.get('BREVO_FROM_EMAIL', default_from)
            )
            ok, error = _post_json(
                'https://api.brevo.com/v3/smtp/email',
                {
                    'sender': {'email': from_email, 'name': from_name or default_name},
                    'to': [{'email': to_email}],
                    'subject': subject,
                    'textContent': text_body,
                    'htmlContent': html_body or text_body,
                },
                {'api-key': _brevo_api_key()},
            )
        else:  # resend
            from_value = os.environ.get('RESEND_FROM_EMAIL', default_from)
            _, from_email = _parse_address(from_value)
            if '<' not in from_value and from_email and ' ' not in from_value:
                from_value = f'{default_name} <{from_email}>'
            ok, error = _post_json(
                'https://api.resend.com/emails',
                {
                    'from': from_value,
                    'to': [to_email],
                    'subject': subject,
                    'text': text_body,
                    'html': html_body or text_body,
                },
                {'Authorization': f'Bearer {_resend_api_key()}'},
            )
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception('Unexpected error sending email: %s', exc)
        return False

    if not ok:
        logger.error('Email provider (%s) rejected message: %s', provider, error)
    return ok

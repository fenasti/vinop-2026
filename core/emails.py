"""
One helper for every email the shop sends.

Each email is a set of templates in templates/emails/:
    <name>_subject.txt   one line
    <name>.txt           plain-text body (always)
    <name>.html          HTML body (optional)

Sending never breaks the page or webhook that triggered it: if the mail
server is down, the error is logged and the function returns False.
"""

import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template import TemplateDoesNotExist
from django.template.loader import render_to_string

from studio.models import SiteSettings

log = logging.getLogger(__name__)


def send_templated_email(name: str, context: dict, to: list[str]) -> bool:
    context = {"site": SiteSettings.load(), "site_url": settings.SITE_URL, **context}
    subject = " ".join(render_to_string(f"emails/{name}_subject.txt", context).split())
    text = render_to_string(f"emails/{name}.txt", context)
    message = EmailMultiAlternatives(subject, text, settings.DEFAULT_FROM_EMAIL, to)
    try:
        message.attach_alternative(render_to_string(f"emails/{name}.html", context), "text/html")
    except TemplateDoesNotExist:
        pass
    try:
        message.send()
    except Exception:  # SMTP down, wrong credentials, …
        log.exception("Could not send the '%s' email to %s", name, to)
        return False
    return True

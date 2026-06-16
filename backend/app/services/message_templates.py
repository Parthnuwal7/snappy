"""Message templating for invoice sending.

Each firm can store custom templates for the email subject, email body, and the
WhatsApp text. When a firm field is null we fall back to the built-in defaults
below. Rendering uses a *safe* formatter so an unknown or mistyped placeholder
never raises — it is simply left untouched.
"""

# Built-in defaults. Used when the firm has not customized a template.
DEFAULT_EMAIL_SUBJECT = "Invoice {invoice_number} from {firm_name}"

DEFAULT_EMAIL_BODY = (
    "Dear {client_name},\n\n"
    "Please find attached invoice {invoice_number} for {total}, due {due_date}.\n"
    "You can also view it online here: {invoice_link}\n\n"
    "Thank you for your business.\n\n"
    "Regards,\n{firm_name}"
)

DEFAULT_WHATSAPP = (
    "Hi {client_name}, here's invoice {invoice_number} for {total} "
    "(due {due_date}): {invoice_link}"
)

# Placeholders advertised to users in the settings UI.
PLACEHOLDERS = [
    'client_name', 'invoice_number', 'firm_name', 'total', 'due_date', 'invoice_link',
]


class _SafeDict(dict):
    """dict that leaves unknown {placeholders} verbatim instead of raising."""

    def __missing__(self, key):
        return '{' + key + '}'


def render(template: str, context: dict) -> str:
    """Render `template`, substituting known placeholders, ignoring unknown ones."""
    if template is None:
        template = ''
    return template.format_map(_SafeDict(context))


def build_context(invoice, firm, client, invoice_link, currency='INR'):
    """Assemble the placeholder context from domain objects."""
    symbol = '₹' if (currency or 'INR') == 'INR' else ''
    total = invoice.total if invoice.total is not None else 0
    try:
        total_str = f"{symbol}{float(total):,.2f}"
    except (TypeError, ValueError):
        total_str = f"{symbol}{total}"
    due = invoice.due_date.isoformat() if getattr(invoice, 'due_date', None) else 'on receipt'
    return {
        'client_name': getattr(client, 'name', '') or '',
        'invoice_number': invoice.invoice_number,
        'firm_name': getattr(firm, 'firm_name', '') if firm else '',
        'total': total_str,
        'due_date': due,
        'invoice_link': invoice_link,
    }


def render_email(firm, context):
    """Return (subject, body) using firm templates or defaults."""
    subject_tpl = (getattr(firm, 'email_subject_template', None) if firm else None) or DEFAULT_EMAIL_SUBJECT
    body_tpl = (getattr(firm, 'email_body_template', None) if firm else None) or DEFAULT_EMAIL_BODY
    return render(subject_tpl, context), render(body_tpl, context)


def render_whatsapp(firm, context):
    """Return the WhatsApp message text using firm template or default."""
    tpl = (getattr(firm, 'whatsapp_template', None) if firm else None) or DEFAULT_WHATSAPP
    return render(tpl, context)

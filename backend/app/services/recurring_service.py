"""Recurring invoice cadence math and draft-generation service."""
from calendar import monthrange
from datetime import date, timedelta


def compute_next_run(from_date, frequency):
    """Return the next run date after `from_date` for the given frequency.

    weekly  -> from_date + 7 days
    monthly -> same day next month, clamped to the month's last day
    """
    if frequency == 'weekly':
        return from_date + timedelta(days=7)
    if frequency == 'monthly':
        year = from_date.year + (1 if from_date.month == 12 else 0)
        month = 1 if from_date.month == 12 else from_date.month + 1
        last_day = monthrange(year, month)[1]
        return date(year, month, min(from_date.day, last_day))
    raise ValueError(f"Unknown frequency: {frequency}")


def run_due_schedules(session, today=None):
    """Create one draft invoice per due, active schedule. Returns created invoices.

    Idempotent per period: each schedule advances exactly one period per call, so
    a schedule that is several periods overdue catches up one draft per daily run.
    """
    from app.models.models import Invoice, InvoiceItem, RecurringSchedule
    from app.api.invoices import generate_invoice_number

    today = today or date.today()
    created = []

    due = (
        RecurringSchedule.query
        .filter(RecurringSchedule.active.is_(True))
        .filter(RecurringSchedule.next_run_date <= today)
        .all()
    )

    for sched in due:
        if sched.end_date and sched.next_run_date > sched.end_date:
            sched.active = False
            continue

        invoice = Invoice(
            firm_id=sched.firm_id,
            created_by_user_id=sched.created_by_user_id,
            invoice_number=generate_invoice_number(sched.firm_id),
            client_id=sched.client_id,
            invoice_date=today,
            due_date=None,
            short_desc=sched.short_desc,
            tax_rate=float(sched.tax_rate) if sched.tax_rate is not None else 0.0,
            status='draft',
            source='recurring',
            notes=sched.notes,
        )
        for line in (sched.items or []):
            qty = float(line.get('quantity', 1))
            rate = float(line.get('rate', 0))
            invoice.items.append(InvoiceItem(
                description=line.get('description', ''),
                quantity=qty, rate=rate, amount=qty * rate,
            ))
        invoice.calculate_totals()
        session.add(invoice)

        sched.last_run_date = today
        sched.next_run_date = compute_next_run(sched.next_run_date, sched.frequency)
        if sched.end_date and sched.next_run_date > sched.end_date:
            sched.active = False

        created.append(invoice)

    session.commit()
    return created

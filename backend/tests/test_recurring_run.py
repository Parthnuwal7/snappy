from datetime import date
from app.models.models import db, Client, Invoice, RecurringSchedule
from app.models.auth import User
from app.services.firm_service import provision_firm_for_user
from app.services.recurring_service import run_due_schedules


def _seed(app, next_run, end_date=None, frequency='monthly'):
    with app.app_context():
        db.create_all()
        user = User(supabase_id='sb-rec', email='r@example.com')
        db.session.add(user)
        db.session.flush()
        tenant = provision_firm_for_user(user, 'Acme')
        client = Client(firm_id=tenant.id, created_by_user_id=user.id, name='Acme')
        db.session.add(client)
        db.session.flush()
        sched = RecurringSchedule(
            firm_id=tenant.id, created_by_user_id=user.id,
            client_id=client.id, items=[
                {'description': 'Retainer', 'quantity': 1, 'rate': 5000},
            ], tax_rate=18, short_desc='Monthly retainer', frequency=frequency,
            start_date=next_run, next_run_date=next_run, end_date=end_date, active=True,
        )
        db.session.add(sched)
        db.session.commit()
        return user.id, sched.id


def test_due_schedule_creates_one_draft_and_advances(app):
    user_id, sched_id = _seed(app, next_run=date(2026, 6, 1))
    with app.app_context():
        created = run_due_schedules(db.session, today=date(2026, 6, 1))
        assert len(created) == 1
        inv = Invoice.query.one()
        assert inv.status == 'draft'
        assert inv.source == 'recurring'
        assert float(inv.total) == 5900.0  # 5000 + 18%
        sched = RecurringSchedule.query.get(sched_id)
        assert sched.next_run_date == date(2026, 7, 1)
        assert sched.last_run_date == date(2026, 6, 1)
        assert sched.active is True


def test_not_yet_due_schedule_is_skipped(app):
    user_id, _ = _seed(app, next_run=date(2026, 7, 1))
    with app.app_context():
        created = run_due_schedules(db.session, today=date(2026, 6, 1))
        assert created == []
        assert Invoice.query.count() == 0


def test_end_date_deactivates_after_final_run(app):
    user_id, sched_id = _seed(app, next_run=date(2026, 6, 1), end_date=date(2026, 6, 15))
    with app.app_context():
        run_due_schedules(db.session, today=date(2026, 6, 1))
        sched = RecurringSchedule.query.get(sched_id)
        # next would be 2026-07-01 which is past end_date -> deactivated
        assert sched.active is False


def test_only_one_invoice_per_run_even_if_overdue(app):
    user_id, _ = _seed(app, next_run=date(2026, 6, 1))
    with app.app_context():
        # today is far past the due date; still only one draft this run
        run_due_schedules(db.session, today=date(2026, 9, 1))
        assert Invoice.query.count() == 1

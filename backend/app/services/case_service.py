"""Per-firm case number generation: CF/{YYYY}/{NNNN}.

Mirrors generate_invoice_number: scoped per firm, year-segmented, sequence is
the max existing for the firm this year + 1. The (firm_id, case_number) unique
constraint backstops races.
"""
from datetime import date
from app.models.models import db
from app.models.case import CaseFile


def generate_case_number(firm_id):
    year = date.today().year
    prefix = f"CF/{year}/"
    last = (CaseFile.query
            .filter(CaseFile.firm_id == firm_id,
                    CaseFile.case_number.like(f"{prefix}%"))
            .order_by(CaseFile.id.desc())
            .first())
    if last:
        try:
            next_seq = int(last.case_number.split('/')[-1]) + 1
        except ValueError:
            next_seq = 1
    else:
        next_seq = 1
    return f"{prefix}{str(next_seq).zfill(4)}"


def record_stage_change(case_file, from_stage, to_stage, user_id):
    """Append a stage-change audit row for a case. Caller commits."""
    from app.models.case import CaseStageChange
    change = CaseStageChange(
        firm_id=case_file.firm_id, case_file_id=case_file.id,
        from_stage=from_stage, to_stage=to_stage, changed_by_user_id=user_id)
    db.session.add(change)
    return change


def recompute_next_hearing_date(case_file):
    """Derive next_hearing_date = the soonest hearing event dated today or later
    (None if there is none). Caller commits."""
    from datetime import date
    from app.models.case import CaseEvent
    # A hearing that already carries an outcome is concluded — only undisposed,
    # future hearings count toward "the next date".
    soonest = (CaseEvent.query
               .filter(CaseEvent.case_file_id == case_file.id,
                       CaseEvent.kind == 'hearing',
                       CaseEvent.outcome.is_(None),
                       CaseEvent.event_date >= date.today())
               .order_by(CaseEvent.event_date.asc())
               .first())
    case_file.next_hearing_date = soonest.event_date if soonest else None
    return case_file.next_hearing_date

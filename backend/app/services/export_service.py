"""
Full user data export.

Bundles all of a user's relational data + storage files into a single
ZIP archive. Used by the GET /api/v1/backup/export endpoint to let users
download a complete, restorable copy of their account.
"""
import io
import json
import zipfile
from datetime import datetime, date
from decimal import Decimal
from typing import Any, Optional, Tuple
from uuid import UUID

from app.models.auth import User, BankAccount
from app.models.models import db, Client, Item, Invoice


def _json_default(o: Any):
    """Stringify types the stdlib JSON encoder doesn't handle natively.

    Live Supabase tables use UUID PKs and DECIMAL money columns, but the
    SQLAlchemy models declare Integer/Float — so SQLAlchemy hands back
    UUID/Decimal objects untouched. Coerce here to keep the export robust.
    """
    if isinstance(o, UUID):
        return str(o)
    if isinstance(o, Decimal):
        return float(o)
    if isinstance(o, (datetime, date)):
        return o.isoformat()
    if isinstance(o, bytes):
        return o.decode("utf-8", errors="replace")
    raise TypeError(f"Object of type {o.__class__.__name__} is not JSON serializable")


# Storage assets: (archive_label, bucket, source_obj_attr, column_name).
# logo + signature live on firm_details. (The UPI QR is now generated per-invoice
# from the bank's UPI deep link, not a stored image — nothing to back up.)
STORAGE_ASSETS = [
    ("logo",      "firm-logos",  "firm", "logo_path"),
    ("signature", "signatures",  "firm", "signature_path"),
]


def _serialize_user(user: User) -> dict:
    return {
        "id": user.id,
        "supabase_id": user.supabase_id,
        "email": user.email,
        "is_active": user.is_active,
        "is_onboarded": user.is_onboarded,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "updated_at": user.updated_at.isoformat() if user.updated_at else None,
        "last_login": user.last_login.isoformat() if user.last_login else None,
    }


def _serialize_invoice(invoice: Invoice) -> dict:
    data = invoice.to_dict(include_items=True)
    data["items"] = [item.to_dict() for item in invoice.items]
    return data


def _download_storage_files(firm, bank) -> list:
    """
    Return [(archive_path, bytes), ...] for each storage file the user has.
    Download failures are recorded as .FAILED.txt entries, not raised, so
    one missing/broken file does not abort the whole export.
    """
    try:
        from app.services.supabase_client import get_supabase_client
        client = get_supabase_client()
    except Exception as e:
        return [("storage/__error__.txt", f"storage client unavailable: {e}".encode())]

    sources = {"firm": firm, "bank": bank}
    out = []
    for label, bucket, source_key, column in STORAGE_ASSETS:
        source = sources.get(source_key)
        path = getattr(source, column, None) if source else None
        if not path:
            continue
        try:
            data = client.storage.from_(bucket).download(path)
            ext = path.rsplit(".", 1)[-1] if "." in path else "bin"
            out.append((f"storage/{label}.{ext}", data))
        except Exception as e:
            out.append((
                f"storage/{label}.FAILED.txt",
                f"Failed to download {bucket}/{path}: {e}".encode(),
            ))
    return out


def export_full_user_data(
    supabase_id: str, user_email: Optional[str] = None
) -> Tuple[Optional[bytes], Optional[str]]:
    """
    Build a ZIP archive of everything belonging to the user identified by
    their Supabase UUID. Returns (zip_bytes, filename) or (None, None) if
    the user could not be resolved.
    """
    user = User.query.filter_by(supabase_id=supabase_id).first()
    if not user:
        return None, None

    firm = user.firm_details
    bank_accounts = BankAccount.query.filter_by(user_id=user.id).all()
    default_bank = next((b for b in bank_accounts if b.is_default), None) \
        or (bank_accounts[0] if bank_accounts else None)
    clients = Client.query.filter_by(firm_id=user.firm_id).all()
    items = Item.query.filter_by(firm_id=user.firm_id).all()
    invoices = (
        Invoice.query.filter_by(firm_id=user.firm_id)
        .order_by(Invoice.invoice_date.desc())
        .all()
    )

    payload = {
        "schema_version": "1.1",
        "app": "SNAPPY",
        "exported_at": datetime.utcnow().isoformat() + "Z",
        "user": _serialize_user(user),
        "firm_details": firm.to_dict() if firm else None,
        "bank_accounts": [b.to_dict() for b in bank_accounts],
        "clients": [c.to_dict() for c in clients],
        "items": [i.to_dict() for i in items],
        "invoices": [_serialize_invoice(inv) for inv in invoices],
        "counts": {
            "clients": len(clients),
            "items": len(items),
            "invoices": len(invoices),
            "invoice_items": sum(len(inv.items) for inv in invoices),
            "bank_accounts": len(bank_accounts),
        },
    }

    json_bytes = json.dumps(
        payload, indent=2, ensure_ascii=False, default=_json_default
    ).encode("utf-8")

    storage_files = _download_storage_files(firm, default_bank)

    readme = (
        "SNAPPY data export\n"
        f"Exported at:  {payload['exported_at']}\n"
        f"User:         {user.email}\n"
        f"Supabase ID:  {user.supabase_id}\n\n"
        "Contents:\n"
        "  data.json       All relational data (firm, clients, items,\n"
        "                  invoices with line items, bank accounts, settings).\n"
        "  storage/        Firm logo, signature, and UPI QR images (if set).\n\n"
        "Counts:\n"
        + "\n".join(f"  {k:<15}{v}" for k, v in payload["counts"].items())
        + "\n\nThis archive is the authoritative restore point for your account.\n"
        "Keep it private — it contains business and banking information.\n"
    )

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("data.json", json_bytes)
        zf.writestr("README.txt", readme)
        for archive_path, data in storage_files:
            zf.writestr(archive_path, data)

    safe_email = (user_email or user.email or "user").replace("@", "_at_").replace(".", "_")
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"snappy_export_{safe_email}_{ts}.zip"

    return buf.getvalue(), filename

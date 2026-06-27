"""Thin wrapper over Supabase Storage for case documents.

Module-level functions so tests can monkeypatch them without a network call.
Bytes live in a private bucket; download is always a short-lived signed URL.
"""
import uuid

BUCKET = "case-documents"


class StorageError(Exception):
    """Raised when storage is unconfigured or the provider call fails."""


def build_storage_path(firm_id, case_file_id, ext):
    return f"{firm_id}/{case_file_id}/{uuid.uuid4().hex}.{ext}"


def _bucket():
    from app.services.supabase_client import get_supabase_client
    try:
        client = get_supabase_client()
    except ValueError as e:
        raise StorageError(f"Storage not configured: {e}") from e
    return client.storage.from_(BUCKET)


def put_object(storage_path, data, content_type):
    try:
        _bucket().upload(storage_path, data,
                         file_options={'content-type': content_type or 'application/octet-stream'})
    except StorageError:
        raise
    except Exception as e:
        raise StorageError(f"Upload failed: {e}") from e


def signed_url(storage_path, ttl=3600):
    try:
        result = _bucket().create_signed_url(storage_path, expires_in=ttl)
    except StorageError:
        raise
    except Exception as e:
        raise StorageError(f"Could not sign URL: {e}") from e
    url = (result or {}).get('signedURL') or (result or {}).get('signedUrl')
    if not url:
        raise StorageError("No signed URL returned")
    return url


def remove_object(storage_path):
    try:
        _bucket().remove([storage_path])
    except StorageError:
        raise
    except Exception as e:
        raise StorageError(f"Delete failed: {e}") from e

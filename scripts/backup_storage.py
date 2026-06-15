"""
Download all Supabase Storage buckets to a local folder.

Usage:
    cd backend
    python ../scripts/backup_storage.py [output_dir]

Reads SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY from backend/.env.
Default output: ../snappy_backup_storage_<timestamp>/
"""
import os
import sys
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client

BUCKETS = ["firm-logos", "signatures", "qr-codes", "snappy-backups"]


def walk_bucket(client, bucket, prefix=""):
    """Yield (remote_path, is_file) for every object under prefix."""
    entries = client.storage.from_(bucket).list(prefix)
    for entry in entries or []:
        name = entry["name"]
        full = f"{prefix}/{name}" if prefix else name
        if entry.get("id") is None:
            yield from walk_bucket(client, bucket, full)
        else:
            yield full


def main():
    load_dotenv()
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_SERVICE_KEY")
    if not url or not key:
        sys.exit("Missing SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY in env")

    client = create_client(url, key)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(f"../snappy_backup_storage_{ts}")
    out_root.mkdir(parents=True, exist_ok=True)
    print(f"-> {out_root.resolve()}")

    total_files = 0
    total_bytes = 0
    for bucket in BUCKETS:
        print(f"\n[{bucket}]")
        try:
            paths = list(walk_bucket(client, bucket))
        except Exception as e:
            print(f"  skipped: {e}")
            continue

        for remote_path in paths:
            local_path = out_root / bucket / remote_path
            local_path.parent.mkdir(parents=True, exist_ok=True)
            try:
                data = client.storage.from_(bucket).download(remote_path)
                local_path.write_bytes(data)
                total_files += 1
                total_bytes += len(data)
                print(f"  {remote_path} ({len(data):,} B)")
            except Exception as e:
                print(f"  FAILED {remote_path}: {e}")

    print(f"\nDone: {total_files} files, {total_bytes:,} bytes")


if __name__ == "__main__":
    main()

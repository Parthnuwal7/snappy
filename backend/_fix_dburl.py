import re, subprocess, sys, urllib.parse

REF = "zpcjxonzgevcqaidhkwl"
POOLER_HOST = "aws-1-ap-northeast-1.pooler.supabase.com"
POOLER_PORT = "5432"

# Pull the prod DATABASE_URL secret (the value never gets printed).
out = subprocess.run(
    ["gcloud", "secrets", "versions", "access", "latest",
     "--secret=snappy-database-url"],
    capture_output=True, text=True, shell=True,
)
if out.returncode != 0:
    print("FAILED to read secret:", out.stderr.strip()[:200])
    sys.exit(1)

secret = out.stdout.strip()

# Extract the password from postgresql://USER:PASSWORD@host...
m = re.search(r"postgres(?:\.[^:]+)?:([^@]+)@", secret)
if not m:
    print("FAILED: could not parse password from secret value")
    sys.exit(1)
enc_pw = m.group(1)                     # keep URL-encoded form as-is for the URL
pw = urllib.parse.unquote(enc_pw)       # decoded, for the live connection test

# Build the Session-pooler URL (IPv4).
new_url = (f"postgresql://postgres.{REF}:{enc_pw}"
           f"@{POOLER_HOST}:{POOLER_PORT}/postgres")

# Verify it actually connects before writing anything.
import psycopg2
try:
    c = psycopg2.connect(host=POOLER_HOST, port=int(POOLER_PORT),
                         user=f"postgres.{REF}", password=pw,
                         dbname="postgres", connect_timeout=10)
    c.close()
except Exception as e:
    print("CONNECT FAILED:", str(e).splitlines()[0][-80:])
    sys.exit(1)

# Rewrite the DATABASE_URL line in .env, leaving everything else intact.
lines = open(".env", encoding="utf-8").read().splitlines()
for i, ln in enumerate(lines):
    if ln.startswith("DATABASE_URL="):
        lines[i] = "DATABASE_URL=" + new_url
        break
open(".env", "w", encoding="utf-8").write("\n".join(lines) + "\n")
print("OK: pooler connection verified and backend/.env updated")

#!/bin/bash
# Common utilities for ASC API testing
# Generates ES256 JWT and provides helper functions

set -euo pipefail

CREDS_FILE="$HOME/.blitz/asc-credentials.json"
BASE_URL="https://api.appstoreconnect.apple.com"
CURL=/usr/bin/curl

# Parse credentials
ISSUER_ID=$(python3 -c "import json; print(json.load(open('$CREDS_FILE'))['issuerId'])")
KEY_ID=$(python3 -c "import json; print(json.load(open('$CREDS_FILE'))['keyId'])")
PRIVATE_KEY=$(python3 -c "import json; print(json.load(open('$CREDS_FILE'))['privateKey'])")

# Generate JWT token using python3 (ES256)
generate_jwt() {
  python3 << 'PYEOF'
import json, time, hashlib, hmac, base64, struct, subprocess, tempfile, os

creds = json.load(open(os.path.expanduser("~/.blitz/asc-credentials.json")))

def b64url(data):
    if isinstance(data, str):
        data = data.encode()
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode()

header = {"alg": "ES256", "kid": creds["keyId"], "typ": "JWT"}
now = int(time.time())
payload = {"iss": creds["issuerId"], "iat": now, "exp": now + 1200, "aud": "appstoreconnect-v1"}

header_b64 = b64url(json.dumps(header, separators=(',', ':')))
payload_b64 = b64url(json.dumps(payload, separators=(',', ':')))
message = f"{header_b64}.{payload_b64}"

# Write PEM key to temp file for openssl
with tempfile.NamedTemporaryFile(mode='w', suffix='.pem', delete=False) as f:
    f.write(creds["privateKey"])
    keyfile = f.name

try:
    # Sign with openssl (DER format)
    result = subprocess.run(
        ["openssl", "dgst", "-sha256", "-sign", keyfile],
        input=message.encode(),
        capture_output=True
    )
    der_sig = result.stdout

    # Convert DER signature to raw r||s (64 bytes) for ES256
    # DER: 30 <len> 02 <rlen> <r> 02 <slen> <s>
    idx = 2  # skip 30 <len>
    if der_sig[1] & 0x80:
        idx += (der_sig[1] & 0x7f)
    idx += 1  # now at 02

    # Parse r
    idx += 1  # skip 02
    rlen = der_sig[idx]; idx += 1
    r = der_sig[idx:idx+rlen]; idx += rlen

    # Parse s
    idx += 1  # skip 02
    slen = der_sig[idx]; idx += 1
    s = der_sig[idx:idx+slen]

    # Pad/trim to 32 bytes each
    r = r[-32:].rjust(32, b'\x00')
    s = s[-32:].rjust(32, b'\x00')

    raw_sig = r + s
    sig_b64 = b64url(raw_sig)
    print(f"{message}.{sig_b64}")
finally:
    os.unlink(keyfile)
PYEOF
}

# Cache the token for reuse within a script
JWT_TOKEN=$(generate_jwt)

# Helper: GET request
asc_get() {
  local path="$1"
  shift
  $CURL -s -w "\n%{http_code}" \
    -H "Authorization: Bearer $JWT_TOKEN" \
    -H "Accept: application/json" \
    "$BASE_URL/$path" "$@"
}

# Helper: POST request
asc_post() {
  local path="$1"
  local body="$2"
  $CURL -s -w "\n%{http_code}" \
    -X POST \
    -H "Authorization: Bearer $JWT_TOKEN" \
    -H "Accept: application/json" \
    -H "Content-Type: application/json" \
    -d "$body" \
    "$BASE_URL/$path"
}

# Helper: PATCH request
asc_patch() {
  local path="$1"
  local body="$2"
  $CURL -s -w "\n%{http_code}" \
    -X PATCH \
    -H "Authorization: Bearer $JWT_TOKEN" \
    -H "Accept: application/json" \
    -H "Content-Type: application/json" \
    -d "$body" \
    "$BASE_URL/$path"
}

# Helper: DELETE request
asc_delete() {
  local path="$1"
  $CURL -s -w "\n%{http_code}" \
    -X DELETE \
    -H "Authorization: Bearer $JWT_TOKEN" \
    -H "Accept: application/json" \
    "$BASE_URL/$path"
}

# Helper: parse response (body and status code)
parse_response() {
  local response="$1"
  local http_code=$(echo "$response" | tail -1)
  local body=$(echo "$response" | sed '$d')
  echo "$http_code"
  echo "$body"
}

# Helper: pretty print JSON
pp() {
  python3 -m json.tool 2>/dev/null || cat
}

# Helper: check response and print result
check() {
  local label="$1"
  local response="$2"
  local http_code=$(echo "$response" | tail -1)
  local body=$(echo "$response" | sed '$d')

  if [[ "$http_code" =~ ^2 ]]; then
    echo "  PASS  $label (HTTP $http_code)"
    echo "$body"
  else
    echo "  FAIL  $label (HTTP $http_code)"
    echo "$body" | pp
    return 1
  fi
}

echo "JWT Token generated successfully (${#JWT_TOKEN} chars)"

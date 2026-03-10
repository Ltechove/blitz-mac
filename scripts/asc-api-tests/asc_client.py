#!/usr/bin/env python3
"""ASC API test client - JWT auth + HTTP helpers for testing IAP/subscription/pricing endpoints."""

import json, time, base64, subprocess, tempfile, os, sys, urllib.request, urllib.parse, urllib.error

CREDS_FILE = os.path.expanduser("~/.blitz/asc-credentials.json")
BASE_URL = "https://api.appstoreconnect.apple.com"

def load_creds():
    with open(CREDS_FILE) as f:
        return json.load(f)

def b64url(data):
    if isinstance(data, str):
        data = data.encode()
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode()

def generate_jwt(creds):
    header = {"alg": "ES256", "kid": creds["keyId"], "typ": "JWT"}
    now = int(time.time())
    payload = {"iss": creds["issuerId"], "iat": now, "exp": now + 1200, "aud": "appstoreconnect-v1"}

    header_b64 = b64url(json.dumps(header, separators=(',', ':')))
    payload_b64 = b64url(json.dumps(payload, separators=(',', ':')))
    message = f"{header_b64}.{payload_b64}"

    with tempfile.NamedTemporaryFile(mode='w', suffix='.pem', delete=False) as f:
        f.write(creds["privateKey"])
        keyfile = f.name

    try:
        result = subprocess.run(
            ["openssl", "dgst", "-sha256", "-sign", keyfile],
            input=message.encode(), capture_output=True
        )
        if result.returncode != 0:
            raise RuntimeError(f"openssl sign failed: {result.stderr.decode()}")
        der_sig = result.stdout

        # DER to raw r||s conversion
        idx = 2
        if der_sig[1] & 0x80:
            idx += (der_sig[1] & 0x7f)

        # r
        assert der_sig[idx] == 0x02
        idx += 1
        rlen = der_sig[idx]; idx += 1
        r = der_sig[idx:idx+rlen]; idx += rlen

        # s
        assert der_sig[idx] == 0x02
        idx += 1
        slen = der_sig[idx]; idx += 1
        s = der_sig[idx:idx+slen]

        r = r[-32:].rjust(32, b'\x00')
        s = s[-32:].rjust(32, b'\x00')
        sig_b64 = b64url(r + s)
        return f"{message}.{sig_b64}"
    finally:
        os.unlink(keyfile)


class ASCClient:
    def __init__(self):
        creds = load_creds()
        self.token = generate_jwt(creds)
        print(f"[auth] JWT generated ({len(self.token)} chars)")

    def _request(self, method, path, body=None):
        url = f"{BASE_URL}/{path}"
        data = json.dumps(body).encode() if body else None
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/json",
        }
        if body:
            headers["Content-Type"] = "application/json"

        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                raw = resp.read()
                return resp.status, json.loads(raw) if raw else {}
        except urllib.error.HTTPError as e:
            raw = e.read().decode()
            try:
                return e.code, json.loads(raw)
            except:
                return e.code, {"raw": raw}

    def get(self, path):
        return self._request("GET", path)

    def post(self, path, body):
        return self._request("POST", path, body)

    def patch(self, path, body):
        return self._request("PATCH", path, body)

    def delete(self, path):
        return self._request("DELETE", path)

    def get_app_id(self, bundle_id):
        """Lookup ASC app ID by bundle ID."""
        status, data = self.get(f"v1/apps?filter[bundleId]={bundle_id}&limit=1")
        if status == 200 and data.get("data"):
            app = data["data"][0]
            return app["id"], app["attributes"]["name"]
        return None, None


def pp(obj):
    print(json.dumps(obj, indent=2))


if __name__ == "__main__":
    client = ASCClient()
    # Quick test: fetch the pureswift2 app
    app_id, name = client.get_app_id("mjso")
    if app_id:
        print(f"[ok] App found: {name} (id={app_id})")
    else:
        print("[!!] App 'mjso' not found in ASC")
        # List all apps as fallback
        status, data = client.get("v1/apps?limit=5")
        print(f"[info] Available apps (HTTP {status}):")
        for a in data.get("data", []):
            print(f"  - {a['attributes']['name']} ({a['attributes']['bundleId']}) id={a['id']}")

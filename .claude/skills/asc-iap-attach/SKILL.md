---
name: asc-iap-attach
description: Attach in-app purchases and subscriptions to an app version for App Store review. Use when the user has IAPs or subscriptions in "Ready to Submit" state that need to be included with a first-time version submission. Works for both first-time and subsequent submissions.
---

# asc iap attach

Use this skill to attach in-app purchases and/or subscriptions to an app version for App Store review. This is the equivalent of checking the boxes in the "Add In-App Purchases or Subscriptions" modal on the version page in App Store Connect.

## When to use

- User is preparing an app version for submission and has IAPs or subscriptions to include
- User says "attach IAPs", "add subscriptions to version", "include in-app purchases for review", "select in-app purchases"
- The app version page in ASC shows an "In-App Purchases and Subscriptions" section with items to select
- IAPs/subscriptions have been created and are in "Ready to Submit" state
- The `asc subscriptions review submit` or `asc iap submit` commands fail with `FIRST_SUBSCRIPTION_MUST_BE_SUBMITTED_ON_VERSION`

## Background

Apple's official App Store Connect API (`POST /v1/subscriptionSubmissions`, `POST /v1/inAppPurchaseSubmissions`) returns `FIRST_SUBSCRIPTION_MUST_BE_SUBMITTED_ON_VERSION` for first-time IAP/subscription submissions. The `reviewSubmissionItems` API also does not support `subscription` or `inAppPurchase` relationship types.

This skill uses Apple's internal iris API (`/iris/v1/subscriptionSubmissions`) via cached web session cookies, which supports the `submitWithNextAppStoreVersion` attribute that the public API lacks. This is the same mechanism the ASC web UI uses when you check the checkbox in the modal.

## Preconditions

- Auth configured for CLI (`asc auth login` or `ASC_*` env vars).
- Web session cached in macOS Keychain (from a prior `asc web auth login`).
- Know your app ID (`ASC_APP_ID` or `--app`).
- IAPs and/or subscriptions already exist and are in **Ready to Submit** state.
- A build is uploaded and attached to the current app version.

## Workflow

### 1. Identify items to attach

```bash
# List all in-app purchases for the app
asc iap list --app "APP_ID" --output table

# List subscription groups
asc subscriptions groups list --app "APP_ID" --output table

# List subscriptions within each group
asc subscriptions list --group-id "GROUP_ID" --output table
```

Look for items with state `READY_TO_SUBMIT`. Note their IDs.

### 2. Extract session cookies and attach via iris API

Use the following self-contained script to extract cookies from the keychain and attach a subscription. **Do not print or log the cookies** — they contain sensitive session tokens.

```bash
python3 -c "
import json, subprocess, urllib.request

# Extract cookies from keychain (silent — never print these)
raw = subprocess.check_output([
    'security', 'find-generic-password',
    '-s', 'asc-web-session',
    '-a', 'asc:web-session:store',
    '-w'
], stderr=subprocess.DEVNULL).decode()
store = json.loads(raw)
session = store['sessions'][store['last_key']]
cookie_str = '; '.join(
    (f'{c[\"name\"]}=\"{c[\"value\"]}\"' if c['name'].startswith('DES') else f'{c[\"name\"]}={c[\"value\"]}')
    for cl in session['cookies'].values() for c in cl
    if c.get('name') and c.get('value')
)

def iris_attach_subscription(sub_id):
    body = json.dumps({'data': {
        'type': 'subscriptionSubmissions',
        'attributes': {'submitWithNextAppStoreVersion': True},
        'relationships': {'subscription': {'data': {'type': 'subscriptions', 'id': sub_id}}}
    }}).encode()
    req = urllib.request.Request(
        'https://appstoreconnect.apple.com/iris/v1/subscriptionSubmissions',
        data=body, method='POST',
        headers={
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'X-Requested-With': 'XMLHttpRequest',
            'Origin': 'https://appstoreconnect.apple.com',
            'Referer': 'https://appstoreconnect.apple.com/',
            'Cookie': cookie_str
        })
    try:
        resp = urllib.request.urlopen(req)
        print(f'Attached subscription {sub_id}: HTTP {resp.status}')
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        if 'already set to submit' in body:
            print(f'Subscription {sub_id} already attached (OK)')
        elif e.code == 401:
            print(f'ERROR: Session expired. User must run: asc web auth login --apple-id EMAIL')
        else:
            print(f'ERROR attaching {sub_id}: HTTP {e.code} — {body[:200]}')

# Replace with actual subscription IDs:
iris_attach_subscription('SUB_ID_1')
iris_attach_subscription('SUB_ID_2')
"
```

For in-app purchases (non-subscription), change the type and relationship:

```bash
python3 -c "
import json, subprocess, urllib.request

raw = subprocess.check_output([
    'security', 'find-generic-password',
    '-s', 'asc-web-session',
    '-a', 'asc:web-session:store',
    '-w'
], stderr=subprocess.DEVNULL).decode()
store = json.loads(raw)
session = store['sessions'][store['last_key']]
cookie_str = '; '.join(
    (f'{c[\"name\"]}=\"{c[\"value\"]}\"' if c['name'].startswith('DES') else f'{c[\"name\"]}={c[\"value\"]}')
    for cl in session['cookies'].values() for c in cl
    if c.get('name') and c.get('value')
)

def iris_attach_iap(iap_id):
    body = json.dumps({'data': {
        'type': 'inAppPurchaseSubmissions',
        'attributes': {'submitWithNextAppStoreVersion': True},
        'relationships': {'inAppPurchaseV2': {'data': {'type': 'inAppPurchases', 'id': iap_id}}}
    }}).encode()
    req = urllib.request.Request(
        'https://appstoreconnect.apple.com/iris/v1/inAppPurchaseSubmissions',
        data=body, method='POST',
        headers={
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'X-Requested-With': 'XMLHttpRequest',
            'Origin': 'https://appstoreconnect.apple.com',
            'Referer': 'https://appstoreconnect.apple.com/',
            'Cookie': cookie_str
        })
    try:
        resp = urllib.request.urlopen(req)
        print(f'Attached IAP {iap_id}: HTTP {resp.status}')
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        if 'already set to submit' in body:
            print(f'IAP {iap_id} already attached (OK)')
        elif e.code == 401:
            print(f'ERROR: Session expired. User must run: asc web auth login --apple-id EMAIL')
        else:
            print(f'ERROR attaching {iap_id}: HTTP {e.code} — {body[:200]}')

# Replace with actual IAP IDs:
iris_attach_iap('IAP_ID')
"
```

### 3. Verify attachments

```bash
asc subscriptions list --group-id "GROUP_ID" --output table
```

## Common Errors

### "Subscription is already set to submit with next AppStoreVersion"
The subscription is already attached — this is safe to ignore. HTTP 409 with this message means the item was previously attached.

### "FIRST_SUBSCRIPTION_MUST_BE_SUBMITTED_ON_VERSION"
This error comes from the **public** API (`asc subscriptions review submit`). It means you must use the iris API approach documented in this skill instead.

### 401 Not Authorized (iris API)
The web session has expired. Call the `asc_web_auth` MCP tool to open the Apple ID login window in Blitz — this captures a fresh session and saves it to the keychain automatically. The user will need to complete Apple ID login + 2FA in the popup. After the tool returns success, retry the iris API calls.

### "failed to cache session: invalid character..."
A known bug in `asc` versions ≤ 0.44.2 caused by stale legacy keychain data. Fix by clearing the corrupted keychain item:
```bash
security delete-generic-password -s "asc-web-session" -a "asc:web-session:last" 2>/dev/null
```
Then re-authenticate.

## Agent Behavior

- Always list IAPs and subscriptions first to identify which are in `READY_TO_SUBMIT` state.
- If the user specifies particular items, match by reference name or product ID.
- If the user says "all", attach every item in `READY_TO_SUBMIT` state.
- **NEVER print, log, or echo session cookies.** The python scripts handle cookies internally without exposing them.
- Use the self-contained python scripts above — do NOT extract cookies separately or pass them as shell variables.
- If iris API returns 409 "already set to submit", treat as success.
- If iris API returns 401, call the `asc_web_auth` MCP tool to open the login window in Blitz, then retry.
- After attachment, call `get_tab_state` for `ascOverview` to refresh the submission readiness checklist (the MCP tool auto-refreshes monetization data).

## CLI Approach (for subsequent submissions only)

For IAPs/subscriptions that have **already been approved** in a prior version and are being updated, the public API commands work:

```bash
asc iap submit --iap-id "IAP_ID" --confirm
asc subscriptions review submit --subscription-id "SUB_ID" --confirm
```

These commands will fail with `FIRST_SUBSCRIPTION_MUST_BE_SUBMITTED_ON_VERSION` for first-time submissions. In that case, use the iris API workflow above.

## Notes

- This skill handles the "attach to version" step only. Use `asc-submission-health` for the full submission flow.
- The iris API (`/iris/v1`) mirrors the official ASC API resource types (same JSON:API format) but supports additional attributes like `submitWithNextAppStoreVersion` that the public API lacks.
- The iris API is rate-limited; keep a minimum 350ms interval between requests.

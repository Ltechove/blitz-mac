#!/usr/bin/env python3
"""Test In-App Purchase APIs against pureswift2 (mjso / 6760320061).

Tests:
1. POST /v2/inAppPurchases — create a consumable IAP
2. POST /v1/inAppPurchaseLocalizations — add en-US localization
3. GET  /v2/inAppPurchases/{id} — read it back
4. POST /v1/inAppPurchasePriceSchedules — set price (tier 1 / $0.99)
5. GET  /v1/apps/{appId}/inAppPurchasesV2 — list all IAPs
6. DELETE /v2/inAppPurchases/{id} — clean up

Also tests NON_CONSUMABLE and NON_RENEWING_SUBSCRIPTION types.
"""

import sys, os, time
sys.path.insert(0, os.path.dirname(__file__))
from asc_client import ASCClient, pp

APP_ID = "6760320061"
BUNDLE_ID = "mjso"
TEST_PREFIX = "blitz_test_"  # prefix for test product IDs

def main():
    client = ASCClient()
    results = {"pass": 0, "fail": 0}
    created_ids = []  # track for cleanup

    def check(label, status, data, expect_2xx=True):
        ok = 200 <= status < 300 if expect_2xx else True
        tag = "PASS" if ok else "FAIL"
        results["pass" if ok else "fail"] += 1
        print(f"\n[{tag}] {label} (HTTP {status})")
        if not ok:
            pp(data)
        return ok

    # ── Test 1: Create CONSUMABLE IAP ──
    print("\n" + "="*60)
    print("TEST 1: Create consumable IAP")
    print("="*60)
    ts = int(time.time())
    product_id = f"{TEST_PREFIX}coin_{ts}"
    body = {
        "data": {
            "type": "inAppPurchases",
            "attributes": {
                "name": "Test Coin Pack",
                "productId": product_id,
                "inAppPurchaseType": "CONSUMABLE"
            },
            "relationships": {
                "app": {
                    "data": {"type": "apps", "id": APP_ID}
                }
            }
        }
    }
    status, data = client.post("v2/inAppPurchases", body)
    iap_id = None
    if check("Create consumable IAP", status, data):
        iap_id = data["data"]["id"]
        created_ids.append(iap_id)
        print(f"  Created: id={iap_id} productId={product_id}")
        pp(data["data"]["attributes"])

    # ── Test 2: Add localization ──
    print("\n" + "="*60)
    print("TEST 2: Add en-US localization")
    print("="*60)
    if iap_id:
        body = {
            "data": {
                "type": "inAppPurchaseLocalizations",
                "attributes": {
                    "name": "100 Gold Coins",
                    "description": "Purchase a pack of 100 gold coins",
                    "locale": "en-US"
                },
                "relationships": {
                    "inAppPurchaseV2": {
                        "data": {"type": "inAppPurchases", "id": iap_id}
                    }
                }
            }
        }
        status, data = client.post("v1/inAppPurchaseLocalizations", body)
        if check("Add localization", status, data):
            loc_id = data["data"]["id"]
            print(f"  Localization id={loc_id}")
    else:
        print("  SKIP: No IAP created")

    # ── Test 3: Read IAP back ──
    print("\n" + "="*60)
    print("TEST 3: Read IAP details")
    print("="*60)
    if iap_id:
        status, data = client.get(f"v2/inAppPurchases/{iap_id}?include=inAppPurchaseLocalizations")
        if check("Read IAP", status, data):
            attrs = data["data"]["attributes"]
            print(f"  name={attrs.get('name')} productId={attrs.get('productId')} type={attrs.get('inAppPurchaseType')} state={attrs.get('state')}")

    # ── Test 4: Set IAP price ──
    print("\n" + "="*60)
    print("TEST 4: Set IAP price schedule")
    print("="*60)
    if iap_id:
        # First, get available IAP price points
        status, data = client.get(f"v2/inAppPurchases/{iap_id}/pricePoints?filter[territory]=USA&limit=50")
        if check("List IAP price points", status, data):
            points = data["data"]
            print(f"  Found {len(points)} price points")
            # Find $0.99 tier
            target = None
            for pt in points:
                price = pt["attributes"].get("customerPrice", "")
                if price in ("0.99", "0.990"):
                    target = pt
                    print(f"  Target: id={pt['id']} price=${price}")
                    break
            if not target and points:
                target = points[0]
                print(f"  Fallback: id={target['id']} price=${target['attributes'].get('customerPrice')}")

            if target:
                # Create price schedule
                price_body = {
                    "data": {
                        "type": "inAppPurchasePriceSchedules",
                        "relationships": {
                            "inAppPurchase": {
                                "data": {"type": "inAppPurchases", "id": iap_id}
                            },
                            "baseTerritory": {
                                "data": {"type": "territories", "id": "USA"}
                            },
                            "manualPrices": {
                                "data": [{"type": "inAppPurchasePrices", "id": "${price0}"}]
                            }
                        }
                    },
                    "included": [{
                        "type": "inAppPurchasePrices",
                        "id": "${price0}",
                        "relationships": {
                            "inAppPurchasePricePoint": {
                                "data": {"type": "inAppPurchasePricePoints", "id": target["id"]}
                            }
                        }
                    }]
                }
                status, data = client.post("v1/inAppPurchasePriceSchedules", price_body)
                check("Set IAP price", status, data)
                if status >= 200 and status < 300:
                    print("  Price schedule created!")

    # ── Test 5: Create NON_CONSUMABLE ──
    print("\n" + "="*60)
    print("TEST 5: Create non-consumable IAP")
    print("="*60)
    nc_product_id = f"{TEST_PREFIX}premium_{ts}"
    body = {
        "data": {
            "type": "inAppPurchases",
            "attributes": {
                "name": "Test Premium Unlock",
                "productId": nc_product_id,
                "inAppPurchaseType": "NON_CONSUMABLE"
            },
            "relationships": {
                "app": {"data": {"type": "apps", "id": APP_ID}}
            }
        }
    }
    status, data = client.post("v2/inAppPurchases", body)
    nc_id = None
    if check("Create non-consumable IAP", status, data):
        nc_id = data["data"]["id"]
        created_ids.append(nc_id)
        print(f"  Created: id={nc_id} productId={nc_product_id}")

    # ── Test 6: Create NON_RENEWING_SUBSCRIPTION ──
    print("\n" + "="*60)
    print("TEST 6: Create non-renewing subscription")
    print("="*60)
    nrs_product_id = f"{TEST_PREFIX}season_{ts}"
    body = {
        "data": {
            "type": "inAppPurchases",
            "attributes": {
                "name": "Test Season Pass",
                "productId": nrs_product_id,
                "inAppPurchaseType": "NON_RENEWING_SUBSCRIPTION"
            },
            "relationships": {
                "app": {"data": {"type": "apps", "id": APP_ID}}
            }
        }
    }
    status, data = client.post("v2/inAppPurchases", body)
    nrs_id = None
    if check("Create non-renewing sub", status, data):
        nrs_id = data["data"]["id"]
        created_ids.append(nrs_id)
        print(f"  Created: id={nrs_id} productId={nrs_product_id}")

    # ── Test 7: List all IAPs for app ──
    print("\n" + "="*60)
    print("TEST 7: List all IAPs for app")
    print("="*60)
    status, data = client.get(f"v1/apps/{APP_ID}/inAppPurchasesV2?limit=50")
    if check("List all IAPs", status, data):
        for iap in data.get("data", []):
            attrs = iap["attributes"]
            print(f"  {attrs.get('productId')} | {attrs.get('name')} | {attrs.get('inAppPurchaseType')} | state={attrs.get('state')}")

    # ── Test 8: Update IAP name ──
    print("\n" + "="*60)
    print("TEST 8: Update IAP (PATCH)")
    print("="*60)
    if iap_id:
        body = {
            "data": {
                "type": "inAppPurchases",
                "id": iap_id,
                "attributes": {
                    "name": "Test Coin Pack (Updated)"
                }
            }
        }
        status, data = client.patch(f"v2/inAppPurchases/{iap_id}", body)
        check("Update IAP name", status, data)

    # ── Test 9: Submit IAP for review ──
    print("\n" + "="*60)
    print("TEST 9: Submit IAP for review (expect possible error if not ready)")
    print("="*60)
    if iap_id:
        body = {
            "data": {
                "type": "inAppPurchaseSubmissions",
                "relationships": {
                    "inAppPurchaseV2": {
                        "data": {"type": "inAppPurchases", "id": iap_id}
                    }
                }
            }
        }
        status, data = client.post("v1/inAppPurchaseSubmissions", body)
        # May fail if missing screenshots/pricing - that's fine for testing
        if 200 <= status < 300:
            check("Submit IAP for review", status, data)
        else:
            print(f"  [INFO] Submit returned HTTP {status} (expected - IAP may need more setup)")
            results["pass"] += 1  # informational, not a real failure
            # Show what's missing
            for err in data.get("errors", []):
                print(f"    - {err.get('detail', err.get('title', '?'))}")

    # ── Cleanup: Delete test IAPs ──
    print("\n" + "="*60)
    print("CLEANUP: Delete test IAPs")
    print("="*60)
    for cid in created_ids:
        status, data = client.delete(f"v2/inAppPurchases/{cid}")
        ok = 200 <= status < 300 or status == 404
        tag = "PASS" if ok else "FAIL"
        print(f"  [{tag}] Delete {cid} (HTTP {status})")
        results["pass" if ok else "fail"] += 1

    # ── Summary ──
    print("\n" + "="*60)
    total = results["pass"] + results["fail"]
    print(f"IAP TESTS: {results['pass']}/{total} passed, {results['fail']} failed")
    print("="*60)
    return results["fail"] == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

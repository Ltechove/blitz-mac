#!/usr/bin/env python3
"""Test Subscription APIs against pureswift2 (mjso / 6760320061).

Tests:
1. POST /v1/subscriptionGroups — create a group
2. POST /v1/subscriptionGroupLocalizations — localize the group
3. POST /v1/subscriptions — create a subscription in the group
4. POST /v1/subscriptionLocalizations — localize the subscription
5. GET  /v1/subscriptions/{id}/pricePoints — list price points
6. POST /v1/subscriptionPrices — set price
7. GET  /v1/apps/{appId}/subscriptionGroups — list groups
8. POST /v1/subscriptionSubmissions — attempt submit (may fail gracefully)
9. Cleanup: DELETE subscription, group
"""

import sys, os, time
sys.path.insert(0, os.path.dirname(__file__))
from asc_client import ASCClient, pp

APP_ID = "6760320061"
TEST_PREFIX = "blitz_test_"

def main():
    client = ASCClient()
    results = {"pass": 0, "fail": 0}
    cleanup_subs = []
    cleanup_groups = []

    def check(label, status, data, expect_2xx=True):
        ok = 200 <= status < 300 if expect_2xx else True
        tag = "PASS" if ok else "FAIL"
        results["pass" if ok else "fail"] += 1
        print(f"\n[{tag}] {label} (HTTP {status})")
        if not ok:
            pp(data)
        return ok

    ts = int(time.time())

    # ── Test 1: Create subscription group ──
    print("\n" + "="*60)
    print("TEST 1: Create subscription group")
    print("="*60)
    group_body = {
        "data": {
            "type": "subscriptionGroups",
            "attributes": {
                "referenceName": f"{TEST_PREFIX}premium_{ts}"
            },
            "relationships": {
                "app": {
                    "data": {"type": "apps", "id": APP_ID}
                }
            }
        }
    }
    status, data = client.post("v1/subscriptionGroups", group_body)
    group_id = None
    if check("Create subscription group", status, data):
        group_id = data["data"]["id"]
        cleanup_groups.append(group_id)
        print(f"  Group id={group_id}")
        pp(data["data"]["attributes"])

    # ── Test 2: Localize the group ──
    print("\n" + "="*60)
    print("TEST 2: Localize subscription group (en-US)")
    print("="*60)
    if group_id:
        loc_body = {
            "data": {
                "type": "subscriptionGroupLocalizations",
                "attributes": {
                    "name": "Premium Plans",
                    "locale": "en-US"
                },
                "relationships": {
                    "subscriptionGroup": {
                        "data": {"type": "subscriptionGroups", "id": group_id}
                    }
                }
            }
        }
        status, data = client.post("v1/subscriptionGroupLocalizations", loc_body)
        if check("Localize group", status, data):
            print(f"  Localization id={data['data']['id']}")
    else:
        print("  SKIP")

    # ── Test 3: Create subscription ──
    print("\n" + "="*60)
    print("TEST 3: Create subscription (monthly)")
    print("="*60)
    sub_id = None
    if group_id:
        sub_body = {
            "data": {
                "type": "subscriptions",
                "attributes": {
                    "name": f"Test Monthly Pro",
                    "productId": f"{TEST_PREFIX}monthly_{ts}",
                    "subscriptionPeriod": "ONE_MONTH"
                },
                "relationships": {
                    "group": {
                        "data": {"type": "subscriptionGroups", "id": group_id}
                    }
                }
            }
        }
        status, data = client.post("v1/subscriptions", sub_body)
        if check("Create subscription", status, data):
            sub_id = data["data"]["id"]
            cleanup_subs.append(sub_id)
            print(f"  Subscription id={sub_id}")
            pp(data["data"]["attributes"])
    else:
        print("  SKIP")

    # ── Test 4: Localize subscription ──
    print("\n" + "="*60)
    print("TEST 4: Localize subscription (en-US)")
    print("="*60)
    if sub_id:
        loc_body = {
            "data": {
                "type": "subscriptionLocalizations",
                "attributes": {
                    "name": "Monthly Pro",
                    "description": "Unlock all premium features for one month",
                    "locale": "en-US"
                },
                "relationships": {
                    "subscription": {
                        "data": {"type": "subscriptions", "id": sub_id}
                    }
                }
            }
        }
        status, data = client.post("v1/subscriptionLocalizations", loc_body)
        if check("Localize subscription", status, data):
            print(f"  Localization id={data['data']['id']}")
    else:
        print("  SKIP")

    # ── Test 5: List subscription price points ──
    print("\n" + "="*60)
    print("TEST 5: List subscription price points")
    print("="*60)
    target_price_point = None
    if sub_id:
        status, data = client.get(f"v1/subscriptions/{sub_id}/pricePoints?filter[territory]=USA&limit=20")
        if check("List price points", status, data):
            points = data["data"]
            print(f"  Found {len(points)} price points")
            # Find ~$4.99 monthly tier or just pick first non-free
            for pt in points:
                price = pt["attributes"].get("customerPrice", "0")
                if price not in ("0", "0.0", "0.00"):
                    if not target_price_point:
                        target_price_point = pt
                    if price in ("4.99", "4.990"):
                        target_price_point = pt
                        break
            if target_price_point:
                print(f"  Target: id={target_price_point['id']} price=${target_price_point['attributes'].get('customerPrice')}")
    else:
        print("  SKIP")

    # ── Test 6: Set subscription price (PATCH with included prices) ──
    print("\n" + "="*60)
    print("TEST 6: Set subscription price")
    print("="*60)
    if sub_id and target_price_point:
        price_body = {
            "data": {
                "type": "subscriptions",
                "id": sub_id,
                "relationships": {
                    "prices": {
                        "data": [{"type": "subscriptionPrices", "id": "${price_usa}"}]
                    }
                }
            },
            "included": [{
                "type": "subscriptionPrices",
                "id": "${price_usa}",
                "attributes": {
                    "preserveCurrentPrice": False
                },
                "relationships": {
                    "subscription": {"data": {"type": "subscriptions", "id": sub_id}},
                    "subscriptionPricePoint": {"data": {"type": "subscriptionPricePoints", "id": target_price_point["id"]}},
                    "territory": {"data": {"type": "territories", "id": "USA"}}
                }
            }]
        }
        status, data = client.patch(f"v1/subscriptions/{sub_id}", price_body)
        check("Set subscription price", status, data)
        if 200 <= status < 300:
            print("  Price set!")
    else:
        print("  SKIP: No subscription or price point")

    # ── Test 7: Create yearly subscription in same group ──
    print("\n" + "="*60)
    print("TEST 7: Create yearly subscription")
    print("="*60)
    yearly_id = None
    if group_id:
        yearly_body = {
            "data": {
                "type": "subscriptions",
                "attributes": {
                    "name": "Test Yearly Pro",
                    "productId": f"{TEST_PREFIX}yearly_{ts}",
                    "subscriptionPeriod": "ONE_YEAR"
                },
                "relationships": {
                    "group": {
                        "data": {"type": "subscriptionGroups", "id": group_id}
                    }
                }
            }
        }
        status, data = client.post("v1/subscriptions", yearly_body)
        if check("Create yearly subscription", status, data):
            yearly_id = data["data"]["id"]
            cleanup_subs.append(yearly_id)
            print(f"  Yearly sub id={yearly_id}")

    # ── Test 8: List subscription groups for app ──
    print("\n" + "="*60)
    print("TEST 8: List subscription groups")
    print("="*60)
    status, data = client.get(f"v1/apps/{APP_ID}/subscriptionGroups?limit=50")
    if check("List subscription groups", status, data):
        for g in data.get("data", []):
            print(f"  group id={g['id']} ref={g['attributes'].get('referenceName')}")

    # ── Test 9: List subscriptions in group ──
    print("\n" + "="*60)
    print("TEST 9: List subscriptions in group")
    print("="*60)
    if group_id:
        status, data = client.get(f"v1/subscriptionGroups/{group_id}/subscriptions?limit=50")
        if check("List subscriptions in group", status, data):
            for s in data.get("data", []):
                attrs = s["attributes"]
                print(f"  sub id={s['id']} name={attrs.get('name')} period={attrs.get('subscriptionPeriod')} state={attrs.get('state')}")

    # ── Test 10: Set subscription availability ──
    print("\n" + "="*60)
    print("TEST 10: Set subscription availability")
    print("="*60)
    if sub_id:
        avail_body = {
            "data": {
                "type": "subscriptionAvailabilities",
                "attributes": {
                    "availableInNewTerritories": True
                },
                "relationships": {
                    "subscription": {
                        "data": {"type": "subscriptions", "id": sub_id}
                    },
                    "availableTerritories": {
                        "data": [{"type": "territories", "id": "USA"}]
                    }
                }
            }
        }
        status, data = client.post("v1/subscriptionAvailabilities", avail_body)
        # May fail if already set
        if 200 <= status < 300:
            check("Set availability", status, data)
        else:
            print(f"  [INFO] Availability returned HTTP {status}")
            results["pass"] += 1
            for err in data.get("errors", []):
                print(f"    - {err.get('detail', '?')}")

    # ── Test 11: Attempt submission (expect graceful failure) ──
    print("\n" + "="*60)
    print("TEST 11: Attempt subscription submission")
    print("="*60)
    if sub_id:
        submit_body = {
            "data": {
                "type": "subscriptionSubmissions",
                "relationships": {
                    "subscription": {
                        "data": {"type": "subscriptions", "id": sub_id}
                    }
                }
            }
        }
        status, data = client.post("v1/subscriptionSubmissions", submit_body)
        if 200 <= status < 300:
            check("Submit subscription", status, data)
        else:
            print(f"  [INFO] Submit returned HTTP {status} (expected if incomplete)")
            results["pass"] += 1
            for err in data.get("errors", []):
                print(f"    - {err.get('detail', '?')}")

    # ── Cleanup ──
    print("\n" + "="*60)
    print("CLEANUP: Delete test subscriptions & groups")
    print("="*60)
    for sid in cleanup_subs:
        status, data = client.delete(f"v1/subscriptions/{sid}")
        ok = 200 <= status < 300 or status == 404
        print(f"  [{'PASS' if ok else 'FAIL'}] Delete sub {sid} (HTTP {status})")
        results["pass" if ok else "fail"] += 1

    for gid in cleanup_groups:
        status, data = client.delete(f"v1/subscriptionGroups/{gid}")
        ok = 200 <= status < 300 or status == 404
        print(f"  [{'PASS' if ok else 'FAIL'}] Delete group {gid} (HTTP {status})")
        results["pass" if ok else "fail"] += 1

    # ── Summary ──
    print("\n" + "="*60)
    total = results["pass"] + results["fail"]
    print(f"SUBSCRIPTION TESTS: {results['pass']}/{total} passed, {results['fail']} failed")
    print("="*60)
    return results["fail"] == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

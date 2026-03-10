#!/usr/bin/env python3
"""Test paid app pricing APIs against pureswift2 (mjso / 6760320061).

Tests:
1. GET price points for USA territory (find free + paid tiers)
2. GET current price schedule
3. POST appPriceSchedules to set a paid price
4. Verify the schedule was created
5. Revert back to free
"""

import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from asc_client import ASCClient, pp

APP_ID = "6760320061"
BUNDLE_ID = "mjso"

def main():
    client = ASCClient()
    results = {"pass": 0, "fail": 0}

    def check(label, status, data, expect_2xx=True):
        ok = 200 <= status < 300 if expect_2xx else True
        tag = "PASS" if ok else "FAIL"
        results["pass" if ok else "fail"] += 1
        print(f"\n[{tag}] {label} (HTTP {status})")
        if not ok:
            pp(data)
        return ok

    # ── Test 1: List price points for USA ──
    print("\n" + "="*60)
    print("TEST 1: List app price points (USA)")
    print("="*60)
    status, data = client.get(f"v1/apps/{APP_ID}/appPricePoints?filter[territory]=USA&limit=50")
    check("List price points", status, data)
    if status == 200:
        points = data["data"]
        print(f"  Found {len(points)} price points")
        # Show first few
        free_point = None
        paid_points = []
        for pt in points:
            price = pt["attributes"].get("customerPrice", "?")
            if price in ("0", "0.0", "0.00"):
                free_point = pt
                print(f"  FREE: id={pt['id']} price={price}")
            elif len(paid_points) < 5:
                paid_points.append(pt)
                print(f"  PAID: id={pt['id']} price=${price}")
        print(f"  ... (total {len(points)} points, showing free + first 5 paid)")
    else:
        print("  Cannot proceed without price points")
        return

    # ── Test 2: Get current price schedule ──
    print("\n" + "="*60)
    print("TEST 2: Get current price schedule")
    print("="*60)
    status, data = client.get(f"v1/apps/{APP_ID}/appPriceSchedule")
    check("Get price schedule", status, data)
    if status == 200:
        pp(data.get("data", {}))

    # Also check manual prices
    schedule_id = data.get("data", {}).get("id") if status == 200 else None
    if schedule_id:
        status2, data2 = client.get(f"v1/appPriceSchedules/{schedule_id}/manualPrices?include=appPricePoint")
        check("Get manual prices", status2, data2)
        if status2 == 200:
            for mp in data2.get("data", []):
                print(f"  manualPrice id={mp['id']}")
            for inc in data2.get("included", []):
                if inc["type"] == "appPricePoints":
                    print(f"  pricePoint id={inc['id']} price={inc['attributes'].get('customerPrice')}")

    # ── Test 3: Set a paid price ($0.99 tier) ──
    print("\n" + "="*60)
    print("TEST 3: Set paid price ($0.99)")
    print("="*60)
    if not paid_points:
        print("  SKIP: No paid price points found")
    else:
        # Use the cheapest paid point (first one, which should be ~$0.99)
        target_point = paid_points[0]
        target_price = target_point["attributes"].get("customerPrice", "?")
        print(f"  Using price point id={target_point['id']} (${target_price})")

        body = {
            "data": {
                "type": "appPriceSchedules",
                "relationships": {
                    "app": {"data": {"type": "apps", "id": APP_ID}},
                    "baseTerritory": {"data": {"type": "territories", "id": "USA"}},
                    "manualPrices": {"data": [{"type": "appPrices", "id": "${price0}"}]}
                }
            },
            "included": [{
                "type": "appPrices",
                "id": "${price0}",
                "relationships": {
                    "appPricePoint": {"data": {"type": "appPricePoints", "id": target_point["id"]}}
                }
            }]
        }
        status, data = client.post("v1/appPriceSchedules", body)
        check("Set paid price", status, data)
        if status >= 200 and status < 300:
            print(f"  Price schedule created successfully!")
            pp(data.get("data", {}))

    # ── Test 4: Verify the schedule ──
    print("\n" + "="*60)
    print("TEST 4: Verify price schedule after change")
    print("="*60)
    status, data = client.get(f"v1/apps/{APP_ID}/appPriceSchedule")
    check("Verify schedule", status, data)

    # ── Test 5: Revert to free ──
    print("\n" + "="*60)
    print("TEST 5: Revert to free pricing")
    print("="*60)
    if free_point:
        body = {
            "data": {
                "type": "appPriceSchedules",
                "relationships": {
                    "app": {"data": {"type": "apps", "id": APP_ID}},
                    "baseTerritory": {"data": {"type": "territories", "id": "USA"}},
                    "manualPrices": {"data": [{"type": "appPrices", "id": "${price0}"}]}
                }
            },
            "included": [{
                "type": "appPrices",
                "id": "${price0}",
                "relationships": {
                    "appPricePoint": {"data": {"type": "appPricePoints", "id": free_point["id"]}}
                }
            }]
        }
        status, data = client.post("v1/appPriceSchedules", body)
        check("Revert to free", status, data)
    else:
        print("  SKIP: No free point found to revert to")

    # ── Test 6: List price points with equalizations ──
    print("\n" + "="*60)
    print("TEST 6: Get price point equalizations (for multi-territory)")
    print("="*60)
    if paid_points:
        pt_id = paid_points[0]["id"]
        # Note: v3 endpoint for equalizations
        status, data = client.get(f"v3/appPricePoints/{pt_id}/equalizations?limit=5")
        check("Get equalizations", status, data)
        if status == 200:
            for eq in data.get("data", [])[:3]:
                attrs = eq.get("attributes", {})
                print(f"  territory={attrs.get('territory','?')} price={attrs.get('customerPrice','?')}")

    # ── Summary ──
    print("\n" + "="*60)
    total = results["pass"] + results["fail"]
    print(f"PRICING TESTS: {results['pass']}/{total} passed, {results['fail']} failed")
    print("="*60)
    return results["fail"] == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

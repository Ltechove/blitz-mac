#!/usr/bin/env python3
"""Debug subscription pricing - try different price points and fetch more data."""

import sys, os, time, base64, json
sys.path.insert(0, os.path.dirname(__file__))
from asc_client import ASCClient, pp

APP_ID = "6760320061"

def main():
    client = ASCClient()
    ts = int(time.time())

    # Create temp group + subscription
    print("Creating temp group + subscription...")
    _, data = client.post("v1/subscriptionGroups", {
        "data": {
            "type": "subscriptionGroups",
            "attributes": {"referenceName": f"debug2_{ts}"},
            "relationships": {"app": {"data": {"type": "apps", "id": APP_ID}}}
        }
    })
    group_id = data["data"]["id"]

    _, data = client.post("v1/subscriptions", {
        "data": {
            "type": "subscriptions",
            "attributes": {
                "name": "Debug Monthly v2",
                "productId": f"debug2_monthly_{ts}",
                "subscriptionPeriod": "ONE_MONTH"
            },
            "relationships": {
                "group": {"data": {"type": "subscriptionGroups", "id": group_id}}
            }
        }
    })
    sub_id = data["data"]["id"]
    print(f"  group_id={group_id} sub_id={sub_id}")

    # Fetch ALL price points (paginate)
    print("\nFetching all price points for USA...")
    status, data = client.get(f"v1/subscriptions/{sub_id}/pricePoints?filter[territory]=USA&limit=200")
    points = data.get("data", [])
    print(f"  Total: {len(points)} points")

    # Decode the IDs to understand structure
    for pt in points[:3]:
        decoded = base64.urlsafe_b64decode(pt["id"] + "==")
        print(f"  id decoded: {decoded.decode()}")
        print(f"  price: ${pt['attributes']['customerPrice']}")

    # Try multiple price tiers
    tried = set()
    for pt in points:
        price = pt["attributes"]["customerPrice"]
        if price in tried:
            continue
        tried.add(price)
        if float(price) < 0.49:
            continue  # skip very low tiers
        if len(tried) > 10:
            break

        print(f"\n  Trying price ${price} (id={pt['id'][:30]}...)")
        body = {
            "data": {
                "type": "subscriptionPrices",
                "attributes": {"startDate": None},
                "relationships": {
                    "subscription": {"data": {"type": "subscriptions", "id": sub_id}},
                    "subscriptionPricePoint": {"data": {"type": "subscriptionPricePoints", "id": pt["id"]}}
                }
            }
        }
        status, resp = client.post("v1/subscriptionPrices", body)
        if 200 <= status < 300:
            print(f"    SUCCESS! HTTP {status}")
            pp(resp)
            break
        else:
            detail = resp.get("errors", [{}])[0].get("detail", "?")
            code = resp.get("errors", [{}])[0].get("code", "?")
            print(f"    FAIL HTTP {status}: {code} - {detail}")

    # Also try: maybe we need to use the v2 subscription price point ID format
    # by querying with include=territory
    print("\n\nTrying with include=territory...")
    status, data = client.get(f"v1/subscriptions/{sub_id}/pricePoints?filter[territory]=USA&include=territory&limit=5")
    if data.get("data"):
        pt = data["data"][0]
        print(f"  Price point with territory included:")
        pp(pt)

    # Try the inline creation pattern (like IAP price schedules)
    print("\n\nTrying inline creation (included pattern) via subscription relationship...")
    if points:
        pt = next((p for p in points if float(p["attributes"]["customerPrice"]) >= 0.99), points[0])
        print(f"  Using price ${pt['attributes']['customerPrice']}")

        # Maybe subscriptions need pricing set via PATCH on the subscription itself?
        print("\n  Checking subscription relationships...")
        status, data = client.get(f"v1/subscriptions/{sub_id}?include=prices")
        if status == 200:
            pp(data.get("data", {}).get("relationships", {}).get("prices", {}))

        # Try setting via subscription's prices relationship
        print("\n  Trying POST to subscription's prices sub-resource...")
        status, data = client.post(f"v1/subscriptions/{sub_id}/prices", {
            "data": {
                "type": "subscriptionPrices",
                "attributes": {"startDate": None},
                "relationships": {
                    "subscriptionPricePoint": {"data": {"type": "subscriptionPricePoints", "id": pt["id"]}}
                }
            }
        })
        print(f"  HTTP {status}")
        if status >= 400:
            pp(data)
        else:
            print("  SUCCESS!")
            pp(data)

    # Cleanup
    print("\nCleaning up...")
    client.delete(f"v1/subscriptions/{sub_id}")
    client.delete(f"v1/subscriptionGroups/{group_id}")
    print("Done.")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Debug subscription pricing - compound document PATCH approach."""

import sys, os, time
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
            "attributes": {"referenceName": f"debug3_{ts}"},
            "relationships": {"app": {"data": {"type": "apps", "id": APP_ID}}}
        }
    })
    group_id = data["data"]["id"]

    _, data = client.post("v1/subscriptions", {
        "data": {
            "type": "subscriptions",
            "attributes": {
                "name": "Debug Monthly v3",
                "productId": f"debug3_monthly_{ts}",
                "subscriptionPeriod": "ONE_MONTH"
            },
            "relationships": {
                "group": {"data": {"type": "subscriptionGroups", "id": group_id}}
            }
        }
    })
    sub_id = data["data"]["id"]
    print(f"  group_id={group_id} sub_id={sub_id}")

    # Fetch price points
    status, data = client.get(f"v1/subscriptions/{sub_id}/pricePoints?filter[territory]=USA&limit=20")
    points = data.get("data", [])
    # Pick $0.99 or first available
    target = next((p for p in points if p["attributes"]["customerPrice"] in ("0.99", "0.990")), points[0])
    print(f"  Target price: ${target['attributes']['customerPrice']} (id={target['id'][:40]}...)")

    # ── Approach A: PATCH subscription with inline prices ──
    print("\n--- Approach A: PATCH subscription with included prices ---")
    body_a = {
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
                "subscriptionPricePoint": {"data": {"type": "subscriptionPricePoints", "id": target["id"]}},
                "territory": {"data": {"type": "territories", "id": "USA"}}
            }
        }]
    }
    status, data = client.patch(f"v1/subscriptions/{sub_id}", body_a)
    print(f"  HTTP {status}")
    if status >= 400:
        pp(data)
    else:
        print("  SUCCESS!")
        # Check the prices
        s2, d2 = client.get(f"v1/subscriptions/{sub_id}/prices?limit=5")
        print(f"  Prices after set (HTTP {s2}):")
        for p in d2.get("data", []):
            print(f"    price id={p['id']}")
            pp(p.get("attributes", {}))

    # ── Approach B: If A failed, try startDate=null in included ──
    if status >= 400:
        print("\n--- Approach B: With startDate=null ---")
        body_b = {
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
                    "startDate": None,
                    "preserveCurrentPrice": False
                },
                "relationships": {
                    "subscription": {"data": {"type": "subscriptions", "id": sub_id}},
                    "subscriptionPricePoint": {"data": {"type": "subscriptionPricePoints", "id": target["id"]}},
                    "territory": {"data": {"type": "territories", "id": "USA"}}
                }
            }]
        }
        status, data = client.patch(f"v1/subscriptions/{sub_id}", body_b)
        print(f"  HTTP {status}")
        if status >= 400:
            pp(data)
        else:
            print("  SUCCESS!")

    # ── Approach C: POST /v1/subscriptionPrices with territory relationship ──
    if status >= 400:
        print("\n--- Approach C: POST subscriptionPrices with all rels ---")
        body_c = {
            "data": {
                "type": "subscriptionPrices",
                "attributes": {
                    "startDate": None,
                    "preserveCurrentPrice": False
                },
                "relationships": {
                    "subscription": {"data": {"type": "subscriptions", "id": sub_id}},
                    "subscriptionPricePoint": {"data": {"type": "subscriptionPricePoints", "id": target["id"]}},
                    "territory": {"data": {"type": "territories", "id": "USA"}}
                }
            }
        }
        status, data = client.post("v1/subscriptionPrices", body_c)
        print(f"  HTTP {status}")
        if status >= 400:
            pp(data)
        else:
            print("  SUCCESS!")

    # ── Approach D: Use the gist pattern from the search results ──
    if status >= 400:
        print("\n--- Approach D: Gist pattern (priceId=subscription_price_usa) ---")
        # The gist uses: PATCH /v1/subscriptions/{id} with prices inline
        # where the inline ID is a placeholder AND uses startDate
        body_d = {
            "data": {
                "type": "subscriptions",
                "id": sub_id,
                "relationships": {
                    "prices": {
                        "data": [{"type": "subscriptionPrices", "id": "sub_price_usa"}]
                    }
                }
            },
            "included": [{
                "type": "subscriptionPrices",
                "id": "sub_price_usa",
                "attributes": {
                    "startDate": None
                },
                "relationships": {
                    "subscriptionPricePoint": {
                        "data": {"type": "subscriptionPricePoints", "id": target["id"]}
                    }
                }
            }]
        }
        status, data = client.patch(f"v1/subscriptions/{sub_id}", body_d)
        print(f"  HTTP {status}")
        if status >= 400:
            pp(data)
        else:
            print("  SUCCESS!")

    # Cleanup
    print("\nCleaning up...")
    client.delete(f"v1/subscriptions/{sub_id}")
    client.delete(f"v1/subscriptionGroups/{group_id}")
    print("Done.")

if __name__ == "__main__":
    main()

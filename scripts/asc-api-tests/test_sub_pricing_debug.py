#!/usr/bin/env python3
"""Debug subscription pricing - figure out correct payload format."""

import sys, os, time
sys.path.insert(0, os.path.dirname(__file__))
from asc_client import ASCClient, pp

APP_ID = "6760320061"

def main():
    client = ASCClient()
    ts = int(time.time())

    # Create temp group + subscription
    print("Creating temp group...")
    status, data = client.post("v1/subscriptionGroups", {
        "data": {
            "type": "subscriptionGroups",
            "attributes": {"referenceName": f"debug_pricing_{ts}"},
            "relationships": {"app": {"data": {"type": "apps", "id": APP_ID}}}
        }
    })
    group_id = data["data"]["id"]
    print(f"  group_id={group_id}")

    print("Creating temp subscription...")
    status, data = client.post("v1/subscriptions", {
        "data": {
            "type": "subscriptions",
            "attributes": {
                "name": "Debug Monthly",
                "productId": f"debug_monthly_{ts}",
                "subscriptionPeriod": "ONE_MONTH"
            },
            "relationships": {
                "group": {"data": {"type": "subscriptionGroups", "id": group_id}}
            }
        }
    })
    sub_id = data["data"]["id"]
    print(f"  sub_id={sub_id}")

    # Fetch price points - print full structure
    print("\nFetching price points...")
    status, data = client.get(f"v1/subscriptions/{sub_id}/pricePoints?filter[territory]=USA&limit=5")
    print(f"  HTTP {status}")
    if data.get("data"):
        print("  First price point (full):")
        pp(data["data"][0])
        target_pp_id = data["data"][0]["id"]
        target_price = data["data"][0]["attributes"].get("customerPrice", "?")
        print(f"\n  Using: id={target_pp_id} price={target_price}")
    else:
        print("  No price points!")
        pp(data)
        return

    # Attempt 1: Original format (no startDate)
    print("\n--- Attempt 1: Without startDate ---")
    body1 = {
        "data": {
            "type": "subscriptionPrices",
            "relationships": {
                "subscription": {"data": {"type": "subscriptions", "id": sub_id}},
                "subscriptionPricePoint": {"data": {"type": "subscriptionPricePoints", "id": target_pp_id}}
            }
        }
    }
    status, data = client.post("v1/subscriptionPrices", body1)
    print(f"  HTTP {status}")
    pp(data)

    # Attempt 2: With startDate: null
    if status >= 400:
        print("\n--- Attempt 2: With startDate=null ---")
        body2 = {
            "data": {
                "type": "subscriptionPrices",
                "attributes": {
                    "startDate": None
                },
                "relationships": {
                    "subscription": {"data": {"type": "subscriptions", "id": sub_id}},
                    "subscriptionPricePoint": {"data": {"type": "subscriptionPricePoints", "id": target_pp_id}}
                }
            }
        }
        status, data = client.post("v1/subscriptionPrices", body2)
        print(f"  HTTP {status}")
        pp(data)

    # Attempt 3: With preserveCurrentPrice
    if status >= 400:
        print("\n--- Attempt 3: With preserveCurrentPrice=false ---")
        body3 = {
            "data": {
                "type": "subscriptionPrices",
                "attributes": {
                    "startDate": None,
                    "preserveCurrentPrice": False
                },
                "relationships": {
                    "subscription": {"data": {"type": "subscriptions", "id": sub_id}},
                    "subscriptionPricePoint": {"data": {"type": "subscriptionPricePoints", "id": target_pp_id}}
                }
            }
        }
        status, data = client.post("v1/subscriptionPrices", body3)
        print(f"  HTTP {status}")
        pp(data)

    # Attempt 4: Use inAppPurchasePriceSchedules pattern with included
    if status >= 400:
        print("\n--- Attempt 4: Schedule pattern (included) ---")
        body4 = {
            "data": {
                "type": "subscriptionPriceSchedules",  # maybe this endpoint exists?
                "relationships": {
                    "subscription": {"data": {"type": "subscriptions", "id": sub_id}},
                    "baseTerritory": {"data": {"type": "territories", "id": "USA"}},
                    "manualPrices": {"data": [{"type": "subscriptionPrices", "id": "${price0}"}]}
                }
            },
            "included": [{
                "type": "subscriptionPrices",
                "id": "${price0}",
                "attributes": {"startDate": None},
                "relationships": {
                    "subscriptionPricePoint": {"data": {"type": "subscriptionPricePoints", "id": target_pp_id}}
                }
            }]
        }
        status, data = client.post("v1/subscriptionPriceSchedules", body4)
        print(f"  HTTP {status}")
        pp(data)

    # Attempt 5: Try with territory relationship instead
    if status >= 400:
        print("\n--- Attempt 5: With territory relationship ---")
        body5 = {
            "data": {
                "type": "subscriptionPrices",
                "attributes": {
                    "startDate": None
                },
                "relationships": {
                    "subscription": {"data": {"type": "subscriptions", "id": sub_id}},
                    "subscriptionPricePoint": {"data": {"type": "subscriptionPricePoints", "id": target_pp_id}},
                    "territory": {"data": {"type": "territories", "id": "USA"}}
                }
            }
        }
        status, data = client.post("v1/subscriptionPrices", body5)
        print(f"  HTTP {status}")
        pp(data)

    # Cleanup
    print("\nCleaning up...")
    client.delete(f"v1/subscriptions/{sub_id}")
    client.delete(f"v1/subscriptionGroups/{group_id}")
    print("Done.")

if __name__ == "__main__":
    main()

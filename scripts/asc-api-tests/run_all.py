#!/usr/bin/env python3
"""Run all ASC API tests sequentially."""

import subprocess, sys, os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TESTS = [
    ("Paid Pricing", "test_paid_pricing.py"),
    ("In-App Purchases", "test_iap.py"),
    ("Subscriptions", "test_subscriptions.py"),
]

def main():
    all_passed = True
    for label, script in TESTS:
        print(f"\n{'#'*70}")
        print(f"# Running: {label}")
        print(f"{'#'*70}\n")
        result = subprocess.run(
            [sys.executable, os.path.join(SCRIPT_DIR, script)],
            cwd=SCRIPT_DIR
        )
        if result.returncode != 0:
            all_passed = False
            print(f"\n  >>> {label}: SOME TESTS FAILED <<<")
        else:
            print(f"\n  >>> {label}: ALL PASSED <<<")

    print(f"\n{'#'*70}")
    print(f"# OVERALL: {'ALL PASSED' if all_passed else 'SOME FAILURES'}")
    print(f"{'#'*70}")
    return all_passed

if __name__ == "__main__":
    sys.exit(0 if main() else 1)

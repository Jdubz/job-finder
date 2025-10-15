#!/usr/bin/env python
"""Test Portland office bonus logic.

This script simulates the bonus calculation to verify it works correctly.
"""

import sys

sys.path.insert(0, "src")

print("=" * 80)
print("PORTLAND OFFICE BONUS LOGIC TEST")
print("=" * 80)
print()

# Bonus configuration
PORTLAND_BONUS = 15
MIN_THRESHOLD = 80


def calculate_result(base_score, has_portland_office):
    """Simulate the bonus logic from AIJobMatcher."""
    adjusted_score = base_score

    if has_portland_office and PORTLAND_BONUS > 0:
        adjusted_score = min(100, base_score + PORTLAND_BONUS)

    # Calculate priority
    if adjusted_score >= 75:
        priority = "High"
    elif adjusted_score >= 50:
        priority = "Medium"
    else:
        priority = "Low"

    passes = adjusted_score >= MIN_THRESHOLD

    return {
        "base": base_score,
        "adjusted": adjusted_score,
        "bonus": adjusted_score - base_score,
        "priority": priority,
        "passes": passes,
    }


# Test scenarios
test_cases = [
    # (base_score, has_portland_office, description)
    (85, False, "Strong match, no Portland office"),
    (85, True, "Strong match, WITH Portland office (capped at 100)"),
    (70, False, "Medium match, no Portland office"),
    (70, True, "Medium match, WITH Portland office (crosses threshold!)"),
    (65, False, "Borderline, no Portland office"),
    (65, True, "Borderline, WITH Portland office (passes!)"),
    (60, False, "Below threshold, no Portland office"),
    (60, True, "Below threshold, WITH Portland office (now Medium priority)"),
    (45, False, "Low score, no Portland office"),
    (45, True, "Low score, WITH Portland office (still Low, but better)"),
]

print(f"Configuration:")
print(f"  Portland Bonus: +{PORTLAND_BONUS} points")
print(f"  Min Threshold: {MIN_THRESHOLD}")
print()
print("=" * 80)
print()

for base_score, has_portland, description in test_cases:
    result = calculate_result(base_score, has_portland)

    portland_icon = "🏙️ " if has_portland else "  "
    pass_icon = "✅" if result["passes"] else "❌"

    print(f"{pass_icon} {portland_icon}{description}")
    print(f"   Base: {result['base']} → Adjusted: {result['adjusted']} (Bonus: +{result['bonus']})")
    print(f"   Priority: {result['priority']} | Passes threshold: {result['passes']}")
    print()

print("=" * 80)
print("KEY INSIGHTS")
print("=" * 80)
print()
print(f"✅ Portland companies need only {MIN_THRESHOLD - PORTLAND_BONUS} base score to pass")
print(f"✅ Non-Portland companies need {MIN_THRESHOLD} base score to pass")
print()
print("Priority Tier Shifts (with +15 bonus):")
print("  • Base 60 → 75 (Medium → High)")
print("  • Base 70 → 85 (Medium → High)")
print("  • Base 45 → 60 (Low → Medium)")
print()
print("Companies with Portland offices:")
print("  • Coinbase (Portland secondary HQ)")
print("  • Cloudflare (Portland data center)")
print()

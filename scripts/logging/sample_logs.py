#!/usr/bin/env python3
"""Sample logging script to demonstrate company name truncation."""

import argparse
import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from job_finder.logging_config import format_company_name


def demo_truncation(company_names):
    """Demonstrate the truncation behavior."""
    print("\n" + "=" * 80)
    print("COMPANY NAME TRUNCATION DEMONSTRATION")
    print("=" * 80)
    
    results = []
    
    for company_name in company_names:
        full_name, display_name = format_company_name(company_name)
        
        result = {
            "original_name": company_name,
            "full_name": full_name,
            "display_name": display_name,
            "original_length": len(company_name),
            "display_length": len(display_name),
            "truncated": full_name != display_name,
        }
        results.append(result)
        
        print(f"\n{'-' * 80}")
        print(f"Original: {company_name}")
        print(f"  Length: {len(company_name)} chars")
        print(f"\nDisplay:  {display_name}")
        print(f"  Length: {len(display_name)} chars")
        print(f"  Truncated: {'Yes' if result['truncated'] else 'No'}")
    
    print(f"\n{'=' * 80}\n")
    return results


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Demonstrate company name truncation")
    parser.add_argument("--company", type=str, help="Company name to test")
    parser.add_argument("--all", action="store_true", help="Run with test names")
    parser.add_argument("--output", type=str, help="JSON output file")
    
    args = parser.parse_args()
    
    if args.company:
        company_names = [args.company]
    elif args.all:
        company_names = [
            "Acme Inc",
            "International Business Machines Corporation",
            "Sony Interactive Entertainment America LLC Worldwide Studios Division",
            "The Walt Disney Company Global Entertainment and Media Distribution",
            "A" * 150,
        ]
    else:
        print("Error: Provide --company or --all", file=sys.stderr)
        return 1
    
    results = demo_truncation(company_names)
    
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\n✅ Results saved to: {output_path}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

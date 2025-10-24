#!/usr/bin/env python3
"""
Test script for Canadian Mining HS Codes classification.
"""

from hs_codes_mining import get_mining_hs_codes, MineralCategory


def main():
    """Test the HS code classification."""
    hs = get_mining_hs_codes()
    
    print("="*70)
    print("Canadian Mining HS Codes Classification")
    print("="*70)
    
    # Summary Statistics
    stats = hs.get_summary_stats()
    print(f"\n📊 Summary Statistics:")
    print(f"  Total HS Codes: {stats['total_codes']}")
    print(f"  Canadian Production: {stats['canadian_production']}")
    print(f"  Chapters Covered: {stats['chapters_covered']}")
    print(f"  Regions with Production: {stats['regions_covered']}")
    
    print(f"\n📋 By Category:")
    for cat, count in stats['by_category'].items():
        if count > 0:
            print(f"  {cat}: {count} codes")
    
    # Example 1: Copper Ore
    print("\n" + "="*70)
    print("Example 1: Copper Ore")
    print("="*70)
    copper = hs.get("2603.00")
    if copper:
        print(f"HS Code: {copper.code}")
        print(f"Common Name: {copper.common_name}")
        print(f"Description: {copper.description}")
        print(f"Category: {copper.category.value}")
        print(f"Chapter: {copper.chapter}")
        print(f"Canadian Regions: {', '.join(copper.major_canadian_regions)}")
    
    # Example 2: Search for Potash
    print("\n" + "="*70)
    print("Example 2: Search for Potash")
    print("="*70)
    potash_codes = hs.search_by_name("potash")
    for code in potash_codes:
        print(f"  {code}")
        print(f"    Regions: {', '.join(code.major_canadian_regions)}")
    
    # Example 3: Saskatchewan Production
    print("\n" + "="*70)
    print("Example 3: Saskatchewan (SK) Mining Production")
    print("="*70)
    sk_codes = hs.get_by_region("SK")
    print(f"Found {len(sk_codes)} mineral products produced in Saskatchewan:\n")
    for code in sk_codes:
        print(f"  • {code.common_name} (HS {code.code})")
    
    # Example 4: Precious Metals
    print("\n" + "="*70)
    print("Example 4: Precious Metals")
    print("="*70)
    precious = hs.get_by_category(MineralCategory.PRECIOUS_METALS)
    print(f"Found {len(precious)} precious metal products:\n")
    for code in precious:
        print(f"  • {code.common_name} (HS {code.code})")
        if code.major_canadian_regions:
            print(f"    Produced in: {', '.join(code.major_canadian_regions)}")
    
    # Example 5: Base Metals (BC Production)
    print("\n" + "="*70)
    print("Example 5: British Columbia (BC) Mining Production")
    print("="*70)
    bc_codes = hs.get_by_region("BC")
    print(f"Found {len(bc_codes)} mineral products produced in BC:\n")
    for code in sorted(bc_codes, key=lambda x: x.category.value):
        print(f"  • {code.common_name} (HS {code.code}) - {code.category.value}")
    
    # Example 6: Chapter 26 (Ores, slag and ash)
    print("\n" + "="*70)
    print("Example 6: Chapter 26 - Ores, Slag and Ash")
    print("="*70)
    chapter_26 = hs.get_by_chapter("26")
    print(f"Found {len(chapter_26)} products in Chapter 26:\n")
    for code in chapter_26[:10]:  # Show first 10
        canadian = "✓" if code.canadian_production else "✗"
        print(f"  {canadian} HS {code.code}: {code.common_name}")
    
    # Example 7: Uranium (Major Canadian Export)
    print("\n" + "="*70)
    print("Example 7: Uranium (Major Canadian Export)")
    print("="*70)
    uranium = hs.get("2612.10")
    if uranium:
        print(f"Product: {uranium.common_name}")
        print(f"HS Code: {uranium.code}")
        print(f"Description: {uranium.description}")
        print(f"Major Production: {', '.join(uranium.major_canadian_regions)}")
        print(f"Note: Canada (Saskatchewan) is the 2nd largest uranium producer globally")
    
    # Example 8: Diamonds
    print("\n" + "="*70)
    print("Example 8: Canadian Diamonds")
    print("="*70)
    diamonds = hs.get_by_category(MineralCategory.DIAMONDS)
    print(f"Found {len(diamonds)} diamond products:\n")
    for code in diamonds:
        print(f"  • {code.common_name} (HS {code.code})")
        print(f"    Produced in: {', '.join(code.major_canadian_regions)}")
    
    print("\n" + "="*70)
    print("✓ Classification system ready for use!")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()



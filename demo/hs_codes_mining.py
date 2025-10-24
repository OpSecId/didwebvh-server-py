"""
Harmonized System (HS) Code Classification for Canadian Mining Raw Materials
Based on HS 2022 Nomenclature

Reference: https://www.wcoomd.org/en/topics/nomenclature/instrument-and-tools/hs-nomenclature-2022-edition.aspx
Canadian Trade Data: https://www.cbsa-asfc.gc.ca/trade-commerce/tariff-tarif/2024/html/tblmod-1-eng.html
"""

from typing import Optional, List, Dict
from dataclasses import dataclass
from enum import Enum


class MineralCategory(str, Enum):
    """Main categories of mining products."""
    PRECIOUS_METALS = "Precious Metals"
    BASE_METALS = "Base Metals"
    COAL = "Coal"
    IRON_ORE = "Iron Ore"
    INDUSTRIAL_MINERALS = "Industrial Minerals"
    RARE_EARTH_ELEMENTS = "Rare Earth Elements"
    URANIUM = "Uranium"
    POTASH = "Potash and Fertilizers"
    DIAMONDS = "Diamonds"
    OTHER_MINERALS = "Other Minerals"


@dataclass
class HSCode:
    """
    Harmonized System Code for a mining product.
    
    HS Code Structure:
    - Chapter (2 digits): General product category (e.g., 26 = Ores, slag and ash)
    - Heading (4 digits): More specific category (e.g., 2603 = Copper ores)
    - Subheading (6 digits): Detailed classification (e.g., 2603.00 = Copper ores and concentrates)
    - National (8-10 digits): Country-specific classification
    """
    code: str  # Full HS code (6-10 digits)
    description: str
    category: MineralCategory
    chapter: str  # 2-digit chapter
    heading: str  # 4-digit heading
    common_name: str
    canadian_production: bool = True  # Whether Canada produces this mineral
    major_canadian_regions: List[str] = None  # BC, ON, QC, SK, NT, YT, etc.
    
    def __post_init__(self):
        """Validate and extract HS code components."""
        self.code = self.code.replace(".", "")
        if len(self.code) < 6:
            raise ValueError(f"HS code must be at least 6 digits: {self.code}")
        
        self.chapter = self.code[:2]
        self.heading = self.code[:4]
        
        if self.major_canadian_regions is None:
            self.major_canadian_regions = []
    
    @property
    def subheading(self) -> str:
        """6-digit subheading."""
        return self.code[:6]
    
    def __str__(self) -> str:
        return f"HS {self.code}: {self.common_name} ({self.description})"


class CanadianMiningHSCodes:
    """
    Classification system for Canadian mining products using HS codes.
    
    Major Canadian Mining Products:
    - Potash (Saskatchewan - 40% of world production)
    - Uranium (Saskatchewan, Athabasca Basin)
    - Nickel (Ontario, Manitoba)
    - Copper (BC, Ontario, Quebec)
    - Gold (Ontario, Quebec, BC)
    - Diamonds (NWT, Nunavut)
    - Iron Ore (Quebec, Newfoundland and Labrador)
    - Coal (BC, Alberta)
    - Zinc (BC, NB, Quebec)
    """
    
    def __init__(self):
        """Initialize with comprehensive Canadian mining HS codes."""
        self._codes: Dict[str, HSCode] = {}
        self._initialize_codes()
    
    def _initialize_codes(self):
        """Initialize all mining-related HS codes."""
        
        # ================================================================
        # Chapter 25: Salt; sulphur; earths and stone; plastering materials, lime and cement
        # ================================================================
        
        # Potash (Major Canadian export)
        self._add(HSCode(
            code="2504.10",
            description="Natural graphite in powder or in flakes",
            category=MineralCategory.INDUSTRIAL_MINERALS,
            chapter="25",
            heading="2504",
            common_name="Graphite",
            major_canadian_regions=["QC"]
        ))
        
        self._add(HSCode(
            code="2510.10",
            description="Natural calcium phosphates, unground",
            category=MineralCategory.INDUSTRIAL_MINERALS,
            chapter="25",
            heading="2510",
            common_name="Phosphate Rock",
            major_canadian_regions=["BC", "ON"]
        ))
        
        # ================================================================
        # Chapter 26: Ores, slag and ash
        # ================================================================
        
        # Iron Ore
        self._add(HSCode(
            code="2601.11",
            description="Iron ores and concentrates, non-agglomerated",
            category=MineralCategory.IRON_ORE,
            chapter="26",
            heading="2601",
            common_name="Iron Ore",
            major_canadian_regions=["QC", "NL"]
        ))
        
        self._add(HSCode(
            code="2601.12",
            description="Iron ores and concentrates, agglomerated",
            category=MineralCategory.IRON_ORE,
            chapter="26",
            heading="2601",
            common_name="Iron Ore Pellets",
            major_canadian_regions=["QC", "NL"]
        ))
        
        # Copper Ores
        self._add(HSCode(
            code="2603.00",
            description="Copper ores and concentrates",
            category=MineralCategory.BASE_METALS,
            chapter="26",
            heading="2603",
            common_name="Copper Ore",
            major_canadian_regions=["BC", "ON", "QC"]
        ))
        
        # Nickel Ores
        self._add(HSCode(
            code="2604.00",
            description="Nickel ores and concentrates",
            category=MineralCategory.BASE_METALS,
            chapter="26",
            heading="2604",
            common_name="Nickel Ore",
            major_canadian_regions=["ON", "MB", "QC"]
        ))
        
        # Cobalt Ores
        self._add(HSCode(
            code="2605.00",
            description="Cobalt ores and concentrates",
            category=MineralCategory.BASE_METALS,
            chapter="26",
            heading="2605",
            common_name="Cobalt Ore",
            major_canadian_regions=["ON"]
        ))
        
        # Aluminum Ores (Bauxite)
        self._add(HSCode(
            code="2606.00",
            description="Aluminium ores and concentrates",
            category=MineralCategory.BASE_METALS,
            chapter="26",
            heading="2606",
            common_name="Bauxite",
            canadian_production=False  # Canada imports bauxite
        ))
        
        # Lead Ores
        self._add(HSCode(
            code="2607.00",
            description="Lead ores and concentrates",
            category=MineralCategory.BASE_METALS,
            chapter="26",
            heading="2607",
            common_name="Lead Ore",
            major_canadian_regions=["BC", "NB"]
        ))
        
        # Zinc Ores
        self._add(HSCode(
            code="2608.00",
            description="Zinc ores and concentrates",
            category=MineralCategory.BASE_METALS,
            chapter="26",
            heading="2608",
            common_name="Zinc Ore",
            major_canadian_regions=["BC", "NB", "QC"]
        ))
        
        # Tin Ores
        self._add(HSCode(
            code="2609.00",
            description="Tin ores and concentrates",
            category=MineralCategory.BASE_METALS,
            chapter="26",
            heading="2609",
            common_name="Tin Ore",
            canadian_production=False
        ))
        
        # Chromium Ores
        self._add(HSCode(
            code="2610.00",
            description="Chromium ores and concentrates",
            category=MineralCategory.BASE_METALS,
            chapter="26",
            heading="2610",
            common_name="Chromite",
            canadian_production=False
        ))
        
        # Tungsten Ores
        self._add(HSCode(
            code="2611.00",
            description="Tungsten ores and concentrates",
            category=MineralCategory.BASE_METALS,
            chapter="26",
            heading="2611",
            common_name="Tungsten Ore",
            major_canadian_regions=["YT", "NT"]
        ))
        
        # Uranium/Thorium Ores (Major Canadian export)
        self._add(HSCode(
            code="2612.10",
            description="Uranium ores and concentrates",
            category=MineralCategory.URANIUM,
            chapter="26",
            heading="2612",
            common_name="Uranium Ore",
            major_canadian_regions=["SK"]  # Athabasca Basin
        ))
        
        self._add(HSCode(
            code="2612.20",
            description="Thorium ores and concentrates",
            category=MineralCategory.RARE_EARTH_ELEMENTS,
            chapter="26",
            heading="2612",
            common_name="Thorium Ore",
            major_canadian_regions=["ON", "QC"]
        ))
        
        # Molybdenum Ores
        self._add(HSCode(
            code="2613.10",
            description="Molybdenum ores and concentrates, roasted",
            category=MineralCategory.BASE_METALS,
            chapter="26",
            heading="2613",
            common_name="Molybdenum Ore",
            major_canadian_regions=["BC"]
        ))
        
        # Titanium Ores
        self._add(HSCode(
            code="2614.00",
            description="Titanium ores and concentrates",
            category=MineralCategory.BASE_METALS,
            chapter="26",
            heading="2614",
            common_name="Ilmenite",
            major_canadian_regions=["QC"]
        ))
        
        # Niobium, Tantalum, Vanadium Ores
        self._add(HSCode(
            code="2615.10",
            description="Zirconium ores and concentrates",
            category=MineralCategory.RARE_EARTH_ELEMENTS,
            chapter="26",
            heading="2615",
            common_name="Zircon",
            major_canadian_regions=["QC"]
        ))
        
        self._add(HSCode(
            code="2615.90",
            description="Niobium, tantalum, vanadium or other ores",
            category=MineralCategory.RARE_EARTH_ELEMENTS,
            chapter="26",
            heading="2615",
            common_name="Niobium/Tantalum Ore",
            major_canadian_regions=["ON", "QC"]
        ))
        
        # Precious Metal Ores
        self._add(HSCode(
            code="2616.10",
            description="Silver ores and concentrates",
            category=MineralCategory.PRECIOUS_METALS,
            chapter="26",
            heading="2616",
            common_name="Silver Ore",
            major_canadian_regions=["BC", "ON", "QC"]
        ))
        
        self._add(HSCode(
            code="2616.90",
            description="Precious metal ores and concentrates (other)",
            category=MineralCategory.PRECIOUS_METALS,
            chapter="26",
            heading="2616",
            common_name="Precious Metal Ores",
            major_canadian_regions=["ON", "QC", "BC", "YT", "NT", "NU"]
        ))
        
        # Other Ores
        self._add(HSCode(
            code="2617.10",
            description="Antimony ores and concentrates",
            category=MineralCategory.OTHER_MINERALS,
            chapter="26",
            heading="2617",
            common_name="Antimony Ore",
            major_canadian_regions=["NB"]
        ))
        
        self._add(HSCode(
            code="2617.90",
            description="Other ores and concentrates",
            category=MineralCategory.OTHER_MINERALS,
            chapter="26",
            heading="2617",
            common_name="Other Ores",
            major_canadian_regions=[]
        ))
        
        # ================================================================
        # Chapter 27: Mineral fuels, oils, distillation products
        # ================================================================
        
        # Coal
        self._add(HSCode(
            code="2701.11",
            description="Anthracite coal, not agglomerated",
            category=MineralCategory.COAL,
            chapter="27",
            heading="2701",
            common_name="Anthracite Coal",
            major_canadian_regions=["BC", "AB"]
        ))
        
        self._add(HSCode(
            code="2701.12",
            description="Bituminous coal, not agglomerated",
            category=MineralCategory.COAL,
            chapter="27",
            heading="2701",
            common_name="Bituminous Coal",
            major_canadian_regions=["BC", "AB", "SK"]
        ))
        
        self._add(HSCode(
            code="2701.19",
            description="Other coal, not agglomerated",
            category=MineralCategory.COAL,
            chapter="27",
            heading="2701",
            common_name="Sub-bituminous Coal",
            major_canadian_regions=["BC", "AB", "SK"]
        ))
        
        self._add(HSCode(
            code="2701.20",
            description="Briquettes, ovoids and similar solid fuels from coal",
            category=MineralCategory.COAL,
            chapter="27",
            heading="2701",
            common_name="Coal Briquettes",
            major_canadian_regions=["BC", "AB"]
        ))
        
        # ================================================================
        # Chapter 28: Potash and other fertilizers
        # ================================================================
        
        # Potash (Saskatchewan - World's largest producer)
        self._add(HSCode(
            code="3104.20",
            description="Potassium chloride",
            category=MineralCategory.POTASH,
            chapter="31",
            heading="3104",
            common_name="Potash (KCl)",
            major_canadian_regions=["SK"]  # 40% of world production
        ))
        
        self._add(HSCode(
            code="3104.30",
            description="Potassium sulphate",
            category=MineralCategory.POTASH,
            chapter="31",
            heading="3104",
            common_name="Potassium Sulphate",
            major_canadian_regions=["SK"]
        ))
        
        # ================================================================
        # Chapter 71: Diamonds and precious stones
        # ================================================================
        
        # Diamonds (NWT, Nunavut)
        self._add(HSCode(
            code="7102.10",
            description="Diamonds, unsorted",
            category=MineralCategory.DIAMONDS,
            chapter="71",
            heading="7102",
            common_name="Diamonds (unsorted)",
            major_canadian_regions=["NT", "NU"]
        ))
        
        self._add(HSCode(
            code="7102.21",
            description="Industrial diamonds, unworked or simply sawn",
            category=MineralCategory.DIAMONDS,
            chapter="71",
            heading="7102",
            common_name="Industrial Diamonds",
            major_canadian_regions=["NT", "NU"]
        ))
        
        self._add(HSCode(
            code="7102.31",
            description="Non-industrial diamonds, unworked or simply sawn",
            category=MineralCategory.DIAMONDS,
            chapter="71",
            heading="7102",
            common_name="Gem Diamonds",
            major_canadian_regions=["NT", "NU"]
        ))
        
        # ================================================================
        # Chapter 74-81: Refined metals (unwrought)
        # ================================================================
        
        # Copper (unwrought)
        self._add(HSCode(
            code="7403.11",
            description="Refined copper cathodes and sections of cathodes",
            category=MineralCategory.BASE_METALS,
            chapter="74",
            heading="7403",
            common_name="Copper Cathodes",
            major_canadian_regions=["BC", "ON", "QC"]
        ))
        
        # Nickel (unwrought)
        self._add(HSCode(
            code="7502.10",
            description="Nickel, not alloyed, unwrought",
            category=MineralCategory.BASE_METALS,
            chapter="75",
            heading="7502",
            common_name="Nickel (unwrought)",
            major_canadian_regions=["ON", "MB"]
        ))
        
        # Gold (unwrought)
        self._add(HSCode(
            code="7108.13",
            description="Gold in semi-manufactured forms",
            category=MineralCategory.PRECIOUS_METALS,
            chapter="71",
            heading="7108",
            common_name="Gold Bars",
            major_canadian_regions=["ON", "QC", "BC", "NT", "NU"]
        ))
    
    def _add(self, hs_code: HSCode):
        """Add an HS code to the classification."""
        self._codes[hs_code.code] = hs_code
    
    def get(self, code: str) -> Optional[HSCode]:
        """Get an HS code by its code number."""
        code = code.replace(".", "")
        return self._codes.get(code)
    
    def search_by_name(self, name: str) -> List[HSCode]:
        """Search for HS codes by common name or description."""
        name_lower = name.lower()
        results = []
        for hs_code in self._codes.values():
            if (name_lower in hs_code.common_name.lower() or 
                name_lower in hs_code.description.lower()):
                results.append(hs_code)
        return results
    
    def get_by_category(self, category: MineralCategory) -> List[HSCode]:
        """Get all HS codes for a specific mineral category."""
        return [code for code in self._codes.values() if code.category == category]
    
    def get_by_region(self, region: str) -> List[HSCode]:
        """Get all HS codes produced in a specific Canadian region."""
        region_upper = region.upper()
        return [
            code for code in self._codes.values() 
            if region_upper in [r.upper() for r in code.major_canadian_regions]
        ]
    
    def get_canadian_production(self) -> List[HSCode]:
        """Get all HS codes for minerals produced in Canada."""
        return [code for code in self._codes.values() if code.canadian_production]
    
    def get_by_chapter(self, chapter: str) -> List[HSCode]:
        """Get all HS codes in a specific chapter."""
        return [code for code in self._codes.values() if code.chapter == chapter]
    
    def list_all(self) -> List[HSCode]:
        """Get all HS codes."""
        return list(self._codes.values())
    
    def get_summary_stats(self) -> Dict:
        """Get summary statistics about the classification."""
        all_codes = self.list_all()
        return {
            "total_codes": len(all_codes),
            "canadian_production": len(self.get_canadian_production()),
            "by_category": {
                cat.value: len(self.get_by_category(cat))
                for cat in MineralCategory
            },
            "chapters_covered": len(set(code.chapter for code in all_codes)),
            "regions_covered": len(set(
                region 
                for code in all_codes 
                for region in code.major_canadian_regions
            ))
        }


# Singleton instance
_mining_hs_codes = None


def get_mining_hs_codes() -> CanadianMiningHSCodes:
    """Get the singleton instance of CanadianMiningHSCodes."""
    global _mining_hs_codes
    if _mining_hs_codes is None:
        _mining_hs_codes = CanadianMiningHSCodes()
    return _mining_hs_codes



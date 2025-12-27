from typing import List, Dict, Any
from enum import Enum
from dataclasses import dataclass
from .gsc_ingestor import GSCPageMetrics

class StrategyType(Enum):
    PROTECT = "PROTECT" # Winners
    OPTIMIZE_CTR = "OPTIMIZE_CTR" # Striking Distance
    REVIVE = "REVIVE" # Underperformers
    PRUNE = "PRUNE" # Dead Weight
    MERGE = "MERGE" # Cannibalization (Future)
    IGNORE = "IGNORE"

@dataclass
class StrategyAction:
    url: str
    strategy: StrategyType
    reason: str
    suggested_fix: str
    metrics: GSCPageMetrics

class PerformanceAnalyzer:
    """
    Analyzes GSCPageMetrics and assigns a StrategyAction based on the 5-Bucket Logic.
    """

    def analyze_batch(self, pages: List[GSCPageMetrics]) -> List[StrategyAction]:
        actions = []
        for page in pages:
            actions.append(self.analyze_url(page))
        return actions

    def analyze_url(self, page: GSCPageMetrics) -> StrategyAction:
        
        # 4. 💀 Dead Weight (Prune)
        # Logic: 0 Clicks in 12 months AND < 100 Impressions
        if page.clicks == 0 and page.impressions < 100:
            return StrategyAction(
                url=page.url,
                strategy=StrategyType.PRUNE,
                reason="Zero clicks and low visibility in 12 months.",
                suggested_fix="301 Redirect to relevant category or delete.",
                metrics=page
            )

        # 1. 🏆 Winners (Protect)
        # Logic: High Traffic (Pos < 3) - Simplified for Phase 1
        if page.position < 3.0:
            return StrategyAction(
                url=page.url,
                strategy=StrategyType.PROTECT,
                reason="Ranking in top 3 positions.",
                suggested_fix="Monitor & Protect. Ensure technical health is perfect.",
                metrics=page
            )

        # 2. 🎯 Striking Distance (Quick Wins)
        # Logic: Pos 4-20 AND Impressions > 1000
        if 4.0 <= page.position <= 20.0 and page.impressions > 1000:
            return StrategyAction(
                url=page.url,
                strategy=StrategyType.OPTIMIZE_CTR,
                reason=f"Ranking #{page.position:.1f} with good visibility ({page.impressions} impr).",
                suggested_fix="Rewrite Title/Meta for CTR. Add FAQ schema.",
                metrics=page
            )

        # 3. 📉 Underperformers (Revive)
        # Logic: Pos > 20 BUT High Impressions (> 1000)
        # Or just generally poor performance despite existing
        if page.position > 20.0 and page.impressions > 1000:
             return StrategyAction(
                url=page.url,
                strategy=StrategyType.REVIVE,
                reason=f"Ranking poorly (#{page.position:.1f}) but has demand ({page.impressions} impr).",
                suggested_fix="Quality Update. Expand content, add internal links.",
                metrics=page
            )

        # Default / Ignore
        return StrategyAction(
            url=page.url,
            strategy=StrategyType.IGNORE,
            reason="Metrics do not trigger a specific strategy bucket.",
            suggested_fix="No immediate action.",
            metrics=page
        )

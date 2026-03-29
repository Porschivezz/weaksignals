"""Signal scoring and classification for the weak signals detection pipeline."""

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


# Score thresholds for signal classification
NOISE_THRESHOLD = 0.3
EMERGING_TREND_THRESHOLD = 0.6
WEAK_SIGNAL_THRESHOLD = 0.8

SIGNAL_TYPE_NOISE = "noise"
SIGNAL_TYPE_EMERGING_TREND = "emerging_trend"
SIGNAL_TYPE_WEAK_SIGNAL = "weak_signal"
SIGNAL_TYPE_STRONG_SIGNAL = "strong_signal"


@dataclass
class CompositeScore:
    """Composite score combining novelty, momentum, and community signals."""

    novelty_score: float
    momentum_score: float
    community_score: float
    composite: float
    signal_type: str
    components: dict[str, float]


@dataclass
class TenantRelevanceScore:
    """Tenant-specific relevance scoring for a signal."""

    industry_relevance: float
    competitor_activity: float
    opportunity_score: float
    total_relevance: float


# Default weights for composite score
DEFAULT_COMPOSITE_WEIGHTS: dict[str, float] = {
    "novelty": 0.40,
    "momentum": 0.35,
    "community": 0.25,
}

# Default weights for tenant relevance
DEFAULT_RELEVANCE_WEIGHTS: dict[str, float] = {
    "industry": 0.45,
    "competitor": 0.25,
    "opportunity": 0.30,
}


class SignalScorer:
    """Scorer for computing composite signal scores and tenant relevance.

    Combines novelty, momentum, and community change signals into a
    single composite score, then classifies signals by type based
    on configurable thresholds.
    """

    def __init__(
        self,
        composite_weights: dict[str, float] | None = None,
        relevance_weights: dict[str, float] | None = None,
    ) -> None:
        self.composite_weights = composite_weights or DEFAULT_COMPOSITE_WEIGHTS.copy()
        self.relevance_weights = relevance_weights or DEFAULT_RELEVANCE_WEIGHTS.copy()

    def compute_composite_score(
        self,
        novelty: float,
        momentum: float,
        community_change: float,
    ) -> CompositeScore:
        """Compute a weighted composite score from sub-scores.

        Args:
            novelty: Novelty score (0-1).
            momentum: Momentum score (0-1).
            community_change: Community change score (0-1).

        Returns:
            CompositeScore with classification and components.
        """
        # Clamp inputs to [0, 1]
        novelty = max(0.0, min(1.0, novelty))
        momentum = max(0.0, min(1.0, momentum))
        community_change = max(0.0, min(1.0, community_change))

        composite = (
            self.composite_weights["novelty"] * novelty
            + self.composite_weights["momentum"] * momentum
            + self.composite_weights["community"] * community_change
        )
        composite = round(max(0.0, min(1.0, composite)), 4)

        signal_type = self.classify_signal(composite)

        components = {
            "novelty": round(novelty, 4),
            "momentum": round(momentum, 4),
            "community_change": round(community_change, 4),
            "weights": self.composite_weights.copy(),
        }

        result = CompositeScore(
            novelty_score=novelty,
            momentum_score=momentum,
            community_score=community_change,
            composite=composite,
            signal_type=signal_type,
            components=components,
        )

        logger.debug(
            "Composite score: %.4f (%s) [novelty=%.4f, momentum=%.4f, community=%.4f]",
            composite, signal_type, novelty, momentum, community_change,
        )
        return result

    def compute_tenant_relevance(
        self,
        signal: dict,
        tenant_config: dict,
        embeddings_service: object = None,
    ) -> TenantRelevanceScore:
        """Compute tenant-specific relevance for a signal.

        Args:
            signal: Dict with signal data including 'title', 'description',
                    'entities' (list of names), 'authors' (list of dicts).
            tenant_config: Dict with tenant settings:
                - industry_verticals: list[str]
                - competitor_list: dict with 'names' and/or 'institutions'
                - technology_watchlist: list[str]
                - signal_sensitivity: float
            embeddings_service: An EmbeddingService instance.

        Returns:
            TenantRelevanceScore with sub-scores and total relevance.
        """
        industry_relevance = self._compute_industry_relevance(
            signal, tenant_config, embeddings_service
        )
        competitor_activity = self._compute_competitor_activity(signal, tenant_config)
        opportunity_score = self._compute_opportunity_score(
            signal, tenant_config, embeddings_service
        )

        total = (
            self.relevance_weights["industry"] * industry_relevance
            + self.relevance_weights["competitor"] * competitor_activity
            + self.relevance_weights["opportunity"] * opportunity_score
        )

        # Apply tenant sensitivity multiplier
        sensitivity = tenant_config.get("signal_sensitivity", 0.5)
        # Higher sensitivity = lower threshold = more signals shown
        # Boost total when sensitivity is high
        adjusted_total = total * (0.5 + sensitivity)
        adjusted_total = max(0.0, min(1.0, adjusted_total))

        result = TenantRelevanceScore(
            industry_relevance=round(industry_relevance, 4),
            competitor_activity=round(competitor_activity, 4),
            opportunity_score=round(opportunity_score, 4),
            total_relevance=round(adjusted_total, 4),
        )

        logger.debug(
            "Tenant relevance: %.4f [industry=%.4f, competitor=%.4f, opportunity=%.4f]",
            result.total_relevance,
            result.industry_relevance,
            result.competitor_activity,
            result.opportunity_score,
        )
        return result

    @staticmethod
    def classify_signal(composite_score: float) -> str:
        """Classify a signal based on its composite score.

        Thresholds:
            NOISE < 0.3 < EMERGING_TREND < 0.6 < WEAK_SIGNAL < 0.8 < STRONG_SIGNAL

        Args:
            composite_score: The composite score to classify.

        Returns:
            Signal type string.
        """
        if composite_score < NOISE_THRESHOLD:
            return SIGNAL_TYPE_NOISE
        if composite_score < EMERGING_TREND_THRESHOLD:
            return SIGNAL_TYPE_EMERGING_TREND
        if composite_score < WEAK_SIGNAL_THRESHOLD:
            return SIGNAL_TYPE_WEAK_SIGNAL
        return SIGNAL_TYPE_STRONG_SIGNAL

    def _compute_industry_relevance(
        self,
        signal: dict,
        tenant_config: dict,
        embeddings_service: object = None,
    ) -> float:
        """Compute relevance of signal to tenant's industry verticals.

        Uses keyword matching between signal text and industry verticals.
        """
        industry_verticals = tenant_config.get("industry_verticals", [])
        if not industry_verticals:
            return 0.5  # Neutral if no industry configured

        signal_text = f"{signal.get('title', '')} {signal.get('description', '')}".lower()
        if not signal_text.strip():
            return 0.0

        # Keyword matching against industry verticals
        matches = 0
        total_terms = 0
        for vertical in industry_verticals:
            keywords = [kw.strip().lower() for kw in vertical.split() if len(kw.strip()) > 2]
            total_terms += len(keywords)
            for kw in keywords:
                if kw in signal_text:
                    matches += 1

        if total_terms == 0:
            return 0.5

        # Normalize: even a few keyword matches indicate relevance
        score = min(matches / max(total_terms * 0.3, 1), 1.0)
        return round(max(0.0, min(1.0, score)), 4)

    @staticmethod
    def _compute_competitor_activity(signal: dict, tenant_config: dict) -> float:
        """Check if competitors are mentioned in the signal.

        Checks signal title, description, and authors against competitor names.
        """
        competitor_list = tenant_config.get("competitor_list") or {}
        if not competitor_list:
            return 0.0

        # Extract competitor names — support both formats:
        # {"names": [...]} or {"CompanyName": {...}}
        competitor_names = set()
        if "names" in competitor_list:
            competitor_names = set(n.lower() for n in competitor_list["names"])
        else:
            # Keys are competitor names
            competitor_names = set(n.lower() for n in competitor_list.keys())

        if not competitor_names:
            return 0.0

        # Check signal text for competitor mentions
        signal_text = f"{signal.get('title', '')} {signal.get('description', '')}".lower()
        text_matches = sum(1 for cn in competitor_names if cn in signal_text)

        # Check authors
        authors = signal.get("authors", [])
        author_matches = 0
        for author in authors:
            author_name = (author.get("name", "") or "").lower()
            author_inst = (author.get("institution", "") or "").lower()
            if any(cn in author_name or cn in author_inst for cn in competitor_names):
                author_matches += 1

        total_matches = text_matches + author_matches
        if total_matches >= 3:
            return 1.0
        if total_matches >= 1:
            return 0.5 + (total_matches * 0.15)
        return 0.0

    def _compute_opportunity_score(
        self,
        signal: dict,
        tenant_config: dict,
        embeddings_service: object = None,
    ) -> float:
        """Compute how actionable a signal is for a tenant.

        Based on overlap between signal text/entities and tenant's technology watchlist.
        """
        watchlist = tenant_config.get("technology_watchlist", [])
        if not watchlist:
            return 0.5  # Neutral if no watchlist

        signal_entities = signal.get("entities", [])
        signal_text = f"{signal.get('title', '')} {signal.get('description', '')}".lower()

        # Check direct text overlap from entities
        watchlist_lower = set(w.lower() for w in watchlist)
        entity_names = [e.lower() if isinstance(e, str) else e.get("name", "").lower() for e in signal_entities]

        direct_matches = 0
        for entity_name in entity_names:
            for watch_term in watchlist_lower:
                if watch_term in entity_name or entity_name in watch_term:
                    direct_matches += 1
                    break

        # Also check watchlist keywords against signal title/description
        text_matches = 0
        for watch_term in watchlist_lower:
            if watch_term in signal_text:
                text_matches += 1

        if direct_matches > 0:
            direct_score = min(direct_matches / len(watchlist), 1.0)
        else:
            direct_score = 0.0

        if text_matches > 0:
            text_score = min(text_matches / len(watchlist), 1.0)
        else:
            text_score = 0.0

        # Combine: direct entity matches + text matches
        return round(max(direct_score, text_score), 4)

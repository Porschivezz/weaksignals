"""Signal scoring and classification for the weak signals detection pipeline."""

import logging
from dataclasses import dataclass

import numpy as np

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
        embeddings_service: object,
    ) -> float:
        """Compute cosine similarity of signal embedding to tenant industry verticals.

        Args:
            signal: Signal dict with 'title' and 'description'.
            tenant_config: Tenant config with 'industry_verticals'.
            embeddings_service: EmbeddingService instance.

        Returns:
            Float between 0 and 1 indicating industry relevance.
        """
        industry_verticals = tenant_config.get("industry_verticals", [])
        if not industry_verticals:
            return 0.5  # Neutral if no industry configured

        signal_text = f"{signal.get('title', '')} {signal.get('description', '')}"
        if not signal_text.strip():
            return 0.0

        try:
            signal_embedding = np.array(embeddings_service.embed_text(signal_text))
            signal_norm = np.linalg.norm(signal_embedding)
            if signal_norm == 0:
                return 0.0

            industry_text = " ".join(industry_verticals)
            industry_embedding = np.array(embeddings_service.embed_text(industry_text))
            industry_norm = np.linalg.norm(industry_embedding)
            if industry_norm == 0:
                return 0.0

            cosine_sim = float(
                np.dot(signal_embedding, industry_embedding)
                / (signal_norm * industry_norm)
            )
            # Map from [-1, 1] to [0, 1]
            return max(0.0, min(1.0, (cosine_sim + 1.0) / 2.0))
        except Exception as exc:
            logger.warning("Industry relevance computation failed: %s", exc)
            return 0.0

    @staticmethod
    def _compute_competitor_activity(signal: dict, tenant_config: dict) -> float:
        """Check if competitors are among the signal's authors.

        Args:
            signal: Signal dict with 'authors' (list of dicts with name, institution).
            tenant_config: Tenant config with 'competitor_list' dict containing
                          'names' and/or 'institutions'.

        Returns:
            Float between 0 and 1 indicating competitor activity level.
        """
        competitor_list = tenant_config.get("competitor_list") or {}
        competitor_names = set(
            n.lower() for n in competitor_list.get("names", [])
        )
        competitor_institutions = set(
            i.lower() for i in competitor_list.get("institutions", [])
        )

        if not competitor_names and not competitor_institutions:
            return 0.0

        authors = signal.get("authors", [])
        if not authors:
            return 0.0

        matches = 0
        total_checks = 0

        for author in authors:
            author_name = (author.get("name", "") or "").lower()
            author_inst = (author.get("institution", "") or "").lower()

            if author_name and any(cn in author_name or author_name in cn for cn in competitor_names):
                matches += 1
            if author_inst and any(ci in author_inst or author_inst in ci for ci in competitor_institutions):
                matches += 1
            total_checks += 1

        if total_checks == 0:
            return 0.0

        # Even a single competitor match is significant
        if matches >= 3:
            return 1.0
        if matches >= 1:
            return 0.5 + (matches * 0.15)
        return 0.0

    def _compute_opportunity_score(
        self,
        signal: dict,
        tenant_config: dict,
        embeddings_service: object,
    ) -> float:
        """Compute how actionable a signal is for a tenant.

        Based on overlap between signal entities and tenant's technology watchlist.

        Args:
            signal: Signal dict with 'entities' (list of entity names).
            tenant_config: Tenant config with 'technology_watchlist'.
            embeddings_service: EmbeddingService instance.

        Returns:
            Float between 0 and 1 indicating opportunity level.
        """
        watchlist = tenant_config.get("technology_watchlist", [])
        if not watchlist:
            return 0.5  # Neutral if no watchlist

        signal_entities = signal.get("entities", [])
        if not signal_entities:
            return 0.0

        # Check direct text overlap
        watchlist_lower = set(w.lower() for w in watchlist)
        entity_names = [e.lower() if isinstance(e, str) else e.get("name", "").lower() for e in signal_entities]

        direct_matches = 0
        for entity_name in entity_names:
            for watch_term in watchlist_lower:
                if watch_term in entity_name or entity_name in watch_term:
                    direct_matches += 1
                    break

        if direct_matches > 0:
            direct_score = min(direct_matches / len(watchlist), 1.0)
        else:
            direct_score = 0.0

        # Embedding-based similarity for non-direct matches
        try:
            entity_text = " ".join(entity_names)
            watchlist_text = " ".join(watchlist)

            entity_emb = np.array(embeddings_service.embed_text(entity_text))
            watchlist_emb = np.array(embeddings_service.embed_text(watchlist_text))

            e_norm = np.linalg.norm(entity_emb)
            w_norm = np.linalg.norm(watchlist_emb)

            if e_norm > 0 and w_norm > 0:
                sim = float(np.dot(entity_emb, watchlist_emb) / (e_norm * w_norm))
                embedding_score = max(0.0, min(1.0, (sim + 1.0) / 2.0))
            else:
                embedding_score = 0.0
        except Exception as exc:
            logger.warning("Opportunity embedding computation failed: %s", exc)
            embedding_score = 0.0

        # Combine direct matches (stronger signal) with embedding similarity
        return 0.6 * direct_score + 0.4 * embedding_score

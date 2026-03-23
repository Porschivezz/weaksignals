"""Momentum analysis for tracking concept acceleration over time."""

import logging
from dataclasses import dataclass, field

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class MomentumResult:
    """Result of momentum analysis for a concept."""

    concept_name: str
    publication_velocity: float
    author_diversity: float
    geographic_spread: float
    citation_momentum: float
    betweenness_velocity: float
    pagerank_velocity: float
    composite_score: float

    @property
    def sub_scores(self) -> dict[str, float]:
        return {
            "publication_velocity": self.publication_velocity,
            "author_diversity": self.author_diversity,
            "geographic_spread": self.geographic_spread,
            "citation_momentum": self.citation_momentum,
            "betweenness_velocity": self.betweenness_velocity,
            "pagerank_velocity": self.pagerank_velocity,
        }


# Default weights for composite momentum score
DEFAULT_WEIGHTS: dict[str, float] = {
    "publication_velocity": 0.25,
    "author_diversity": 0.15,
    "geographic_spread": 0.10,
    "citation_momentum": 0.20,
    "betweenness_velocity": 0.15,
    "pagerank_velocity": 0.15,
}


class MomentumAnalyzer:
    """Analyzer for computing concept momentum across multiple dimensions.

    Tracks the rate of change in publications, authorship diversity,
    geographic spread, citations, and graph centrality to identify
    concepts gaining traction.
    """

    def __init__(self, weights: dict[str, float] | None = None) -> None:
        self.weights = weights or DEFAULT_WEIGHTS.copy()

    def compute_momentum(
        self, concept_name: str, time_windows: list[dict]
    ) -> MomentumResult:
        """Compute multi-dimensional momentum for a concept.

        Args:
            concept_name: The name of the concept to analyze.
            time_windows: List of dicts, each representing a time window
                with keys:
                    - period: str (e.g., "2024-Q1")
                    - paper_count: int
                    - authors: list[str]
                    - institutions: list[str]
                    - countries: list[str]
                    - citation_count: int
                    - betweenness: float
                    - pagerank: float

        Returns:
            MomentumResult with all sub-scores and composite.
        """
        if not time_windows:
            return MomentumResult(
                concept_name=concept_name,
                publication_velocity=0.0,
                author_diversity=0.0,
                geographic_spread=0.0,
                citation_momentum=0.0,
                betweenness_velocity=0.0,
                pagerank_velocity=0.0,
                composite_score=0.0,
            )

        pub_velocity = self._compute_publication_velocity(time_windows)
        auth_diversity = self._compute_author_diversity(time_windows)
        geo_spread = self._compute_geographic_spread(time_windows)
        cite_momentum = self._compute_citation_momentum(time_windows)
        btw_velocity = self._compute_betweenness_velocity(time_windows)
        pr_velocity = self._compute_pagerank_velocity(time_windows)

        composite = (
            self.weights["publication_velocity"] * pub_velocity
            + self.weights["author_diversity"] * auth_diversity
            + self.weights["geographic_spread"] * geo_spread
            + self.weights["citation_momentum"] * cite_momentum
            + self.weights["betweenness_velocity"] * btw_velocity
            + self.weights["pagerank_velocity"] * pr_velocity
        )

        result = MomentumResult(
            concept_name=concept_name,
            publication_velocity=round(pub_velocity, 4),
            author_diversity=round(auth_diversity, 4),
            geographic_spread=round(geo_spread, 4),
            citation_momentum=round(cite_momentum, 4),
            betweenness_velocity=round(btw_velocity, 4),
            pagerank_velocity=round(pr_velocity, 4),
            composite_score=round(max(0.0, min(1.0, composite)), 4),
        )

        logger.debug(
            "Momentum for '%s': composite=%.4f, sub_scores=%s",
            concept_name, result.composite_score, result.sub_scores,
        )
        return result

    def _compute_publication_velocity(self, windows: list[dict]) -> float:
        """Compute d(papers)/dt over a sliding window.

        Measures the rate of increase in publication count across time windows.
        A positive slope indicates growing publication activity.
        """
        counts = np.array([w.get("paper_count", 0) for w in windows], dtype=float)

        if len(counts) < 2:
            return min(counts[0] / 10.0, 1.0) if len(counts) == 1 else 0.0

        # Compute slope via linear regression
        x = np.arange(len(counts), dtype=float)
        slope = self._linear_slope(x, counts)

        # Normalize: positive slope = growing, scale to [0, 1]
        max_count = max(counts.max(), 1.0)
        normalized = slope / max_count

        return max(0.0, min(1.0, float(normalized + 0.5)))

    def _compute_author_diversity(self, windows: list[dict]) -> float:
        """Compute unique author and institution count growth.

        Higher diversity suggests broader adoption and interest.
        """
        all_authors: set[str] = set()
        all_institutions: set[str] = set()
        window_diversity: list[float] = []

        for window in windows:
            authors = set(window.get("authors", []))
            institutions = set(window.get("institutions", []))
            all_authors.update(authors)
            all_institutions.update(institutions)

            window_count = len(authors) + len(institutions)
            window_diversity.append(float(window_count))

        if not all_authors:
            return 0.0

        total_diversity = len(all_authors) + len(all_institutions)

        if len(window_diversity) >= 2:
            x = np.arange(len(window_diversity), dtype=float)
            slope = self._linear_slope(x, np.array(window_diversity))
            max_div = max(max(window_diversity), 1.0)
            growth = slope / max_div
        else:
            growth = 0.0

        # Combine absolute diversity with growth
        abs_score = min(total_diversity / 50.0, 1.0)
        growth_score = max(0.0, min(1.0, growth + 0.5))

        return 0.6 * growth_score + 0.4 * abs_score

    def _compute_geographic_spread(self, windows: list[dict]) -> float:
        """Compute number of distinct countries contributing.

        Broader geographic spread indicates wider global interest.
        """
        all_countries: set[str] = set()
        for window in windows:
            countries = window.get("countries", [])
            all_countries.update(c for c in countries if c)

        num_countries = len(all_countries)

        if num_countries == 0:
            return 0.0

        # Normalize: 10+ countries = score of 1.0
        return min(num_countries / 10.0, 1.0)

    def _compute_citation_momentum(self, windows: list[dict]) -> float:
        """Compute citation growth rate over time windows.

        Accelerating citations indicate growing impact.
        """
        citations = np.array(
            [w.get("citation_count", 0) for w in windows], dtype=float
        )

        if len(citations) < 2:
            return min(citations[0] / 100.0, 1.0) if len(citations) == 1 else 0.0

        x = np.arange(len(citations), dtype=float)
        slope = self._linear_slope(x, citations)

        max_cite = max(citations.max(), 1.0)
        normalized = slope / max_cite

        return max(0.0, min(1.0, float(normalized + 0.5)))

    def _compute_betweenness_velocity(self, windows: list[dict]) -> float:
        """Compute d(betweenness)/dt over time windows.

        Growing betweenness centrality indicates the concept is becoming
        a more important bridge between other concepts.
        """
        values = np.array(
            [w.get("betweenness", 0.0) for w in windows], dtype=float
        )
        return self._velocity_score(values)

    def _compute_pagerank_velocity(self, windows: list[dict]) -> float:
        """Compute d(pagerank)/dt over time windows.

        Growing PageRank indicates the concept is becoming more prominent
        in the overall knowledge graph.
        """
        values = np.array(
            [w.get("pagerank", 0.0) for w in windows], dtype=float
        )
        return self._velocity_score(values)

    def _velocity_score(self, values: np.ndarray) -> float:
        """Compute a normalized velocity score from a time series.

        Args:
            values: Array of metric values over time.

        Returns:
            Float between 0 and 1, centered at 0.5 for no change.
        """
        if len(values) < 2:
            return 0.5

        x = np.arange(len(values), dtype=float)
        slope = self._linear_slope(x, values)

        max_val = max(np.abs(values).max(), 1e-10)
        normalized = slope / max_val

        return max(0.0, min(1.0, float(normalized + 0.5)))

    @staticmethod
    def _linear_slope(x: np.ndarray, y: np.ndarray) -> float:
        """Compute the slope of a simple linear regression.

        Args:
            x: Independent variable values.
            y: Dependent variable values.

        Returns:
            The slope of the best-fit line.
        """
        n = len(x)
        if n < 2:
            return 0.0

        x_mean = x.mean()
        y_mean = y.mean()

        numerator = np.sum((x - x_mean) * (y - y_mean))
        denominator = np.sum((x - x_mean) ** 2)

        if denominator == 0:
            return 0.0

        return float(numerator / denominator)

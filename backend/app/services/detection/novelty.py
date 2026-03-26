"""Novelty detection for identifying genuinely new concepts in the corpus."""

import logging
from dataclasses import dataclass, field

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class NoveltyResult:
    """Result of novelty analysis for a single entity."""

    score: float
    components: dict[str, float]
    is_novel: bool

    @property
    def corpus_novelty(self) -> float:
        return self.components.get("corpus_novelty", 0.0)

    @property
    def terminological_novelty(self) -> float:
        return self.components.get("terminological_novelty", 0.0)

    @property
    def cross_domain_flag(self) -> bool:
        return self.components.get("cross_domain", 0.0) > 0.5


# Default known taxonomy of established concepts for terminological novelty check
KNOWN_TAXONOMY: set[str] = {
    "machine learning", "deep learning", "neural network", "artificial intelligence",
    "natural language processing", "computer vision", "reinforcement learning",
    "supervised learning", "unsupervised learning", "semi-supervised learning",
    "convolutional neural network", "recurrent neural network", "transformer",
    "attention mechanism", "generative adversarial network", "autoencoder",
    "support vector machine", "random forest", "gradient boosting", "decision tree",
    "k-means", "clustering", "dimensionality reduction", "feature engineering",
    "transfer learning", "fine-tuning", "data augmentation", "regularization",
    "batch normalization", "dropout", "backpropagation", "gradient descent",
    "stochastic gradient descent", "adam optimizer", "learning rate",
    "bert", "gpt", "lstm", "gru", "resnet", "vgg", "inception",
    "object detection", "image classification", "semantic segmentation",
    "named entity recognition", "sentiment analysis", "machine translation",
    "speech recognition", "text generation", "question answering",
    "knowledge graph", "graph neural network", "federated learning",
    "meta-learning", "few-shot learning", "zero-shot learning",
    "contrastive learning", "self-supervised learning", "diffusion model",
    "large language model", "retrieval-augmented generation",
    "prompt engineering", "chain-of-thought", "instruction tuning",
}

# Domain tags for cross-domain detection
DOMAIN_MAP: dict[str, set[str]] = {
    "cs": {"algorithm", "framework", "neural network", "transformer", "gpt", "bert", "cnn"},
    "biology": {"protein", "gene", "cell", "drug", "molecular", "genomic", "dna", "rna"},
    "physics": {"quantum", "particle", "photon", "superconductor", "entanglement"},
    "materials": {"material", "alloy", "polymer", "ceramic", "nanostructure", "graphene"},
    "chemistry": {"synthesis", "catalyst", "molecule", "compound", "reaction"},
    "medicine": {"clinical", "patient", "diagnosis", "treatment", "therapeutic", "pathology"},
    "energy": {"solar", "battery", "fuel cell", "wind", "photovoltaic", "hydrogen"},
    "finance": {"trading", "portfolio", "risk", "market", "pricing", "fintech"},
}


class NoveltyDetector:
    """Detector for identifying novel concepts emerging in the research corpus.

    Combines multiple signals: vector-space distance, terminological novelty,
    and cross-domain appearance to produce a composite novelty score.
    """

    def __init__(self, novelty_threshold: float = 0.6) -> None:
        self.novelty_threshold = novelty_threshold
        self.known_taxonomy = KNOWN_TAXONOMY.copy()

    def compute_novelty(
        self,
        entity: dict,
        all_entities: list[dict],
        embeddings_service: object,
    ) -> NoveltyResult:
        """Compute a multi-dimensional novelty score for an entity.

        Args:
            entity: Dict with at least 'name' and 'type' keys.
            all_entities: List of dicts of existing entities to compare against.
            embeddings_service: An EmbeddingService instance with embed_text method.

        Returns:
            NoveltyResult with composite score, sub-scores, and novelty flag.
        """
        entity_name = entity.get("name", "").lower().strip()
        entity_type = entity.get("type", "technology")

        if not entity_name:
            return NoveltyResult(score=0.0, components={}, is_novel=False)

        # 1. Corpus novelty via embedding distance
        corpus_novelty = self._compute_corpus_novelty(
            entity_name, all_entities, embeddings_service
        )

        # 2. Terminological novelty: is it in our known taxonomy?
        terminological_novelty = self._compute_terminological_novelty(entity_name)

        # 3. Cross-domain flag
        cross_domain = self._compute_cross_domain(entity_name, entity_type, all_entities)

        # Weighted composite
        composite = (
            0.45 * corpus_novelty
            + 0.35 * terminological_novelty
            + 0.20 * cross_domain
        )

        components = {
            "corpus_novelty": round(corpus_novelty, 4),
            "terminological_novelty": round(terminological_novelty, 4),
            "cross_domain": round(cross_domain, 4),
        }

        is_novel = composite >= self.novelty_threshold

        result = NoveltyResult(
            score=round(composite, 4),
            components=components,
            is_novel=is_novel,
        )

        logger.debug(
            "Novelty for '%s': score=%.4f, novel=%s, components=%s",
            entity_name, result.score, result.is_novel, components,
        )
        return result

    def _compute_corpus_novelty(
        self,
        entity_name: str,
        all_entities: list[dict],
        embeddings_service: object,
    ) -> float:
        """Compute cosine distance to the nearest existing concept in vector space.

        Args:
            entity_name: The candidate entity name.
            all_entities: List of existing entity dicts.
            embeddings_service: Service with embed_text method.

        Returns:
            Float between 0 (identical to existing) and 1 (maximally distant).
        """
        if not all_entities:
            return 1.0

        try:
            entity_embedding = np.array(embeddings_service.embed_text(entity_name))
        except Exception as exc:
            logger.warning("Could not embed entity '%s': %s", entity_name, exc)
            return 0.5

        existing_names = [e.get("name", "") for e in all_entities if e.get("name")]
        if not existing_names:
            return 1.0

        try:
            existing_embeddings = embeddings_service.embed_batch(existing_names)
        except Exception as exc:
            logger.warning("Could not embed existing entities: %s", exc)
            return 0.5

        min_distance = float("inf")
        entity_norm = np.linalg.norm(entity_embedding)
        if entity_norm == 0:
            return 0.5

        for emb in existing_embeddings:
            existing_vec = np.array(emb)
            existing_norm = np.linalg.norm(existing_vec)
            if existing_norm == 0:
                continue
            cosine_sim = np.dot(entity_embedding, existing_vec) / (entity_norm * existing_norm)
            distance = 1.0 - float(cosine_sim)
            if distance < min_distance:
                min_distance = distance

        if min_distance == float("inf"):
            return 1.0

        return max(0.0, min(1.0, min_distance))

    def _compute_terminological_novelty(self, entity_name: str) -> float:
        """Check if the entity name exists in the known taxonomy.

        Args:
            entity_name: The candidate entity name (lowercased).

        Returns:
            1.0 if completely new term, 0.0 if exact match, intermediate for partial matches.
        """
        if entity_name in self.known_taxonomy:
            return 0.0

        # Check for partial matches
        for known in self.known_taxonomy:
            if entity_name in known or known in entity_name:
                return 0.3

        return 1.0

    def _compute_cross_domain(
        self,
        entity_name: str,
        entity_type: str,
        all_entities: list[dict],
    ) -> float:
        """Detect if this concept appears from a different domain than expected.

        Args:
            entity_name: The candidate entity name.
            entity_type: The entity type classification.
            all_entities: List of existing entities with domain context.

        Returns:
            Float between 0 (same domain) and 1 (cross-domain appearance).
        """
        entity_domains: set[str] = set()
        for domain, keywords in DOMAIN_MAP.items():
            for keyword in keywords:
                if keyword in entity_name:
                    entity_domains.add(domain)

        if not entity_domains:
            return 0.0

        # Check if other entities in the same batch are from different domains
        batch_domains: set[str] = set()
        for existing in all_entities:
            existing_name = existing.get("name", "").lower()
            for domain, keywords in DOMAIN_MAP.items():
                for keyword in keywords:
                    if keyword in existing_name:
                        batch_domains.add(domain)

        if not batch_domains:
            return 0.0

        # Cross-domain score is the proportion of entity domains not in the batch
        overlap = entity_domains & batch_domains
        non_overlap = entity_domains - batch_domains

        if not entity_domains:
            return 0.0

        cross_domain_score = len(non_overlap) / len(entity_domains)
        return cross_domain_score

    def detect_new_concepts(
        self,
        documents: list[dict],
        existing_entities: list[dict],
        embeddings_service: object,
    ) -> list[dict]:
        """Detect novel concepts from a batch of documents.

        Args:
            documents: List of document dicts, each with 'entities' key
                       containing a list of extracted entity dicts.
            existing_entities: List of previously known entity dicts.
            embeddings_service: An EmbeddingService instance.

        Returns:
            List of dicts for novel concepts, each containing the entity
            info plus a 'novelty_result' key.
        """
        novel_concepts: list[dict] = []
        seen_names: set[str] = set()

        for doc in documents:
            entities = doc.get("entities", [])
            for entity in entities:
                name = entity.get("name", "").lower().strip()
                if not name or name in seen_names:
                    continue
                seen_names.add(name)

                novelty_result = self.compute_novelty(
                    entity, existing_entities, embeddings_service
                )

                if novelty_result.is_novel:
                    novel_concepts.append({
                        "name": entity.get("name", ""),
                        "type": entity.get("type", "technology"),
                        "confidence": entity.get("confidence", 0.0),
                        "novelty_score": novelty_result.score,
                        "novelty_components": novelty_result.components,
                        "source_document": doc.get("title", ""),
                    })

        logger.info(
            "Detected %d novel concepts from %d documents",
            len(novel_concepts), len(documents),
        )
        return novel_concepts

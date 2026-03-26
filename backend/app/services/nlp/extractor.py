"""Level 1 entity extraction using TF-IDF and regex patterns."""

import logging
import re
from difflib import SequenceMatcher

from sklearn.feature_extraction.text import TfidfVectorizer

logger = logging.getLogger(__name__)

# Regex patterns for common technology/method terms
TECH_PATTERNS: list[tuple[str, str]] = [
    # Neural network architectures
    (r"\b(transformer|attention mechanism|self-attention|multi-head attention)\b", "algorithm"),
    (r"\b(convolutional neural network|CNN|ResNet|VGG|Inception|EfficientNet)\b", "algorithm"),
    (r"\b(recurrent neural network|RNN|LSTM|GRU|bidirectional LSTM)\b", "algorithm"),
    (r"\b(generative adversarial network|GAN|DCGAN|StyleGAN|CycleGAN|WGAN)\b", "algorithm"),
    (r"\b(variational autoencoder|VAE|autoencoder|denoising autoencoder)\b", "algorithm"),
    (r"\b(diffusion model|denoising diffusion|DDPM|score-based model)\b", "algorithm"),
    (r"\b(graph neural network|GNN|GCN|GAT|GraphSAGE|message passing)\b", "algorithm"),
    (r"\b(vision transformer|ViT|DeiT|Swin Transformer|BEiT)\b", "algorithm"),
    # Large language models
    (r"\b(large language model|LLM|GPT-\d|BERT|RoBERTa|T5|LLaMA|Mistral|Claude|Gemini)\b", "technology"),
    (r"\b(retrieval-augmented generation|RAG|chain-of-thought|prompt engineering)\b", "method"),
    (r"\b(fine-tuning|LoRA|QLoRA|PEFT|adapter tuning|instruction tuning)\b", "method"),
    (r"\b(RLHF|reinforcement learning from human feedback|DPO|PPO)\b", "method"),
    # ML methods
    (r"\b(reinforcement learning|Q-learning|policy gradient|actor-critic|DDPG|SAC|TD3)\b", "algorithm"),
    (r"\b(federated learning|differential privacy|secure aggregation)\b", "method"),
    (r"\b(meta-learning|few-shot learning|zero-shot|one-shot|in-context learning)\b", "method"),
    (r"\b(contrastive learning|SimCLR|MoCo|CLIP|self-supervised learning)\b", "method"),
    (r"\b(knowledge distillation|model compression|pruning|quantization)\b", "method"),
    (r"\b(transfer learning|domain adaptation|multi-task learning)\b", "method"),
    (r"\b(active learning|curriculum learning|data augmentation)\b", "method"),
    (r"\b(neural architecture search|NAS|AutoML)\b", "method"),
    # Frameworks and tools
    (r"\b(PyTorch|TensorFlow|JAX|Flax|Keras|Hugging Face|transformers library)\b", "framework"),
    (r"\b(LangChain|LlamaIndex|Haystack|vLLM|TensorRT)\b", "framework"),
    (r"\b(CUDA|ROCm|OpenCL|Triton|ONNX)\b", "framework"),
    # Hardware
    (r"\b(TPU|GPU cluster|A100|H100|neuromorphic chip|quantum processor)\b", "technology"),
    (r"\b(edge computing|on-device inference|TinyML|FPGA)\b", "technology"),
    # Materials and domains
    (r"\b(protein folding|drug discovery|molecular dynamics|AlphaFold)\b", "technology"),
    (r"\b(autonomous driving|robotics|computer vision|NLP|speech recognition)\b", "technology"),
    (r"\b(blockchain|smart contract|decentralized|Web3)\b", "technology"),
    (r"\b(quantum computing|quantum machine learning|quantum annealing|qubit)\b", "technology"),
]

# Pre-compile patterns for performance
COMPILED_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(pattern, re.IGNORECASE), entity_type)
    for pattern, entity_type in TECH_PATTERNS
]


class EntityExtractor:
    """Level 1 entity extractor using TF-IDF and regex patterns.

    Provides fast, local extraction of technology entities from text
    without requiring any external API calls.
    """

    def __init__(self, max_features: int = 500, ngram_range: tuple[int, int] = (1, 3)) -> None:
        self.vectorizer = TfidfVectorizer(
            max_features=max_features,
            ngram_range=ngram_range,
            stop_words="english",
            token_pattern=r"(?u)\b[A-Za-z][A-Za-z0-9\-]{1,}\b",
        )
        self._is_fitted = False

    def extract_entities(self, text: str) -> list[dict]:
        """Extract technology entities from text using regex patterns and TF-IDF.

        Args:
            text: The text to extract entities from (typically abstract + title).

        Returns:
            List of dicts with keys: name, type, confidence.
        """
        if not text or not text.strip():
            return []

        entities: dict[str, dict] = {}

        # Phase 1: Regex pattern matching (high confidence)
        for compiled_pattern, entity_type in COMPILED_PATTERNS:
            for match in compiled_pattern.finditer(text):
                matched_text = match.group(0).strip()
                normalized_name = matched_text.lower()
                if normalized_name not in entities:
                    entities[normalized_name] = {
                        "name": matched_text,
                        "type": entity_type,
                        "confidence": 0.85,
                    }
                else:
                    current = entities[normalized_name]
                    current["confidence"] = min(current["confidence"] + 0.05, 0.99)

        # Phase 2: TF-IDF keyword extraction (medium confidence)
        tfidf_entities = self._extract_tfidf_terms(text)
        for term, score in tfidf_entities:
            normalized = term.lower()
            if normalized not in entities and len(normalized) > 2:
                entities[normalized] = {
                    "name": term,
                    "type": "technology",
                    "confidence": min(score * 0.7, 0.75),
                }

        result = list(entities.values())
        result.sort(key=lambda e: e["confidence"], reverse=True)
        logger.debug("Extracted %d entities from text (%d chars)", len(result), len(text))
        return result

    def _extract_tfidf_terms(self, text: str) -> list[tuple[str, float]]:
        """Extract key terms using TF-IDF scoring on a single document."""
        try:
            tfidf_matrix = self.vectorizer.fit_transform([text])
            feature_names = self.vectorizer.get_feature_names_out()
            scores = tfidf_matrix.toarray()[0]

            term_scores: list[tuple[str, float]] = []
            for idx, score in enumerate(scores):
                if score > 0.1:
                    term_scores.append((feature_names[idx], float(score)))

            term_scores.sort(key=lambda x: x[1], reverse=True)
            return term_scores[:20]
        except ValueError:
            logger.debug("TF-IDF extraction failed, likely empty vocabulary after filtering")
            return []

    def compute_novelty_score(
        self, entity_name: str, existing_entities: list[str]
    ) -> float:
        """Compute a novelty score for an entity against known entities.

        Uses fuzzy string matching to determine how novel a term is
        relative to a corpus of existing entity names.

        Args:
            entity_name: The candidate entity name to score.
            existing_entities: List of known entity names to compare against.

        Returns:
            Float between 0.0 (not novel, exact match) and 1.0 (completely novel).
        """
        if not existing_entities:
            return 1.0

        entity_lower = entity_name.lower().strip()
        if not entity_lower:
            return 0.0

        max_similarity = 0.0
        for existing in existing_entities:
            existing_lower = existing.lower().strip()

            # Exact match
            if entity_lower == existing_lower:
                return 0.0

            # Substring containment
            if entity_lower in existing_lower or existing_lower in entity_lower:
                similarity = 0.85
            else:
                # Fuzzy matching via SequenceMatcher
                similarity = SequenceMatcher(None, entity_lower, existing_lower).ratio()

            if similarity > max_similarity:
                max_similarity = similarity

        novelty = 1.0 - max_similarity
        return round(novelty, 4)

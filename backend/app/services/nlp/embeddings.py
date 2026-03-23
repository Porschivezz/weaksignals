"""Embedding service with Cohere API and deterministic fallback."""

import hashlib
import logging
from functools import lru_cache

import numpy as np
from sklearn.feature_extraction.text import HashingVectorizer

logger = logging.getLogger(__name__)

EMBEDDING_DIM = 1024


class EmbeddingService:
    """Text embedding service using Cohere API with local fallback.

    If COHERE_API_KEY is provided, uses Cohere's embed endpoint for
    production-quality embeddings. Otherwise, generates deterministic
    pseudo-embeddings using sklearn HashingVectorizer for testing.
    """

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key
        self._cohere_client = None
        self._cache: dict[str, list[float]] = {}
        self._fallback_vectorizer = HashingVectorizer(
            n_features=EMBEDDING_DIM,
            alternate_sign=True,
            norm="l2",
        )

        if api_key:
            try:
                import cohere
                self._cohere_client = cohere.ClientV2(api_key=api_key)
                logger.info("Cohere embedding client initialized")
            except Exception as exc:
                logger.warning(
                    "Failed to initialize Cohere client, falling back to local embeddings: %s",
                    exc,
                )

    def _cache_key(self, text: str) -> str:
        """Generate a cache key for the given text."""
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def embed_text(self, text: str) -> list[float]:
        """Embed a single text string into a 1024-dimensional vector.

        Args:
            text: The text to embed.

        Returns:
            List of 1024 floats representing the embedding vector.
        """
        if not text or not text.strip():
            return [0.0] * EMBEDDING_DIM

        cache_key = self._cache_key(text)
        if cache_key in self._cache:
            return self._cache[cache_key]

        if self._cohere_client is not None:
            embedding = self._embed_cohere([text])[0]
        else:
            embedding = self._embed_local(text)

        self._cache[cache_key] = embedding
        return embedding

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of texts into 1024-dimensional vectors.

        Args:
            texts: List of texts to embed.

        Returns:
            List of embedding vectors, one per input text.
        """
        if not texts:
            return []

        results: list[list[float]] = []
        uncached_indices: list[int] = []
        uncached_texts: list[str] = []

        for i, text in enumerate(texts):
            if not text or not text.strip():
                results.append([0.0] * EMBEDDING_DIM)
                continue

            cache_key = self._cache_key(text)
            if cache_key in self._cache:
                results.append(self._cache[cache_key])
            else:
                results.append([])  # placeholder
                uncached_indices.append(i)
                uncached_texts.append(text)

        if uncached_texts:
            if self._cohere_client is not None:
                embeddings = self._embed_cohere(uncached_texts)
            else:
                embeddings = [self._embed_local(t) for t in uncached_texts]

            for idx, embedding in zip(uncached_indices, embeddings):
                results[idx] = embedding
                cache_key = self._cache_key(texts[idx])
                self._cache[cache_key] = embedding

        return results

    def _embed_cohere(self, texts: list[str]) -> list[list[float]]:
        """Embed texts using the Cohere API.

        Args:
            texts: List of texts to embed.

        Returns:
            List of embedding vectors.
        """
        try:
            # Process in batches of 96 (Cohere limit)
            all_embeddings: list[list[float]] = []
            batch_size = 96

            for start in range(0, len(texts), batch_size):
                batch = texts[start : start + batch_size]
                response = self._cohere_client.embed(
                    texts=batch,
                    model="embed-english-v3.0",
                    input_type="search_document",
                    embedding_types=["float"],
                )
                batch_embeddings = response.embeddings.float_
                for emb in batch_embeddings:
                    vec = list(emb)
                    # Pad or truncate to EMBEDDING_DIM
                    if len(vec) < EMBEDDING_DIM:
                        vec.extend([0.0] * (EMBEDDING_DIM - len(vec)))
                    elif len(vec) > EMBEDDING_DIM:
                        vec = vec[:EMBEDDING_DIM]
                    all_embeddings.append(vec)

            return all_embeddings
        except Exception as exc:
            logger.error("Cohere embedding error, falling back to local: %s", exc)
            return [self._embed_local(t) for t in texts]

    def _embed_local(self, text: str) -> list[float]:
        """Generate deterministic pseudo-embedding using HashingVectorizer.

        This provides consistent embeddings for the same input text,
        suitable for testing and development without an API key.

        Args:
            text: The text to embed.

        Returns:
            List of 1024 floats (L2-normalized).
        """
        matrix = self._fallback_vectorizer.transform([text])
        vec = matrix.toarray()[0].tolist()
        return vec

    def clear_cache(self) -> None:
        """Clear the embedding cache."""
        self._cache.clear()
        logger.info("Embedding cache cleared")

from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from collections.abc import Sequence

from financial_data_agent.agent.tablerag.constants import BM25_B, BM25_K1, RRF_K
from financial_data_agent.db.DTO.document_chunk import RetrievedChunk

TOKEN_PATTERN = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> list[str]:
    """Split text into lowercase alphanumeric terms.

    Args:
        text: Text to split.

    Returns:
        The terms in order.
    """
    return TOKEN_PATTERN.findall(text.lower())


def bm25_scores(query: str, documents: Sequence[str], k1: float = BM25_K1, b: float = BM25_B) -> list[float]:
    """Score each document against the query with Okapi BM25.

    Args:
        query: The query text.
        documents: The documents to score.
        k1: Term-frequency saturation.
        b: Document-length normalisation.

    Returns:
        One score per document, in the same order.
    """
    tokenized = [tokenize(document) for document in documents]
    if not tokenized:
        return []
    average_length = sum(map(len, tokenized)) / len(tokenized) or 1.0
    document_frequency = Counter(term for terms in tokenized for term in set(terms))
    query_terms = set(tokenize(query))
    scores = []
    for terms in tokenized:
        frequency = Counter(terms)
        length_norm = k1 * (1 - b + b * len(terms) / average_length)
        score = 0.0
        for term in query_terms & frequency.keys():
            df = document_frequency[term]
            idf = math.log(1 + (len(tokenized) - df + 0.5) / (df + 0.5))
            score += idf * frequency[term] * (k1 + 1) / (frequency[term] + length_norm)
        scores.append(score)
    return scores


def reciprocal_rank_fusion(rankings: Sequence[Sequence[int]], k: int = RRF_K) -> list[int]:
    """Fuse several rankings of the same items by reciprocal rank.

    Ties keep the order in which items first appear, so the first ranking breaks them.

    Args:
        rankings: Item indices, best first, one sequence per ranker.
        k: Damping constant; larger values flatten the contribution of top ranks.

    Returns:
        The item indices, best first.
    """
    scores: defaultdict[int, float] = defaultdict(float)
    for ranking in rankings:
        for rank, index in enumerate(ranking):
            scores[index] += 1 / (k + rank + 1)
    return sorted(scores, key=lambda index: -scores[index])


def rerank(query: str, chunks: Sequence[RetrievedChunk], top_k: int) -> list[RetrievedChunk]:
    """Fuse the vector ranking with a BM25 ranking and keep the best chunks.

    Args:
        query: The subquery the chunks were retrieved for.
        chunks: Retrieved chunks, closest by vector first.
        top_k: Number of chunks to keep.

    Returns:
        The best `top_k` chunks, best first.
    """
    scores = bm25_scores(query, [f"{chunk.heading_path or ''} {chunk.content}" for chunk in chunks])
    keyword_ranking = sorted(range(len(chunks)), key=lambda index: -scores[index])
    fused = reciprocal_rank_fusion([range(len(chunks)), keyword_ranking])
    return [chunks[index] for index in fused[:top_k]]

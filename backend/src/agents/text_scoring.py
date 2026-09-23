import math
import re
from collections import Counter

from src.db.models import Topic

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


def bm25_scores(query_tokens: list[str], documents: list[list[str]]) -> list[float]:
    """Score `documents` against `query_tokens` with BM25 — the keyword fallback.

    Implemented in-process (no full-text search engine in the stack), over
    whatever candidate pool the caller passes in, not the whole corpus.
    """
    k1, b = 1.5, 0.75
    doc_count = len(documents)
    if doc_count == 0:
        return []

    avg_len = sum(len(doc) for doc in documents) / doc_count
    doc_freq: Counter[str] = Counter()
    for doc in documents:
        doc_freq.update(set(doc))

    scores = [0.0] * doc_count
    for term in set(query_tokens):
        df = doc_freq.get(term, 0)
        if df == 0:
            continue
        idf = math.log(1 + (doc_count - df + 0.5) / (df + 0.5))
        for i, doc in enumerate(documents):
            tf = doc.count(term)
            if tf == 0:
                continue
            doc_len = len(doc) or 1
            denom = tf + k1 * (1 - b + b * doc_len / avg_len)
            scores[i] += idf * (tf * (k1 + 1)) / denom
    return scores


def normalize(scores: list[float]) -> list[float]:
    if not scores:
        return []
    lo, hi = min(scores), max(scores)
    if hi - lo < 1e-9:
        return [0.0 for _ in scores]
    return [(s - lo) / (hi - lo) for s in scores]


def topic_overlap_score(topic: Topic, doc_tokens: list[str]) -> float:
    topic_tokens = set(tokenize(f"{topic.name} {topic.description or ''}"))
    if not topic_tokens or not doc_tokens:
        return 0.0
    return len(topic_tokens & set(doc_tokens)) / len(topic_tokens)

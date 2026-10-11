import re
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

POLICIES_DIR = Path("policies")
SECTION_PATTERN = re.compile(r"^## (.+)$", re.MULTILINE)


def load_policy_chunks(policies_dir: str = "policies") -> list:
    """Split every policy markdown file into chunks by its '## ' section
    headings. Each chunk keeps its heading as part of the text so the
    retriever can match on section titles too."""
    chunks = []
    for path in sorted(Path(policies_dir).glob("*.md")):
        text = path.read_text(encoding="utf-8")
        matches = list(SECTION_PATTERN.finditer(text))
        for i, match in enumerate(matches):
            start = match.start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            chunks.append({
                "doc": path.name,
                "section": match.group(1).strip(),
                "text": text[start:end].strip(),
            })
    return chunks


class PolicyRetriever:
    """TF-IDF retriever over policy chunks -- no model download, pure
    scikit-learn, fits in milliseconds on a document set this small."""

    def __init__(self, chunks: list):
        self.chunks = chunks
        self.vectorizer = TfidfVectorizer(stop_words="english")
        self.matrix = self.vectorizer.fit_transform(c["text"] for c in chunks)

    def search(self, query: str, top_k: int = 2) -> list:
        query_vec = self.vectorizer.transform([query])
        scores = cosine_similarity(query_vec, self.matrix)[0]
        ranked = scores.argsort()[::-1][:top_k]
        return [{**self.chunks[i], "score": float(scores[i])} for i in ranked if scores[i] > 0]


def retrieve_for_applicant(decision: dict, reason_codes: list, retriever: PolicyRetriever, top_k: int = 2) -> list:
    """Run one search per: risk band, each triggered rule, adverse-action
    requirements, and the applicant's top reason codes -- then merge,
    deduplicating by (doc, section) and keeping the first (highest-priority)
    occurrence. Returns chunks in citation order, numbered from 1."""
    queries = [f"Band {decision['band']} {decision['band_decision']} risk band score cut-off decision"]
    for rule_id, desc, action in decision["rule_details"]:
        queries.append(f"{rule_id} {desc} {action}")
    queries.append("adverse action notice specific principal reasons ECOA Regulation B fair lending rejection")
    if reason_codes:
        reason_text = " ".join(f"{r['variable']} {r['applicant_bin']}" for r in reason_codes)
        queries.append(f"reason codes points deduction {reason_text}")

    seen = set()
    merged = []
    for query in queries:
        for hit in retriever.search(query, top_k=top_k):
            key = (hit["doc"], hit["section"])
            if key not in seen:
                seen.add(key)
                merged.append(hit)

    for i, chunk in enumerate(merged, start=1):
        chunk["citation"] = i
    return merged


if __name__ == "__main__":
    chunks = load_policy_chunks()
    print(f"Loaded {len(chunks)} chunks from {len(set(c['doc'] for c in chunks))} policy documents:")
    for c in chunks:
        print(f"  [{c['doc']}] {c['section']}")

    retriever = PolicyRetriever(chunks)
    print("\n--- Test search: 'utilization above 100%' ---")
    for hit in retriever.search("revolving utilization above 100 percent refer underwriter", top_k=3):
        print(f"  {hit['score']:.3f}  [{hit['doc']}] {hit['section']}")

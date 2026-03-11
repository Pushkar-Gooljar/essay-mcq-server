import json
import os
import random
import re
from collections import defaultdict
from mcp.server.fastmcp import FastMCP

# ── Init ──────────────────────────────────────────────────────────────────────
port = int(os.environ.get("PORT", 8000))
mcp = FastMCP("GP Question Bank", host="0.0.0.0", port=port)

with open("classified_questions.json", "r") as f:
    QUESTION_DB = json.load(f)

# ── Friendly display names ────────────────────────────────────────────────────
CATEGORY_LABELS = {
    "economic_historical_moral_political_and_social": "Economic, Historical, Moral, Political & Social",
    "science_environment_technology_and_mathematics": "Science, Environment, Technology & Mathematics",
    "literature_language_arts_crafts_and_media":      "Literature, Language, Arts, Crafts & Media",
}

def _fmt_category(key: str) -> str:
    return CATEGORY_LABELS.get(key, key.replace("_", " ").title())

def _all_questions() -> list[dict]:
    """Flat list of every question with category + sub_topic attached."""
    out = []
    for cat, subtopics in QUESTION_DB.items():
        for sub, questions in subtopics.items():
            for q in questions:
                out.append({**q, "category": cat, "sub_topic": sub})
    return out


# ════════════════════════════════════════════════════════════════════════════
# 1. BROWSE / NAVIGATION
# ════════════════════════════════════════════════════════════════════════════

@mcp.tool()
def get_overview() -> dict:
    """
    Returns a full overview of the question bank:
    - Total question count
    - Per-category counts with sub-topic breakdown
    Great first call to understand what's available.
    """
    overview = {"total_questions": 0, "categories": {}}
    for cat, subtopics in QUESTION_DB.items():
        cat_total = sum(len(qs) for qs in subtopics.values())
        overview["total_questions"] += cat_total
        overview["categories"][_fmt_category(cat)] = {
            "total": cat_total,
            "sub_topics": {
                sub.replace("_", " ").title(): len(qs)
                for sub, qs in subtopics.items()
            },
        }
    return overview


@mcp.tool()
def get_categories() -> list[dict]:
    """Lists all three main syllabus categories with friendly names and question counts."""
    return [
        {
            "key": cat,
            "label": _fmt_category(cat),
            "sub_topic_count": len(subtopics),
            "question_count": sum(len(qs) for qs in subtopics.values()),
        }
        for cat, subtopics in QUESTION_DB.items()
    ]


@mcp.tool()
def get_sub_topics(category: str) -> list[dict]:
    """
    Returns all sub-topics for a category with question counts.
    Pass the category key (e.g. 'economic_historical_moral_political_and_social')
    or a partial/friendly name — the tool will fuzzy-match.
    """
    # fuzzy match
    matched = None
    for key in QUESTION_DB:
        if category.lower() in key.lower() or key.lower() in category.lower():
            matched = key
            break
        if category.lower() in _fmt_category(key).lower():
            matched = key
            break
    if not matched:
        return [{"error": f"Category '{category}' not found. Use get_categories() to see valid keys."}]
    return [
        {
            "key": sub,
            "label": sub.replace("_", " ").title(),
            "question_count": len(qs),
        }
        for sub, qs in QUESTION_DB[matched].items()
    ]


@mcp.tool()
def get_questions_by_topic(category: str, sub_topic: str) -> list[dict]:
    """
    Returns all questions for a specific category + sub-topic pair.
    Both arguments support fuzzy/partial matching.
    Each question includes: paper code, question number, and full text.
    """
    # match category
    matched_cat = None
    for key in QUESTION_DB:
        if category.lower() in key.lower() or key.lower() in category.lower():
            matched_cat = key
            break
    if not matched_cat:
        return [{"error": f"Category '{category}' not found."}]

    # match sub-topic
    matched_sub = None
    for sub in QUESTION_DB[matched_cat]:
        if sub_topic.lower() in sub.lower() or sub.lower() in sub_topic.lower():
            matched_sub = sub
            break
    if not matched_sub:
        return [{"error": f"Sub-topic '{sub_topic}' not found in '{matched_cat}'."}]

    return [
        {
            "paper": q["paper"],
            "question": q["question"],
            "text": q["text"],
            "category": _fmt_category(matched_cat),
            "sub_topic": matched_sub.replace("_", " ").title(),
        }
        for q in QUESTION_DB[matched_cat][matched_sub]
    ]


# ════════════════════════════════════════════════════════════════════════════
# 2. SEARCH
# ════════════════════════════════════════════════════════════════════════════

@mcp.tool()
def search_questions(keyword: str, max_results: int = 20) -> dict:
    """
    Full-text search across all questions.
    Returns matched questions with their category, sub-topic, paper, and text.
    Args:
        keyword:     Word or phrase to search for (case-insensitive).
        max_results: Cap on results returned (default 20, max 100).
    """
    max_results = min(max_results, 100)
    pattern = re.compile(re.escape(keyword), re.IGNORECASE)
    results = []
    for q in _all_questions():
        if pattern.search(q["text"]):
            results.append({
                "paper": q["paper"],
                "question": q["question"],
                "text": q["text"],
                "category": _fmt_category(q["category"]),
                "sub_topic": q["sub_topic"].replace("_", " ").title(),
            })
    return {
        "keyword": keyword,
        "total_matches": len(results),
        "shown": min(len(results), max_results),
        "results": results[:max_results],
    }


@mcp.tool()
def search_by_paper(paper_code: str) -> list[dict]:
    """
    Retrieves all questions from a specific past paper.
    Example paper codes: '8021_w22_qp_11', '8019_s23_qp_12'
    Supports partial matching (e.g. 'w22' returns all winter 2022 papers).
    """
    results = []
    for q in _all_questions():
        if paper_code.lower() in q["paper"].lower():
            results.append({
                "paper": q["paper"],
                "question": q["question"],
                "text": q["text"],
                "category": _fmt_category(q["category"]),
                "sub_topic": q["sub_topic"].replace("_", " ").title(),
            })
    return results


@mcp.tool()
def search_multi_keyword(keywords: list[str], match_all: bool = False, max_results: int = 20) -> dict:
    """
    Search questions matching multiple keywords.
    Args:
        keywords:    List of words/phrases to search for.
        match_all:   If True, question must contain ALL keywords (AND logic).
                     If False, any keyword matches (OR logic). Default: False.
        max_results: Cap on results (default 20).
    """
    max_results = min(max_results, 100)
    patterns = [re.compile(re.escape(kw), re.IGNORECASE) for kw in keywords]
    results = []
    for q in _all_questions():
        hits = [bool(p.search(q["text"])) for p in patterns]
        matched = all(hits) if match_all else any(hits)
        if matched:
            results.append({
                "paper": q["paper"],
                "question": q["question"],
                "text": q["text"],
                "category": _fmt_category(q["category"]),
                "sub_topic": q["sub_topic"].replace("_", " ").title(),
                "matched_keywords": [kw for kw, h in zip(keywords, hits) if h],
            })
    return {
        "keywords": keywords,
        "logic": "AND" if match_all else "OR",
        "total_matches": len(results),
        "shown": min(len(results), max_results),
        "results": results[:max_results],
    }


# ════════════════════════════════════════════════════════════════════════════
# 3. RANDOM / PRACTICE
# ════════════════════════════════════════════════════════════════════════════

@mcp.tool()
def get_random_question(category: str = "", sub_topic: str = "") -> dict:
    """
    Returns a single random question, optionally filtered by category and/or sub-topic.
    Leave blank for a completely random question from the whole bank.
    Perfect for surprise practice or warm-up questions.
    """
    pool = _all_questions()
    if category:
        pool = [q for q in pool if category.lower() in q["category"].lower()
                or category.lower() in _fmt_category(q["category"]).lower()]
    if sub_topic:
        pool = [q for q in pool if sub_topic.lower() in q["sub_topic"].lower()]
    if not pool:
        return {"error": "No questions matched the given filters."}
    q = random.choice(pool)
    return {
        "paper": q["paper"],
        "question": q["question"],
        "text": q["text"],
        "category": _fmt_category(q["category"]),
        "sub_topic": q["sub_topic"].replace("_", " ").title(),
    }


@mcp.tool()
def get_practice_set(
    n: int = 5,
    category: str = "",
    sub_topic: str = "",
    avoid_papers: list[str] = [],
) -> dict:
    """
    Generates a unique practice set of n random questions (no duplicates).
    Args:
        n:             Number of questions (1–20). Default 5.
        category:      Optional category filter.
        sub_topic:     Optional sub-topic filter.
        avoid_papers:  List of paper codes to exclude (e.g. papers you've done).
    """
    n = min(max(n, 1), 20)
    pool = _all_questions()
    if category:
        pool = [q for q in pool if category.lower() in q["category"].lower()
                or category.lower() in _fmt_category(q["category"]).lower()]
    if sub_topic:
        pool = [q for q in pool if sub_topic.lower() in q["sub_topic"].lower()]
    if avoid_papers:
        avoid_set = {p.lower() for p in avoid_papers}
        pool = [q for q in pool if q["paper"].lower() not in avoid_set]
    if len(pool) < n:
        return {"error": f"Only {len(pool)} questions available with those filters (requested {n})."}
    chosen = random.sample(pool, n)
    return {
        "count": n,
        "questions": [
            {
                "index": i + 1,
                "paper": q["paper"],
                "question": q["question"],
                "text": q["text"],
                "category": _fmt_category(q["category"]),
                "sub_topic": q["sub_topic"].replace("_", " ").title(),
            }
            for i, q in enumerate(chosen)
        ],
    }


@mcp.tool()
def get_balanced_practice_set(n_per_category: int = 2) -> dict:
    """
    Generates a balanced practice set with equal questions from each of the 3 categories.
    Great for full-syllabus revision sessions.
    Args:
        n_per_category: Questions per category (1–5). Total = n × 3. Default 2.
    """
    n_per_category = min(max(n_per_category, 1), 5)
    result = {"total": n_per_category * 3, "questions": []}
    idx = 1
    for cat, subtopics in QUESTION_DB.items():
        pool = []
        for sub, qs in subtopics.items():
            for q in qs:
                pool.append({**q, "category": cat, "sub_topic": sub})
        chosen = random.sample(pool, min(n_per_category, len(pool)))
        for q in chosen:
            result["questions"].append({
                "index": idx,
                "paper": q["paper"],
                "question": q["question"],
                "text": q["text"],
                "category": _fmt_category(q["category"]),
                "sub_topic": q["sub_topic"].replace("_", " ").title(),
            })
            idx += 1
    return result


# ════════════════════════════════════════════════════════════════════════════
# 4. ANALYTICS / INSIGHTS
# ════════════════════════════════════════════════════════════════════════════

@mcp.tool()
def get_topic_stats() -> dict:
    """
    Returns rich statistics about the question bank:
    - Top 5 most-questioned sub-topics overall
    - Least-covered sub-topics (revision gaps)
    - Question counts per category
    Useful for identifying high-priority revision areas.
    """
    topic_counts = []
    for cat, subtopics in QUESTION_DB.items():
        for sub, qs in subtopics.items():
            topic_counts.append({
                "category": _fmt_category(cat),
                "sub_topic": sub.replace("_", " ").title(),
                "count": len(qs),
            })
    topic_counts.sort(key=lambda x: x["count"], reverse=True)
    return {
        "top_5_most_common": topic_counts[:5],
        "bottom_5_least_common": topic_counts[-5:],
        "all_topics_ranked": topic_counts,
    }


@mcp.tool()
def get_paper_index() -> dict:
    """
    Lists every unique past paper in the database with a question count.
    Useful for seeing which years/sessions are represented.
    """
    paper_map: dict[str, int] = defaultdict(int)
    for q in _all_questions():
        paper_map[q["paper"]] += 1
    sorted_papers = sorted(paper_map.items(), key=lambda x: x[0])
    return {
        "total_papers": len(sorted_papers),
        "papers": [{"paper": p, "question_count": c} for p, c in sorted_papers],
    }


@mcp.tool()
def get_questions_by_year(year: str) -> dict:
    """
    Returns all questions from a specific year.
    Args:
        year: 2-digit or 4-digit year, e.g. '22' or '2022'.
    """
    # normalise to 2-digit suffix used in paper codes
    yr = year[-2:] if len(year) >= 2 else year
    results = []
    for q in _all_questions():
        # paper codes contain 'w22', 's22', 'm22' style
        if f"_{yr}_" in q["paper"] or q["paper"].endswith(f"_{yr}"):
            results.append({
                "paper": q["paper"],
                "question": q["question"],
                "text": q["text"],
                "category": _fmt_category(q["category"]),
                "sub_topic": q["sub_topic"].replace("_", " ").title(),
            })
    return {
        "year": year,
        "total": len(results),
        "questions": results,
    }


@mcp.tool()
def get_keyword_frequency(top_n: int = 20) -> list[dict]:
    """
    Analyses question text to find the most frequently appearing meaningful words.
    Ignores common stop-words.
    Args:
        top_n: How many top keywords to return (default 20).
    """
    STOP = {
        "the","a","an","and","or","but","in","on","to","of","for","with",
        "that","this","is","are","was","were","be","been","being","have",
        "has","had","do","does","did","will","would","could","should","may",
        "might","shall","can","not","it","its","as","by","from","at","how",
        "what","why","when","which","who","whether","if","than","more","less",
        "their","there","they","we","our","your","his","her","its","my","i",
        "you","he","she","them","us","into","about","these","those","such",
        "any","all","no","so","up","out","some","much","many","also","both",
        "each","other","own","same","even","extent","should","view","assess",
    }
    freq: dict[str, int] = defaultdict(int)
    for q in _all_questions():
        words = re.findall(r"[a-zA-Z]{3,}", q["text"].lower())
        for w in words:
            if w not in STOP:
                freq[w] += 1
    ranked = sorted(freq.items(), key=lambda x: x[1], reverse=True)
    return [{"word": w, "count": c} for w, c in ranked[:top_n]]


@mcp.tool()
def compare_topics(sub_topic_a: str, sub_topic_b: str) -> dict:
    """
    Compares two sub-topics side-by-side: question counts, sample questions, and common keywords.
    Helpful for deciding which topic needs more revision.
    """
    def _find(sub: str):
        for cat, subtopics in QUESTION_DB.items():
            for key, qs in subtopics.items():
                if sub.lower() in key.lower():
                    return _fmt_category(cat), key, qs
        return None, None, []

    cat_a, key_a, qs_a = _find(sub_topic_a)
    cat_b, key_b, qs_b = _find(sub_topic_b)

    def _top_words(qs):
        freq: dict[str, int] = defaultdict(int)
        STOP = {"the","a","an","and","or","to","of","for","is","are","in","that","this"}
        for q in qs:
            for w in re.findall(r"[a-zA-Z]{4,}", q["text"].lower()):
                if w not in STOP:
                    freq[w] += 1
        return [w for w, _ in sorted(freq.items(), key=lambda x: x[1], reverse=True)[:8]]

    return {
        sub_topic_a: {
            "found_as": key_a,
            "category": cat_a,
            "question_count": len(qs_a),
            "sample": qs_a[0]["text"] if qs_a else None,
            "top_keywords": _top_words(qs_a),
        },
        sub_topic_b: {
            "found_as": key_b,
            "category": cat_b,
            "question_count": len(qs_b),
            "sample": qs_b[0]["text"] if qs_b else None,
            "top_keywords": _top_words(qs_b),
        },
    }


# ════════════════════════════════════════════════════════════════════════════
# 5. STUDY UTILITIES
# ════════════════════════════════════════════════════════════════════════════

@mcp.tool()
def get_revision_priority(weak_topics: list[str]) -> dict:
    """
    Given a list of topics you find difficult, returns:
    - All questions for those topics
    - Question count per topic
    - A suggested study order (most questions first = most exam weight)
    Args:
        weak_topics: List of sub-topic names (partial matching supported).
    """
    results = {}
    for topic in weak_topics:
        for cat, subtopics in QUESTION_DB.items():
            for sub, qs in subtopics.items():
                if topic.lower() in sub.lower():
                    results[sub.replace("_", " ").title()] = {
                        "category": _fmt_category(cat),
                        "question_count": len(qs),
                        "questions": [q["text"] for q in qs],
                    }
    # sort by question count (more = higher exam frequency)
    ordered = dict(sorted(results.items(), key=lambda x: x[1]["question_count"], reverse=True))
    return {
        "suggested_study_order": list(ordered.keys()),
        "topics": ordered,
    }


@mcp.tool()
def get_similar_questions(question_text: str, top_n: int = 5) -> list[dict]:
    """
    Given a question or keywords, finds the most thematically similar questions
    in the bank using word-overlap scoring.
    Args:
        question_text: The question (or theme) you want to find similar ones to.
        top_n:         How many similar questions to return (default 5).
    """
    STOP = {"the","a","an","and","or","to","of","for","is","are","in","that","this","with","how"}
    query_words = set(re.findall(r"[a-zA-Z]{3,}", question_text.lower())) - STOP
    scored = []
    for q in _all_questions():
        q_words = set(re.findall(r"[a-zA-Z]{3,}", q["text"].lower())) - STOP
        overlap = len(query_words & q_words)
        if overlap > 0:
            scored.append((overlap, q))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [
        {
            "similarity_score": score,
            "paper": q["paper"],
            "question": q["question"],
            "text": q["text"],
            "category": _fmt_category(q["category"]),
            "sub_topic": q["sub_topic"].replace("_", " ").title(),
        }
        for score, q in scored[:top_n]
    ]


# ════════════════════════════════════════════════════════════════════════════
# Entry point
# ════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    mcp.run(transport="sse")
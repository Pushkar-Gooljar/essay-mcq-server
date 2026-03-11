import json
import os
import random
from typing import List, Dict, Optional
from mcp.server.fastmcp import FastMCP

# Initialize the server
mcp = FastMCP("General Paper Examiner Tools")

# Load the database
DB_PATH = os.path.join(os.path.dirname(__file__), "mcp_questions_db.json")
with open(DB_PATH, "r", encoding="utf-8") as f:
    db = json.load(f)

@mcp.tool()
def list_syllabus_topics() -> Dict[str, List[str]]:
    """
    Returns the full syllabus structure: the 3 main areas and their available sub-topics.
    Use this to understand the categories available before querying specific topics.
    """
    return {main: list(subs.keys()) for main, subs in db.items()}

@mcp.tool()
def get_questions_by_topic(main_topic: str, sub_topic: str) -> List[Dict]:
    """
    Retrieves all past paper questions for a specific syllabus sub-topic.
    """
    try:
        return db[main_topic][sub_topic]
    except KeyError:
        return [{"error": f"Topic '{sub_topic}' under '{main_topic}' not found."}]

@mcp.tool()
def search_questions(keyword: str) -> List[Dict]:
    """
    Searches across all syllabus areas for questions containing a specific keyword (e.g., 'technology', 'art').
    """
    results = []
    keyword_lower = keyword.lower()
    for main, subs in db.items():
        for sub, questions in subs.items():
            for q in questions:
                if keyword_lower in q['text'].lower():
                    results.append({
                        "main_topic": main,
                        "sub_topic": sub,
                        "paper": q["paper"],
                        "question": q["question"],
                        "text": q["text"]
                    })
    return results

@mcp.tool()
def get_paper_composition(paper_id: str) -> Dict:
    """
    Reconstructs an entire past paper (e.g., '8021_w22_qp_11') showing all questions 
    and the syllabus topics they were mapped to. Great for analyzing paper balance.
    """
    paper_questions = []
    for main, subs in db.items():
        for sub, questions in subs.items():
            for q in questions:
                if q["paper"] == paper_id:
                    paper_questions.append({
                        "question_number": int(q["question"]),
                        "text": q["text"],
                        "main_topic": main,
                        "sub_topic": sub
                    })
    
    # Sort by question number
    paper_questions.sort(key=lambda x: x["question_number"])
    
    if not paper_questions:
        return {"error": f"No questions found for paper ID {paper_id}"}
        
    return {"paper_id": paper_id, "questions": paper_questions}

@mcp.tool()
def generate_mock_paper() -> List[Dict]:
    """
    Generates a 10-question mock exam by randomly selecting questions from 
    a diverse range of sub-topics across all three main syllabus areas.
    """
    all_questions = []
    for main, subs in db.items():
        for sub, questions in subs.items():
            for q in questions:
                all_questions.append({**q, "main_topic": main, "sub_topic": sub})
                
    # Randomly select 10 questions
    mock_paper = random.sample(all_questions, min(10, len(all_questions)))
    
    # Re-number them 1 to 10 for the mock paper format
    formatted_paper = []
    for i, q in enumerate(mock_paper, 1):
        formatted_paper.append({
            "mock_question_number": i,
            "text": q["text"],
            "original_paper": q["paper"],
            "syllabus_topic": q["sub_topic"]
        })
        
    return formatted_paper

if __name__ == "__main__":
    # For Railway deployment, we use SSE transport and bind to 0.0.0.0
    port = int(os.environ.get("PORT", 8000))
    print(f"Starting General Paper MCP Server on port {port}...")
    mcp.run(transport='sse', host="0.0.0.0", port=port)
# GP Question Bank — MCP Server

An MCP server exposing Cambridge AS Level General Paper (8019/8021) past paper questions to AI assistants via the Model Context Protocol.

---

## Tools Available

| Tool | Description |
|------|-------------|
| `get_overview` | Full stats: total questions, per-category breakdown |
| `get_categories` | List the 3 main syllabus categories |
| `get_sub_topics` | Sub-topics for a category (with question counts) |
| `get_questions_by_topic` | All questions for a category + sub-topic |
| `search_questions` | Full-text keyword search |
| `search_by_paper` | All questions from a specific paper code |
| `search_multi_keyword` | AND/OR search across multiple keywords |
| `get_random_question` | Random question (optional filters) |
| `get_practice_set` | Unique random set of N questions |
| `get_balanced_practice_set` | Equal questions from all 3 categories |
| `get_topic_stats` | Most/least common topics ranking |
| `get_paper_index` | Every paper in the DB with question count |
| `get_questions_by_year` | All questions from a given year |
| `get_keyword_frequency` | Most frequent words across all questions |
| `compare_topics` | Side-by-side comparison of two sub-topics |
| `get_revision_priority` | Study order for your weak topics |
| `get_similar_questions` | Find questions similar to a given prompt |

---

## Local Development

```bash
pip install -r requirements.txt
python server.py          # runs SSE server on http://localhost:8000/sse
```

---

## Deploy to Railway

### Prerequisites
- [Railway account](https://railway.app) (free)
- [Railway CLI](https://docs.railway.app/develop/cli): `npm install -g @railway/cli`
- Git installed

### Steps

**1. Create a GitHub repo and push your code**
```bash
cd gp-question-bank
git init
git add .
git commit -m "initial commit"
# Create a repo on github.com, then:
git remote add origin https://github.com/YOUR_USERNAME/gp-question-bank.git
git push -u origin main
```

**2. Deploy via Railway CLI**
```bash
railway login
railway init          # select "Empty Project", give it a name
railway up            # deploys from current directory
```

**3. Get your public URL**
```bash
railway domain        # generates a URL like https://gp-question-bank.up.railway.app
```

**4. Connect MCP SuperAssistant**

In the Chrome extension sidebar, set your server URL to:
```
https://your-app.up.railway.app/sse
```

---

## File Structure

```
gp-question-bank/
├── server.py                  # MCP server (all tools)
├── classified_questions.json  # Your question database (add this!)
├── requirements.txt
├── Procfile
├── railway.toml
└── .gitignore
```

> ⚠️ Make sure `classified_questions.json` is in the same folder before deploying.

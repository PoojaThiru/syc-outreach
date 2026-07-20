import os
import json
import requests
import anthropic
from datetime import datetime
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "syc-secret-2026")
client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
SERPER_API_KEY = os.getenv("SERPER_API_KEY")
FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")
APP_PASSWORD = os.getenv("APP_PASSWORD", "ScalingYourCompany2026")

def get_db():
    conn = psycopg2.connect(DATABASE_URL)
    return conn

def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS contacts (
            id SERIAL PRIMARY KEY,
            name TEXT,
            title TEXT,
            company TEXT,
            email TEXT,
            phone TEXT,
            website TEXT,
            linkedin TEXT,
            address TEXT,
            event TEXT,
            date_met TEXT,
            notes TEXT,
            category TEXT DEFAULT 'unknown',
            enrichment JSONB DEFAULT '{}',
            web_context JSONB DEFAULT '{}',
            emails JSONB DEFAULT '{}',
            timeline JSONB DEFAULT '[]',
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)
    conn.commit()
    cur.close()
    conn.close()

init_db()

def serper_search(query):
    if not SERPER_API_KEY:
        return ""
    try:
        res = requests.post("https://google.serper.dev/search",
            headers={"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"},
            json={"q": query, "num": 5},
            timeout=8
        )
        data = res.json()
        snippets = [r.get("snippet", "") for r in data.get("organic", [])]
        return " ".join(snippets[:3])
    except:
        return ""

def search_person(name, company):
    results = {}
    results["person"] = serper_search(f"{name} {company}")
    results["company"] = serper_search(f"{company} Japan startup")
    results["news"] = serper_search(f'"{name}" OR "{company}" news 2024 2025')
    results["funding"] = serper_search(f"{company} funding investors crunchbase")
    return results

def scrape_website(url):
    if not FIRECRAWL_API_KEY or not url:
        return ""
    try:
        if not url.startswith("http"):
            url = "https://" + url
        res = requests.post("https://api.firecrawl.dev/v0/scrape",
            headers={"Authorization": f"Bearer {FIRECRAWL_API_KEY}", "Content-Type": "application/json"},
            json={"url": url, "pageOptions": {"onlyMainContent": True}},
            timeout=15
        )
        data = res.json()
        content = data.get("data", {}).get("markdown", "")
        return content[:2000]
    except:
        return ""

CARD_SCAN_PROMPT = """You are scanning a business card image. Extract ALL contact information visible on the card.
If there are multiple business cards in the image, extract each one separately.

Return ONLY valid JSON, no markdown:
{
  "cards": [
    {
      "name": "...",
      "title": "...",
      "company": "...",
      "email": "...",
      "phone": "...",
      "website": "...",
      "linkedin": "...",
      "address": "..."
    }
  ]
}

If a field is not visible on the card, use an empty string. Never guess or invent information."""

PASTE_PROMPT = """You are extracting contact information from unstructured text for Tyson Batino, CEO of Scaling Your Company in Japan.

The input could be anything: an email signature, LinkedIn profile text, a URL, voice transcript, raw notes, or a mix.

Extract whatever contact info you can find. Also extract any useful context notes about who this person is.

Return ONLY valid JSON, no markdown:
{
  "name": "...",
  "title": "...",
  "company": "...",
  "email": "...",
  "phone": "...",
  "website": "...",
  "linkedin": "...",
  "extracted_notes": "any useful context about this person extracted from the text"
}

Use empty string for any field not found. Never invent information."""

ENRICH_PROMPT = """You are building a detailed contact intelligence profile for Tyson Batino, CEO of Scaling Your Company (SYC) in Japan.

You have been given contact information plus multiple sources of web research about this person. Synthesize all of this into a rich, useful profile.

Return ONLY valid JSON, no markdown:
{
  "company_description": "what the company does, who their customers are, their market",
  "industry": "specific industry",
  "stage_and_size": "funding stage, team size, revenue stage if known",
  "recent_news": "any recent news, launches, funding rounds, press in 2024-2025",
  "person_background": "career history, expertise, notable background",
  "relevance_to_syc": "why this person matters to Tyson and SYC specifically",
  "talking_points": "2-3 specific things Tyson could reference in a follow-up email",
  "enrichment_notes": "anything else useful",
  "category": "founder_prospect|investor|press_media|corporate_partner|service_provider|community_connector|other",
  "category_reason": "why this category"
}"""

CLASSIFY_PROMPT = """You are an AI assistant for Tyson Batino, CEO of Scaling Your Company (SYC) and SmartStart Japan.

Read the contact record including all web research and enrichment data, then write highly personalised follow-up email drafts.

Use Tyson's voice:
- Direct and warm. No corporate fluff.
- Reference REAL specifics from the research
- Short sentences. Active voice. Max 6 lines per email.
- Signs off as Tyson

EXAMPLES OF TYSON'S VOICE:
"Hey Sarah, Really enjoyed our chat yesterday. The payments infrastructure problem you're solving for SMEs is one I see a lot of founders underestimate until it becomes a bottleneck at 20+ people. Would love to stay in touch. Tyson"

Return ONLY valid JSON:
{
  "follow_up_angle": "one sentence specific hook for this person using real details",
  "flags": "any issues or gaps noticed, or empty string",
  "day1": { "subject": "...", "body": "..." },
  "day7": { "subject": "...", "body": "..." },
  "day21": { "subject": "...", "body": "..." }
}"""

def row_to_dict(row):
    d = dict(row)
    d['id'] = int(d['id'])
    if d.get('created_at'):
        d['created_at'] = d['created_at'].isoformat()
    for field in ['enrichment', 'web_context', 'emails', 'timeline']:
        if d.get(field) is None:
            d[field] = {} if field != 'timeline' else []
    return d

def require_auth():
    if not session.get("authenticated"):
        return redirect(url_for("login"))
    return None

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.json.get("password") == APP_PASSWORD:
            session["authenticated"] = True
            return jsonify({"success": True})
        return jsonify({"success": False, "error": "Incorrect password"})
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/")
def index():
    auth = require_auth()
    if auth: return auth
    return render_template("index.html")

@app.route("/api/contacts", methods=["GET"])
def get_contacts():
    try:
        conn = get_db()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT * FROM contacts ORDER BY created_at DESC")
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return jsonify({"success": True, "contacts": [row_to_dict(r) for r in rows]})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route("/api/contacts", methods=["POST"])
def add_contact():
    data = request.json
    c = data.get("contact", {})
    try:
        conn = get_db()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            INSERT INTO contacts (name, title, company, email, phone, website, linkedin, address, event, date_met, notes, category)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING *
        """, (
            c.get("name", ""), c.get("title", ""), c.get("company", ""),
            c.get("email", ""), c.get("phone", ""), c.get("website", ""),
            c.get("linkedin", ""), c.get("address", ""), c.get("event", ""),
            c.get("date_met", ""), c.get("notes", ""), "unknown"
        ))
        row = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({"success": True, "contact": row_to_dict(row)})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route("/api/contacts/<int:contact_id>", methods=["DELETE"])
def delete_contact(contact_id):
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("DELETE FROM contacts WHERE id = %s", (contact_id,))
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route("/api/parse-paste", methods=["POST"])
def parse_paste():
    data = request.json
    raw_text = data.get("raw_text", "")
    if not raw_text:
        return jsonify({"success": False, "error": "No text provided"})

    scraped_context = ""
    urls = [word for word in raw_text.split() if word.startswith("http")]
    if urls:
        scraped_context = scrape_website(urls[0])

    try:
        content = raw_text
        if scraped_context:
            content += f"\n\nScraped content from URL:\n{scraped_context}"
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=800,
            system=PASTE_PROMPT,
            messages=[{"role": "user", "content": content}]
        )
        text = response.content[0].text
        clean = text.replace("```json", "").replace("```", "").strip()
        result = json.loads(clean)
        return jsonify({"success": True, "contact": result})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route("/api/scan-card", methods=["POST"])
def scan_card():
    data = request.json
    image_data = data.get("image")
    media_type = data.get("media_type", "image/jpeg")
    qr_url = data.get("qr_url", "")

    qr_context = ""
    if qr_url:
        qr_context = scrape_website(qr_url)

    try:
        content = [
            {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": image_data}},
            {"type": "text", "text": CARD_SCAN_PROMPT + (f"\n\nAdditional context from QR code ({qr_url}):\n{qr_context}" if qr_context else "")}
        ]
        response = client.messages.create(model="claude-sonnet-4-6", max_tokens=1000, messages=[{"role": "user", "content": content}])
        text = response.content[0].text
        clean = text.replace("```json", "").replace("```", "").strip()
        result = json.loads(clean)
        return jsonify({"success": True, "cards": result.get("cards", [])})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route("/api/enrich", methods=["POST"])
def enrich_contact():
    data = request.json
    contact = data.get("contact", {})

    search_results = search_person(contact.get("name", ""), contact.get("company", ""))
    website_context = scrape_website(contact.get("website", ""))
    linkedin_context = scrape_website(contact.get("linkedin", ""))

    web_context = {
        "person_search": search_results.get("person", ""),
        "company_search": search_results.get("company", ""),
        "news_search": search_results.get("news", ""),
        "funding_search": search_results.get("funding", ""),
        "website_content": website_context,
        "linkedin_content": linkedin_context
    }

    try:
        enrich_input = {**contact, "web_research": web_context}
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1200,
            system=ENRICH_PROMPT,
            messages=[{"role": "user", "content": f"Contact and research:\n{json.dumps(enrich_input, indent=2)}"}]
        )
        text = response.content[0].text
        clean = text.replace("```json", "").replace("```", "").strip()
        result = json.loads(clean)

        conn = get_db()
        cur = conn.cursor()
        cur.execute(
            "UPDATE contacts SET enrichment = %s, web_context = %s, category = %s WHERE id = %s",
            (json.dumps(result), json.dumps(web_context), result.get("category", "other"), contact.get("id"))
        )
        conn.commit()
        cur.close()
        conn.close()

        return jsonify({"success": True, "enrichment": result})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route("/api/generate-emails/<int:contact_id>", methods=["POST"])
def generate_emails(contact_id):
    try:
        conn = get_db()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT * FROM contacts WHERE id = %s", (contact_id,))
        contact = cur.fetchone()
        cur.close()
        conn.close()

        if not contact:
            return jsonify({"success": False, "error": "Contact not found"})

        contact = row_to_dict(contact)
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1500,
            system=CLASSIFY_PROMPT,
            messages=[{"role": "user", "content": f"Contact record:\n{json.dumps(contact, indent=2)}"}]
        )
        text = response.content[0].text
        clean = text.replace("```json", "").replace("```", "").strip()
        result = json.loads(clean)

        timeline = contact.get("timeline", [])
        timeline.append({"type": "emails_generated", "date": datetime.now().isoformat(), "note": "Email drafts generated"})

        conn = get_db()
        cur = conn.cursor()
        cur.execute(
            "UPDATE contacts SET emails = %s, timeline = %s WHERE id = %s",
            (json.dumps(result), json.dumps(timeline), contact_id)
        )
        conn.commit()
        cur.close()
        conn.close()

        return jsonify({"success": True, "result": result})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route("/api/contacts/<int:contact_id>/timeline", methods=["POST"])
def add_timeline_entry(contact_id):
    data = request.json
    try:
        conn = get_db()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT timeline FROM contacts WHERE id = %s", (contact_id,))
        row = cur.fetchone()
        if not row:
            return jsonify({"success": False, "error": "Contact not found"})

        timeline = row["timeline"] or []
        timeline.append({"type": data.get("type", "note"), "date": datetime.now().isoformat(), "note": data.get("note", "")})

        cur.execute("UPDATE contacts SET timeline = %s WHERE id = %s", (json.dumps(timeline), contact_id))
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

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
N8N_WEBHOOK_URL = "https://pthirupu.app.n8n.cloud/webhook/a49d8f84-0b23-4f95-92c8-de51214f9b07"

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
            status TEXT DEFAULT 'new',
            syc_company TEXT DEFAULT 'unknown',
            enrichment JSONB DEFAULT '{}',
            web_context JSONB DEFAULT '{}',
            emails JSONB DEFAULT '{}',
            timeline JSONB DEFAULT '[]',
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)
    cur.execute("ALTER TABLE contacts ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'new'")
    cur.execute("ALTER TABLE contacts ADD COLUMN IF NOT EXISTS syc_company TEXT DEFAULT 'unknown'")
    conn.commit()
    cur.close()
    conn.close()

init_db()

def serper_search(query):
    if not SERPER_API_KEY:
        return {"text": "", "sources": []}
    try:
        res = requests.post("https://google.serper.dev/search",
            headers={"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"},
            json={"q": query, "num": 5}, timeout=8
        )
        data = res.json()
        organic = data.get("organic", [])
        snippets = [r.get("snippet", "") for r in organic[:3]]
        sources = [{"title": r.get("title", ""), "url": r.get("link", "")} for r in organic[:3] if r.get("link")]
        return {"text": " ".join(snippets), "sources": sources}
    except:
        return {"text": "", "sources": []}

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
            json={"url": url, "pageOptions": {"onlyMainContent": True}}, timeout=15
        )
        data = res.json()
        content = data.get("data", {}).get("markdown", "")
        return content[:2000]
    except:
        return ""

def send_to_sheets(contact):
    try:
        payload = {
            "name": contact.get("name", ""),
            "title": contact.get("title", ""),
            "company": contact.get("company", ""),
            "email": contact.get("email", ""),
            "phone": contact.get("phone", ""),
            "website": contact.get("website", ""),
            "event": contact.get("event", ""),
            "date_met": contact.get("date_met", ""),
            "category": contact.get("category", ""),
            "status": contact.get("status", ""),
            "syc_company": contact.get("syc_company", ""),
            "notes": contact.get("notes", ""),
            "created_at": contact.get("created_at", "")
        }
        requests.post(N8N_WEBHOOK_URL, json=payload, timeout=10)
    except:
        pass

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

ENRICH_PROMPT = """You are building a detailed contact intelligence profile for Tyson Batino who runs two companies in Japan:

1. SCALING YOUR COMPANY (SYC) — business coaching and scaling services for founders and operators already running businesses in Japan. Helps with management structure, team building, operations, and growth.

2. SMARTSTART JAPAN — helps foreign entrepreneurs and companies enter the Japanese market. Covers Business Manager Visa applications, company setup in Japan, immigration support, and market entry strategy.

Based on the contact information and web research, build a rich profile AND determine which company is most relevant.

Rules for company assignment:
- SmartStart Japan: foreign founders wanting to enter Japan, Business Manager Visa needs, company setup in Japan, immigration, market entry
- Scaling Your Company: founders already operating who need coaching, scaling help, management structure, business growth
- Both: if they need both market entry AND scaling help
- Use the manual_company field if provided — it overrides your detection

Return ONLY valid JSON, no markdown:
{
  "company_description": "what the company does, who their customers are",
  "industry": "specific industry",
  "stage_and_size": "funding stage, team size if known",
  "recent_news": "any recent news, launches, funding in 2024-2025",
  "person_background": "career history, expertise",
  "relevance_to_syc": "why this person matters and which SYC company can help them",
  "talking_points": "2-3 specific things Tyson could reference",
  "enrichment_notes": "anything else useful",
  "syc_company": "Scaling Your Company|SmartStart Japan|Both",
  "category": "founder_prospect|investor|press_media|corporate_partner|service_provider|community_connector|other",
  "category_reason": "why this category"
}"""

CLASSIFY_PROMPT = """You are an AI assistant for Tyson Batino who runs Scaling Your Company (SYC) and SmartStart Japan.

Read the contact record and write personalised follow-up email drafts. The syc_company field tells you which company is relevant — tailor the emails accordingly.

For Scaling Your Company contacts: focus on business coaching, scaling, management, operations.
For SmartStart Japan contacts: focus on Japan market entry, Business Manager Visa, company setup.
For Both: mention both angles.

Use Tyson's voice:
- Direct and warm. No corporate fluff.
- Reference REAL specifics from the research
- Short sentences. Active voice. Max 6 lines per email.
- Signs off as Tyson

EXAMPLES:
"Hey Sarah, Really enjoyed our chat. The management layer challenge you're facing at 12 people is exactly when founders need to get ahead of it. That's what we focus on at SYC. Tyson"

"Hey Marco, Great meeting you. If you're serious about the Business Manager Visa, SmartStart can walk you through the full process — we've done it for dozens of founders. Tyson"

Return ONLY valid JSON:
{
  "follow_up_angle": "one sentence specific hook",
  "flags": "any issues or gaps, or empty string",
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
            INSERT INTO contacts (name, title, company, email, phone, website, linkedin, address, event, date_met, notes, category, status, syc_company)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING *
        """, (
            c.get("name", ""), c.get("title", ""), c.get("company", ""),
            c.get("email", ""), c.get("phone", ""), c.get("website", ""),
            c.get("linkedin", ""), c.get("address", ""), c.get("event", ""),
            c.get("date_met", ""), c.get("notes", ""), "unknown", "new",
            c.get("syc_company", "unknown")
        ))
        row = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        contact = row_to_dict(row)
        return jsonify({"success": True, "contact": contact})
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

@app.route("/api/contacts/<int:contact_id>/status", methods=["POST"])
def update_status(contact_id):
    data = request.json
    status = data.get("status", "")
    try:
        conn = get_db()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT timeline FROM contacts WHERE id = %s", (contact_id,))
        row = cur.fetchone()
        if not row:
            return jsonify({"success": False, "error": "Contact not found"})
        timeline = row["timeline"] or []
        timeline.append({"type": "status_change", "date": datetime.now().isoformat(), "note": f"Status updated to {status}"})
        cur.execute("UPDATE contacts SET status = %s, timeline = %s WHERE id = %s",
            (status, json.dumps(timeline), contact_id))
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route("/api/contacts/<int:contact_id>/syc-company", methods=["POST"])
def update_syc_company(contact_id):
    data = request.json
    syc_company = data.get("syc_company", "")
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("UPDATE contacts SET syc_company = %s WHERE id = %s", (syc_company, contact_id))
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route("/api/contacts/<int:contact_id>/mark-sent", methods=["POST"])
def mark_sent(contact_id):
    data = request.json
    email_day = data.get("email_day", "day1")
    try:
        conn = get_db()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT timeline FROM contacts WHERE id = %s", (contact_id,))
        row = cur.fetchone()
        if not row:
            return jsonify({"success": False, "error": "Contact not found"})
        timeline = row["timeline"] or []
        timeline.append({"type": "email_sent", "date": datetime.now().isoformat(), "note": f"{email_day.replace('day', 'Day ')} email marked as sent"})
        cur.execute("UPDATE contacts SET timeline = %s WHERE id = %s", (json.dumps(timeline), contact_id))
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
            model="claude-sonnet-4-6", max_tokens=800, system=PASTE_PROMPT,
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
    extra_context = data.get("extra_context", "")

    qr_context = ""
    if qr_url:
        qr_context = scrape_website(qr_url)

    try:
        extra = ""
        if extra_context:
            extra += f"\n\nAdditional context provided by the user:\n{extra_context}"
        if qr_context:
            extra += f"\n\nScraped from QR code ({qr_url}):\n{qr_context}"

        content = [
            {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": image_data}},
            {"type": "text", "text": CARD_SCAN_PROMPT + extra}
        ]
        response = client.messages.create(model="claude-sonnet-4-6", max_tokens=1000,
            messages=[{"role": "user", "content": content}])
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

    all_sources = []
    for key in ["person", "company", "news", "funding"]:
        r = search_results.get(key, {})
        if isinstance(r, dict):
            all_sources.extend(r.get("sources", []))

    web_context = {
        "person_search": search_results.get("person", {}).get("text", "") if isinstance(search_results.get("person"), dict) else "",
        "company_search": search_results.get("company", {}).get("text", "") if isinstance(search_results.get("company"), dict) else "",
        "news_search": search_results.get("news", {}).get("text", "") if isinstance(search_results.get("news"), dict) else "",
        "funding_search": search_results.get("funding", {}).get("text", "") if isinstance(search_results.get("funding"), dict) else "",
        "website_content": website_context,
        "linkedin_content": linkedin_context,
        "sources": all_sources
    }

    try:
        enrich_input = {**contact, "web_research": web_context}
        response = client.messages.create(
            model="claude-sonnet-4-6", max_tokens=1200, system=ENRICH_PROMPT,
            messages=[{"role": "user", "content": f"Contact and research:\n{json.dumps(enrich_input, indent=2)}"}]
        )
        text = response.content[0].text
        clean = text.replace("```json", "").replace("```", "").strip()
        result = json.loads(clean)

        syc_company = result.get("syc_company", "unknown")

        conn = get_db()
        cur = conn.cursor()
        cur.execute(
            "UPDATE contacts SET enrichment = %s, web_context = %s, category = %s, syc_company = %s WHERE id = %s",
            (json.dumps(result), json.dumps(web_context), result.get("category", "other"), syc_company, contact.get("id"))
        )
        conn.commit()
        cur.close()
        conn.close()

        updated_contact = {**contact, "enrichment": result, "web_context": web_context, "syc_company": syc_company}
        send_to_sheets(updated_contact)

        return jsonify({"success": True, "enrichment": result, "syc_company": syc_company})
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
            model="claude-sonnet-4-6", max_tokens=1500, system=CLASSIFY_PROMPT,
            messages=[{"role": "user", "content": f"Contact record:\n{json.dumps(contact, indent=2)}"}]
        )
        text = response.content[0].text
        clean = text.replace("```json", "").replace("```", "").strip()
        result = json.loads(clean)

        timeline = contact.get("timeline", [])
        timeline.append({"type": "emails_generated", "date": datetime.now().isoformat(), "note": "Email drafts generated"})

        conn = get_db()
        cur = conn.cursor()
        cur.execute("UPDATE contacts SET emails = %s, timeline = %s WHERE id = %s",
            (json.dumps(result), json.dumps(timeline), contact_id))
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

import os
import json
import base64
import requests
import anthropic
from datetime import datetime
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
SERPER_API_KEY = os.getenv("SERPER_API_KEY")
FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY")

contacts_db = []
contact_id_counter = 1

def get_next_id():
    global contact_id_counter
    cid = contact_id_counter
    contact_id_counter += 1
    return cid

def search_person(name, company):
    if not SERPER_API_KEY:
        return ""
    try:
        res = requests.post("https://google.serper.dev/search",
            headers={"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"},
            json={"q": f"{name} {company} Japan", "num": 5}
        )
        data = res.json()
        snippets = [r.get("snippet", "") for r in data.get("organic", [])]
        return " ".join(snippets[:3])
    except:
        return ""

def scrape_website(url):
    if not FIRECRAWL_API_KEY or not url:
        return ""
    try:
        if not url.startswith("http"):
            url = "https://" + url
        res = requests.post("https://api.firecrawl.dev/v0/scrape",
            headers={"Authorization": f"Bearer {FIRECRAWL_API_KEY}", "Content-Type": "application/json"},
            json={"url": url, "pageOptions": {"onlyMainContent": True}}
        )
        data = res.json()
        content = data.get("data", {}).get("markdown", "")
        return content[:2000]
    except:
        return ""

def clean_contact(contact):
    return {k: (v if v is not None else "") for k, v in contact.items()}

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

ENRICH_PROMPT = """You are helping build a contact profile for Tyson Batino, CEO of Scaling Your Company (SYC) in Japan.

Based on the contact information and any web context provided, add useful context:
- What their company does
- The industry they operate in
- Company size or stage if known
- Any relevant background about the person
- Why they might be relevant to a business coaching/scaling company in Japan

Be honest about what you know vs what you are inferring. Keep it brief and practical.

Return ONLY valid JSON, no markdown:
{
  "company_description": "...",
  "industry": "...",
  "enrichment_notes": "...",
  "category": "founder_prospect|investor|press_media|corporate_partner|service_provider|community_connector|other",
  "category_reason": "..."
}"""

CLASSIFY_PROMPT = """You are an AI assistant for Tyson Batino, CEO of Scaling Your Company (SYC) and SmartStart Japan.

Read the contact record including any web context and enrichment data, then write follow-up email drafts.

Use Tyson's voice:
- Direct and warm. No corporate fluff.
- Reference real specifics from notes and web context
- Short sentences. Active voice. Max 6 lines per email.
- Signs off as Tyson

EXAMPLES OF TYSON'S VOICE:
"Hey Sarah, Really enjoyed our chat yesterday. The payments infrastructure problem you're solving for SMEs is one I see a lot of founders underestimate until it becomes a bottleneck at 20+ people. Would love to stay in touch. Tyson"

"Hey Kenji, Good to meet you yesterday. Always good to talk to someone who's been in the Japan market long enough to see what actually works. Let's stay in touch. Tyson"

Return ONLY valid JSON:
{
  "follow_up_angle": "one sentence specific hook for this person",
  "flags": "any issues or gaps noticed, or empty string",
  "day1": { "subject": "...", "body": "..." },
  "day7": { "subject": "...", "body": "..." },
  "day21": { "subject": "...", "body": "..." }
}"""

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/contacts", methods=["GET"])
def get_contacts():
    return jsonify({"success": True, "contacts": contacts_db})

@app.route("/api/contacts", methods=["POST"])
def add_contact():
    data = request.json
    contact = data.get("contact", {})
    contact["id"] = get_next_id()
    contact["created_at"] = datetime.now().isoformat()
    contact["timeline"] = []
    contact["emails"] = {}
    contact["enrichment"] = {}
    contact["web_context"] = {}
    contact["category"] = "unknown"
    contact = clean_contact(contact)
    contacts_db.append(contact)
    return jsonify({"success": True, "contact": contact})

@app.route("/api/scan-card", methods=["POST"])
def scan_card():
    data = request.json
    image_data = data.get("image")
    media_type = data.get("media_type", "image/jpeg")

    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1000,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": image_data
                        }
                    },
                    {
                        "type": "text",
                        "text": CARD_SCAN_PROMPT
                    }
                ]
            }]
        )
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

    search_context = search_person(contact.get("name", ""), contact.get("company", ""))
    website_context = scrape_website(contact.get("website", ""))

    web_context = {
        "search_results": search_context,
        "website_content": website_context
    }

    try:
        enrich_input = {**contact, "web_context": web_context}
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=800,
            system=ENRICH_PROMPT,
            messages=[{
                "role": "user",
                "content": f"Contact: {json.dumps(enrich_input, indent=2)}"
            }]
        )
        text = response.content[0].text
        clean = text.replace("```json", "").replace("```", "").strip()
        result = json.loads(clean)

        for c in contacts_db:
            if c["id"] == contact.get("id"):
                c["enrichment"] = result
                c["web_context"] = web_context
                c["category"] = result.get("category", "other")
                break

        return jsonify({"success": True, "enrichment": result})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route("/api/generate-emails/<int:contact_id>", methods=["POST"])
def generate_emails(contact_id):
    contact = next((c for c in contacts_db if c["id"] == contact_id), None)
    if not contact:
        return jsonify({"success": False, "error": "Contact not found"})

    try:
        context = {**contact}
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1500,
            system=CLASSIFY_PROMPT,
            messages=[{
                "role": "user",
                "content": f"Contact record:\n{json.dumps(context, indent=2)}"
            }]
        )
        text = response.content[0].text
        clean = text.replace("```json", "").replace("```", "").strip()
        result = json.loads(clean)

        for c in contacts_db:
            if c["id"] == contact_id:
                c["emails"] = result
                c["timeline"].append({
                    "type": "emails_generated",
                    "date": datetime.now().isoformat(),
                    "note": "Email drafts generated"
                })
                break

        return jsonify({"success": True, "result": result})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route("/api/contacts/<int:contact_id>/timeline", methods=["POST"])
def add_timeline_entry(contact_id):
    data = request.json
    for c in contacts_db:
        if c["id"] == contact_id:
            c["timeline"].append({
                "type": data.get("type", "note"),
                "date": datetime.now().isoformat(),
                "note": data.get("note", "")
            })
            return jsonify({"success": True})
    return jsonify({"success": False, "error": "Contact not found"})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

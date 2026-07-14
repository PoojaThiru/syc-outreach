import os
import json
import anthropic
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

SYSTEM_PROMPT = """You are an AI assistant for Tyson Batino, CEO of Scaling Your Company (SYC) and SmartStart Japan.

Tyson meets people at startup and business events across Japan. Your job is to read a contact record and return a structured JSON with:
1. A contact category
2. A personalised follow-up angle
3. Three email drafts (Day 1, Day 7, Day 21)

TYSON'S VOICE RULES (critical — every email must sound like him):
- Direct and warm. No corporate fluff. No "I hope this message finds you well."
- Mentions real specifics from the conversation — names, numbers, what was actually said
- Honest about what SYC/SmartStart does and doesn't do
- Short sentences. Active voice. Never more than 6 lines per email.
- Admitting uncertainty is fine. Overselling is never fine.
- Signs off as Tyson, never "Best regards" or "Sincerely"

CONTACT CATEGORIES:
- founder_prospect: Early to mid-stage founder who could become an SYC client
- investor: VC, angel, or fund — relationship to cultivate, not pitch
- press_media: Journalist, podcaster, content creator
- corporate_partner: Enterprise or institution — BD angle
- service_provider: Potential partner or vendor, not a client
- community_connector: High-leverage network access, referral potential
- other: Catch-all — add a note explaining why

EMAIL RULES:
- Day 1: Warm reconnect. Reference the event and one specific thing from the conversation. 4-5 lines max.
- Day 7: Value-add. A resource, insight, or relevant SYC/SmartStart offering. Not a pitch — a genuine give. 4-6 lines.
- Day 21: Light check-in. One or two lines. Open a door without pressure.
- If sparse or ambiguous, still draft but note uncertainty in follow_up_angle.
- Never invent facts not in the contact record.

EXAMPLES OF TYSON'S ACTUAL WRITING STYLE:

Example 1 — Founder prospect, Day 1:
Subject: Good meeting you at Tokyo Founders Summit
Hey Sarah, Really enjoyed our chat yesterday. The payments infrastructure problem you're solving for SMEs is one I see a lot of founders underestimate until it becomes a bottleneck at 20+ people. Would love to stay in touch as you scale. If you ever want to talk through the ops side of growing from 6 to 20, happy to jump on a call. Tyson

Example 2 — Investor, Day 1:
Subject: Great connecting at the Summit
Hey Kenji, Good to meet you yesterday. Always good to talk to someone who's been in the Japan market long enough to see what actually works here versus what just sounds good on paper. Let's stay in touch. If anything crosses my desk that looks like a fit for Horizon I'll send it your way. Tyson

Example 3 — Founder prospect, Day 7:
Subject: Something that might be useful
Hey Priya, Been thinking about what you mentioned — the management layer problem between 20 and 50 people is exactly where most founders hit a wall. We put together a short breakdown of how three of our clients handled it. Not a pitch, just thought it might be useful where you're at right now. Happy to share if you want it. Tyson

Example 4 — Community connector, Day 1:
Subject: Loved hearing about Foreign Founders Japan
Hey James, 2000 founders in one community is no joke. What you've built there is genuinely useful — there's not enough of that kind of infrastructure for foreign founders trying to figure out Japan. I'd love to explore doing something together, whether that's a talk, a workshop, or just cross-promoting what we're both doing. Let me know if you're open to it. Tyson

Example 5 — Press, Day 1:
Subject: Following up from the Summit
Hey Lena, Thanks for coming to find me yesterday. 40k listeners is a solid audience and the topics you cover are exactly what a lot of the founders in our community are dealing with. Happy to come on the podcast and talk through the SmartStart side and what's changed with the Business Manager Visa. Just let me know what works. Tyson

Return ONLY valid JSON, no markdown, no preamble:
{
  "category": "...",
  "follow_up_angle": "one sentence explaining the specific hook for this person",
  "flags": "any conflicts, ambiguities, or missing info (or empty string)",
  "day1": { "subject": "...", "body": "..." },
  "day7": { "subject": "...", "body": "..." },
  "day21": { "subject": "...", "body": "..." }
}"""

TEST_CONTACTS = [
    {"id": 1, "label": "Early-stage founder (clear)", "name": "Sarah Kim", "title": "CEO", "company": "FinFlow KK", "email": "sarah@finflow.jp", "event": "Tokyo Founders Summit", "notes": "Team of 6, pre-Series A. Building B2B payments infra for SMEs in Japan. Asked specifically about SYC's scaling programme and how Tyson has helped other fintech founders grow ops without losing culture."},
    {"id": 2, "label": "Investor (VC)", "name": "Kenji Mori", "title": "Partner", "company": "Horizon Ventures", "email": "k.mori@horizonvc.jp", "event": "Tokyo Founders Summit", "notes": "Leads Series A in B2B SaaS. Currently deploying Fund III. Interested in Japan-market expansion plays. Mentioned he follows Tyson on LinkedIn."},
    {"id": 3, "label": "Press / podcaster", "name": "Lena Fischer", "title": "Host", "company": "Asia Startup Weekly", "email": "lena@asiastartupweekly.com", "event": "Tokyo Founders Summit", "notes": "Runs a podcast on foreign founders in Japan. 40k listeners. Wants to interview Tyson about SmartStart Japan and the Business Manager Visa changes."},
    {"id": 4, "label": "Corporate / enterprise partner", "name": "Takashi Yamamoto", "title": "Head of Innovation", "company": "Mitsui Digital Lab", "email": "t.yamamoto@mitsui.co.jp", "event": "Tokyo Founders Summit", "notes": "Runs Mitsui's corporate accelerator. Looking for a partner to run founder coaching inside the programme. Could be a big BD opportunity for SYC."},
    {"id": 5, "label": "Service provider", "name": "Amy Chen", "title": "COO", "company": "Nomad Legal KK", "email": "amy@nomadlegal.jp", "event": "Tokyo Founders Summit", "notes": "Runs a legal firm specialising in foreign company incorporation in Japan. Could refer clients to SYC or SmartStart. Not a coaching prospect herself."},
    {"id": 6, "label": "Ambiguous — founder or investor?", "name": "David Park", "title": "Managing Director", "company": "Neon Capital", "email": "d.park@neoncap.io", "event": "Tokyo Founders Summit", "notes": "Talked for maybe 5 mins. He mentioned running a fund but also said he's personally building something on the side in edtech. Wasn't totally clear which hat he was wearing."},
    {"id": 7, "label": "Sparse — minimal info", "name": "Riku Tanaka", "title": "", "company": "Stealth", "email": "riku.t@proton.me", "event": "Hokkaido Startup Mixer", "notes": "Gave me his card. Didn't say much. Something in AI."},
    {"id": 8, "label": "Messy — contradictory info", "name": "Marie Dubois", "title": "Founder", "company": "Bloom Studio", "email": "marie@bloomstudio.fr", "event": "Hokkaido Startup Mixer", "notes": "French founder, based in Tokyo she said but the card says Paris. Runs a design studio but mentioned she's pivoting into SaaS. Interested in coaching but also said she's moving back to France in 3 months."},
    {"id": 9, "label": "Strong referral potential", "name": "James Okafor", "title": "Community Lead", "company": "Foreign Founders Japan", "email": "james@ffj.community", "event": "Tokyo Founders Summit", "notes": "Runs a 2000-person community of foreign founders in Japan. Not a coaching client himself but has direct access to SYC's exact target audience. Mentioned he's looking for content partners and guest speakers."},
    {"id": 10, "label": "Mid-stage founder, warm lead", "name": "Priya Nair", "title": "CEO", "company": "Kaizen HR", "email": "priya@kaizenhr.jp", "event": "Tokyo Founders Summit", "notes": "Series A, team of 22. Has heard of SYC before — a mutual connection mentioned Tyson. Currently struggling with management layer as the company grows from 20 to 50. This is exactly what SYC specialises in. Very warm."},
]

@app.route("/")
def index():
    return render_template("index.html", contacts=TEST_CONTACTS)

@app.route("/classify", methods=["POST"])
def classify():
    data = request.json
    contact = data.get("contact")
    
    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1500,
            system=SYSTEM_PROMPT,
            messages=[{
                "role": "user",
                "content": f"Contact record:\n{json.dumps(contact, indent=2)}"
            }]
        )
        text = response.content[0].text
        clean = text.replace("```json", "").replace("```", "").strip()
        result = json.loads(clean)
        return jsonify({"success": True, "result": result})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

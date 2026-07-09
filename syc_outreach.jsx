import { useState } from "react";

const TEST_CONTACTS = [
  {
    id: 1,
    label: "Early-stage founder (clear)",
    name: "Sarah Kim", title: "CEO", company: "FinFlow KK",
    email: "sarah@finflow.jp", phone: "+81-90-1234-5678",
    event: "Tokyo Founders Summit", met_date: "2025-07-08",
    notes: "Team of 6, pre-Series A. Building B2B payments infra for SMEs in Japan. Asked specifically about SYC's scaling programme and how Tyson has helped other fintech founders grow ops without losing culture.",
    category: "", score: null, notes_eval: ""
  },
  {
    id: 2,
    label: "Investor (VC)",
    name: "Kenji Mori", title: "Partner", company: "Horizon Ventures",
    email: "k.mori@horizonvc.jp", phone: "",
    event: "Tokyo Founders Summit", met_date: "2025-07-08",
    notes: "Leads Series A in B2B SaaS. Currently deploying Fund III. Interested in Japan-market expansion plays. Mentioned he follows Tyson on LinkedIn.",
    category: "", score: null, notes_eval: ""
  },
  {
    id: 3,
    label: "Press / podcaster",
    name: "Lena Fischer", title: "Host", company: "Asia Startup Weekly",
    email: "lena@asiastartupweekly.com", phone: "",
    event: "Tokyo Founders Summit", met_date: "2025-07-08",
    notes: "Runs a podcast on foreign founders in Japan. 40k listeners. Wants to interview Tyson about SmartStart Japan and the Business Manager Visa changes.",
    category: "", score: null, notes_eval: ""
  },
  {
    id: 4,
    label: "Corporate / enterprise partner",
    name: "Takashi Yamamoto", title: "Head of Innovation", company: "Mitsui Digital Lab",
    email: "t.yamamoto@mitsui.co.jp", phone: "+81-3-9876-5432",
    event: "Tokyo Founders Summit", met_date: "2025-07-08",
    notes: "Runs Mitsui's corporate accelerator. Looking for a partner to run founder coaching inside the programme. Could be a big BD opportunity for SYC.",
    category: "", score: null, notes_eval: ""
  },
  {
    id: 5,
    label: "Service provider / potential vendor",
    name: "Amy Chen", title: "COO", company: "Nomad Legal KK",
    email: "amy@nomadlegal.jp", phone: "",
    event: "Tokyo Founders Summit", met_date: "2025-07-08",
    notes: "Runs a legal firm specialising in foreign company incorporation in Japan. Could refer clients to SYC or SmartStart. Not a coaching prospect herself.",
    category: "", score: null, notes_eval: ""
  },
  {
    id: 6,
    label: "Ambiguous — founder or investor?",
    name: "David Park", title: "Managing Director", company: "Neon Capital",
    email: "d.park@neoncap.io", phone: "",
    event: "Tokyo Founders Summit", met_date: "2025-07-08",
    notes: "Talked for maybe 5 mins. He mentioned running a fund but also said he's personally building something on the side in edtech. Wasn't totally clear which hat he was wearing.",
    category: "", score: null, notes_eval: ""
  },
  {
    id: 7,
    label: "Sparse — minimal info",
    name: "Riku Tanaka", title: "", company: "Stealth",
    email: "riku.t@proton.me", phone: "",
    event: "Hokkaido Startup Mixer", met_date: "2025-07-05",
    notes: "Gave me his card. Didn't say much. Something in AI.",
    category: "", score: null, notes_eval: ""
  },
  {
    id: 8,
    label: "Messy — contradictory info",
    name: "Marie Dubois", title: "Founder", company: "Bloom Studio",
    email: "marie@bloomstudio.fr", phone: "",
    event: "Hokkaido Startup Mixer", met_date: "2025-07-05",
    notes: "French founder, based in Tokyo she said but the card says Paris. Runs a design studio but mentioned she's pivoting into SaaS. Interested in coaching but also said she's moving back to France in 3 months.",
    category: "", score: null, notes_eval: ""
  },
  {
    id: 9,
    label: "Strong referral potential",
    name: "James Okafor", title: "Community Lead", company: "Foreign Founders Japan",
    email: "james@ffj.community", phone: "+81-80-5555-1234",
    event: "Tokyo Founders Summit", met_date: "2025-07-08",
    notes: "Runs a 2000-person community of foreign founders in Japan. Not a coaching client himself but has direct access to SYC's exact target audience. Mentioned he's looking for content partners and guest speakers.",
    category: "", score: null, notes_eval: ""
  },
  {
    id: 10,
    label: "Mid-stage founder, warm lead",
    name: "Priya Nair", title: "CEO", company: "Kaizen HR",
    email: "priya@kaizenhr.jp", phone: "+81-90-8888-2222",
    event: "Tokyo Founders Summit", met_date: "2025-07-08",
    notes: "Series A, team of 22. Has heard of SYC before — a mutual connection mentioned Tyson. Currently struggling with management layer as the company grows from 20 to 50. This is exactly what SYC specialises in. Very warm.",
    category: "", score: null, notes_eval: ""
  }
];

const SYSTEM_PROMPT = `You are an AI assistant for Tyson Batino, CEO of Scaling Your Company (SYC) and SmartStart Japan.

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
- Day 1: Warm reconnect. Reference the event and one specific thing from the conversation. 4–5 lines max. Goal: keep the connection warm while it's fresh.
- Day 7: Value-add. A resource, insight, case study, or relevant SYC/SmartStart offering mapped to their specific situation. Not a pitch — a genuine give. 4–6 lines.
- Day 21: Light check-in. One or two lines. Open a door without pressure.
- If the contact record is sparse or ambiguous, still draft the emails but note the uncertainty in follow_up_angle.
- Never invent facts not present in the contact record.

Return ONLY valid JSON, no markdown, no preamble:
{
  "category": "...",
  "follow_up_angle": "one sentence explaining the specific hook for this person",
  "flags": "any conflicts, ambiguities, or missing info Claude notices (or empty string)",
  "day1": { "subject": "...", "body": "..." },
  "day7": { "subject": "...", "body": "..." },
  "day21": { "subject": "...", "body": "..." }
}`;

const SCORE_OPTIONS = [
  { value: 5, label: "5 — Perfect", color: "#22c55e" },
  { value: 4, label: "4 — Good", color: "#84cc16" },
  { value: 3, label: "3 — OK", color: "#eab308" },
  { value: 2, label: "2 — Off", color: "#f97316" },
  { value: 1, label: "1 — Wrong", color: "#ef4444" },
];

export default function App() {
  const [activeTab, setActiveTab] = useState("prototype");
  const [contacts] = useState(TEST_CONTACTS);
  const [selectedContact, setSelectedContact] = useState(null);
  const [customContact, setCustomContact] = useState({
    name: "", title: "", company: "", email: "", phone: "",
    event: "", met_date: "", notes: ""
  });
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [useCustom, setUseCustom] = useState(false);
  const [evalScores, setEvalScores] = useState({});
  const [evalNotes, setEvalNotes] = useState({});
  const [expandedEmail, setExpandedEmail] = useState("day1");

  const runClassification = async () => {
    setLoading(true);
    setError("");
    setResult(null);
    const contact = useCustom ? customContact : selectedContact;
    if (!contact) return;

    try {
      const res = await fetch("https://api.anthropic.com/v1/messages", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          model: "claude-sonnet-4-6",
          max_tokens: 1500,
          system: SYSTEM_PROMPT,
          messages: [{ role: "user", content: `Contact record:\n${JSON.stringify(contact, null, 2)}` }]
        })
      });
      const data = await res.json();
      const text = data.content?.map(b => b.text || "").join("") || "";
      const clean = text.replace(/```json|```/g, "").trim();
      setResult(JSON.parse(clean));
    } catch (e) {
      setError("Something went wrong. Check the contact record and try again.");
    }
    setLoading(false);
  };

  const setScore = (contactId, field, value) => {
    setEvalScores(prev => ({ ...prev, [`${contactId}_${field}`]: value }));
  };

  const setNote = (contactId, value) => {
    setEvalNotes(prev => ({ ...prev, [contactId]: value }));
  };

  const getCategoryColor = (cat) => {
    const colors = {
      founder_prospect: "#6366f1",
      investor: "#0ea5e9",
      press_media: "#8b5cf6",
      corporate_partner: "#0d9488",
      service_provider: "#64748b",
      community_connector: "#f59e0b",
      other: "#94a3b8"
    };
    return colors[cat] || "#94a3b8";
  };

  const tabs = [
    { id: "prototype", label: "🤖 Prototype" },
    { id: "contacts", label: "📋 Test Contacts" },
    { id: "prompt", label: "📝 Master Prompt" },
    { id: "eval", label: "📊 Eval Sheet" },
  ];

  return (
    <div style={{ fontFamily: "'Inter', system-ui, sans-serif", background: "#0f0f13", minHeight: "100vh", color: "#e2e8f0" }}>
      {/* Header */}
      <div style={{ background: "#16161d", borderBottom: "1px solid #2a2a3a", padding: "16px 24px", display: "flex", alignItems: "center", gap: "12px" }}>
        <div style={{ width: 36, height: 36, borderRadius: 8, background: "linear-gradient(135deg, #6366f1, #8b5cf6)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 18 }}>⚡</div>
        <div>
          <div style={{ fontWeight: 700, fontSize: 16, color: "#f1f5f9" }}>Event Outreach System</div>
          <div style={{ fontSize: 12, color: "#64748b" }}>Phase 1 — Claude Core · Scaling Your Company</div>
        </div>
      </div>

      {/* Tabs */}
      <div style={{ display: "flex", gap: 0, background: "#16161d", borderBottom: "1px solid #2a2a3a", padding: "0 24px" }}>
        {tabs.map(t => (
          <button key={t.id} onClick={() => setActiveTab(t.id)} style={{
            padding: "12px 18px", fontSize: 13, fontWeight: 500, border: "none", cursor: "pointer",
            background: "transparent", color: activeTab === t.id ? "#818cf8" : "#64748b",
            borderBottom: activeTab === t.id ? "2px solid #818cf8" : "2px solid transparent",
            transition: "all 0.15s"
          }}>{t.label}</button>
        ))}
      </div>

      <div style={{ padding: "24px", maxWidth: 860, margin: "0 auto" }}>

        {/* PROTOTYPE TAB */}
        {activeTab === "prototype" && (
          <div>
            <div style={{ marginBottom: 20 }}>
              <div style={{ display: "flex", gap: 10, marginBottom: 16 }}>
                <button onClick={() => setUseCustom(false)} style={{
                  padding: "8px 16px", borderRadius: 6, fontSize: 13, fontWeight: 500, cursor: "pointer", border: "none",
                  background: !useCustom ? "#6366f1" : "#1e1e2e", color: !useCustom ? "#fff" : "#94a3b8"
                }}>Use test contact</button>
                <button onClick={() => setUseCustom(true)} style={{
                  padding: "8px 16px", borderRadius: 6, fontSize: 13, fontWeight: 500, cursor: "pointer", border: "none",
                  background: useCustom ? "#6366f1" : "#1e1e2e", color: useCustom ? "#fff" : "#94a3b8"
                }}>Enter custom contact</button>
              </div>

              {!useCustom ? (
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
                  {contacts.map(c => (
                    <button key={c.id} onClick={() => { setSelectedContact(c); setResult(null); }} style={{
                      padding: "10px 14px", borderRadius: 8, cursor: "pointer", textAlign: "left", border: "none",
                      background: selectedContact?.id === c.id ? "#1e1e3a" : "#1a1a24",
                      borderLeft: `3px solid ${selectedContact?.id === c.id ? "#6366f1" : "#2a2a3a"}`,
                      transition: "all 0.15s"
                    }}>
                      <div style={{ fontSize: 12, fontWeight: 600, color: "#e2e8f0", marginBottom: 2 }}>{c.name}</div>
                      <div style={{ fontSize: 11, color: "#64748b" }}>{c.label}</div>
                    </button>
                  ))}
                </div>
              ) : (
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
                  {["name", "title", "company", "email", "phone", "event", "met_date"].map(field => (
                    <div key={field}>
                      <label style={{ fontSize: 11, color: "#64748b", display: "block", marginBottom: 4, textTransform: "uppercase", letterSpacing: "0.05em" }}>{field.replace("_", " ")}</label>
                      <input value={customContact[field]} onChange={e => setCustomContact(p => ({ ...p, [field]: e.target.value }))}
                        style={{ width: "100%", padding: "8px 10px", borderRadius: 6, border: "1px solid #2a2a3a", background: "#1a1a24", color: "#e2e8f0", fontSize: 13, boxSizing: "border-box" }} />
                    </div>
                  ))}
                  <div style={{ gridColumn: "1 / -1" }}>
                    <label style={{ fontSize: 11, color: "#64748b", display: "block", marginBottom: 4, textTransform: "uppercase", letterSpacing: "0.05em" }}>Notes</label>
                    <textarea value={customContact.notes} onChange={e => setCustomContact(p => ({ ...p, notes: e.target.value }))} rows={4}
                      style={{ width: "100%", padding: "8px 10px", borderRadius: 6, border: "1px solid #2a2a3a", background: "#1a1a24", color: "#e2e8f0", fontSize: 13, resize: "vertical", boxSizing: "border-box" }} />
                  </div>
                </div>
              )}
            </div>

            {/* Selected contact preview */}
            {!useCustom && selectedContact && (
              <div style={{ background: "#1a1a24", borderRadius: 10, padding: "14px 16px", marginBottom: 16, border: "1px solid #2a2a3a" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 8 }}>
                  <div>
                    <span style={{ fontWeight: 600, fontSize: 15, color: "#f1f5f9" }}>{selectedContact.name}</span>
                    <span style={{ fontSize: 13, color: "#64748b", marginLeft: 8 }}>{selectedContact.title}{selectedContact.title && selectedContact.company ? " · " : ""}{selectedContact.company}</span>
                  </div>
                  <span style={{ fontSize: 11, color: "#94a3b8", background: "#0f0f13", padding: "3px 8px", borderRadius: 4 }}>{selectedContact.event}</span>
                </div>
                <p style={{ fontSize: 13, color: "#94a3b8", margin: 0, lineHeight: 1.6 }}>{selectedContact.notes}</p>
              </div>
            )}

            <button onClick={runClassification} disabled={loading || (!useCustom && !selectedContact)}
              style={{
                width: "100%", padding: "12px", borderRadius: 8, border: "none", cursor: loading ? "not-allowed" : "pointer",
                background: loading ? "#2a2a3a" : "linear-gradient(135deg, #6366f1, #8b5cf6)",
                color: "#fff", fontWeight: 600, fontSize: 14, marginBottom: 20, transition: "all 0.2s"
              }}>
              {loading ? "Classifying + drafting emails..." : "Run Classification →"}
            </button>

            {error && <div style={{ background: "#2d1b1b", border: "1px solid #7f1d1d", borderRadius: 8, padding: 14, color: "#fca5a5", fontSize: 13, marginBottom: 16 }}>{error}</div>}

            {result && (
              <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
                <div style={{ background: "#1a1a24", borderRadius: 10, padding: 16, border: "1px solid #2a2a3a" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 10 }}>
                    <span style={{ background: getCategoryColor(result.category), color: "#fff", fontSize: 12, fontWeight: 600, padding: "3px 10px", borderRadius: 20 }}>
                      {result.category?.replace("_", " ")}
                    </span>
                  </div>
                  <div style={{ fontSize: 14, color: "#e2e8f0", fontStyle: "italic", marginBottom: result.flags ? 10 : 0 }}>"{result.follow_up_angle}"</div>
                  {result.flags && (
                    <div style={{ marginTop: 10, padding: "8px 12px", background: "#1e1a0e", borderRadius: 6, border: "1px solid #78350f" }}>
                      <span style={{ fontSize: 11, fontWeight: 600, color: "#fbbf24", textTransform: "uppercase", letterSpacing: "0.05em" }}>⚠ Flags: </span>
                      <span style={{ fontSize: 12, color: "#fcd34d" }}>{result.flags}</span>
                    </div>
                  )}
                </div>

                <div style={{ background: "#1a1a24", borderRadius: 10, border: "1px solid #2a2a3a", overflow: "hidden" }}>
                  <div style={{ display: "flex", borderBottom: "1px solid #2a2a3a" }}>
                    {["day1", "day7", "day21"].map(day => (
                      <button key={day} onClick={() => setExpandedEmail(day)} style={{
                        flex: 1, padding: "10px", border: "none", cursor: "pointer", fontSize: 13, fontWeight: 500,
                        background: expandedEmail === day ? "#0f0f13" : "transparent",
                        color: expandedEmail === day ? "#818cf8" : "#64748b",
                        borderBottom: expandedEmail === day ? "2px solid #6366f1" : "2px solid transparent"
                      }}>
                        {day === "day1" ? "Day 1 — Reconnect" : day === "day7" ? "Day 7 — Value-add" : "Day 21 — Check-in"}
                      </button>
                    ))}
                  </div>
                  {result[expandedEmail] && (
                    <div style={{ padding: 16 }}>
                      <div style={{ fontSize: 12, color: "#64748b", marginBottom: 4, textTransform: "uppercase", letterSpacing: "0.05em" }}>Subject</div>
                      <div style={{ fontSize: 14, fontWeight: 600, color: "#e2e8f0", marginBottom: 14 }}>{result[expandedEmail].subject}</div>
                      <div style={{ fontSize: 12, color: "#64748b", marginBottom: 4, textTransform: "uppercase", letterSpacing: "0.05em" }}>Body</div>
                      <div style={{ fontSize: 14, color: "#cbd5e1", lineHeight: 1.75, whiteSpace: "pre-wrap" }}>{result[expandedEmail].body}</div>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        )}

        {/* TEST CONTACTS TAB */}
        {activeTab === "contacts" && (
          <div>
            <div style={{ marginBottom: 20 }}>
              <div style={{ fontSize: 15, fontWeight: 600, color: "#f1f5f9", marginBottom: 6 }}>10 Test Contacts</div>
              <div style={{ fontSize: 13, color: "#64748b" }}>Covers all contact categories including edge cases. Use these in the Prototype tab to validate Claude's output before moving to real data.</div>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              {contacts.map((c, i) => (
                <div key={c.id} style={{ background: "#1a1a24", borderRadius: 10, padding: 16, border: "1px solid #2a2a3a" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 8 }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                      <span style={{ width: 22, height: 22, borderRadius: "50%", background: "#2a2a3a", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 11, fontWeight: 700, color: "#818cf8", flexShrink: 0 }}>{i + 1}</span>
                      <div>
                        <div style={{ fontWeight: 600, fontSize: 14, color: "#f1f5f9" }}>{c.name}</div>
                        <div style={{ fontSize: 12, color: "#64748b" }}>{c.title}{c.title && c.company ? " · " : ""}{c.company}</div>
                      </div>
                    </div>
                    <span style={{ fontSize: 11, color: "#818cf8", background: "#1e1e3a", padding: "3px 8px", borderRadius: 4, whiteSpace: "nowrap" }}>{c.label}</span>
                  </div>
                  <div style={{ fontSize: 12, color: "#64748b", marginBottom: 6 }}>📍 {c.event} · {c.email || "no email"}</div>
                  <div style={{ fontSize: 13, color: "#94a3b8", lineHeight: 1.6 }}>{c.notes}</div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* PROMPT TAB */}
        {activeTab === "prompt" && (
          <div>
            <div style={{ marginBottom: 16 }}>
              <div style={{ fontSize: 15, fontWeight: 600, color: "#f1f5f9", marginBottom: 6 }}>Master System Prompt</div>
              <div style={{ fontSize: 13, color: "#64748b", marginBottom: 16 }}>This is the exact prompt used in the prototype above. Copy this into your Python script, n8n node, or wherever you wire the Claude API call. Iterate on this prompt — not the code — to improve output quality.</div>
            </div>
            <div style={{ background: "#1a1a24", borderRadius: 10, border: "1px solid #2a2a3a", overflow: "hidden" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "10px 16px", borderBottom: "1px solid #2a2a3a", background: "#16161d" }}>
                <span style={{ fontSize: 12, color: "#64748b", fontFamily: "monospace" }}>system_prompt.txt</span>
                <button onClick={() => navigator.clipboard.writeText(SYSTEM_PROMPT)} style={{
                  padding: "4px 12px", borderRadius: 5, border: "none", cursor: "pointer",
                  background: "#2a2a3a", color: "#94a3b8", fontSize: 12
                }}>Copy</button>
              </div>
              <pre style={{ padding: 16, margin: 0, fontSize: 13, color: "#cbd5e1", lineHeight: 1.7, whiteSpace: "pre-wrap", fontFamily: "'Courier New', monospace" }}>
                {SYSTEM_PROMPT}
              </pre>
            </div>

            <div style={{ marginTop: 20, background: "#1a1a24", borderRadius: 10, padding: 16, border: "1px solid #2a2a3a" }}>
              <div style={{ fontSize: 13, fontWeight: 600, color: "#f1f5f9", marginBottom: 10 }}>How to use this in Python</div>
              <pre style={{ margin: 0, fontSize: 12, color: "#94a3b8", lineHeight: 1.7, fontFamily: "'Courier New', monospace", whiteSpace: "pre-wrap" }}>{`import anthropic, json

client = anthropic.Anthropic(api_key="your_key")

def classify_contact(contact: dict) -> dict:
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1500,
        system=SYSTEM_PROMPT,  # paste prompt here
        messages=[{
            "role": "user",
            "content": f"Contact record:\\n{json.dumps(contact, indent=2)}"
        }]
    )
    text = response.content[0].text
    return json.loads(text)

# Run on all 10 test contacts
for contact in test_contacts:
    result = classify_contact(contact)
    print(contact["name"], "→", result["category"])
    print(result["follow_up_angle"])
    print("---")`}
              </pre>
            </div>
          </div>
        )}

        {/* EVAL SHEET TAB */}
        {activeTab === "eval" && (
          <div>
            <div style={{ marginBottom: 16 }}>
              <div style={{ fontSize: 15, fontWeight: 600, color: "#f1f5f9", marginBottom: 6 }}>Prompt Evaluation Sheet</div>
              <div style={{ fontSize: 13, color: "#64748b", marginBottom: 4 }}>After running all 10 contacts through the prototype, score each output here. Share this with Heikin as evidence of what the prompt gets right and where it needs tuning before sign-off.</div>
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
              {contacts.map((c, i) => (
                <div key={c.id} style={{ background: "#1a1a24", borderRadius: 10, border: "1px solid #2a2a3a", overflow: "hidden" }}>
                  <div style={{ padding: "12px 16px", borderBottom: "1px solid #2a2a3a", display: "flex", alignItems: "center", gap: 10 }}>
                    <span style={{ width: 22, height: 22, borderRadius: "50%", background: "#2a2a3a", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 11, fontWeight: 700, color: "#818cf8", flexShrink: 0 }}>{i + 1}</span>
                    <div>
                      <div style={{ fontSize: 13, fontWeight: 600, color: "#f1f5f9" }}>{c.name}</div>
                      <div style={{ fontSize: 11, color: "#64748b" }}>{c.label}</div>
                    </div>
                  </div>
                  <div style={{ padding: 16 }}>
                    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 12, marginBottom: 12 }}>
                      {[
                        { key: "category", label: "Category correct?" },
                        { key: "angle", label: "Follow-up angle useful?" },
                        { key: "voice", label: "Emails in Tyson's voice?" },
                      ].map(({ key, label }) => (
                        <div key={key}>
                          <div style={{ fontSize: 11, color: "#64748b", marginBottom: 6, textTransform: "uppercase", letterSpacing: "0.05em" }}>{label}</div>
                          <div style={{ display: "flex", gap: 4 }}>
                            {[1, 2, 3, 4, 5].map(n => (
                              <button key={n} onClick={() => setScore(c.id, key, n)} style={{
                                width: 28, height: 28, borderRadius: 5, border: "none", cursor: "pointer", fontSize: 12, fontWeight: 600,
                                background: evalScores[`${c.id}_${key}`] === n ? SCORE_OPTIONS[5 - n].color : "#2a2a3a",
                                color: evalScores[`${c.id}_${key}`] === n ? "#fff" : "#64748b",
                              }}>{n}</button>
                            ))}
                          </div>
                        </div>
                      ))}
                    </div>
                    <div>
                      <div style={{ fontSize: 11, color: "#64748b", marginBottom: 4, textTransform: "uppercase", letterSpacing: "0.05em" }}>Notes for Heikin</div>
                      <textarea value={evalNotes[c.id] || ""} onChange={e => setNote(c.id, e.target.value)}
                        placeholder="What was wrong or what surprised you about this output..."
                        rows={2} style={{
                          width: "100%", padding: "8px 10px", borderRadius: 6, border: "1px solid #2a2a3a",
                          background: "#0f0f13", color: "#e2e8f0", fontSize: 13, resize: "vertical", boxSizing: "border-box"
                        }} />
                    </div>
                  </div>
                </div>
              ))}
            </div>

            <div style={{ marginTop: 20, background: "#1e1e3a", borderRadius: 10, padding: 16, border: "1px solid #3730a3" }}>
              <div style={{ fontSize: 13, fontWeight: 600, color: "#818cf8", marginBottom: 10 }}>Score Summary</div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 10 }}>
                {["category", "angle", "voice"].map(key => {
                  const scores = contacts.map(c => evalScores[`${c.id}_${key}`]).filter(Boolean);
                  const avg = scores.length ? (scores.reduce((a, b) => a + b, 0) / scores.length).toFixed(1) : "—";
                  return (
                    <div key={key} style={{ textAlign: "center" }}>
                      <div style={{ fontSize: 24, fontWeight: 700, color: "#e2e8f0" }}>{avg}</div>
                      <div style={{ fontSize: 11, color: "#64748b" }}>{key === "category" ? "Category" : key === "angle" ? "Angle" : "Voice"} avg</div>
                      <div style={{ fontSize: 11, color: "#475569" }}>{scores.length}/10 scored</div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

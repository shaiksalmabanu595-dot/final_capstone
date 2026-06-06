"""
AI-Powered Medical Equipment Reliability Intelligence Assistant
Clean, visual PowerPoint — Architecture & Data Flow
"""

from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN

prs = Presentation()
prs.slide_width  = Inches(13.33)
prs.slide_height = Inches(7.5)

# ── Palette ────────────────────────────────────────────────────────────────
NAVY    = RGBColor(0x0f, 0x28, 0x4a)
BLUE    = RGBColor(0x1d, 0x6f, 0xd1)
LTBLUE  = RGBColor(0xdb, 0xea, 0xfe)
CYAN    = RGBColor(0x06, 0xb6, 0xd4)
LTCYAN  = RGBColor(0xcf, 0xf0, 0xf7)
GREEN   = RGBColor(0x05, 0x96, 0x69)
LTGREEN = RGBColor(0xd1, 0xfa, 0xe5)
AMBER   = RGBColor(0xd9, 0x77, 0x06)
LTAMBER = RGBColor(0xfe, 0xf3, 0xc7)
PURPLE  = RGBColor(0x6d, 0x28, 0xd9)
LTPURP  = RGBColor(0xed, 0xe9, 0xfe)
RED     = RGBColor(0xdc, 0x26, 0x26)
LTRED   = RGBColor(0xfe, 0xe2, 0xe2)
WHITE   = RGBColor(0xff, 0xff, 0xff)
OFFWHT  = RGBColor(0xf8, 0xfa, 0xfc)
LGRAY   = RGBColor(0xe2, 0xe8, 0xf0)
MGRAY   = RGBColor(0x94, 0xa3, 0xb8)
DGRAY   = RGBColor(0x1e, 0x29, 0x3b)


# ── Primitive helpers ──────────────────────────────────────────────────────
def slide():
    return prs.slides.add_slide(prs.slide_layouts[6])

def bg(sl, rgb):
    f = sl.background.fill; f.solid(); f.fore_color.rgb = rgb

def rect(sl, x, y, w, h, fill, border=None, bw=1.0):
    sh = sl.shapes.add_shape(1, Inches(x), Inches(y), Inches(w), Inches(h))
    sh.fill.solid(); sh.fill.fore_color.rgb = fill
    if border: sh.line.color.rgb = border; sh.line.width = Pt(bw)
    else:       sh.line.fill.background()
    return sh

def label(sl, text, x, y, w, h, size=11, bold=False, color=DGRAY,
          align=PP_ALIGN.LEFT, italic=False):
    tb = sl.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tb.word_wrap = True
    tf = tb.text_frame; tf.word_wrap = True
    p  = tf.paragraphs[0]; p.alignment = align
    r  = p.add_run(); r.text = text
    r.font.size = Pt(size); r.font.bold = bold
    r.font.italic = italic; r.font.color.rgb = color

def card(sl, x, y, w, h, fill, border, title, title_color=None,
         title_size=10.5, border_w=1.5):
    rect(sl, x, y, w, h, fill, border, border_w)
    tc = title_color or border
    label(sl, title, x+0.14, y+0.1, w-0.28, 0.36,
          size=title_size, bold=True, color=tc, align=PP_ALIGN.CENTER)

def arrow(sl, x1, y1, x2, y2, color=MGRAY, w=1.8):
    c = sl.shapes.add_connector(1, Inches(x1), Inches(y1),
                                   Inches(x2), Inches(y2))
    c.line.color.rgb = color; c.line.width = Pt(w)

def hdr(sl, title, subtitle="", bg_color=NAVY, title_color=WHITE, sub_color=CYAN):
    rect(sl, 0, 0, 13.33, 0.82, bg_color)
    label(sl, title,    0.4, 0.07, 12.5, 0.46,
          size=22, bold=True, color=title_color)
    if subtitle:
        label(sl, subtitle, 0.4, 0.5, 12.5, 0.3,
              size=9.5, color=sub_color)


# ══════════════════════════════════════════════════════════════════════════
# SLIDE 1 — TITLE
# ══════════════════════════════════════════════════════════════════════════
sl = slide(); bg(sl, NAVY)
rect(sl, 0, 0, 13.33, 0.12, CYAN)
rect(sl, 0, 7.38, 13.33, 0.12, CYAN)

# logo block
rect(sl, 0.55, 1.0, 1.1, 1.1, CYAN)
label(sl, "⚕", 0.58, 1.04, 1.04, 1.02,
      size=34, bold=True, color=WHITE, align=PP_ALIGN.CENTER)

label(sl, "AI-Powered Medical Equipment",
      1.85, 0.95, 10.8, 0.65, size=34, bold=True, color=WHITE)
label(sl, "Reliability Intelligence Assistant",
      1.85, 1.58, 10.8, 0.65, size=34, bold=True, color=CYAN)

label(sl, "Architecture · Data Flow · Multi-Agent System",
      1.85, 2.28, 10.8, 0.45, size=14, color=MGRAY, italic=True)

rect(sl, 0.55, 2.85, 12.2, 0.04, CYAN)

# tech badge row
badges = [
    ("LangGraph Pipeline",      BLUE),
    ("GPT-4o mini Guardrails",  PURPLE),
    ("FAISS + BM25 Hybrid RAG", GREEN),
    ("DeepEval Evaluation",     AMBER),
    ("UCI AI4I 2020 Dataset",   CYAN),
]
bx = 0.55
for lbl, col in badges:
    rect(sl, bx, 3.05, 2.34, 0.46, col)
    label(sl, lbl, bx+0.1, 3.1, 2.14, 0.36,
          size=10, bold=True, color=WHITE, align=PP_ALIGN.CENTER)
    bx += 2.44

# bottom credits
label(sl, "FastAPI  ·  React 18  ·  Claude Sonnet 4.6  ·  Python 3.10",
      0.55, 3.72, 12.2, 0.38, size=10, color=MGRAY, align=PP_ALIGN.CENTER)

# key numbers
stats = [("10,000", "Maintenance Records"), ("12", "API Endpoints"),
         ("8", "LangGraph Nodes"),("4", "AI Agents"), ("6", "Frontend Views")]
sx = 0.55
for num, desc in stats:
    rect(sl, sx, 4.25, 2.34, 1.1, RGBColor(0x1a,0x38,0x60))
    label(sl, num,  sx+0.1, 4.34, 2.14, 0.52,
          size=26, bold=True, color=CYAN, align=PP_ALIGN.CENTER)
    label(sl, desc, sx+0.1, 4.84, 2.14, 0.38,
          size=8.5, color=MGRAY, align=PP_ALIGN.CENTER)
    sx += 2.44

label(sl, "Capstone Project  —  Biomedical Engineering AI",
      0.55, 6.9, 12.2, 0.38, size=10, color=MGRAY, align=PP_ALIGN.CENTER)


# ══════════════════════════════════════════════════════════════════════════
# SLIDE 2 — WHAT DOES THE SYSTEM DO? (Problem → Solution → Impact)
# ══════════════════════════════════════════════════════════════════════════
sl = slide(); bg(sl, OFFWHT)
hdr(sl, "What Does This System Do?",
    "AI assistant that helps biomedical engineers diagnose, predict and plan medical equipment maintenance")

cols = [
    ("⚠", "THE PROBLEM", RED, LTRED, [
        "Medical equipment failures put patients at risk",
        "Manual maintenance is reactive, not predictive",
        "Engineers lack fast access to historical failure data",
        "No intelligent root-cause analysis at scale",
        "Recommendations are slow and inconsistent",
    ]),
    ("🤖", "OUR SOLUTION", BLUE, LTBLUE, [
        "AI chat interface for natural language queries",
        "Hybrid RAG retrieves similar past incidents instantly",
        "4 AI agents analyse, plan and recommend actions",
        "GPT-4o mini validates every query and response",
        "DeepEval scores recommendation quality automatically",
    ]),
    ("✅", "THE IMPACT", GREEN, LTGREEN, [
        "Faster root-cause identification",
        "Data-driven preventive maintenance plans",
        "Reduced equipment downtime and repair costs",
        "Clinically safe, guardrail-validated outputs",
        "Works without API keys (rule-based fallback)",
    ]),
]
cx = 0.3
for icon, title, col, lt, points in cols:
    rect(sl, cx, 1.0, 4.18, 6.2, lt, col, 2)
    rect(sl, cx, 1.0, 4.18, 0.68, col)
    label(sl, icon+" "+title, cx+0.15, 1.06, 3.88, 0.52,
          size=13, bold=True, color=WHITE, align=PP_ALIGN.CENTER)
    py = 1.85
    for pt in points:
        rect(sl, cx+0.18, py, 3.82, 0.62, WHITE, col, 0.8)
        label(sl, "• "+pt, cx+0.34, py+0.1, 3.5, 0.42, size=10, color=DGRAY)
        py += 0.74
    cx += 4.47


# ══════════════════════════════════════════════════════════════════════════
# SLIDE 3 — HIGH-LEVEL SYSTEM ARCHITECTURE
# ══════════════════════════════════════════════════════════════════════════
sl = slide(); bg(sl, OFFWHT)
hdr(sl, "System Architecture — Three-Tier Overview",
    "User → React Frontend → FastAPI Backend → LangGraph Multi-Agent Pipeline → Data Layer")

# Tier boxes
tiers = [
    ("👤  USER", 0.25, 1.05, 2.4, 5.9, RGBColor(0x64,0x74,0x8b), LGRAY, [
        "Biomedical Engineer",
        "Types natural language query",
        "Views results in browser",
    ]),
    ("⚛  REACT FRONTEND", 2.95, 1.05, 3.1, 5.9, BLUE, LTBLUE, [
        "Dashboard (charts & KPIs)",
        "AI Assistant (chat interface)",
        "Maintenance Records table",
        "Anomaly Detection tool",
        "LangGraph Pipeline view",
        "Evaluation & Judge view",
    ]),
    ("⚡  FASTAPI BACKEND", 6.35, 1.05, 3.1, 5.9, NAVY, RGBColor(0xd0,0xd8,0xe8), [
        "12 REST API endpoints",
        "LangGraph pipeline runner",
        "RAG retrieval system",
        "4 AI analysis agents",
        "Input + Output guardrails",
        "DeepEval + LLM judge",
    ]),
    ("🗄  DATA LAYER", 9.75, 1.05, 3.3, 5.9, GREEN, LTGREEN, [
        "ai4i2020.csv  (10k rows UCI)",
        "medical_equipment_maint.csv",
        "FAISS index  (15 MB)",
        "BM25 index  (5.6 MB)",
        "Embeddings  (10k × 384-dim)",
        "LangGraph state (TypedDict)",
    ]),
]

for title, x, y, w, h, col, lt, items in tiers:
    rect(sl, x, y, w, h, lt, col, 2.5)
    rect(sl, x, y, w, 0.62, col)
    label(sl, title, x+0.12, y+0.1, w-0.24, 0.44,
          size=11, bold=True, color=WHITE, align=PP_ALIGN.CENTER)
    iy = y + 0.85
    for item in items:
        rect(sl, x+0.15, iy, w-0.3, 0.62, WHITE, col, 0.6)
        label(sl, item, x+0.28, iy+0.1, w-0.56, 0.42, size=9.5, color=DGRAY)
        iy += 0.72

# Arrows between tiers
arrow_data = [(2.65, 4.05, 2.95, 4.05), (6.05, 4.05, 6.35, 4.05),
              (9.45, 4.05, 9.75, 4.05)]
for x1, y1, x2, y2 in arrow_data:
    arrow(sl, x1, y1, x2, y2, NAVY, 2.5)

# Arrow labels
label(sl, "Axios\nHTTP",   2.58, 3.52, 0.45, 0.42, size=7.5, color=MGRAY, align=PP_ALIGN.CENTER)
label(sl, "REST\nAPI",     6.0,  3.52, 0.45, 0.42, size=7.5, color=MGRAY, align=PP_ALIGN.CENTER)
label(sl, "Read/\nWrite",  9.38, 3.52, 0.45, 0.42, size=7.5, color=MGRAY, align=PP_ALIGN.CENTER)


# ══════════════════════════════════════════════════════════════════════════
# SLIDE 4 — LANGGRAPH PIPELINE (visual flow)
# ══════════════════════════════════════════════════════════════════════════
sl = slide(); bg(sl, OFFWHT)
hdr(sl, "LangGraph Multi-Agent Pipeline — State Machine",
    "8 nodes · Conditional routing (VALID → analysis path / INVALID → rejection) · Shared TypedDict state")

# Node definitions  (label, x, y, w, h, fill, lt)
nodes = [
    ("Input\nGuardrail",          1.0,  2.6,  1.7, 0.95, AMBER,  LTAMBER),
    ("RAG\nRetrieval",            3.05, 2.6,  1.7, 0.95, BLUE,   LTBLUE),
    ("Equipment\nRetrieval Agent",5.1,  2.6,  1.7, 0.95, GREEN,  LTGREEN),
    ("Reliability\nAnalysis Agent",7.15, 2.6, 1.7, 0.95, GREEN,  LTGREEN),
    ("Maintenance\nAgent",        9.2,  2.6,  1.7, 0.95, PURPLE, LTPURP),
    ("Recommendation\nAgent",    11.25, 2.6,  1.7, 0.95, PURPLE, LTPURP),
]
# Draw nodes
for lbl, x, y, w, h, fill, lt in nodes:
    rect(sl, x, y, w, h, lt, fill, 2)
    label(sl, lbl, x+0.1, y+0.14, w-0.2, h-0.28,
          size=9, bold=True, color=fill, align=PP_ALIGN.CENTER)

# Output guardrail (after last agent — on new row)
rect(sl, 11.25, 4.1, 1.7, 0.95, LTAMBER, AMBER, 2)
label(sl, "Output\nGuardrail", 11.35, 4.24, 1.5, 0.67, size=9, bold=True,
      color=AMBER, align=PP_ALIGN.CENTER)

# START
rect(sl, 0.18, 2.78, 0.72, 0.6, NAVY)
label(sl, "START", 0.18, 2.82, 0.72, 0.52, size=8, bold=True, color=WHITE, align=PP_ALIGN.CENTER)

# END (main path)
rect(sl, 12.42, 4.28, 0.68, 0.6, NAVY)
label(sl, "END", 12.42, 4.32, 0.68, 0.52, size=8, bold=True, color=WHITE, align=PP_ALIGN.CENTER)

# Main flow arrows (horizontal)
main_arrows = [
    (0.9, 3.07, 1.0, 3.07),    # start → guardrail
    (2.7, 3.07, 3.05, 3.07),   # guardrail → RAG
    (4.75,3.07, 5.1, 3.07),    # RAG → retrieval agent
    (6.8, 3.07, 7.15, 3.07),   # → reliability
    (8.85,3.07, 9.2, 3.07),    # → maintenance
    (10.95,3.07,11.25,3.07),   # → recommendation
]
for x1,y1,x2,y2 in main_arrows:
    arrow(sl, x1, y1, x2, y2, NAVY, 2)

# Recommendation → output guardrail (down arrow)
arrow(sl, 12.1, 3.07, 12.1, 4.1, NAVY, 2)
label(sl, "↓", 12.02, 3.6, 0.3, 0.36, size=14, bold=True, color=NAVY, align=PP_ALIGN.CENTER)

# Output guardrail → END
arrow(sl, 12.42, 4.58, 12.76, 4.58, NAVY, 2)

# VALID / INVALID labels
label(sl, "✓ VALID", 2.72, 2.65, 0.95, 0.32, size=8.5, bold=True, color=GREEN)

# Rejection branch (down from input guardrail)
rect(sl, 1.0, 4.7, 1.7, 0.75, LTRED, RED, 2)
label(sl, "🚫  Rejection\nNode", 1.08, 4.78, 1.54, 0.6, size=9, bold=True, color=RED, align=PP_ALIGN.CENTER)
rect(sl, 1.0, 5.65, 0.72, 0.5, NAVY)
label(sl, "END", 1.0, 5.7, 0.72, 0.4, size=8, bold=True, color=WHITE, align=PP_ALIGN.CENTER)

arrow(sl, 1.85, 3.55, 1.85, 4.7, RED, 1.8)
arrow(sl, 1.36, 5.45, 1.36, 5.65, RED, 1.8)
label(sl, "✗ INVALID", 0.9, 4.05, 1.05, 0.32, size=8.5, bold=True, color=RED)

# Node detail cards below main flow
details = [
    (1.0,  1.05, 1.7, "GPT-4o mini\nValidates relevance\nSafety check\nRefines query"),
    (3.05, 1.05, 1.7, "FAISS + BM25\nHybrid search\nEmbedding rerank\nTop-k results"),
    (5.1,  1.05, 1.7, "Claude / Rules\nEquip. focus\nQuery intent\nRelevant incidents"),
    (7.15, 1.05, 1.7, "Claude / Rules\nFailure rate %\nReliability score\nAnomaly detection"),
    (9.2,  1.05, 1.7, "Claude / Rules\nAction plan\nUrgency level\nPreventive steps"),
    (11.25,1.05, 1.7, "Claude / Rules\nFinal synthesis\nRisk assessment\nConfidence 0-100"),
]
for x, y, w, detail in details:
    rect(sl, x, y, w, 1.42, WHITE, LGRAY, 0.8)
    label(sl, detail, x+0.1, y+0.08, w-0.2, 1.26, size=7.5, color=DGRAY)
    arrow(sl, x+w/2, y+1.42, x+w/2, 2.6, LGRAY, 1)

# State strip
rect(sl, 0.18, 6.52, 12.9, 0.82, NAVY)
label(sl, "Shared State  (MedEquipState TypedDict)  — 17 fields passed between every node",
      0.38, 6.57, 12.5, 0.32, size=9.5, bold=True, color=CYAN)
state = "query  ·  refined_query  ·  filters  ·  k  ·  alpha  ·  input_guardrail_result  ·  is_valid  ·  retrieved_docs[ ]  ·  retrieval_result  ·  reliability_result  ·  maintenance_result  ·  recommendation_result  ·  output_guardrail_result  ·  error  ·  analysis_mode  ·  execution_log[ ]  ·  node_timings{ }"
label(sl, state, 0.38, 6.88, 12.5, 0.38, size=7.5, color=LGRAY)


# ══════════════════════════════════════════════════════════════════════════
# SLIDE 5 — HOW RAG WORKS (step-by-step visual)
# ══════════════════════════════════════════════════════════════════════════
sl = slide(); bg(sl, OFFWHT)
hdr(sl, "Hybrid RAG — How Retrieval Works",
    "4-phase pipeline: dual retrieval → score fusion → embedding reranking → metadata filtering")

# Phase boxes (full height columns)
ph = [
    ("PHASE 1\nDual Retrieval",     0.2,  0.9, 3.2,  6.35, BLUE,   LTBLUE),
    ("PHASE 2\nScore Fusion",       3.65, 0.9, 2.55, 6.35, PURPLE, LTPURP),
    ("PHASE 3\nEmbedding Rerank",   6.45, 0.9, 3.2,  6.35, GREEN,  LTGREEN),
    ("PHASE 4\nFilter & Output",    9.9,  0.9, 3.2,  6.35, AMBER,  LTAMBER),
]
for title, x, y, w, h, col, lt in ph:
    rect(sl, x, y, w, h, lt, col, 2)
    rect(sl, x, y, w, 0.66, col)
    label(sl, title, x+0.1, y+0.08, w-0.2, 0.5,
          size=11, bold=True, color=WHITE, align=PP_ALIGN.CENTER)

# Phase arrows between columns
for ax in [3.4, 6.2, 9.65]:
    label(sl, "→", ax, 3.52, 0.34, 0.44,
          size=20, bold=True, color=NAVY, align=PP_ALIGN.CENTER)

# Phase 1 content — two sub-boxes
p1_items = [
    ("🔍  FAISS Vector Search", BLUE, [
        "Model: all-MiniLM-L6-v2",
        "Dimensions: 384-dim",
        "Index: IndexFlatIP",
        "(cosine similarity after",
        " L2 normalisation)",
        "Pool: top k×6 results",
    ]),
    ("📝  BM25 Keyword Search", CYAN, [
        "Library: rank-bm25",
        "Model: BM25Okapi",
        "Tokenise: lower().split()",
        "Scores all 10,000 docs",
        "Pool: top k×6 results",
        "",
    ]),
]
py = 1.72
for ptitle, pcol, pitems in p1_items:
    rect(sl, 0.38, py, 2.84, 2.62, WHITE, pcol, 1.2)
    label(sl, ptitle, 0.5, py+0.1, 2.6, 0.36, size=9, bold=True, color=pcol)
    iy = py + 0.52
    for it in pitems:
        label(sl, it, 0.52, iy, 2.6, 0.3, size=8, color=DGRAY)
        iy += 0.33
    py += 2.82

# Phase 2 content — fusion formula
rect(sl, 3.82, 1.72, 2.2, 5.2, WHITE, PURPLE, 1.2)
label(sl, "Normalise scores\nto [0.0 – 1.0] range",
      3.95, 1.82, 1.94, 0.65, size=9, color=DGRAY)
rect(sl, 3.95, 2.6, 1.94, 1.15, NAVY)
label(sl, "combined =\n  0.6 × v_score\n+ 0.4 × b_score",
      4.05, 2.68, 1.74, 1.0, size=9.5, bold=True, color=CYAN, align=PP_ALIGN.CENTER)
items2 = ["α = 0.6 → vector",
          "α = 0.4 → BM25",
          "Union of both sets",
          "Sort combined score",
          "Keep top k×4 docs",
          "for reranking phase"]
iy = 3.88
for it in items2:
    label(sl, "• "+it, 3.95, iy, 1.94, 0.32, size=8.5, color=DGRAY)
    iy += 0.36

# Phase 3 content
rect(sl, 6.62, 1.72, 2.86, 5.2, WHITE, GREEN, 1.2)
steps3 = [
    ("①", "Re-encode query",   "SentenceTransformer\n→ unit vector"),
    ("②", "Cosine similarity", "query_emb · doc_emb\nfor each candidate"),
    ("③", "Metadata bonus",    "+0.08 equip type match\n+0.06 failure type\n+0.04 hospital unit"),
    ("④", "Recency bonus",     "tool_wear ÷ 10000\n(max +0.03)"),
    ("⑤", "Final score",       "0.65×cosine\n+0.25×hybrid\n+meta+recency"),
]
sy = 1.86
for num, stitle, sdesc in steps3:
    label(sl, num, 6.72, sy, 0.3, 0.28, size=10, bold=True, color=GREEN)
    label(sl, stitle, 7.05, sy, 2.3, 0.28, size=8.5, bold=True, color=GREEN)
    label(sl, sdesc, 7.05, sy+0.3, 2.3, 0.55, size=8, color=DGRAY)
    sy += 0.92

# Phase 4 content
rect(sl, 10.08, 1.72, 2.84, 5.2, WHITE, AMBER, 1.2)
items4 = [
    ("Filter by equipment_type",  "Exact match (case-insensitive)"),
    ("Filter by hospital_unit",   "Exact match"),
    ("Filter by severity",        "Low/Medium/High/Critical"),
    ("failure_only flag",         "machine_failure == 1 only"),
    ("Token budget",              "max 1200 tokens\n(word_count ÷ 0.75)"),
    ("Return top k docs",         "With relevance_score\n& document_text"),
]
iy = 1.86
for fname, fdesc in items4:
    rect(sl, 10.2, iy, 2.6, 0.75, OFFWHT, AMBER, 0.8)
    label(sl, fname, 10.3, iy+0.04, 2.4, 0.28, size=8.5, bold=True, color=AMBER)
    label(sl, fdesc, 10.3, iy+0.34, 2.4, 0.34, size=7.5, color=DGRAY)
    iy += 0.84


# ══════════════════════════════════════════════════════════════════════════
# SLIDE 6 — 4 AI AGENTS
# ══════════════════════════════════════════════════════════════════════════
sl = slide(); bg(sl, OFFWHT)
hdr(sl, "Multi-Agent Intelligence System — 4 AI Agents",
    "Sequential pipeline: each agent reads the previous agent's output from shared LangGraph state")

agents = [
    ("🔍", "Equipment\nRetrieval Agent", BLUE, LTBLUE, [
        ("Takes",    "Query + top-k retrieved docs"),
        ("Finds",    "Relevant equipment types\nhospital units, query intent"),
        ("Returns",  "equipment_focus[]\nquery_intent, relevant_incidents[]"),
        ("Fallback", "Keyword extraction from\nequipment names and units"),
    ]),
    ("📈", "Reliability\nAnalysis Agent", GREEN, LTGREEN, [
        ("Takes",    "Query + docs + retrieval result"),
        ("Computes", "Failure rate %, reliability score\nanomaly detection, patterns"),
        ("Returns",  "reliability_score (0–100)\nanomalies[], failure_patterns[]"),
        ("Fallback", "Threshold-based analysis\non sensor values"),
    ]),
    ("🔧", "Maintenance\nPlanning Agent", PURPLE, LTPURP, [
        ("Takes",    "Query + docs + reliability result"),
        ("Creates",  "Prioritised action plan\nwith urgency level"),
        ("Returns",  "immediate_actions[]\nscheduled_maintenance[]\nurgency: critical/high/routine"),
        ("Fallback", "Failure type → standard\nmaintenance protocol lookup"),
    ]),
    ("💡", "Recommendation\nAgent", AMBER, LTAMBER, [
        ("Takes",    "Query + ALL 3 prior outputs"),
        ("Builds",   "Final recommendation\nwith root cause analysis"),
        ("Returns",  "summary, root_cause\nconfidence_score (0–100)\nrisk_assessment, action_plan[]"),
        ("Fallback", "Aggregates rule-based\nfindings into summary"),
    ]),
]

ax = 0.2
for icon, title, col, lt, rows in agents:
    rect(sl, ax, 0.98, 3.18, 6.22, lt, col, 2.5)
    # Header
    rect(sl, ax, 0.98, 3.18, 0.82, col)
    label(sl, icon, ax+0.12, 1.02, 0.55, 0.72, size=24, align=PP_ALIGN.CENTER, color=WHITE)
    label(sl, title, ax+0.7, 1.08, 2.35, 0.65,
          size=11, bold=True, color=WHITE)
    # Flow badge
    rect(sl, ax+0.18, 1.88, 2.82, 0.26, col)
    label(sl, "Claude Sonnet 4.6  (rule-based fallback)",
          ax+0.25, 1.89, 2.68, 0.24, size=7.5, bold=True, color=WHITE, align=PP_ALIGN.CENTER)
    # Rows
    ry = 2.24
    for rk, rv in rows:
        rect(sl, ax+0.18, ry, 2.82, 0.88, WHITE, col, 0.8)
        label(sl, rk, ax+0.28, ry+0.08, 0.65, 0.28, size=8, bold=True, color=col)
        label(sl, rv, ax+0.96, ry+0.08, 1.94, 0.72, size=8, color=DGRAY)
        ry += 0.97
    ax += 3.28

# Sequential flow arrows
for ax2 in [3.38, 6.66, 9.94]:
    arrow(sl, ax2, 4.08, ax2+0.2, 4.08, NAVY, 2.5)
    label(sl, "→", ax2-0.02, 3.82, 0.3, 0.32, size=14, bold=True, color=NAVY, align=PP_ALIGN.CENTER)


# ══════════════════════════════════════════════════════════════════════════
# SLIDE 7 — GUARDRAILS (visual flow)
# ══════════════════════════════════════════════════════════════════════════
sl = slide(); bg(sl, OFFWHT)
hdr(sl, "GPT-4o mini Guardrails — Input & Output Validation",
    "Every query is validated before processing · Every recommendation is scored before delivery")

# === Input Guardrail (left half) ===
rect(sl, 0.2, 0.95, 6.3, 6.3, LTAMBER, AMBER, 2)
rect(sl, 0.2, 0.95, 6.3, 0.58, AMBER)
label(sl, "🛡  INPUT GUARDRAIL", 0.38, 1.01, 5.94, 0.44,
      size=14, bold=True, color=WHITE)

# Flow inside input guardrail
rect(sl, 0.48, 1.68, 2.55, 0.65, WHITE, BLUE, 1.5)
label(sl, "User Query", 0.58, 1.74, 2.35, 0.5, size=11, bold=True, color=BLUE, align=PP_ALIGN.CENTER)

arrow(sl, 1.75, 2.33, 1.75, 2.72, AMBER, 2)

rect(sl, 0.48, 2.72, 2.55, 0.82, AMBER)
label(sl, "GPT-4o mini\n(rule-based fallback)", 0.58, 2.78, 2.35, 0.66,
      size=10, bold=True, color=WHITE, align=PP_ALIGN.CENTER)

arrow(sl, 1.75, 3.54, 1.75, 3.9, AMBER, 2)

# Checks box
rect(sl, 0.38, 3.9, 2.75, 2.85, WHITE, AMBER, 1)
label(sl, "What it checks:", 0.52, 4.0, 2.48, 0.3, size=9, bold=True, color=AMBER)
checks = ["Medical equipment relevance?",
          "Harmful patterns? (bypass, hack…)",
          "Intent: failure_analysis / status…",
          "Urgency: immediate / routine / low",
          "Refines query if needed"]
cy = 4.36
for ch in checks:
    label(sl, "✓  "+ch, 0.52, cy, 2.48, 0.36, size=9, color=DGRAY)
    cy += 0.42

# VALID / INVALID paths
rect(sl, 3.3, 2.52, 2.9, 0.78, LTGREEN, GREEN, 1.5)
label(sl, "✅  VALID\n→ Pipeline continues", 3.44, 2.6, 2.62, 0.62,
      size=10, bold=True, color=GREEN, align=PP_ALIGN.CENTER)

rect(sl, 3.3, 3.58, 2.9, 0.78, LTRED, RED, 1.5)
label(sl, "❌  INVALID\n→ Rejection + reason returned", 3.44, 3.66, 2.62, 0.62,
      size=10, bold=True, color=RED, align=PP_ALIGN.CENTER)

arrow(sl, 3.03, 2.88, 3.3, 2.88, GREEN, 2)
arrow(sl, 3.03, 3.95, 3.3, 3.95, RED, 2)
label(sl, "VALID\nrouting", 2.94, 2.68, 0.5, 0.28, size=7, color=GREEN)
label(sl, "INVALID\nrouting", 2.94, 3.82, 0.6, 0.28, size=7, color=RED)

label(sl, "Returns: is_valid · refined_query · intent · equipment_type · urgency",
      0.38, 6.88, 5.9, 0.28, size=8, color=DGRAY, italic=True)

# === Output Guardrail (right half) ===
rect(sl, 6.85, 0.95, 6.28, 6.3, LTAMBER, AMBER, 2)
rect(sl, 6.85, 0.95, 6.28, 0.58, AMBER)
label(sl, "🛡  OUTPUT GUARDRAIL", 7.02, 1.01, 5.94, 0.44,
      size=14, bold=True, color=WHITE)

rect(sl, 7.1, 1.68, 2.55, 0.65, WHITE, PURPLE, 1.5)
label(sl, "Recommendation\nfrom Agents", 7.2, 1.72, 2.35, 0.56,
      size=11, bold=True, color=PURPLE, align=PP_ALIGN.CENTER)

arrow(sl, 8.37, 2.33, 8.37, 2.72, AMBER, 2)

rect(sl, 7.1, 2.72, 2.55, 0.82, AMBER)
label(sl, "GPT-4o mini\n(rule-based fallback)", 7.2, 2.78, 2.35, 0.66,
      size=10, bold=True, color=WHITE, align=PP_ALIGN.CENTER)

arrow(sl, 8.37, 3.54, 8.37, 3.9, AMBER, 2)

rect(sl, 7.0, 3.9, 2.75, 3.2, WHITE, AMBER, 1)
label(sl, "Scoring rubric (0–100):", 7.12, 4.02, 2.5, 0.3, size=9, bold=True, color=AMBER)
scoring = [
    ("+10", "Has ≥ 3 action items"),
    ("+10", "Has ≥ 3 key findings"),
    ("+10", "Summary ≥ 50 chars"),
    ("+10", "Confidence ≥ 70%"),
    ("−20", "High risk but no actions"),
    ("−30", "Unsafe language detected"),
]
sy = 4.4
for pts, desc in scoring:
    col_s = GREEN if "+" in pts else RED
    label(sl, pts, 7.12, sy, 0.44, 0.34, size=9, bold=True, color=col_s)
    label(sl, desc, 7.6, sy, 2.1, 0.34, size=9, color=DGRAY)
    sy += 0.38

# Quality output
rect(sl, 9.9, 1.72, 2.85, 4.0, WHITE, AMBER, 1)
label(sl, "Output includes:", 10.05, 1.85, 2.55, 0.3, size=9, bold=True, color=AMBER)
outputs = ["quality_score  (0–100)",
           "safety_rating: safe / caution / unsafe",
           "is_safe  (True / False)",
           "approved_recommendation",
           "completeness_check{ }",
           "issues[ ]  (if any flagged)"]
oy = 2.22
for op in outputs:
    rect(sl, 10.05, oy, 2.55, 0.46, OFFWHT, AMBER, 0.5)
    label(sl, op, 10.15, oy+0.06, 2.35, 0.34, size=8.5, color=DGRAY)
    oy += 0.52

label(sl, "Returns: quality_score · safety_rating · is_safe · completeness_check{ }",
      6.92, 6.88, 5.9, 0.28, size=8, color=DGRAY, italic=True)


# ══════════════════════════════════════════════════════════════════════════
# SLIDE 8 — DEEPEVAL + LLM-AS-JUDGE
# ══════════════════════════════════════════════════════════════════════════
sl = slide(); bg(sl, OFFWHT)
hdr(sl, "DeepEval RAG Evaluation + LLM-as-Judge",
    "Post-hoc quality measurement: 4 RAG metrics + 4-dimension judge scoring (total 0–100)")

# DeepEval left
rect(sl, 0.2, 0.98, 6.3, 6.3, LTPURP, PURPLE, 2)
rect(sl, 0.2, 0.98, 6.3, 0.62, PURPLE)
label(sl, "📊  DeepEval RAG Metrics  (evaluation.py)", 0.38, 1.04, 5.9, 0.48,
      size=14, bold=True, color=WHITE)

de_metrics = [
    ("Answer Relevancy",      "Is the recommendation relevant to the original query?\nChecks keyword overlap and entity presence in the answer.",         "≥ 0.6 to pass"),
    ("Faithfulness",          "Is the answer grounded in the retrieved incident context?\nTraces entities in the answer back to retrieved documents.",     "≥ 0.6 to pass"),
    ("Contextual Precision",  "Are the top-ranked retrieved docs more relevant than lower-ranked?\nChecks precision@k ordering is monotone decreasing.",   "≥ 0.5 to pass"),
    ("Contextual Recall",     "Does the retrieved context cover all facts in the answer?\nExtracts medical entities from answer and checks in context.",   "≥ 0.5 to pass"),
]
dy = 1.74
for metric, desc, threshold in de_metrics:
    rect(sl, 0.38, dy, 5.94, 1.24, WHITE, PURPLE, 1.2)
    rect(sl, 0.38, dy, 5.94, 0.36, PURPLE)
    label(sl, metric, 0.52, dy+0.05, 4.5, 0.28, size=10, bold=True, color=WHITE)
    label(sl, threshold, 4.8, dy+0.05, 1.4, 0.28, size=8.5, color=LTPURP, align=PP_ALIGN.RIGHT)
    label(sl, desc, 0.52, dy+0.44, 5.6, 0.7, size=8.5, color=DGRAY)
    dy += 1.36

label(sl, "Mode: LLM-powered (OpenAI) when key available · Rule-based fallback always available",
      0.38, 6.88, 5.9, 0.28, size=8, color=MGRAY, italic=True)

# LLM-as-Judge right
rect(sl, 6.85, 0.98, 6.28, 6.3, LTAMBER, AMBER, 2)
rect(sl, 6.85, 0.98, 6.28, 0.62, AMBER)
label(sl, "⚖  LLM-as-Judge  (llm_judge.py)  — Total: 0–100", 7.02, 1.04, 5.9, 0.48,
      size=14, bold=True, color=WHITE)

dims = [
    ("Clinical Safety",    "0–25", RED,    "Are recommendations safe for patients and staff?\n25: All actions safe, hazards flagged for shutdown\n 0: Could endanger patients"),
    ("Technical Accuracy", "0–25", BLUE,   "Are technical details correct and evidence-based?\n25: Temperatures, torque, wear correctly cited\n 0: Fabricated or contradicts retrieved data"),
    ("Actionability",      "0–25", GREEN,  "Are actions concrete and immediately implementable?\n25: Specific, prioritised, biomedical-ready steps\n 0: Vague or contradictory actions"),
    ("Evidence Basis",     "0–25", AMBER,  "Is recommendation grounded in retrieved incidents?\n25: All claims traceable to specific incidents\n 0: Ignores evidence, hallucinated data"),
]
jy = 1.74
for dim, pts, col, desc in dims:
    rect(sl, 7.02, jy, 5.94, 1.24, WHITE, col, 1.2)
    rect(sl, 7.02, jy, 5.94, 0.36, col)
    label(sl, dim, 7.15, jy+0.05, 4.5, 0.28, size=10, bold=True, color=WHITE)
    label(sl, pts, 11.3, jy+0.05, 0.55, 0.28, size=11, bold=True, color=WHITE, align=PP_ALIGN.RIGHT)
    label(sl, desc, 7.15, jy+0.44, 5.68, 0.72, size=8.5, color=DGRAY)
    jy += 1.36

label(sl, "Priority: GPT-4o mini  →  Claude Sonnet 4.6  →  Rule-based  (all 3 levels fully implemented)",
      7.02, 6.88, 5.9, 0.28, size=8, color=MGRAY, italic=True)


# ══════════════════════════════════════════════════════════════════════════
# SLIDE 9 — END-TO-END DATA FLOW (numbered journey)
# ══════════════════════════════════════════════════════════════════════════
sl = slide(); bg(sl, DGRAY)
rect(sl, 0, 0, 13.33, 0.78, CYAN)
label(sl, "End-to-End Data Flow — From User Query to Recommendation",
      0.35, 0.1, 12.6, 0.52, size=22, bold=True, color=NAVY)

steps = [
    ("1", BLUE,   "User types a maintenance query",
     "e.g.  'Critical MRI overheating failure in Radiology — what should I do?'",
     "React AI Assistant → ChatInterface.jsx"),
    ("2", CYAN,   "React sends POST /api/query via Axios",
     "Payload: { query, k=5, alpha=0.6, equipment_type?, hospital_unit? }",
     "FastAPI validates request with Pydantic model"),
    ("3", RGBColor(0x55,0x80,0xb4), "FastAPI calls run_langgraph_pipeline()",
     "Initialises MedEquipState TypedDict with 17 fields",
     "LangGraph pipeline.invoke(initial_state) begins"),
    ("4", AMBER,  "node_input_guardrail()  runs GPT-4o mini",
     "Checks relevance, safety, intent → returns is_valid=True/False + refined_query",
     "INVALID → rejection node → END  |  VALID → continues"),
    ("5", GREEN,  "node_rag_retrieval()  runs Hybrid Search",
     "FAISS vector search + BM25 keyword search → score fusion → embedding rerank → metadata filter",
     "Returns top-k incidents with relevance_score and full metadata"),
    ("6", PURPLE, "4 Agent nodes run sequentially (Claude / rule-based)",
     "Retrieval → Reliability → Maintenance → Recommendation  (each reads + writes state)",
     "Final output: summary, root_cause, risk_assessment, confidence_score (0–100)"),
    ("7", AMBER,  "node_output_guardrail()  validates recommendation",
     "GPT-4o mini scores quality (0–100), safety_rating, completeness_check",
     "Approved recommendation passed forward"),
    ("8", BLUE,   "FastAPI maps LangGraph final state → JSON response",
     "agent_analysis, guardrails{input+output}, pipeline_log[], node_timings{}",
     "Returns QueryResponse with full pipeline trace"),
    ("9", CYAN,   "React renders the full result in the chat",
     "GuardrailBadges + PipelineLog (expandable) + KeyFindings + ActionPlan + ScoreCircle",
     "User sees structured, validated, evidence-based recommendation"),
]

for i, (num, col, title, detail, note) in enumerate(steps):
    y = 0.9 + i * 0.72
    rect(sl, 0.2, y, 0.56, 0.58, col)
    label(sl, num, 0.2, y+0.06, 0.56, 0.46, size=16, bold=True,
          color=WHITE, align=PP_ALIGN.CENTER)
    rect(sl, 0.86, y, 12.24, 0.58, RGBColor(0x24,0x36,0x52), col)
    label(sl, title,  1.02, y+0.05, 4.8,  0.26, size=9.5, bold=True, color=col)
    label(sl, detail, 1.02, y+0.3,  8.5,  0.24, size=8, color=RGBColor(0xb8,0xca,0xdf))
    label(sl, note,   9.55, y+0.3,  3.42, 0.24, size=7.5, color=MGRAY, italic=True)

    if i < 8:
        rect(sl, 0.38, y+0.58, 0.2, 0.12, RGBColor(0x38,0x50,0x6e))


# ══════════════════════════════════════════════════════════════════════════
# SLIDE 10 — TECH STACK + REQUIREMENT COVERAGE
# ══════════════════════════════════════════════════════════════════════════
sl = slide(); bg(sl, OFFWHT)
hdr(sl, "Technology Stack & Requirement Coverage",
    "All Requirement 1 (Basic) + Requirement 2 (Advanced) items implemented, tested and verified")

# Left: tech stack
rect(sl, 0.2, 0.95, 6.15, 6.3, OFFWHT, NAVY, 1.5)
rect(sl, 0.2, 0.95, 6.15, 0.48, NAVY)
label(sl, "⚙  Technology Stack", 0.38, 1.0, 5.77, 0.38, size=12, bold=True, color=WHITE)

tech = [
    ("Frontend",    BLUE,   "React 18 · Vite 8 · Recharts · Axios"),
    ("Backend",     NAVY,   "FastAPI 0.104 · Uvicorn · Pydantic v2"),
    ("AI / LLM",    PURPLE, "Claude Sonnet 4.6 · GPT-4o mini · LangGraph 1.2"),
    ("RAG",         GREEN,  "FAISS 1.7 · BM25Okapi · sentence-transformers"),
    ("Evaluation",  AMBER,  "DeepEval 4.0 · LLM-as-Judge · Rule-based"),
    ("Dataset",     CYAN,   "UCI AI4I 2020 · 10k records · 14 UCI cols → 32 cols"),
]
ty = 1.55
for layer, col, libs in tech:
    rect(sl, 0.38, ty, 5.8, 0.72, WHITE, col, 1.2)
    rect(sl, 0.38, ty, 1.12, 0.72, col)
    label(sl, layer, 0.42, ty+0.12, 1.04, 0.44, size=9.5, bold=True,
          color=WHITE, align=PP_ALIGN.CENTER)
    label(sl, libs, 1.56, ty+0.17, 4.5, 0.44, size=9, color=DGRAY)
    ty += 0.84

label(sl, "All components have rule-based fallbacks — system works without any API keys",
      0.38, 6.88, 5.77, 0.26, size=8, color=MGRAY, italic=True)

# Right: requirements checklist
rect(sl, 6.65, 0.95, 6.45, 6.3, OFFWHT, NAVY, 1.5)
rect(sl, 6.65, 0.95, 6.45, 0.48, NAVY)
label(sl, "✅  All Requirements Implemented", 6.82, 1.0, 6.1, 0.38,
      size=12, bold=True, color=WHITE)

reqs = [
    (BLUE,   "Req 1",  [
        "Basic RAG incident retrieval",
        "Hybrid search (vector + keyword)",
        "Metadata filtering (4 filter types)",
        "Input validation guardrails",
        "Root-cause recommendation engine",
        "Incident similarity ranking",
        "Maintenance recommendations",
        "12 REST API endpoints",
    ]),
    (PURPLE, "Req 2", [
        "DeepEval evaluation (4 metrics)",
        "Equipment anomaly correlation",
        "Embedding reranking (3-phase)",
        "LLM-as-judge (4 dimensions)",
        "Token optimisation (budget aware)",
        "Equipment Retrieval Agent",
        "Reliability Analysis Agent",
        "Maintenance + Recommendation Agent",
    ]),
]

rx = 6.82
for col, section, items in reqs:
    rect(sl, rx, 1.56, 2.98, 0.34, col)
    label(sl, section, rx+0.1, 1.6, 2.78, 0.26, size=9, bold=True,
          color=WHITE, align=PP_ALIGN.CENTER)
    iy = 1.98
    for item in items:
        rect(sl, rx, iy, 2.98, 0.54, OFFWHT, col, 0.6)
        label(sl, "✓  "+item, rx+0.14, iy+0.08, 2.7, 0.36, size=8.5, color=DGRAY)
        iy += 0.58
    rx += 3.1

label(sl, "Frontend: 6 views · Chat, Dashboard, Maintenance, Anomaly, LangGraph Pipeline, Evaluation & Judge",
      6.82, 6.88, 6.1, 0.26, size=8, color=MGRAY, italic=True)


# ── Save ───────────────────────────────────────────────────────────────────
out = "/home/labuser/capstone med/MedEquip_AI_Architecture.pptx"
prs.save(out)
print(f"Saved → {out}")
print(f"Slides: 10")

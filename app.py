"""
app.py
------
AI-Powered Requirements-to-Architecture Converter
Powered by Groq (free, ultra-fast LLM inference)

The Groq API key is read ONLY from the .env file / environment.
It is never shown, requested, or editable anywhere in the UI.

Run: streamlit run app.py
"""

import os
import json
import time
import re
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AI Architecture Designer",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS — clean light theme ──────────────────────────────────────────────────
st.markdown("""
<style>
/* Base */
.stApp { background-color: #f8fafc; }
.main .block-container { padding-top: 1.5rem; max-width: 1400px; }
[data-testid="stSidebar"] {
    background-color: #ffffff;
    border-right: 1px solid #e2e8f0;
}
[data-testid="stSidebar"] * { color: #1e293b; }

h1, h2, h3, h4, h5, h6, p, span, label, div { color: #1e293b; }

/* Metric cards */
.metric-card {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    padding: 18px;
    text-align: center;
    margin-bottom: 10px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}
.metric-value { font-size: 2.1rem; font-weight: 800; color: #4f46e5; line-height: 1; }
.metric-label { font-size: 0.74rem; color: #64748b; margin-top: 5px; text-transform: uppercase; letter-spacing: .05em; }

/* Hero */
.hero-banner {
    background: linear-gradient(135deg, #eef2ff 0%, #e0e7ff 50%, #eef2ff 100%);
    border: 1px solid #c7d2fe;
    border-radius: 16px;
    padding: 30px;
    text-align: center;
    margin-bottom: 22px;
}
.hero-title { font-size: 2rem; font-weight: 800; color: #312e81; margin-bottom: 6px; }
.hero-sub   { color: #4338ca; font-size: 1rem; }

/* Requirement item */
.req-item {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-left: 3px solid #4f46e5;
    padding: 8px 13px;
    margin-bottom: 6px;
    border-radius: 0 8px 8px 0;
    font-size: .88rem;
    color: #334155;
}

/* Section headers */
.sec-hdr {
    font-size: 1.15rem;
    font-weight: 700;
    color: #1e293b;
    margin-bottom: 14px;
    padding-bottom: 8px;
    border-bottom: 2px solid #c7d2fe;
}

/* Status boxes */
.success-box { background:#f0fdf4; border:1px solid #86efac; border-radius:8px; padding:11px 15px; color:#15803d; margin-bottom:10px; }
.error-box   { background:#fef2f2; border:1px solid #fca5a5; border-radius:8px; padding:11px 15px; color:#b91c1c; margin-bottom:10px; }
.warn-box    { background:#fffbeb; border:1px solid #fcd34d; border-radius:8px; padding:11px 15px; color:#92400e; margin-bottom:10px; }
.info-box    { background:#eff6ff; border:1px solid #93c5fd; border-radius:8px; padding:11px 15px; color:#1d4ed8; margin-bottom:10px; }

/* Buttons */
.stButton > button {
    width: 100%;
    background: linear-gradient(135deg, #4f46e5, #4338ca);
    color: white;
    border: none;
    border-radius: 10px;
    padding: 12px 22px;
    font-size: 1rem;
    font-weight: 700;
    cursor: pointer;
    transition: all .15s;
    box-shadow: 0 1px 2px rgba(0,0,0,0.06);
}
.stButton > button:hover { background: linear-gradient(135deg, #4338ca, #3730a3); transform: translateY(-1px); }
.stButton > button:disabled { background: #e2e8f0; color: #94a3b8; cursor: not-allowed; box-shadow:none; }

/* Tabs */
.stTabs [data-baseweb="tab-list"] { background: #ffffff; border-bottom: 1px solid #e2e8f0; gap: 2px; }
.stTabs [data-baseweb="tab"]      { color: #64748b; font-weight: 600; padding: 9px 18px; }
.stTabs [aria-selected="true"]    { color: #4f46e5 !important; background: #eef2ff !important; border-radius: 8px 8px 0 0; }

/* Expander */
.streamlit-expanderHeader {
    background-color: #ffffff !important;
    border: 1px solid #e2e8f0 !important;
    border-radius: 8px !important;
    color: #1e293b !important;
}

/* Text inputs / text areas */
.stTextInput input, .stTextArea textarea {
    background-color: #ffffff !important;
    color: #1e293b !important;
    border: 1px solid #cbd5e1 !important;
}

/* Dataframe */
[data-testid="stDataFrame"] { border: 1px solid #e2e8f0; border-radius: 8px; }

/* Hide Streamlit chrome */
#MainMenu, footer, header { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# ── Local imports ─────────────────────────────────────────────────────────────
from architecture_generator import ArchitectureGenerator
from diagram_generator import (
    render_mermaid_html, clean_mermaid_code, DIAGRAM_TYPES,
    validate_mermaid_syntax, generate_er_diagram,
)
from requirement_parser import parse_uploaded_file, detect_document_type, estimate_token_count
from utils import (
    generate_markdown_report, generate_json_export,
    generate_pdf_report, generate_docx_report, format_component_count,
)

# ── Session state ─────────────────────────────────────────────────────────────
for k, v in {
    "architecture_data": None,
    "generation_complete": False,
    "chat_history": [],
    "requirements_text": "",
}.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR  (no API key field — key is read only from .env, never displayed)
# ══════════════════════════════════════════════════════════════════════════════
def render_sidebar():
    with st.sidebar:
        st.markdown("""
        <div style="text-align:center;padding:10px 0 18px">
            <div style="font-size:1.9rem">🏗️</div>
            <div style="font-size:1.1rem;font-weight:800;color:#1e293b">AI Architect</div>
            <div style="font-size:.72rem;color:#64748b;margin-top:3px">Requirements → Architecture</div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("---")

        if not GROQ_API_KEY:
            st.markdown(
                '<div class="error-box">⚠️ Service not configured.<br>'
                'Ask the administrator to set the API key in the .env file.</div>',
                unsafe_allow_html=True,
            )
            st.markdown("---")

        if st.session_state.architecture_data:
            counts = format_component_count(st.session_state.architecture_data)
            st.markdown("### Stats")
            c1, c2 = st.columns(2)
            for col, val, lbl, color in [
                (c1, counts["total_components"], "Components", "#4f46e5"),
                (c2, counts["total_conflicts"], "Conflicts", "#dc2626" if counts["high_severity_conflicts"] else "#4f46e5"),
                (c1, counts["functional_reqs"], "Func Reqs", "#4f46e5"),
                (c2, counts["tech_stack_count"], "Tech Items", "#4f46e5"),
            ]:
                col.markdown(
                    f'<div class="metric-card">'
                    f'<div class="metric-value" style="color:{color}">{val}</div>'
                    f'<div class="metric-label">{lbl}</div></div>',
                    unsafe_allow_html=True,
                )
            st.markdown("---")

        if st.session_state.architecture_data:
            arch = st.session_state.architecture_data
            st.markdown("### Export")

            st.download_button("📝 Markdown", generate_markdown_report(arch),
                               "architecture_report.md", "text/markdown", use_container_width=True)
            st.download_button("📋 JSON", generate_json_export(arch),
                               "architecture.json", "application/json", use_container_width=True)

            try:
                import reportlab  # noqa: F401
                st.download_button("📄 PDF", generate_pdf_report(arch),
                                   "architecture_report.pdf", "application/pdf", use_container_width=True)
            except ImportError:
                pass

            try:
                import docx  # noqa: F401
                st.download_button("📑 DOCX", generate_docx_report(arch),
                                   "architecture_report.docx",
                                   "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                                   use_container_width=True)
            except ImportError:
                pass

            diagrams = arch.get("mermaid_diagrams", {})
            if diagrams:
                mmd = "\n\n".join(
                    f"# {DIAGRAM_TYPES.get(k, k)}\n```mermaid\n{v}\n```"
                    for k, v in diagrams.items()
                )
                st.download_button("📊 Diagrams (.md)", mmd,
                                   "diagrams.md", "text/markdown", use_container_width=True)

            st.markdown("---")
            if st.button("🗑️ Clear & New Analysis", use_container_width=True):
                st.session_state.architecture_data = None
                st.session_state.generation_complete = False
                st.session_state.chat_history = []
                st.session_state.requirements_text = ""
                st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# INPUT SECTION
# ══════════════════════════════════════════════════════════════════════════════
def render_input():
    st.markdown("""
    <div class="hero-banner">
        <div class="hero-title">🏗️ AI Architecture Designer</div>
        <div class="hero-sub">Upload requirements → Get a complete software architecture in seconds</div>
    </div>
    """, unsafe_allow_html=True)

    tab_upload, tab_paste = st.tabs(["📁 Upload Document", "✍️ Paste Text"])
    requirements_text = ""

    with tab_upload:
        st.markdown("**Supported:** PDF · DOCX · TXT · Markdown")
        uploaded = st.file_uploader("Upload requirements", type=["pdf", "docx", "txt", "md"],
                                    label_visibility="collapsed")
        if uploaded:
            with st.spinner(f"Parsing {uploaded.name}..."):
                text, ftype = parse_uploaded_file(uploaded)
            if text and not text.startswith("Error"):
                doc_type = detect_document_type(text)
                tokens = estimate_token_count(text)
                c1, c2, c3 = st.columns(3)
                c1.metric("Type", doc_type.split("(")[0].strip())
                c2.metric("Format", ftype)
                c3.metric("Approx. Tokens", f"{tokens:,}")
                if tokens > 12000:
                    st.markdown(
                        '<div class="warn-box">This document is large and will be '
                        'truncated to roughly the first 12,000 tokens for analysis.</div>',
                        unsafe_allow_html=True,
                    )
                requirements_text = text
                with st.expander("Preview extracted text"):
                    st.text_area("", value=text[:3000] + ("..." if len(text) > 3000 else ""),
                                 height=180, disabled=True, label_visibility="collapsed")
            else:
                st.markdown(f'<div class="error-box">{text}</div>', unsafe_allow_html=True)

    with tab_paste:
        text_in = st.text_area(
            "Requirements",
            value=st.session_state.get("requirements_text", ""),
            height=280,
            placeholder="Paste your SRS, BRD, User Stories, or any requirements document here...",
            label_visibility="collapsed",
        )
        if text_in:
            requirements_text = text_in
            c1, c2 = st.columns(2)
            c1.metric("Detected Type", detect_document_type(text_in).split("(")[0].strip())
            c2.metric("Approx. Tokens", f"{estimate_token_count(text_in):,}")

    st.markdown("---")
    st.markdown("**Or load a sample document:**")
    sc = st.columns(4)
    samples = {
        "🛒 E-Commerce": "sample_docs/ecommerce_srs.txt",
        "💬 Chat App": "sample_docs/chat_app_requirements.txt",
        "🏥 Healthcare": "sample_docs/healthcare_platform.txt",
        "📊 Analytics": "sample_docs/analytics_platform.txt",
    }
    for col, (label, path) in zip(sc, samples.items()):
        with col:
            if st.button(label, use_container_width=True):
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        st.session_state.requirements_text = f.read()
                    st.rerun()
                except FileNotFoundError:
                    st.markdown(f'<div class="warn-box">Sample file not found: {path}</div>', unsafe_allow_html=True)

    return requirements_text


# ══════════════════════════════════════════════════════════════════════════════
# GENERATION
# ══════════════════════════════════════════════════════════════════════════════
def run_generation(requirements_text: str) -> bool:
    gen = ArchitectureGenerator(api_key=GROQ_API_KEY)
    prog = st.progress(0)
    status = st.empty()

    def cb(msg, pct):
        prog.progress(pct)
        status.markdown(f"⏳ {msg}")

    t0 = time.time()
    result = gen.generate_architecture(requirements_text, progress_callback=cb)
    elapsed = time.time() - t0

    prog.progress(100)
    if result["success"]:
        status.markdown(f"✅ Completed in {elapsed:.1f}s")
        st.session_state.architecture_data = result["data"]
        st.session_state.generation_complete = True
        issues = gen.validate_architecture(result["data"])
        if issues:
            st.markdown(
                f'<div class="warn-box">Some sections came back incomplete: {", ".join(issues[:3])}. '
                f'You can try regenerating for a fuller result.</div>',
                unsafe_allow_html=True,
            )
        time.sleep(0.4)
        prog.empty()
        status.empty()
        return True
    else:
        prog.empty()
        status.empty()
        st.markdown(f'<div class="error-box">{result["error"]}</div>', unsafe_allow_html=True)
        return False


# ══════════════════════════════════════════════════════════════════════════════
# RESULTS TABS
# ══════════════════════════════════════════════════════════════════════════════
def render_results(arch: dict):
    tabs = st.tabs([
        "🏗️ Overview", "🔧 Components", "📊 Diagrams",
        "🗄️ Database", "🔌 API", "💻 Tech Stack",
        "⚠️ Conflicts", "🔒 Security", "🤖 AI Chat",
    ])

    # ── OVERVIEW ─────────────────────────────────────────────────────────────
    with tabs[0]:
        st.markdown('<div class="sec-hdr">Project Overview</div>', unsafe_allow_html=True)

        summary = arch.get("project_summary", "N/A")
        st.markdown(
            f'<div style="background:#ffffff;border:1px solid #e2e8f0;border-radius:10px;'
            f'padding:18px;margin-bottom:18px;color:#334155;line-height:1.6">{summary}</div>',
            unsafe_allow_html=True,
        )

        arch_type = arch.get("architecture_type", "N/A")
        arch_desc = arch.get("recommended_architecture", "N/A")
        c1, c2 = st.columns([1, 2])
        with c1:
            st.markdown(
                f'<div style="background:#eef2ff;border:2px solid #4f46e5;border-radius:10px;'
                f'padding:18px;text-align:center">'
                f'<div style="font-size:.72rem;color:#4338ca;text-transform:uppercase;margin-bottom:6px">Pattern</div>'
                f'<div style="font-size:1.5rem;font-weight:800;color:#4338ca;text-transform:capitalize">'
                f'{arch_type.replace("-", " ")}</div></div>',
                unsafe_allow_html=True,
            )
        with c2:
            st.markdown(
                f'<div style="background:#ffffff;border:1px solid #e2e8f0;border-radius:10px;'
                f'padding:18px;color:#334155;font-size:.88rem;line-height:1.6">{arch_desc}</div>',
                unsafe_allow_html=True,
            )

        mvs = arch.get("microservices_vs_monolithic", {})
        if isinstance(mvs, dict) and mvs:
            st.markdown("---")
            st.markdown('<div class="sec-hdr">Microservices vs Monolithic</div>', unsafe_allow_html=True)
            rec = mvs.get("recommendation", "N/A")
            jus = mvs.get("justification", "")
            st.markdown(
                f'<div style="background:#f0fdf4;border:1px solid #86efac;border-radius:8px;'
                f'padding:14px;margin-bottom:14px"><span style="font-weight:700;color:#15803d">'
                f'Recommendation: </span><span style="color:#166534;text-transform:capitalize">'
                f'{rec.replace("_", " ")}</span>'
                f'<div style="color:#15803d;margin-top:6px;font-size:.88rem">{jus}</div></div>',
                unsafe_allow_html=True,
            )
            cc1, cc2 = st.columns(2)
            with cc1:
                with st.expander("Microservices Pros"):
                    for p in mvs.get("microservices_pros", []):
                        st.markdown(f"- {p}")
                with st.expander("Microservices Cons"):
                    for p in mvs.get("microservices_cons", []):
                        st.markdown(f"- {p}")
            with cc2:
                with st.expander("Monolithic Pros"):
                    for p in mvs.get("monolithic_pros", []):
                        st.markdown(f"- {p}")
                with st.expander("Monolithic Cons"):
                    for p in mvs.get("monolithic_cons", []):
                        st.markdown(f"- {p}")

        st.markdown("---")
        c1, c2 = st.columns(2)
        with c1:
            st.markdown('<div class="sec-hdr">Functional Requirements</div>', unsafe_allow_html=True)
            for r in arch.get("functional_requirements", []):
                st.markdown(f'<div class="req-item">{r}</div>', unsafe_allow_html=True)
        with c2:
            st.markdown('<div class="sec-hdr">Non-Functional Requirements</div>', unsafe_allow_html=True)
            for r in arch.get("non_functional_requirements", []):
                st.markdown(f'<div class="req-item" style="border-left-color:#a855f7">{r}</div>', unsafe_allow_html=True)

        st.markdown("---")
        st.markdown('<div class="sec-hdr">Scalability Recommendations</div>', unsafe_allow_html=True)
        for r in arch.get("scalability_recommendations", []):
            st.markdown(
                f'<div style="background:#ffffff;border:1px solid #e2e8f0;border-left:3px solid #0891b2;'
                f'padding:8px 13px;margin-bottom:6px;border-radius:0 8px 8px 0;color:#334155;font-size:.88rem">{r}</div>',
                unsafe_allow_html=True,
            )

        cost = arch.get("cost_estimation", {})
        if isinstance(cost, dict) and cost:
            st.markdown("---")
            st.markdown('<div class="sec-hdr">Cost Estimation</div>', unsafe_allow_html=True)
            monthly = cost.get("monthly_estimate", {})
            if monthly:
                scale_colors = {"small_scale": "#16a34a", "medium_scale": "#d97706", "large_scale": "#dc2626"}
                cols = st.columns(len(monthly))
                for col, (scale, est) in zip(cols, monthly.items()):
                    col.markdown(
                        f'<div class="metric-card"><div class="metric-value" style="font-size:1.2rem;'
                        f'color:{scale_colors.get(scale, "#4f46e5")}">{est}</div>'
                        f'<div class="metric-label">{scale.replace("_", " ").title()}</div></div>',
                        unsafe_allow_html=True,
                    )
            drivers = cost.get("major_cost_drivers", [])
            tips = cost.get("optimization_tips", [])
            if drivers or tips:
                dc1, dc2 = st.columns(2)
                with dc1:
                    if drivers:
                        st.markdown("**Major Cost Drivers**")
                        for d in drivers:
                            st.markdown(f"- {d}")
                with dc2:
                    if tips:
                        st.markdown("**Optimization Tips**")
                        for t in tips:
                            st.markdown(f"- {t}")

    # ── COMPONENTS ────────────────────────────────────────────────────────────
    with tabs[1]:
        st.markdown('<div class="sec-hdr">System Components</div>', unsafe_allow_html=True)
        components = arch.get("components", [])
        if not components:
            st.markdown('<div class="info-box">No components were defined.</div>', unsafe_allow_html=True)
        else:
            types_list = sorted(set(c.get("type", "service").lower() for c in components if isinstance(c, dict)))
            sel = st.multiselect("Filter by type", types_list, default=types_list)
            for comp in [c for c in components if isinstance(c, dict) and c.get("type", "service").lower() in sel]:
                with st.expander(f"{comp.get('name', '?')} — {comp.get('type', '').title()} · {comp.get('technology', 'N/A')}"):
                    cc1, cc2 = st.columns([2, 1])
                    with cc1:
                        st.markdown(f"**Description:** {comp.get('description', 'N/A')}")
                        resps = comp.get("responsibilities", [])
                        if resps:
                            st.markdown("**Responsibilities:**")
                            for r in resps:
                                st.markdown(f"- {r}")
                    with cc2:
                        st.markdown(f"**Type:** `{comp.get('type', 'N/A')}`")
                        st.markdown(f"**Technology:** `{comp.get('technology', 'N/A')}`")
                        deps = comp.get("dependencies", [])
                        if deps:
                            st.markdown("**Depends on:**")
                            for d in deps:
                                st.markdown(f"- `{d}`")

        deploy = arch.get("deployment_architecture", {})
        if isinstance(deploy, dict) and deploy:
            st.markdown("---")
            st.markdown('<div class="sec-hdr">Deployment Architecture</div>', unsafe_allow_html=True)
            c1, c2, c3 = st.columns(3)
            c1.metric("Strategy", deploy.get("strategy", "N/A"))
            c2.metric("Cloud Provider", deploy.get("cloud_provider", "N/A"))
            c3.metric("Environments", len(deploy.get("environments", [])))
            st.markdown(f"**Scaling strategy:** {deploy.get('scaling_strategy', 'N/A')}")
            infra = deploy.get("infrastructure", [])
            if infra:
                import pandas as pd
                rows = [{"Component": i.get("component", "N/A"), "Service": i.get("service", "N/A"),
                         "Sizing": i.get("sizing", "N/A")} for i in infra if isinstance(i, dict)]
                if rows:
                    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    # ── DIAGRAMS ──────────────────────────────────────────────────────────────
    with tabs[2]:
        st.markdown('<div class="sec-hdr">Architecture Diagrams</div>', unsafe_allow_html=True)
        diagrams = arch.get("mermaid_diagrams", {})
        if not diagrams:
            st.markdown('<div class="info-box">No diagrams were generated.</div>', unsafe_allow_html=True)
        else:
            opts = {DIAGRAM_TYPES.get(k, k): k for k in diagrams}
            sel_name = st.selectbox("Select diagram", list(opts.keys()))
            sel_key = opts[sel_name]
            code = diagrams[sel_key]
            valid, err = validate_mermaid_syntax(code)
            if valid:
                st.components.v1.html(render_mermaid_html(code, sel_key), height=480, scrolling=True)
                with st.expander("View Mermaid Code"):
                    cleaned = clean_mermaid_code(code)
                    st.code(cleaned, language="text")
                    st.download_button("Download diagram", f"```mermaid\n{cleaned}\n```",
                                       f"{sel_key}.md", "text/markdown", key=f"dl_{sel_key}")
            else:
                st.markdown(f'<div class="error-box">Diagram could not be rendered: {err}</div>', unsafe_allow_html=True)
                st.code(code, language="text")

            st.markdown("---")
            st.markdown("**All diagrams**")
            cols = st.columns(2)
            for i, (k, c) in enumerate(diagrams.items()):
                with cols[i % 2]:
                    st.markdown(f"**{DIAGRAM_TYPES.get(k, k)}**")
                    v, _ = validate_mermaid_syntax(c)
                    if v:
                        st.components.v1.html(render_mermaid_html(c, f"mini_{k}"), height=260, scrolling=True)
                    else:
                        st.code(clean_mermaid_code(c), language="text")

    # ── DATABASE ──────────────────────────────────────────────────────────────
    with tabs[3]:
        st.markdown('<div class="sec-hdr">Database Design</div>', unsafe_allow_html=True)
        db = arch.get("database_design", {})
        if isinstance(db, str):
            st.markdown(db)
        elif isinstance(db, dict):
            pri = db.get("primary_database", {})
            if isinstance(pri, dict):
                c1, c2, c3 = st.columns(3)
                c1.metric("Technology", pri.get("technology", "N/A"))
                c2.metric("Type", pri.get("type", "N/A"))
                c3.metric("Entities", len(pri.get("entities", [])))
                st.markdown(f"**Justification:** {pri.get('justification', 'N/A')}")
                entities = pri.get("entities", [])
                if entities:
                    st.markdown("**Entities**")
                    ecols = st.columns(min(3, max(1, len(entities))))
                    for i, ent in enumerate(entities):
                        if isinstance(ent, dict):
                            with ecols[i % len(ecols)]:
                                with st.expander(ent.get("name", "?")):
                                    for f in ent.get("fields", []):
                                        if ":" in f:
                                            p = f.split(":")
                                            st.markdown(f"- `{p[0]}` : *{p[1]}*")
                                        else:
                                            st.markdown(f"- `{f}`")
                                    for r in ent.get("relationships", []):
                                        st.markdown(f"→ {r}")

                    st.markdown("---")
                    st.markdown("**Entity Relationship Diagram**")
                    er_code = generate_er_diagram(entities)
                    v, _ = validate_mermaid_syntax(er_code)
                    if v:
                        st.components.v1.html(render_mermaid_html(er_code, "er_diag"), height=360, scrolling=True)

            sec_dbs = db.get("secondary_databases", [])
            if sec_dbs:
                st.markdown("---")
                st.markdown("**Secondary Databases**")
                for d in sec_dbs:
                    if isinstance(d, dict):
                        st.markdown(
                            f'<div style="background:#ffffff;border:1px solid #e2e8f0;border-radius:8px;'
                            f'padding:12px;margin-bottom:8px"><span style="font-weight:700;color:#7c3aed">'
                            f'{d.get("purpose", "N/A")}</span> → <span style="color:#4f46e5;font-weight:600">'
                            f'{d.get("technology", "N/A")}</span>'
                            f'<div style="color:#64748b;font-size:.84rem;margin-top:5px">{d.get("justification", "")}</div></div>',
                            unsafe_allow_html=True,
                        )

    # ── API ───────────────────────────────────────────────────────────────────
    with tabs[4]:
        st.markdown('<div class="sec-hdr">API Design</div>', unsafe_allow_html=True)
        api = arch.get("api_design", {})
        if isinstance(api, str):
            st.markdown(api)
        elif isinstance(api, dict):
            c1, c2, c3 = st.columns(3)
            c1.metric("Style", api.get("style", "N/A"))
            c2.metric("Auth", api.get("authentication", "N/A"))
            c3.metric("Versioning", api.get("versioning_strategy", "N/A"))
            eps = api.get("endpoints", [])
            if eps:
                st.markdown("---")
                st.markdown("**Endpoints**")
                method_colors = {"GET": "#0891b2", "POST": "#16a34a", "PUT": "#d97706", "PATCH": "#ea580c", "DELETE": "#dc2626"}
                for ep in eps:
                    if isinstance(ep, dict):
                        mhtml = " ".join(
                            f'<span style="background:{method_colors.get(m, "#4f46e5")}1a;'
                            f'color:{method_colors.get(m, "#4f46e5")};border:1px solid {method_colors.get(m, "#4f46e5")}55;'
                            f'padding:2px 7px;border-radius:4px;font-size:.72rem;font-weight:700">{m}</span>'
                            for m in ep.get("methods", [])
                        )
                        auth_b = ('<span style="background:#f0fdf4;color:#16a34a;border:1px solid #86efac;'
                                  'padding:2px 7px;border-radius:4px;font-size:.72rem">Auth required</span>'
                                  if ep.get("auth_required") else
                                  '<span style="background:#f8fafc;color:#64748b;border:1px solid #e2e8f0;'
                                  'padding:2px 7px;border-radius:4px;font-size:.72rem">Public</span>')
                        st.markdown(
                            f'<div style="background:#ffffff;border:1px solid #e2e8f0;border-radius:8px;'
                            f'padding:12px;margin-bottom:8px"><div style="display:flex;align-items:center;'
                            f'gap:8px;flex-wrap:wrap"><code style="color:#1e293b">{ep.get("resource", "N/A")}</code>'
                            f'{mhtml}{auth_b}</div>'
                            f'<div style="color:#64748b;font-size:.84rem;margin-top:7px">{ep.get("description", "")}</div></div>',
                            unsafe_allow_html=True,
                        )

    # ── TECH STACK ────────────────────────────────────────────────────────────
    with tabs[5]:
        st.markdown('<div class="sec-hdr">Technology Stack</div>', unsafe_allow_html=True)
        ts = arch.get("tech_stack_recommendations", [])
        if not ts:
            st.markdown('<div class="info-box">No tech stack recommendations were generated.</div>', unsafe_allow_html=True)
        else:
            layers = {}
            for t in ts:
                if isinstance(t, dict):
                    layers.setdefault(t.get("layer", "Other"), []).append(t)

            for layer, techs in layers.items():
                st.markdown(f"**{layer}**")
                tcols = st.columns(min(3, len(techs)))
                for i, t in enumerate(techs):
                    with tcols[i % min(3, len(techs))]:
                        alts = ", ".join(t.get("alternatives", []))
                        jus = t.get("justification", "")
                        jus_short = jus[:75] + "..." if len(jus) > 75 else jus
                        st.markdown(
                            f'<div style="background:#ffffff;border:1px solid #e2e8f0;border-radius:10px;'
                            f'padding:14px;margin-bottom:10px;min-height:128px">'
                            f'<div style="font-size:1rem;font-weight:700;color:#4f46e5">{t.get("technology", "N/A")}</div>'
                            f'<div style="font-size:.75rem;color:#94a3b8;margin-bottom:7px">v{t.get("version", "latest")}</div>'
                            f'<div style="font-size:.83rem;color:#475569;line-height:1.4">{jus_short}</div>'
                            f'{"<div style=\"font-size:.72rem;color:#94a3b8;margin-top:6px\">Alt: " + alts + "</div>" if alts else ""}'
                            f'</div>',
                            unsafe_allow_html=True,
                        )

            with st.expander("View as table"):
                import pandas as pd
                rows = [{"Layer": t.get("layer"), "Technology": t.get("technology"), "Version": t.get("version"),
                         "Justification": t.get("justification", ""), "Alternatives": ", ".join(t.get("alternatives", []))}
                        for t in ts if isinstance(t, dict)]
                if rows:
                    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    # ── CONFLICTS ─────────────────────────────────────────────────────────────
    with tabs[6]:
        st.markdown('<div class="sec-hdr">Design Conflicts & Risks</div>', unsafe_allow_html=True)
        conflicts = arch.get("design_conflicts", [])
        if not conflicts:
            st.markdown('<div class="success-box">No significant conflicts detected.</div>', unsafe_allow_html=True)
        else:
            hi = [c for c in conflicts if isinstance(c, dict) and c.get("severity") == "high"]
            me = [c for c in conflicts if isinstance(c, dict) and c.get("severity") == "medium"]
            lo = [c for c in conflicts if isinstance(c, dict) and c.get("severity") == "low"]
            c1, c2, c3 = st.columns(3)
            for col, lst, lbl, color in [(c1, hi, "High Severity", "#dc2626"), (c2, me, "Medium Severity", "#d97706"), (c3, lo, "Low Severity", "#16a34a")]:
                col.markdown(
                    f'<div class="metric-card"><div class="metric-value" style="color:{color}">{len(lst)}</div>'
                    f'<div class="metric-label">{lbl}</div></div>',
                    unsafe_allow_html=True,
                )

            sev_filter = st.multiselect("Filter by severity", ["high", "medium", "low"], default=["high", "medium", "low"])
            sev_cfg = {
                "high": ("#dc2626", "#fef2f2", "#fca5a5"),
                "medium": ("#d97706", "#fffbeb", "#fcd34d"),
                "low": ("#16a34a", "#f0fdf4", "#86efac"),
            }
            for cf in conflicts:
                if not isinstance(cf, dict):
                    continue
                sev = cf.get("severity", "medium")
                if sev not in sev_filter:
                    continue
                tc, bg, bd = sev_cfg.get(sev, ("#1e293b", "#ffffff", "#e2e8f0"))
                ctype = cf.get("type", "issue").replace("_", " ").title()
                aff = ", ".join(cf.get("affected_components", []))
                st.markdown(
                    f'<div style="background:{bg};border:1px solid {bd};border-left:4px solid {tc};'
                    f'border-radius:8px;padding:14px;margin-bottom:10px">'
                    f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:8px">'
                    f'<span style="font-weight:700;color:{tc}">{ctype}</span>'
                    f'<span style="background:{tc}1a;color:{tc};padding:2px 9px;border-radius:20px;font-size:.72rem;font-weight:700">{sev.upper()}</span>'
                    f'</div><div style="color:#334155;font-size:.88rem;margin-bottom:8px">{cf.get("description", "N/A")}</div>'
                    f'{"<div style=\"color:#64748b;font-size:.8rem;margin-bottom:6px\">Affected: " + aff + "</div>" if aff else ""}'
                    f'<div style="background:#ffffffb0;border-radius:6px;padding:9px;border-left:3px solid {tc}">'
                    f'<span style="color:#64748b;font-size:.78rem">RECOMMENDATION: </span>'
                    f'<span style="color:#334155;font-size:.88rem">{cf.get("recommendation", "N/A")}</span></div></div>',
                    unsafe_allow_html=True,
                )

    # ── SECURITY ──────────────────────────────────────────────────────────────
    with tabs[7]:
        st.markdown('<div class="sec-hdr">Security Considerations</div>', unsafe_allow_html=True)
        security = arch.get("security_considerations", [])
        if not security:
            st.markdown('<div class="info-box">No security considerations were documented.</div>', unsafe_allow_html=True)
        else:
            risk_cfg = {"high": ("#dc2626", "#fef2f2"), "medium": ("#d97706", "#fffbeb"), "low": ("#16a34a", "#f0fdf4")}
            for s in security:
                if not isinstance(s, dict):
                    continue
                tc, bg = risk_cfg.get(s.get("risk_level", "medium"), ("#1e293b", "#ffffff"))
                st.markdown(
                    f'<div style="background:{bg};border:1px solid {tc}33;border-radius:8px;'
                    f'padding:14px;margin-bottom:10px">'
                    f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:7px">'
                    f'<span style="font-weight:700;color:{tc}">{s.get("area", "N/A")}</span>'
                    f'<span style="font-size:.72rem;color:{tc};background:{tc}1a;padding:2px 8px;border-radius:10px">'
                    f'{s.get("risk_level", "").upper()}</span></div>'
                    f'<div style="color:#334155;font-size:.88rem;margin-bottom:9px">{s.get("description", "N/A")}</div>'
                    f'<div style="background:#ffffffb0;border-radius:6px;padding:9px">'
                    f'<span style="color:#64748b;font-size:.78rem">MITIGATION: </span>'
                    f'<span style="color:#334155;font-size:.88rem">{s.get("mitigation", "N/A")}</span></div></div>',
                    unsafe_allow_html=True,
                )

    # ── AI CHAT ───────────────────────────────────────────────────────────────
    with tabs[8]:
        st.markdown('<div class="sec-hdr">Architecture Review Chatbot</div>', unsafe_allow_html=True)
        st.markdown("Ask anything about your generated architecture.")

        for msg in st.session_state.chat_history:
            is_user = msg["role"] == "user"
            bg = "#eef2ff" if is_user else "#ffffff"
            label = "You" if is_user else "AI Architect"
            st.markdown(
                f'<div style="background:{bg};border:1px solid #e2e8f0;border-radius:9px;'
                f'padding:11px 14px;margin-bottom:7px;line-height:1.5">'
                f'<span style="font-weight:700;color:#4f46e5">{label}</span>'
                f'<div style="margin-top:5px;color:#334155">{msg["content"]}</div></div>',
                unsafe_allow_html=True,
            )

        st.markdown("**Quick questions**")
        qs = [
            "What are the main scalability risks?",
            "How should I handle authentication?",
            "What monitoring do you recommend?",
            "What CI/CD pipeline fits this stack?",
            "How should I handle database migrations?",
            "Best way to handle service-to-service communication?",
        ]
        qcols = st.columns(3)
        for i, q in enumerate(qs):
            with qcols[i % 3]:
                if st.button(q, key=f"qq{i}", use_container_width=True):
                    st.session_state["_pending_q"] = q

        user_q = st.text_input("Ask the architect", key="chat_in",
                               placeholder="e.g. How should I structure the API gateway?",
                               label_visibility="collapsed")
        if "_pending_q" in st.session_state:
            user_q = st.session_state.pop("_pending_q")

        send_col, clear_col = st.columns([3, 1])
        with send_col:
            send = st.button("Send", key="send_chat", use_container_width=True)
        with clear_col:
            if st.button("Clear", key="clear_chat", use_container_width=True):
                st.session_state.chat_history = []
                st.rerun()

        if user_q and send:
            if not GROQ_API_KEY:
                st.markdown('<div class="error-box">Service not configured. Contact the administrator.</div>', unsafe_allow_html=True)
            else:
                with st.spinner("Thinking..."):
                    st.session_state.chat_history.append({"role": "user", "content": user_q})
                    gen = ArchitectureGenerator(api_key=GROQ_API_KEY)
                    resp = gen.chat_with_architect(json.dumps(arch, indent=2)[:6000], user_q)
                    st.session_state.chat_history.append({"role": "assistant", "content": resp})
                st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════
def main():
    render_sidebar()

    if not st.session_state.generation_complete:
        req_text = render_input()

        st.markdown("---")
        _, btn_col, _ = st.columns([1, 2, 1])
        with btn_col:
            go = st.button("🚀 Generate Architecture",
                           disabled=not (req_text.strip() and GROQ_API_KEY),
                           use_container_width=True)

        if not GROQ_API_KEY:
            st.markdown(
                '<div class="error-box">This application is not yet configured with an API key. '
                'Please contact the administrator.</div>',
                unsafe_allow_html=True,
            )
        elif not req_text.strip():
            st.markdown('<div class="info-box">Upload a document or paste requirements above to get started.</div>',
                        unsafe_allow_html=True)

        if go and req_text.strip() and GROQ_API_KEY:
            st.session_state.requirements_text = req_text
            with st.spinner("Analyzing requirements..."):
                success = run_generation(req_text)
            if success:
                st.markdown('<div class="success-box">Architecture generated successfully.</div>', unsafe_allow_html=True)
                time.sleep(0.4)
                st.rerun()
    else:
        arch = st.session_state.architecture_data
        c1, c2 = st.columns([5, 1])
        with c1:
            st.markdown("### Architecture Analysis Results")
        with c2:
            if st.button("← New"):
                st.session_state.generation_complete = False
                st.session_state.architecture_data = None
                st.rerun()

        if arch:
            render_results(arch)
        else:
            st.markdown('<div class="error-box">Architecture data is missing. Please regenerate.</div>', unsafe_allow_html=True)
            if st.button("← Back"):
                st.session_state.generation_complete = False
                st.rerun()


if __name__ == "__main__":
    main()

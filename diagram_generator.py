"""
diagram_generator.py
--------------------
Handles Mermaid diagram cleanup, validation, and HTML rendering.
Rendering uses the Mermaid CDN inside an isolated HTML component,
themed to match the app's light UI.
"""

import re


# Mermaid diagram keys and their display names
DIAGRAM_TYPES = {
    "system_architecture": "System Architecture",
    "component_diagram": "Component Diagram",
    "data_flow": "Data Flow Diagram",
    "deployment": "Deployment Architecture",
    "sequence": "Sequence Diagram",
}


def clean_mermaid_code(code: str) -> str:
    """Clean and normalize Mermaid diagram code returned by the LLM."""
    if not code:
        return "graph TD\n    A[No diagram available]"

    code = re.sub(r"^```(?:mermaid)?\s*\n?", "", code.strip())
    code = re.sub(r"\n?```\s*$", "", code)

    # Literal \n inside JSON strings becomes real newlines here
    code = code.replace("\\n", "\n")

    lines = [line for line in code.split("\n") if line.strip()]
    result = "\n".join(lines)

    valid_starts = [
        "graph", "flowchart", "sequenceDiagram", "classDiagram",
        "erDiagram", "gantt", "stateDiagram", "pie", "gitGraph",
        "C4Context", "mindmap", "timeline",
    ]

    if not any(result.strip().startswith(s) for s in valid_starts):
        if "participant" in result.lower() or "->>" in result:
            result = "sequenceDiagram\n" + result
        else:
            result = "graph TD\n" + result

    return result


def validate_mermaid_syntax(code: str) -> tuple[bool, str]:
    """
    Structural validation of Mermaid code before rendering.

    This checks the RAW input (after fence/whitespace stripping only, not after
    clean_mermaid_code's auto-prefixing) so that genuinely unrecognized content
    is rejected rather than silently accepted because a "graph TD" header was
    bolted onto it.
    """
    if not code or not code.strip():
        return False, "Empty diagram code"

    # Strip fences/whitespace the same way clean_mermaid_code does, but WITHOUT
    # applying the auto-prefix fallback, so we can judge the real content.
    raw = re.sub(r"^```(?:mermaid)?\s*\n?", "", code.strip())
    raw = re.sub(r"\n?```\s*$", "", raw)
    raw = raw.replace("\\n", "\n").strip()

    valid_starts = [
        "graph", "flowchart", "sequenceDiagram", "classDiagram",
        "erDiagram", "gantt", "stateDiagram", "pie", "gitGraph",
        "mindmap", "timeline", "C4Context",
    ]
    # Signals that this is a recognizable diagram BODY even without an explicit
    # header line (e.g. a sequence diagram fragment starting with "participant")
    body_signals = ["participant ", "-->>", "->>", "-->", "->", "[", "{", "|"]

    has_header = any(raw.startswith(s) for s in valid_starts)
    has_body_signal = any(sig in raw for sig in body_signals)

    if not has_header and not has_body_signal:
        first_word = raw.split()[0] if raw.split() else ""
        return False, f"Unrecognized diagram content (starts with '{first_word}')"

    # Content looks like a real diagram (or a valid body fragment) - now run it
    # through the full cleanup (which applies the header auto-prefix if needed)
    # and make sure there's enough actual content to render.
    cleaned = clean_mermaid_code(code)
    lines = [l for l in cleaned.split("\n") if l.strip()]
    if len(lines) < 2:
        return False, "Diagram has insufficient content"

    return True, ""


def render_mermaid_html(mermaid_code: str, diagram_id: str = "diagram") -> str:
    """
    Generate self-contained HTML that renders a Mermaid diagram via CDN,
    styled to match the app's light theme.
    """
    cleaned_code = clean_mermaid_code(mermaid_code)
    # Escape characters that would break the embedded <div> text content
    safe_code = cleaned_code.replace("</", "<\\/")

    html = f"""
<!DOCTYPE html>
<html>
<head>
    <script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
    <style>
        body {{
            margin: 0;
            padding: 14px;
            background: #ffffff;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            font-family: -apple-system, "Segoe UI", Roboto, sans-serif;
        }}
        .mermaid-container {{
            background: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 12px;
            padding: 22px;
            max-width: 100%;
            overflow-x: auto;
        }}
        .mermaid svg {{
            max-width: 100%;
        }}
    </style>
</head>
<body>
    <div class="mermaid-container">
        <div class="mermaid" id="{diagram_id}">
{safe_code}
        </div>
    </div>
    <script>
        mermaid.initialize({{
            startOnLoad: true,
            theme: 'base',
            themeVariables: {{
                darkMode: false,
                background: '#f8fafc',
                primaryColor: '#e0e7ff',
                primaryTextColor: '#1e293b',
                primaryBorderColor: '#6366f1',
                lineColor: '#94a3b8',
                secondaryColor: '#dbeafe',
                tertiaryColor: '#fef3c7',
                fontSize: '14px',
                nodeBorder: '#6366f1',
                clusterBkg: '#f1f5f9',
                clusterBorder: '#cbd5e1',
                edgeLabelBackground: '#ffffff'
            }},
            securityLevel: 'loose',
            flowchart: {{ curve: 'basis', padding: 20 }}
        }});
        mermaid.init(undefined, document.getElementById('{diagram_id}'));
    </script>
</body>
</html>
"""
    return html


def generate_er_diagram(entities: list) -> str:
    """Build a Mermaid erDiagram block from a list of entity dicts."""
    if not entities:
        return "erDiagram\n    NoEntities"

    lines = ["erDiagram"]
    for entity in entities:
        if not isinstance(entity, dict):
            continue
        name = re.sub(r"[^a-zA-Z0-9_]", "_", entity.get("name", "Entity"))
        lines.append(f"    {name} {{")
        for field in entity.get("fields", [])[:8]:
            if ":" in field:
                parts = field.split(":")
                field_name = re.sub(r"[^a-zA-Z0-9_]", "_", parts[0].strip())
                field_type = parts[1].strip().split("(")[0].strip() or "string"
                lines.append(f"        {field_type} {field_name}")
            else:
                field_name = re.sub(r"[^a-zA-Z0-9_]", "_", field.strip())
                lines.append(f"        string {field_name}")
        lines.append("    }")

    return "\n".join(lines)

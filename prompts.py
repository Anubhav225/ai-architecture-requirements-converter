"""
prompts.py
----------
All Groq LLM prompt templates for architecture generation.
"""

SYSTEM_PROMPT = """You are a Senior Software Architect with 20+ years of experience designing
large-scale enterprise software systems. You have deep expertise in microservices and
distributed systems, cloud-native architectures (AWS, GCP, Azure), database design
(SQL, NoSQL, NewSQL), API design (REST, GraphQL, gRPC), and security/DevOps practices.

Analyze software requirement documents and produce comprehensive, production-ready
architecture recommendations. You must respond with valid, parseable JSON only -
no markdown code fences, no commentary, no text before or after the JSON object."""


def get_architecture_prompt(requirements_text: str) -> str:
    """Build the main architecture analysis prompt sent to Groq."""
    return f"""Analyze the following software requirements and produce a comprehensive architecture design.

REQUIREMENTS DOCUMENT:
{requirements_text}

Return ONLY a valid JSON object with this exact structure (no markdown, no code fences, no extra text):

{{
  "project_summary": "2-3 sentence executive summary",

  "functional_requirements": [
    "FR-001: description", "FR-002: description"
  ],

  "non_functional_requirements": [
    "NFR-001: Performance - description", "NFR-002: Security - description"
  ],

  "recommended_architecture": "Detailed description of the recommended architecture pattern with justification",

  "architecture_type": "microservices|monolithic|serverless|event-driven|hybrid",

  "components": [
    {{
      "name": "Component Name",
      "type": "service|database|queue|cache|gateway|frontend|external",
      "description": "What this component does",
      "technology": "Specific technology",
      "responsibilities": ["responsibility 1", "responsibility 2"],
      "dependencies": ["other component names"]
    }}
  ],

  "database_design": {{
    "primary_database": {{
      "type": "relational|document|key-value|graph|time-series",
      "technology": "PostgreSQL|MongoDB|Redis|etc",
      "justification": "Why this was chosen",
      "entities": [
        {{
          "name": "EntityName",
          "fields": ["id:uuid", "name:string", "created_at:timestamp"],
          "relationships": ["has_many: OtherEntity"]
        }}
      ]
    }},
    "secondary_databases": [
      {{
        "purpose": "Caching|Search|Analytics",
        "technology": "Redis|Elasticsearch|etc",
        "justification": "Why needed"
      }}
    ]
  }},

  "api_design": {{
    "style": "REST|GraphQL|gRPC|hybrid",
    "versioning_strategy": "URL versioning /v1/",
    "authentication": "JWT|OAuth2|API Keys",
    "endpoints": [
      {{
        "resource": "/api/v1/resource",
        "methods": ["GET", "POST"],
        "description": "What this endpoint does",
        "auth_required": true
      }}
    ]
  }},

  "deployment_architecture": {{
    "strategy": "Kubernetes|Docker Compose|Serverless|PaaS",
    "cloud_provider": "AWS|GCP|Azure|Multi-cloud",
    "environments": ["development", "staging", "production"],
    "scaling_strategy": "Horizontal auto-scaling description",
    "infrastructure": [
      {{
        "component": "Component name",
        "service": "Cloud service (e.g. AWS EKS)",
        "sizing": "Instance type or resource allocation"
      }}
    ]
  }},

  "tech_stack_recommendations": [
    {{
      "layer": "Frontend|Backend|Database|Infrastructure|DevOps|Monitoring",
      "technology": "Technology name",
      "version": "Recommended version",
      "justification": "Why this technology",
      "alternatives": ["Alternative 1", "Alternative 2"]
    }}
  ],

  "design_conflicts": [
    {{
      "type": "ambiguity|missing_requirement|scalability|security|performance|incompatibility|architectural_risk",
      "severity": "high|medium|low",
      "description": "Clear description of the conflict",
      "affected_components": ["component1"],
      "recommendation": "How to resolve"
    }}
  ],

  "security_considerations": [
    {{
      "area": "Authentication|Authorization|Encryption|Network Security",
      "risk_level": "high|medium|low",
      "description": "Security consideration details",
      "mitigation": "Recommended mitigation"
    }}
  ],

  "scalability_recommendations": [
    "Specific actionable scalability recommendation"
  ],

  "cost_estimation": {{
    "monthly_estimate": {{
      "small_scale": "$X - $Y (0-1K users/day)",
      "medium_scale": "$X - $Y (1K-100K users/day)",
      "large_scale": "$X+ (100K+ users/day)"
    }},
    "major_cost_drivers": ["Cost component 1", "Cost component 2"],
    "optimization_tips": ["Tip 1", "Tip 2"]
  }},

  "mermaid_diagrams": {{
    "system_architecture": "graph TD\\n  A[User] --> B[Load Balancer]\\n  B --> C[API Gateway]\\n  C --> D[Service]\\n  D --> E[(Database)]",
    "component_diagram": "graph LR\\n  subgraph Frontend\\n    A[Web App]\\n  end\\n  subgraph Backend\\n    B[API Server]\\n  end\\n  A --> B",
    "data_flow": "sequenceDiagram\\n  participant U as User\\n  participant A as API\\n  participant D as Database\\n  U->>A: Request\\n  A->>D: Query\\n  D-->>A: Result\\n  A-->>U: Response",
    "deployment": "graph TD\\n  subgraph Cloud\\n    LB[Load Balancer]\\n    K8[Kubernetes Cluster]\\n    DB[(Managed Database)]\\n  end\\n  LB --> K8\\n  K8 --> DB",
    "sequence": "sequenceDiagram\\n  participant C as Client\\n  participant G as API Gateway\\n  participant S as Service\\n  participant D as Database\\n  C->>G: HTTP Request\\n  G->>S: Route\\n  S->>D: Query\\n  D-->>S: Data\\n  S-->>G: Response\\n  G-->>C: HTTP Response"
  }},

  "microservices_vs_monolithic": {{
    "recommendation": "microservices|monolithic|modular_monolith",
    "justification": "Detailed justification",
    "microservices_pros": ["Pro specific to this project"],
    "microservices_cons": ["Con specific to this project"],
    "monolithic_pros": ["Pro specific to this project"],
    "monolithic_cons": ["Con specific to this project"]
  }}
}}

IMPORTANT:
- Make diagrams specific to the actual requirements, using real component names
- Every list must contain at least 1 item; never return an empty array for a section that applies
- Return ONLY the JSON object, no other text whatsoever, no markdown fences
"""


def get_chatbot_prompt(architecture_json: str, user_question: str) -> str:
    """Build prompt for the architecture review chatbot."""
    return f"""You are an expert Software Architect reviewing this architecture design.

ARCHITECTURE:
{architecture_json}

QUESTION: {user_question}

Provide a detailed expert answer referencing specific components and decisions from this
architecture. Format your response in clear markdown with headers where appropriate.
Keep it focused and practical."""


def get_refinement_prompt(architecture_json: str, feedback: str) -> str:
    """Build prompt for refining an existing architecture based on feedback."""
    return f"""You are a Senior Software Architect. Refine this architecture based on the feedback.

CURRENT ARCHITECTURE:
{architecture_json}

FEEDBACK:
{feedback}

Return the complete updated architecture JSON with changes applied.
Maintain the exact same JSON structure. Return ONLY the JSON, no other text."""

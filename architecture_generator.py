"""
architecture_generator.py
--------------------------
Core module for generating architecture designs using the Groq API
(OpenAI-compatible chat completions, free tier, very low latency).
"""

import json
import time
import re
from typing import Optional

from groq import Groq, APIConnectionError, APIStatusError, AuthenticationError, RateLimitError

from prompts import SYSTEM_PROMPT, get_architecture_prompt, get_chatbot_prompt, get_refinement_prompt
from requirement_parser import truncate_for_api


# Groq production models, in priority order. If the first model errors
# (deprecated / decommissioned / overloaded) we automatically fall back.
MODEL_CANDIDATES = [
    "llama-3.3-70b-versatile",
    "openai/gpt-oss-120b",
    "llama-3.1-8b-instant",
]


class ArchitectureGenerator:
    """Generates software architecture designs using Groq-hosted LLMs."""

    def __init__(self, api_key: str):
        self.client = Groq(api_key=api_key)
        self.models = MODEL_CANDIDATES
        self.max_tokens = 8000

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def generate_architecture(self, requirements_text: str, progress_callback=None) -> dict:
        """Generate a complete architecture analysis from requirements text."""
        if progress_callback:
            progress_callback("Preparing requirements for analysis...", 10)

        processed_text = truncate_for_api(requirements_text)
        prompt = get_architecture_prompt(processed_text)

        if progress_callback:
            progress_callback("Sending to Groq AI for analysis...", 30)

        response_text = None
        try:
            response_text = self._call_groq(prompt, max_retries=3)

            if progress_callback:
                progress_callback("Parsing architecture response...", 70)

            architecture_data = self._parse_json_response(response_text)

            if progress_callback:
                progress_callback("Finalizing architecture design...", 90)

            return {"success": True, "data": architecture_data, "raw_response": response_text}

        except json.JSONDecodeError as e:
            return {
                "success": False,
                "error": f"The AI response could not be parsed as JSON ({str(e)}). Please try again.",
                "raw_response": response_text,
            }
        except AuthenticationError:
            return {
                "success": False,
                "error": "Invalid Groq API key. Check the key in your .env file. "
                         "Get a free key at https://console.groq.com/keys",
            }
        except RateLimitError:
            return {
                "success": False,
                "error": "Groq rate limit reached. Please wait about a minute and try again.",
            }
        except APIConnectionError:
            return {
                "success": False,
                "error": "Could not connect to Groq. Check your internet connection and try again.",
            }
        except APIStatusError as e:
            msg = getattr(e, "message", None) or str(e)
            return {"success": False, "error": f"Groq API error ({e.status_code}): {msg}"}
        except Exception as e:
            return {"success": False, "error": f"Unexpected error: {str(e)}"}

    def chat_with_architect(self, architecture_json: str, question: str) -> str:
        """Chat with the AI about a previously generated architecture."""
        prompt = get_chatbot_prompt(architecture_json, question)
        try:
            return self._call_groq(prompt, max_tokens=1800, json_mode=False)
        except AuthenticationError:
            return "Invalid Groq API key. Please check your .env configuration."
        except RateLimitError:
            return "Rate limit reached. Please wait a moment and try again."
        except Exception as e:
            return f"Error getting response: {str(e)}"

    def refine_architecture(self, architecture_json: str, feedback: str) -> dict:
        """Refine an existing architecture based on user feedback."""
        prompt = get_refinement_prompt(architecture_json, feedback)
        try:
            response_text = self._call_groq(prompt, max_retries=2)
            architecture_data = self._parse_json_response(response_text)
            return {"success": True, "data": architecture_data}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def validate_architecture(self, architecture: dict) -> list:
        """Return a list of missing or null required top-level fields."""
        required_fields = [
            "project_summary", "functional_requirements", "non_functional_requirements",
            "recommended_architecture", "components", "database_design",
            "tech_stack_recommendations", "design_conflicts", "mermaid_diagrams",
        ]
        issues = []
        for field in required_fields:
            if field not in architecture or architecture[field] is None:
                issues.append(f"Missing field: {field}")

        if "mermaid_diagrams" in architecture and isinstance(architecture["mermaid_diagrams"], dict):
            for diagram in ["system_architecture", "component_diagram", "data_flow", "deployment", "sequence"]:
                if diagram not in architecture["mermaid_diagrams"]:
                    issues.append(f"Missing diagram: {diagram}")
        return issues

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    def _call_groq(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        max_retries: int = 3,
        json_mode: bool = True,
    ) -> str:
        """
        Call the Groq chat completions endpoint with retry + model fallback.

        Tries each candidate model in order. Within a model, retries on
        rate limits / transient server errors with exponential backoff.
        """
        tokens = max_tokens or self.max_tokens
        last_error: Optional[Exception] = None

        for model in self.models:
            # use_json_mode toggles off automatically if a model rejects the
            # response_format parameter (some Groq models don't support it)
            use_json_mode = json_mode

            for attempt in range(max_retries):
                try:
                    kwargs = dict(
                        model=model,
                        messages=[
                            {"role": "system", "content": SYSTEM_PROMPT},
                            {"role": "user", "content": prompt},
                        ],
                        max_tokens=tokens,
                        temperature=0.3,
                    )
                    if use_json_mode:
                        kwargs["response_format"] = {"type": "json_object"}

                    completion = self.client.chat.completions.create(**kwargs)
                    content = completion.choices[0].message.content
                    if content and content.strip():
                        return content
                    # Empty content - treat as a failure for this attempt
                    last_error = RuntimeError(f"Empty response from model {model}")

                except RateLimitError as e:
                    last_error = e
                    if attempt < max_retries - 1:
                        time.sleep(2 ** attempt * 3)
                        continue
                    break  # move on to next model

                except AuthenticationError:
                    # Auth errors will not be fixed by retrying or switching models
                    raise

                except APIStatusError as e:
                    last_error = e
                    # If the model rejected response_format specifically, retry the
                    # SAME model once without json_mode before giving up on it
                    if use_json_mode and e.status_code in (400, 422):
                        use_json_mode = False
                        continue
                    # Other 400-class errors (model decommissioned, bad request)
                    # are not recoverable on this model - move to the next one
                    if e.status_code in (400, 404, 422):
                        break
                    if attempt < max_retries - 1:
                        time.sleep(3)
                        continue
                    break

                except APIConnectionError as e:
                    last_error = e
                    if attempt < max_retries - 1:
                        time.sleep(3)
                        continue
                    break

        # All models / retries exhausted
        if last_error:
            raise last_error
        raise RuntimeError("All Groq models failed to return a response.")

    def _parse_json_response(self, response_text: str) -> dict:
        """Parse JSON from the model's response, repairing common formatting issues."""
        if not response_text:
            raise json.JSONDecodeError("Empty response", "", 0)

        text = response_text.strip()

        # Strip markdown code fences if present
        text = re.sub(r"^```(?:json)?\s*\n?", "", text)
        text = re.sub(r"\n?```\s*$", "", text)
        text = text.strip()

        # Attempt direct parse
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Try to locate a JSON object within surrounding text
        match = re.search(r"\{[\s\S]*\}", text)
        if match:
            candidate = match.group()
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                # Try fixing trailing commas before re-attempting
                fixed = re.sub(r",(\s*[}\]])", r"\1", candidate)
                try:
                    return json.loads(fixed)
                except json.JSONDecodeError:
                    pass

        # Last attempt: fix trailing commas on the full text
        fixed_full = re.sub(r",(\s*[}\]])", r"\1", text)
        return json.loads(fixed_full)

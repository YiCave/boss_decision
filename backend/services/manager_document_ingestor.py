"""
Manager / chat document context: async extraction for decision routing.

Used by POST /api/analyze/upload only. Database ingestion uses services.document_service.DocumentIngestor.
"""
from __future__ import annotations

import argparse
import json
import mimetypes
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

from dotenv import load_dotenv

from services.llm_client import UnifiedLLMClient

try:
    from google import genai as google_genai
except Exception:  # pragma: no cover - optional runtime dependency
    google_genai = None

try:
    from docx import Document as DocxDocument
except Exception:  # pragma: no cover - optional runtime dependency
    DocxDocument = None


@dataclass
class DocumentServiceSettings:
    llm_model: str = "gemini-2.5-flash-lite"
    gemini_model: str = "gemini-2.5-flash-lite"
    llm_temperature: float = 0.2
    google_api_key: str | None = None


def load_document_settings() -> DocumentServiceSettings:
    backend_root = Path(__file__).resolve().parents[1]
    load_dotenv(dotenv_path=backend_root / ".env")

    temp_raw = os.getenv("LLM_TEMPERATURE", "0.2")
    try:
        temp = float(temp_raw)
    except ValueError:
        temp = 0.2

    return DocumentServiceSettings(
        llm_model=os.getenv("LLM_MODEL", "gemini-2.5-flash-lite"),
        gemini_model=os.getenv("DOCUMENT_GEMINI_MODEL", "gemini-2.5-flash-lite"),
        llm_temperature=temp,
        google_api_key=os.getenv("GOOGLE_API_KEY"),
    )


ALLOWED_EXTENSIONS = {
    ".pdf", ".doc", ".docx", ".txt", ".md", ".rtf", ".json", ".csv", ".log",
    ".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".tiff",
}


class ManagerDocumentIngestor:
    """Analyze uploaded files and emit structured routing context for the manager agent."""

    def __init__(self):
        self.settings = load_document_settings()
        self.llm_client = UnifiedLLMClient.from_settings()
        self.gemini_client = None
        if google_genai is not None and self.settings.google_api_key:
            try:
                self.gemini_client = google_genai.Client(api_key=self.settings.google_api_key)
            except Exception:
                self.gemini_client = None

    def _validate_file(self, file_path: str) -> Path:
        path = Path(file_path).expanduser().resolve()
        if not path.exists() or not path.is_file():
            raise FileNotFoundError(f"File not found: {path}")
        if path.suffix.lower() not in ALLOWED_EXTENSIONS:
            raise ValueError(f"Unsupported file extension: {path.suffix}")
        return path

    def _detect_mime(self, path: Path) -> str:
        guessed, _ = mimetypes.guess_type(str(path))
        return guessed or "application/octet-stream"

    def _read_text_payload(self, path: Path) -> str:
        ext = path.suffix.lower()

        if ext in {".txt", ".md", ".rtf", ".log", ".csv"}:
            return path.read_text(encoding="utf-8", errors="ignore")[:14000]

        if ext == ".json":
            raw = path.read_text(encoding="utf-8", errors="ignore")
            try:
                parsed = json.loads(raw)
                return json.dumps(parsed, indent=2, ensure_ascii=True)[:14000]
            except json.JSONDecodeError:
                return raw[:14000]

        if ext == ".docx" and DocxDocument is not None:
            try:
                doc = DocxDocument(str(path))
                combined = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
                return combined[:14000]
            except Exception:
                return ""

        # For binaries/images/PDF without OCR: keep metadata-only fallback.
        return ""

    @staticmethod
    def _heuristic_department(content: str, filename: str) -> str:
        haystack = f"{filename} {content}".lower()
        if any(k in haystack for k in ["employee", "termination", "payroll", "pip", "performance"]):
            return "HR"
        if any(k in haystack for k in ["campaign", "roi", "ad", "marketing"]):
            return "Marketing"
        if any(k in haystack for k in ["revenue", "pipeline", "deal", "sales"]):
            return "Sales"
        if any(k in haystack for k in ["invoice", "budget", "expense", "cashflow", "finance"]):
            return "Finance"
        if any(k in haystack for k in ["contract", "compliance", "policy", "legal"]):
            return "Legal"
        if any(k in haystack for k in ["logistics", "inventory", "supply", "operations"]):
            return "Operations"
        return "HR"

    @staticmethod
    def _compact_error(exc: Exception) -> str:
        text = str(exc).replace("\n", " ").strip()
        if len(text) > 180:
            return text[:180] + "..."
        return text

    @staticmethod
    def _parse_json_text(raw: Any) -> Dict[str, Any]:
        """Parse LLM JSON output. Accepts a raw string or an already-parsed dict."""
        # When response_mime_type=application/json the SDK may return a dict directly.
        if isinstance(raw, dict):
            return raw

        text = (raw or "").strip()
        if not text:
            raise ValueError("LLM returned empty content")

        if text.startswith("```"):
            text = text.strip("`")
            if text.lower().startswith("json"):
                text = text[4:].strip()

        if text.startswith("{") and text.endswith("}"):
            return json.loads(text)

        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(text[start : end + 1])

        raise ValueError("LLM output does not contain JSON object")

    def _build_prompt_payload(self, path: Path, content: str) -> tuple[dict[str, Any], str, str, str]:
        metadata = {
            "name": path.name,
            "extension": path.suffix.lower(),
            "size_bytes": path.stat().st_size,
            "mime_type": self._detect_mime(path),
        }
        default_department = self._heuristic_department(content, path.name)
        system_prompt = "You are an enterprise document classifier for manager-agent routing. Return strict JSON only."
        user_prompt = f"""
Analyze this uploaded file for business routing and summary.

File metadata:
{json.dumps(metadata)}

Extracted text sample (may be empty for binary/image files):
{content[:12000]}

Output JSON schema:
{{
  "document_type": "string",
  "department": "HR | Marketing | Sales | Finance | Legal | Operations",
  "confidence": 0.0,
  "summary": "short summary",
  "entities": [{{"type": "EntityType", "name": "name", "value": "optional", "role": "optional"}}],
  "tags": ["tag1", "tag2"],
  "relationships": [{{"source": "A", "target": "B", "type": "related_to", "confidence": 0.0}}]
}}
""".strip()
        return metadata, default_department, system_prompt, user_prompt

    @staticmethod
    def _is_textlike(path: Path) -> bool:
        return path.suffix.lower() in {".txt", ".md", ".rtf", ".log", ".csv", ".json", ".docx"}

    async def _analyze_with_gemini(
        self,
        *,
        path: Path,
        metadata: Dict[str, Any],
        content: str,
    ) -> Dict[str, Any]:
        if self.gemini_client is None or google_genai is None:
            raise RuntimeError("Gemini client unavailable")

        system_prompt = "You are an enterprise document classifier for manager-agent routing. Return strict JSON only."
        if self._is_textlike(path):
            body = f"""
Analyze this business document.

File metadata:
{json.dumps(metadata)}

Document text:
{content[:12000]}

Output JSON schema:
{{
  "document_type": "string",
  "department": "HR | Marketing | Sales | Finance | Legal | Operations",
  "confidence": 0.0,
  "summary": "short summary",
  "entities": [{{"type": "EntityType", "name": "name", "value": "optional", "role": "optional"}}],
  "tags": ["tag1", "tag2"],
  "relationships": [{{"source": "A", "target": "B", "type": "related_to", "confidence": 0.0}}]
}}
""".strip()
            full_prompt = (
                system_prompt
                + "\n\n"
                + body
            )
            response = await self.gemini_client.aio.models.generate_content(
                model=self.settings.gemini_model,
                contents=full_prompt,
                config=google_genai.types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=self.settings.llm_temperature,
                ),
            )
            # The SDK may expose parsed JSON via .parsed when mime_type=application/json.
            raw_response = getattr(response, "parsed", None) or response.text or ""
            parsed = self._parse_json_text(raw_response)
            parsed["provider"] = "gemini"
            parsed["model_used"] = self.settings.gemini_model
            return parsed

        mime_type = self._detect_mime(path)
        uploaded = await self.gemini_client.aio.files.upload(
            file=str(path),
            config={"mime_type": mime_type},
        )
        response = await self.gemini_client.aio.models.generate_content(
            model=self.settings.gemini_model,
            contents=[
                system_prompt,
                uploaded,
                "Return strict JSON with department, summary, entities, tags, relationships.",
            ],
            config=google_genai.types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=self.settings.llm_temperature,
            ),
        )
        parsed = self._parse_json_text(response.text or "")
        parsed["provider"] = "gemini"
        parsed["model_used"] = self.settings.gemini_model
        return parsed

    async def _analyze_with_unified_llm(
        self,
        *,
        metadata: Dict[str, Any],
        default_department: str,
        system_prompt: str,
        user_prompt: str,
    ) -> Dict[str, Any]:
        if not self.llm_client:
            raise RuntimeError("LLM client unavailable")

        parsed, model_used = await self.llm_client.acomplete_json(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=self.settings.llm_temperature,
            max_tokens=700,
        )
        parsed["provider"] = "unified_llm"
        parsed["model_used"] = model_used
        if not parsed.get("department"):
            parsed["department"] = default_department
        return parsed

    def _heuristic_payload(self, *, metadata: Dict[str, Any], default_department: str, reason: str) -> Dict[str, Any]:
        return {
            "document_type": metadata["extension"].lstrip(".") or "unknown",
            "department": default_department,
            "confidence": 0.5,
            "summary": f"LLM parse failed ({reason}). Heuristic classification applied.",
            "entities": [
                {"type": "File", "name": metadata["name"], "value": str(metadata["size_bytes"]), "role": "uploaded_artifact"}
            ],
            "tags": ["heuristic", "upload", "fallback"],
            "relationships": [],
            "provider": "heuristic",
            "metadata": metadata,
        }

    async def aprocess(self, file_path: str, knowledge_service: LocalKnowledgeService | None = None) -> Dict[str, Any]:
        path = Path(file_path).expanduser().resolve()
        
        # Handle directory ingestion if path is a folder
        if path.is_dir():
            results = []
            for sub_path in path.rglob("*"):
                if sub_path.is_file() and sub_path.suffix.lower() in ALLOWED_EXTENSIONS:
                    try:
                        res = await self.aprocess(str(sub_path), knowledge_service)
                        results.append(res)
                    except Exception as exc:
                        print(f"[ManagerDocumentIngestor] Failed to process {sub_path}: {exc}")
            
            # Aggregate folder results
            if not results:
                return {"summary": "Empty or unsupported folder.", "department": "Operations", "tags": ["empty"]}
            
            combined_summary = "\n".join([f"- {r.get('metadata', {}).get('name')}: {r.get('summary')}" for r in results[:5]])
            all_tags = set()
            for r in results:
                all_tags.update(r.get("tags", []))
            
            return {
                "document_type": "folder",
                "department": results[0].get("department", "Operations"), # Use first file's dept as hint
                "confidence": 0.8,
                "summary": f"Folder ingestion of {len(results)} files. Key contents:\n{combined_summary}",
                "tags": list(all_tags),
                "entities": [e for r in results for e in r.get("entities", [])][:20],
                "metadata": {"path": str(path), "file_count": len(results)}
            }

        content = self._read_text_payload(path)
        metadata, default_department, system_prompt, user_prompt = self._build_prompt_payload(path, content)
        
        # If knowledge service is provided, we can "dynamically read" or even cache
        if knowledge_service:
            knowledge_service.add_document(f"ingested_{path.name}", content)

        error_chain: list[str] = []

        if self.gemini_client is not None:
            try:
                parsed = await self._analyze_with_gemini(path=path, metadata=metadata, content=content)
                parsed["metadata"] = metadata
                if not parsed.get("department"):
                    parsed["department"] = default_department
                return parsed
            except Exception as exc:
                error_chain.append(f"gemini:{self._compact_error(exc)}")

        try:
            parsed = await self._analyze_with_unified_llm(
                metadata=metadata,
                default_department=default_department,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
            )
            parsed["metadata"] = metadata
            if not parsed.get("department"):
                parsed["department"] = default_department
            return parsed
        except Exception as exc:
            error_chain.append(f"unified_llm:{self._compact_error(exc)}")

        return self._heuristic_payload(
            metadata=metadata,
            default_department=default_department,
            reason=" | ".join(error_chain) if error_chain else "no llm provider available",
        )

    def process(self, file_path: str) -> Dict[str, Any]:
        """Synchronous helper for terminal workflows."""
        import asyncio

        return asyncio.run(self.aprocess(file_path))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Analyze uploaded document/image for routing context.")
    parser.add_argument("file", help="Path to file")
    args = parser.parse_args()

    ingestor = ManagerDocumentIngestor()
    result = ingestor.process(args.file)
    print(json.dumps(result, indent=2, ensure_ascii=True))

import time
import json
import argparse
from pathlib import Path
from typing import Dict, Any, Optional
import warnings
import os
import mimetypes
from dataclasses import dataclass
from dotenv import load_dotenv

try:
    # Document vision / multimodal client (google-genai)
    from google import genai as google_genai
    HAS_NEW_GENAI = True
except Exception:
    google_genai = None
    HAS_NEW_GENAI = False

legacy_genai = None

try:
    from config import get_settings
except ModuleNotFoundError:
    # Allows running this file directly: python services/document_service.py ...
    import sys
    sys.path.append(str(Path(__file__).resolve().parents[1]))
    from config import get_settings


@dataclass
class DocumentServiceSettings:
    google_api_key: Optional[str]
    llm_model: str = "gemini-2.5-flash-lite"
    llm_temperature: float = 0.7


def load_document_settings() -> DocumentServiceSettings:
    """Load only settings required for document ingestion.

    This keeps document testing independent from unrelated required fields
    in the main application settings (e.g., Supabase keys).
    """
    try:
        app_settings = get_settings()
        return DocumentServiceSettings(
            google_api_key=app_settings.google_api_key,
            llm_model=app_settings.llm_model,
            llm_temperature=app_settings.llm_temperature,
        )
    except Exception:
        # Fall back to direct env loading for standalone script usage.
        backend_root = Path(__file__).resolve().parents[1]
        load_dotenv(dotenv_path=backend_root / ".env")

        temp_raw = os.getenv("LLM_TEMPERATURE", "0.7")
        try:
            temp = float(temp_raw)
        except ValueError:
            temp = 0.7

        return DocumentServiceSettings(
            google_api_key=os.getenv("GOOGLE_API_KEY"),
            llm_model=os.getenv("LLM_MODEL", "gemini-2.5-flash-lite"),
            llm_temperature=temp,
        )


def _validate_google_api_key(api_key: Optional[str]) -> None:
    if not api_key or not api_key.strip():
        raise ValueError(
            "GOOGLE_API_KEY is missing. Add a valid key to backend/.env, then rerun."
        )

    normalized = api_key.strip()
    placeholder_markers = {
        "your_key_here",
        "replace_me",
        "changeme",
        "xxx",
    }
    if (
        normalized.lower() in placeholder_markers
        or "your" in normalized.lower() and "key" in normalized.lower()
    ):
        raise ValueError(
            "GOOGLE_API_KEY appears to be a placeholder. Set a valid key in backend/.env."
        )

ALLOWED_EXTENSIONS = {
    ".pdf", ".doc", ".docx", ".txt", ".md", ".rtf",
    ".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".tiff"
}

MIME_BY_EXTENSION = {
    ".pdf": "application/pdf",
    ".doc": "application/msword",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".txt": "text/plain",
    ".md": "text/markdown",
    ".rtf": "application/rtf",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".gif": "image/gif",
    ".bmp": "image/bmp",
    ".tiff": "image/tiff",
}

class DocumentIngestor:
    def __init__(self):
        # 1. Fetch settings from your config system
        self.settings = load_document_settings()
        _validate_google_api_key(self.settings.google_api_key)
        
        # 2. Configure the document vision client
        self._sdk = None
        self.model = None
        self.client = None

        if HAS_NEW_GENAI:
            self._sdk = "new"
            self.client = google_genai.Client(api_key=self.settings.google_api_key)
        else:
            # Fallback for older environments, imported lazily to avoid
            # deprecation warning when new SDK is available.
            global legacy_genai
            if legacy_genai is None:
                try:
                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore", FutureWarning)
                        import google.generativeai as _legacy_genai
                    legacy_genai = _legacy_genai
                except Exception:
                    legacy_genai = None

        if legacy_genai is not None and self._sdk is None:
            self._sdk = "legacy"
            legacy_genai.configure(api_key=self.settings.google_api_key)
            self.model = legacy_genai.GenerativeModel(model_name=self.settings.llm_model)
        elif self._sdk is None:
            raise ImportError(
                "No document vision client available. Install 'google-genai' or 'google-generativeai'."
            )

        self.extraction_prompt = """You are an enterprise document classification and information extraction system.

Your job:
1. Classify document with BOTH document_type AND department
2. Extract ALL structured business data you can see
3. Identify relationships between entities

=== CRITICAL: DOCUMENT_TYPE vs DEPARTMENT ===

DOCUMENT_TYPE = What the document IS (the format/template)
DEPARTMENT = Where it belongs organizationally

These are DIFFERENT! A payslip is document_type "Employee" but department "HR".

=== DOCUMENT TYPE (Use ONLY these exact values) ===

STRICTLY classify into ONE of these 9 types:

1. "HR Report" - Performance reviews, hiring reports, team evaluations
2. "Sales Log" - Sales deals, revenue tracking, customer deals
3. "Finance Report" - Financial statements, budgets, expense reports, invoices
4. "Marketing Report" - Campaign performance, ROI reports, ad metrics
5. "Supply Chain Log" - Inventory reports, procurement, vendor data
6. "Legal Policy" - Company policies, rules, regulations
7. "Legal Contract" - Employment contracts, vendor contracts, agreements
8. "Legal Case" - Employee legal issues, misconduct cases
9. "Employee" - INDIVIDUAL employee documents: payslips, offer letters, salary slips

=== CLASSIFICATION RULES (STRICT) ===

PAYSLIP / SALARY SLIP ΓåÆ document_type: "Employee", department: "HR"
   - Even if contains financial data, it's still document_type "Employee"
   - Payslips are NEVER "Finance Report"

PERFORMANCE REVIEW ΓåÆ document_type: "HR Report", department: "HR"

SALES DEAL/REVENUE ΓåÆ document_type: "Sales Log", department: "Sales"

BUDGET/INVOICE ΓåÆ document_type: "Finance Report", department: "Finance"

CAMPAIGN METRICS ΓåÆ document_type: "Marketing Report", department: "Marketing"

INVENTORY ΓåÆ document_type: "Supply Chain Log", department: "Operations"

=== EXAMPLES ===

CORRECT:
- "John Tan Payslip March 2026" ΓåÆ document_type: "Employee", department: "HR"
- "Salary Slip" ΓåÆ document_type: "Employee", department: "HR"
- "Q1 Performance Reviews" ΓåÆ document_type: "HR Report", department: "HR"
- "Monthly Sales Report" ΓåÆ document_type: "Sales Log", department: "Sales"

WRONG:
- "Payslip" ΓåÆ "Finance Report" (NO! It's "Employee")
- "Sales Manager Payslip" ΓåÆ "Sales Log" (NO! It's "Employee")

=== OUTPUT FORMAT (STRICT JSON) ===

{
  "document_type": "MUST be ONE of: HR Report | Sales Log | Finance Report | Marketing Report | Supply Chain Log | Legal Policy | Legal Contract | Legal Case | Employee",
  "department": "MUST be ONE of: HR | Sales | Finance | Marketing | Operations | Legal",
  "confidence": 0.95,
  "summary": "clear business summary",
  "entities": [
    {
      "type": "Employee | Campaign | Metric | Organization | Date | Amount",
      "name": "field name (e.g. employee_name, salary, period)",
      "value": "the actual extracted value",
      "role": "optional context"
    }
  ],
  "tags": ["relevant", "keywords"],
  "relationships": [
    {
      "source": "entity_name",
      "target": "entity_name",
      "type": "relationship_type",
      "confidence": 0.9
    }
  ]
}

=== EXTRACTION RULES ===

- Extract ALL visible data: employee names, dates, amounts, metrics
- For payslips: extract employee name, salary, period, attendance, deductions, bonuses
- Normalize numbers (no commas, use plain numbers: 10500 not 10,500)
- Keep entity names consistent
- Always provide at least 1 entity if you can read ANY data

Now analyze the provided document and return ONLY valid JSON."""

    def _detect_mime_type(self, file_path: str) -> str:
        guessed, _ = mimetypes.guess_type(file_path)
        if guessed:
            return guessed

        ext = Path(file_path).suffix.lower()
        mapped = MIME_BY_EXTENSION.get(ext)
        if mapped:
            return mapped

        raise ValueError(
            f"Unknown MIME type for '{file_path}'. Please use a supported file extension."
        )

    def _upload_and_wait(self, file_path: str):
        if self._sdk == "new":
            mime_type = self._detect_mime_type(file_path)
            print(f"    [DOCUMENT_SERVICE]     Detected MIME type: {mime_type}")
            
            uploaded = self.client.files.upload(
                file=file_path,
                config={"mime_type": mime_type},
            )
            name = getattr(uploaded, "name", None)
            if not name:
                return uploaded

            # Some file types require background processing before generation.
            print(f"    [DOCUMENT_SERVICE]     Waiting for file processing...")
            for attempt in range(30):
                current = self.client.files.get(name=name)
                state = getattr(current, "state", None)
                state_name = getattr(state, "name", str(state)) if state is not None else "ACTIVE"
                
                if state_name not in {"PROCESSING", "STATE_UNSPECIFIED"}:
                    print(f"    [DOCUMENT_SERVICE]     File processing completed (state: {state_name})")
                    return current
                    
                if attempt % 5 == 0 and attempt > 0:  # Log every 10 seconds
                    print(f"    [DOCUMENT_SERVICE]     Still processing... ({attempt * 2}s elapsed)")
                time.sleep(2)
            
            print(f"    [DOCUMENT_SERVICE]     File processing timeout, proceeding anyway...")
            return current

        print(f"    [DOCUMENT_SERVICE]     Using legacy document vision API path...")
        file = legacy_genai.upload_file(file_path)
        wait_count = 0
        while file.state.name == "PROCESSING":
            if wait_count % 5 == 0 and wait_count > 0:
                print(f"    [DOCUMENT_SERVICE]     Still processing... ({wait_count * 2}s elapsed)")
            time.sleep(2)
            file = legacy_genai.get_file(file.name)
            wait_count += 1
        
        print(f"    [DOCUMENT_SERVICE]     File ready (state: {file.state.name})")
        return file

    def _parse_json_response(self, text: str) -> Dict[str, Any]:
        text = (text or "").strip()
        if text.startswith("```"):
            text = text.strip("`")
            if text.lower().startswith("json"):
                text = text[4:].strip()
        return json.loads(text)

    def process(self, file_path: str) -> Dict[str, Any]:
        print(f"    [DOCUMENT_SERVICE] Starting document processing...")
        print(f"    [DOCUMENT_SERVICE] File path: {file_path}")
        
        try:
            file_ext = Path(file_path).suffix.lower()
            print(f"    [DOCUMENT_SERVICE] File extension: {file_ext}")
            
            # Determine file type for logging
            file_type = "IMAGE" if file_ext in {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".tiff"} else \
                        "PDF" if file_ext == ".pdf" else \
                        "DOCX" if file_ext == ".docx" else \
                        "TEXT"
            
            print(f"    [DOCUMENT_SERVICE] Processing as {file_type} using Zhipu GLM...")
            print(f"    [DOCUMENT_SERVICE] Uploading file to vision service...")
            
            uploaded_file = self._upload_and_wait(file_path)
            
            print(f"    [DOCUMENT_SERVICE] File uploaded successfully")
            print(f"    [DOCUMENT_SERVICE] Calling Zhipu GLM for extraction...")
            print(f"    [DOCUMENT_SERVICE] Vision extraction pipeline: active")

            if self._sdk == "new":
                response = self.client.models.generate_content(
                    model=self.settings.llm_model,
                    contents=[uploaded_file, self.extraction_prompt],
                    config=google_genai.types.GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=self.settings.llm_temperature,
                    ),
                )
            else:
                response = self.model.generate_content(
                    [uploaded_file, self.extraction_prompt],
                    generation_config={
                        "response_mime_type": "application/json",
                        "temperature": self.settings.llm_temperature
                    }
                )

            print(f"    [DOCUMENT_SERVICE] Zhipu GLM response received")
            print(f"    [DOCUMENT_SERVICE] Parsing JSON response...")
            
            # Show first 500 chars of raw response for debugging
            raw_text = response.text
            print(f"    [DOCUMENT_SERVICE] Raw AI response (first 500 chars):")
            print(f"    [DOCUMENT_SERVICE] {raw_text[:500]}")
            print()
            
            result = self._parse_json_response(raw_text)
            
            print(f"    [DOCUMENT_SERVICE] SUCCESS - Extraction completed")
            print(f"    [DOCUMENT_SERVICE] Document type: {result.get('document_type', 'Unknown')}")
            print(f"    [DOCUMENT_SERVICE] Department: {result.get('department', 'Unknown')}")
            print(f"    [DOCUMENT_SERVICE] Entities extracted: {len(result.get('entities', []))}")
            
            # If no entities, show warning
            if len(result.get('entities', [])) == 0:
                print(f"    [DOCUMENT_SERVICE] ΓÜá∩╕Å  WARNING: No entities extracted from document!")
                print(f"    [DOCUMENT_SERVICE]     This will result in NO_SQL_POSSIBLE")
                print(f"    [DOCUMENT_SERVICE]     Possible reasons:")
                print(f"    [DOCUMENT_SERVICE]     - Image quality too low to read")
                print(f"    [DOCUMENT_SERVICE]     - No structured data in the document")
                print(f"    [DOCUMENT_SERVICE]     - Document format not recognized by AI")
            else:
                print(f"    [DOCUMENT_SERVICE] Entities found:")
                for i, entity in enumerate(result.get('entities', [])[:5], 1):  # Show first 5
                    print(f"    [DOCUMENT_SERVICE]   {i}. {entity.get('type', 'N/A')}: {entity.get('name', 'N/A')} = {entity.get('value', 'N/A')}")
                if len(result.get('entities', [])) > 5:
                    print(f"    [DOCUMENT_SERVICE]   ... and {len(result.get('entities', [])) - 5} more")
            print()
            
            return result
            
        except Exception as e:
            print(f"    [DOCUMENT_SERVICE] FAILED - Zhipu GLM error: {str(e)}")
            print()
            raise Exception(f"Zhipu GLM extraction failed: {str(e)}")

# Example usage in your main app
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Upload a document/image and run AI extraction.")
    parser.add_argument(
        "file",
        help="Path to file (pdf/doc/docx/txt/md/rtf/png/jpg/jpeg/webp/gif/bmp/tiff)"
    )
    args = parser.parse_args()

    raw_path = Path(args.file).expanduser()
    backend_root = Path(__file__).resolve().parents[1]
    repo_root = backend_root.parent

    candidates = []
    if raw_path.is_absolute():
        candidates.append(raw_path)
    else:
        candidates.append(Path.cwd() / raw_path)
        candidates.append(backend_root / raw_path)
        candidates.append(repo_root / raw_path)

    file_path = next((p.resolve() for p in candidates if p.exists() and p.is_file()), None)
    if file_path is None:
        hint1 = (backend_root / "workplaces" / "documents").resolve()
        hint2 = (repo_root / "workplaces" / "documents").resolve()
        raise FileNotFoundError(
            f"File not found: {raw_path}. Try a valid path, e.g. '.\\workplaces\\documents\\...'. "
            f"Checked common locations: {hint1} and {hint2}."
        )
    if file_path.suffix.lower() not in ALLOWED_EXTENSIONS:
        allowed = ", ".join(sorted(ALLOWED_EXTENSIONS))
        raise ValueError(f"Unsupported file type '{file_path.suffix}'. Allowed: {allowed}")

    agent = DocumentIngestor()
    data = agent.process(str(file_path))
    print("\nParsed output:")
    print(json.dumps(data, indent=2))

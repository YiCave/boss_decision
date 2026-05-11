import time
import json
import argparse
import base64
from pathlib import Path
from typing import Dict, Any, Optional
import warnings
import os
import mimetypes
from dataclasses import dataclass
from dotenv import load_dotenv
from openai import OpenAI
import httpx

try:
    from config import get_settings
except ModuleNotFoundError:
    # Allows running this file directly: python services/document_service.py ...
    import sys
    sys.path.append(str(Path(__file__).resolve().parents[1]))
    from config import get_settings


@dataclass
class DocumentServiceSettings:
    zhipu_api_key: Optional[str]
    zhipu_base_url: str = "https://api.ilmu.ai/v1"
    zhipu_model: str = "nemo-super"
    llm_temperature: float = 0.7


def load_document_settings() -> DocumentServiceSettings:
    """Load only settings required for document ingestion."""
    try:
        app_settings = get_settings()
        return DocumentServiceSettings(
            zhipu_api_key=app_settings.zhipu_api_key,
            zhipu_base_url=app_settings.zhipu_base_url,
            zhipu_model=app_settings.zhipu_model,
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
            zhipu_api_key=os.getenv("ZHIPU_API_KEY"),
            zhipu_base_url=os.getenv("ZHIPU_BASE_URL", "https://api.ilmu.ai/v1"),
            zhipu_model=os.getenv("ZHIPU_MODEL", "nemo-super"),
            llm_temperature=temp,
        )


def _validate_zhipu_api_key(api_key: Optional[str]) -> None:
    if not api_key or not api_key.strip():
        raise ValueError(
            "ZHIPU_API_KEY is missing. Add a valid key to backend/.env, then rerun."
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
            "ZHIPU_API_KEY appears to be a placeholder. Set your real Zhipu API key in backend/.env."
        )

ALLOWED_EXTENSIONS = {
    ".pdf", ".doc", ".docx", ".txt", ".md", ".rtf",
    ".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".tiff", ".xlsx", ".csv"
}

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".tiff"}
TEXT_EXTENSIONS = {".txt", ".md", ".csv"}

MIME_BY_EXTENSION = {
    ".pdf": "application/pdf",
    ".doc": "application/msword",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".txt": "text/plain",
    ".md": "text/markdown",
    ".rtf": "application/rtf",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".csv": "text/csv",
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
        # Fetch settings from config
        self.settings = load_document_settings()
        _validate_zhipu_api_key(self.settings.zhipu_api_key)
        
        # Initialize Zhipu AI client (OpenAI-compatible) with longer timeout
        # Use httpx client with custom timeout (120 seconds for vision models)
        http_client = httpx.Client(
            timeout=httpx.Timeout(120.0, connect=30.0),  # 120s total, 30s connect
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
        )
        
        self.client = OpenAI(
            api_key=self.settings.zhipu_api_key,
            base_url=self.settings.zhipu_base_url,
            http_client=http_client,
            max_retries=3  # Retry up to 3 times on failure
        )

        self.extraction_prompt = """You are an enterprise document classification and information extraction system.

CRITICAL INSTRUCTIONS:
1. READ THE ENTIRE DOCUMENT CAREFULLY - extract ALL visible data
2. Classify the document type AND department
3. Extract EVERY piece of structured data you can see
4. Create entities for: employee names, dates, amounts, metrics, organizations

=== CRITICAL: DOCUMENT_TYPE vs DEPARTMENT ===

DOCUMENT_TYPE = What the document IS (the format/template)
DEPARTMENT = Where it belongs organizationally

These are DIFFERENT! A payslip is document_type "Employee" but department "HR".

=== DOCUMENT TYPE RESTRICTIONS (Use ONLY these exact values) ===

STRICTLY classify into ONE of these 9 types:

1. "HR Report" - Performance reviews, hiring reports, team evaluations, workforce analytics
2. "Sales Log" - Sales deals, revenue tracking, customer deals, pipeline reports  
3. "Finance Report" - Financial statements, budgets, expense reports, profit/loss, invoices
4. "Marketing Report" - Campaign performance, ROI reports, ad metrics, marketing analytics
5. "Supply Chain Log" - Inventory reports, procurement, vendor data, supply status
6. "Legal Policy" - Company policies, rules, regulations, compliance guidelines
7. "Legal Contract" - Employment contracts, vendor contracts, agreements
8. "Legal Case" - Employee legal issues, misconduct cases, disputes
9. "Employee" - INDIVIDUAL employee documents: payslips, offer letters, personal benefits, salary slips

=== CLASSIFICATION RULES (STRICT) ===

🔴 PAYSLIP / SALARY SLIP → document_type: "Employee", department: "HR"
   - Even if from "Finance Manager", it's still document_type "Employee"
   - Payslips are NEVER "Finance Report"

🔴 PERFORMANCE REVIEW → document_type: "HR Report", department: "HR"

🔴 SALES DEAL/REVENUE → document_type: "Sales Log", department: "Sales"

🔴 BUDGET/INVOICE/FINANCIAL STATEMENT → document_type: "Finance Report", department: "Finance"

🔴 CAMPAIGN METRICS/ROI → document_type: "Marketing Report", department: "Marketing"

🔴 INVENTORY/PROCUREMENT → document_type: "Supply Chain Log", department: "Operations"

🔴 COMPANY POLICY → document_type: "Legal Policy", department: "Legal"

🔴 EMPLOYMENT CONTRACT → document_type: "Legal Contract", department: "Legal"

🔴 EMPLOYEE LEGAL ISSUE → document_type: "Legal Case", department: "Legal"

=== EXAMPLES (MEMORIZE THESE) ===

✅ CORRECT:
- "John Tan Payslip March 2026" → document_type: "Employee", department: "HR"
- "Marketing Manager Salary Slip" → document_type: "Employee", department: "HR"  
- "Q1 Performance Reviews" → document_type: "HR Report", department: "HR"
- "Monthly Sales Report" → document_type: "Sales Log", department: "Sales"
- "Annual Budget 2026" → document_type: "Finance Report", department: "Finance"

❌ WRONG:
- "Payslip" → "Finance Report" (NO! It's "Employee")
- "Sales Manager Payslip" → "Sales Log" (NO! It's "Employee")
- "Campaign ROI" → "Finance Report" (NO! It's "Marketing Report")

=== OUTPUT FORMAT (STRICT JSON ONLY) ===

Return ONLY valid JSON in this exact format:

{
  "document_type": "MUST be ONE of: HR Report | Sales Log | Finance Report | Marketing Report | Supply Chain Log | Legal Policy | Legal Contract | Legal Case | Employee",
  "department": "MUST be ONE of: HR | Sales | Finance | Marketing | Operations | Legal",
  "confidence": 0.95,
  "summary": "clear business summary of what you see in the document",
  "entities": [
    {
      "type": "Employee | Campaign | Metric | Organization | Date | Amount",
      "name": "field name (e.g., 'employee_name', 'salary', 'period')",
      "value": "the actual value you extracted",
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

=== EXAMPLE FOR PAYSLIP ===

If you see a payslip for "John Tan" with salary "RM 10,500" for period "March 2026", return:

{
  "document_type": "Employee",
  "department": "HR",
  "confidence": 0.95,
  "summary": "Payslip for John Tan showing salary of RM 10,500 for March 2026",
  "entities": [
    {"type": "Employee", "name": "employee_name", "value": "John Tan"},
    {"type": "Amount", "name": "salary", "value": "10500"},
    {"type": "Date", "name": "period", "value": "2026-03-01"},
    {"type": "Metric", "name": "attendance_days", "value": "22"}
  ],
  "tags": ["payslip", "salary", "employee"],
  "relationships": []
}

EXTRACTION RULES - EXTRACT EVERYTHING YOU SEE:

1. **Employee entities**: Extract EVERY employee name, ID, email, role you see
   - type: "Employee", name: "John Tan", value: "employee_id or role"

2. **Date entities**: Extract EVERY date (hire dates, period, review dates)
   - type: "Date", name: "hire_date" or "period", value: "2026-04-01"

3. **Amount entities**: Extract EVERY monetary value (salary, revenue, costs)
   - type: "Amount", name: "salary" or "revenue", value: "10500.00"

4. **Metric entities**: Extract performance scores, attendance, KPIs
   - type: "Metric", name: "performance_score", value: "4.5"

5. **Organization entities**: Extract company names, departments, teams
   - type: "Organization", name: "TNB", value: "customer"

CRITICAL FOR IMAGES/SCANS:
- READ all visible text carefully, even if blurry
- Extract data from tables, forms, structured layouts
- If you see a salary slip/payslip, extract: employee name, salary, period, department, role
- If you see a performance review, extract: employee name, scores, period, reviewer
- If you see an invoice/receipt, extract: amounts, dates, vendor/client names

FORMAT RULES:
- Normalize numbers: remove commas, use plain numbers (e.g., 10500 not 10,500)
- Keep entity names consistent
- Always provide at least 1 entity if you can read ANY data from the document
- If completely unable to extract data, return empty entities array BUT explain why in summary

Now analyze the provided document and return ONLY valid JSON. EXTRACT AS MUCH AS YOU CAN SEE."""

    def _encode_image_base64(self, file_path: str) -> str:
        """Encode image file to base64 string"""
        with open(file_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    
    def _get_mime_type(self, file_path: str) -> str:
        """Get MIME type from file extension"""
        ext = Path(file_path).suffix.lower()
        mime_types = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".webp": "image/webp",
            ".gif": "image/gif",
            ".bmp": "image/bmp",
        }
        return mime_types.get(ext, "image/jpeg")

    def _parse_json_response(self, text: str) -> Dict[str, Any]:
        """Parse JSON from AI response, handling markdown code blocks"""
        text = (text or "").strip()
        if text.startswith("```"):
            text = text.strip("`")
            if text.lower().startswith("json"):
                text = text[4:].strip()
        return json.loads(text)

    def _extract_text_from_pdf(self, file_path: str) -> str:
        """Extract text from PDF file"""
        try:
            from pypdf import PdfReader
            reader = PdfReader(file_path)
            text = ""
            for page in reader.pages:
                text += page.extract_text() + "\n"
            return text
        except ImportError:
            return "[PDF text extraction not available - install pypdf]"
        except Exception as e:
            return f"[PDF text extraction failed: {str(e)}]"
    
    def _extract_text_from_docx(self, file_path: str) -> str:
        """Extract text from DOCX file"""
        try:
            from docx import Document
            doc = Document(file_path)
            return "\n".join([para.text for para in doc.paragraphs])
        except ImportError:
            return "[DOCX text extraction not available - install python-docx]"
        except Exception as e:
            return f"[DOCX text extraction failed: {str(e)}]"

    def process(self, file_path: str) -> Dict[str, Any]:
        """
        Process a document file and extract structured data using Zhipu AI.
        Supports images, PDFs, and text documents.
        """
        print(f"    [DOCUMENT_SERVICE] Starting document processing...")
        print(f"    [DOCUMENT_SERVICE] File path: {file_path}")
        file_ext = Path(file_path).suffix.lower()
        print(f"    [DOCUMENT_SERVICE] File extension: {file_ext}")
        
        # For images, use vision API with base64 encoding
        if file_ext in IMAGE_EXTENSIONS:
            print(f"    [DOCUMENT_SERVICE] Processing as IMAGE using Zhipu GLM Vision API...")
            base64_image = self._encode_image_base64(file_path)
            mime_type = self._get_mime_type(file_path)
            
            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": self.extraction_prompt
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{base64_image}"
                            }
                        }
                    ]
                }
            ]
        
        # For PDFs, extract text first
        elif file_ext == ".pdf":
            print(f"    [DOCUMENT_SERVICE] Processing as PDF, extracting text...")
            text_content = self._extract_text_from_pdf(file_path)
            print(f"    [DOCUMENT_SERVICE] Extracted {len(text_content)} characters from PDF")
            messages = [
                {
                    "role": "user",
                    "content": f"{self.extraction_prompt}\n\nDocument content:\n{text_content}"
                }
            ]
        
        # For DOCX files
        elif file_ext == ".docx":
            print(f"    [DOCUMENT_SERVICE] Processing as DOCX, extracting text...")
            text_content = self._extract_text_from_docx(file_path)
            print(f"    [DOCUMENT_SERVICE] Extracted {len(text_content)} characters from DOCX")
            messages = [
                {
                    "role": "user",
                    "content": f"{self.extraction_prompt}\n\nDocument content:\n{text_content}"
                }
            ]
        
        # For plain text files
        elif file_ext in TEXT_EXTENSIONS:
            print(f"    [DOCUMENT_SERVICE] Processing as TEXT file...")
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            print(f"    [DOCUMENT_SERVICE] Read {len(content)} characters")
            messages = [
                {
                    "role": "user",
                    "content": f"{self.extraction_prompt}\n\nDocument content:\n{content}"
                }
            ]
        
        # For other formats (Excel, etc.), try to read as text
        else:
            print(f"    [DOCUMENT_SERVICE] Processing as OTHER format, reading as text...")
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()[:5000]  # Limit to 5000 chars for non-text formats
            
            print(f"    [DOCUMENT_SERVICE] Read {len(content)} characters (limited)")
            messages = [
                {
                    "role": "user",
                    "content": f"{self.extraction_prompt}\n\nDocument content (first 5000 chars):\n{content}"
                }
            ]
        
        print(f"    [DOCUMENT_SERVICE] Calling Zhipu AI (GLM model) for extraction...")
        print(f"    [DOCUMENT_SERVICE] Model: {self.settings.zhipu_model}")
        
        # Warn if model might not have vision capabilities
        if file_ext in IMAGE_EXTENSIONS and "glm" in self.settings.zhipu_model.lower():
            print(f"    [DOCUMENT_SERVICE] Note: Using vision model for image extraction")
            print(f"    [DOCUMENT_SERVICE]       If extraction fails, model might not support vision well")
        
        # Retry with exponential backoff
        max_attempts = 3
        response = None
        last_error = None
        
        for attempt in range(max_attempts):
            try:
                if attempt > 0:
                    wait_time = 2 ** attempt  # 2s, 4s, 8s
                    print(f"    [DOCUMENT_SERVICE] Retry attempt {attempt + 1}/{max_attempts} after {wait_time}s delay...")
                    time.sleep(wait_time)
                
                print(f"    [DOCUMENT_SERVICE] Sending API request (attempt {attempt + 1})...")
                response = self.client.chat.completions.create(
                    model=self.settings.zhipu_model,
                    messages=messages,
                    temperature=self.settings.llm_temperature,
                    response_format={"type": "json_object"}
                )
                
                # If successful, break out of retry loop
                print(f"    [DOCUMENT_SERVICE] Zhipu AI response received")
                break
                
            except Exception as e:
                last_error = e
                error_str = str(e)
                
                # Check if it's a timeout or 504 error
                is_timeout = "504" in error_str or "timeout" in error_str.lower() or "Gateway time-out" in error_str
                
                if is_timeout and attempt < max_attempts - 1:
                    print(f"    [DOCUMENT_SERVICE] ⚠️  Timeout/504 error on attempt {attempt + 1}")
                    print(f"    [DOCUMENT_SERVICE]     Will retry...")
                    continue  # Retry
                else:
                    # Final attempt failed or non-timeout error
                    if is_timeout:
                        print(f"    [DOCUMENT_SERVICE] FAILED - API timeout after {max_attempts} attempts")
                        print(f"    [DOCUMENT_SERVICE]     The ilmu.ai API is not responding (504 Gateway Timeout)")
                        print(f"    [DOCUMENT_SERVICE]     This is an API infrastructure issue, not a code problem")
                    print(f"    [DOCUMENT_SERVICE] FAILED - Zhipu AI error: {str(e)}")
                    print()
                    raise Exception(f"Zhipu AI extraction failed: {str(e)}")
        
        # If we got here with no response, something went wrong
        if response is None:
            print(f"    [DOCUMENT_SERVICE] FAILED - No response after {max_attempts} attempts")
            raise Exception(f"Zhipu AI extraction failed: {str(last_error)}")
        
        # Parse the successful response
        try:
            print(f"    [DOCUMENT_SERVICE] Parsing JSON response...")
            
            raw_content = response.choices[0].message.content
            print(f"    [DOCUMENT_SERVICE] Raw AI response (first 500 chars):")
            print(f"    [DOCUMENT_SERVICE] {raw_content[:500]}")
            print()
            
            result = self._parse_json_response(raw_content)
            
            print(f"    [DOCUMENT_SERVICE] SUCCESS - Extraction completed")
            print(f"    [DOCUMENT_SERVICE] Document type: {result.get('document_type', 'Unknown')}")
            print(f"    [DOCUMENT_SERVICE] Department: {result.get('department', 'Unknown')}")
            print(f"    [DOCUMENT_SERVICE] Entities extracted: {len(result.get('entities', []))}")
            
            # If no entities, show warning
            if len(result.get('entities', [])) == 0:
                print(f"    [DOCUMENT_SERVICE] ⚠️  WARNING: No entities extracted from document!")
                print(f"    [DOCUMENT_SERVICE]     This will result in NO_SQL_POSSIBLE")
                print(f"    [DOCUMENT_SERVICE]     Possible reasons:")
                print(f"    [DOCUMENT_SERVICE]     - Image quality too low to read")
                print(f"    [DOCUMENT_SERVICE]     - No structured data in the document")
                print(f"    [DOCUMENT_SERVICE]     - Document format not recognized by AI")
            print()
            
            return result
            
        except Exception as e:
            print(f"    [DOCUMENT_SERVICE] FAILED - JSON parsing error: {str(e)}")
            print()
            raise Exception(f"Zhipu AI response parsing failed: {str(e)}")

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
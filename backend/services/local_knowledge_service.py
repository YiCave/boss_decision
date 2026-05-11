"""
Local filesystem-based knowledge service.

This service mirrors the subset of DatabaseService methods used by the API and agents,
so the current stage can run end-to-end without Supabase.
"""
from __future__ import annotations

import json
import re
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class LocalKnowledgeService:
    """Read/write decision data from local folders under backend/workplaces."""

    def __init__(self, workplaces_root: str | Path | None = None):
        backend_root = Path(__file__).resolve().parents[1]
        self.workplaces_root = Path(workplaces_root) if workplaces_root else backend_root / "workplaces"

        self.documents_dir = self.workplaces_root / "documents"
        self.raw_dir = self.workplaces_root / "raw"
        self.entities_dir = self.workplaces_root / "entities"
        self.relationship_dir = self.workplaces_root / "relationship"

        self.cases_dir = self.raw_dir / "cases"
        self.decisions_dir = self.raw_dir / "decisions"

        for directory in [
            self.documents_dir,
            self.raw_dir,
            self.entities_dir,
            self.relationship_dir,
            self.cases_dir,
            self.decisions_dir,
        ]:
            directory.mkdir(parents=True, exist_ok=True)

    async def get_employee(self, employee_id: int) -> Dict[str, Any]:
        """Build a lightweight employee profile from local evidence files."""
        hr_records = await self.get_employee_hr_records(employee_id)
        sales_records = await self.get_employee_sales_records(employee_id)

        return {
            "employee_id": employee_id,
            "name": f"Employee {employee_id}",
            "source": "local_knowledge",
            "hr_record_count": len(hr_records),
            "sales_record_count": len(sales_records),
        }

    async def get_employee_hr_records(self, employee_id: int) -> List[Dict[str, Any]]:
        """Load HR-like records from local markdown/json files."""
        records: List[Dict[str, Any]] = []
        all_files = self._knowledge_files()
        logger.info(f"Scanning {len(all_files)} files for employee_id: {employee_id}")

        for file_path in all_files:
            file_records = self._extract_hr_records(file_path)
            if file_records:
                logger.debug(f"Extracted {len(file_records)} potential HR records from {file_path.name}")
            
            for record in file_records:
                resolved_id = self._resolve_employee_id(record, file_path)
                if resolved_id == employee_id:
                    logger.info(f"MATCH: Found HR record for employee {employee_id} in {file_path.name}")
                    normalized = {
                        "hr_id": record.get("hr_id") or self._stable_record_id(file_path, "hr"),
                        "employee_id": employee_id,
                        "period": str(record.get("period") or "unknown"),
                        "performance_score": self._to_float(record.get("performance_score")),
                        "warning_count": self._to_int(record.get("warning_count"), default=0),
                        "pip_status": record.get("pip_status"),
                        "source_path": str(file_path.relative_to(self.workplaces_root)),
                    }
                    records.append(normalized)

        records.sort(key=lambda r: r.get("period") or "", reverse=True)
        return records

    async def get_employee_sales_records(self, employee_id: int, period: str | None = None) -> List[Dict[str, Any]]:
        """Load sales-like records from local markdown/json files."""
        records: List[Dict[str, Any]] = []

        for file_path in self._knowledge_files():
            file_records = self._extract_sales_records(file_path)
            for record in file_records:
                resolved_id = self._resolve_employee_id(record, file_path)
                if resolved_id != employee_id:
                    continue

                normalized = {
                    "sales_id": record.get("sales_id") or self._stable_record_id(file_path, "sales"),
                    "employee_id": employee_id,
                    "period": str(record.get("period") or "unknown"),
                    "deal_stage": str(record.get("deal_stage") or "pipeline").lower(),
                    "amount": self._to_float(record.get("amount"), default=0.0),
                    "source_path": str(file_path.relative_to(self.workplaces_root)),
                }

                if period and normalized["period"] != period:
                    continue

                records.append(normalized)

        records.sort(key=lambda r: r.get("period") or "", reverse=True)
        return records

    async def get_department_documents(self, department: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Retrieve lightweight department evidence from local documents."""
        department = (department or "").strip().lower().replace(" ", "_")
        results: List[Dict[str, Any]] = []

        for pattern in ("*.md", "*.txt", "*.json"):
            for file_path in sorted(self.documents_dir.glob(pattern)):
                text = file_path.read_text(encoding="utf-8", errors="ignore")
                hint = self._extract_department_hint(text)
                if hint != department and department not in file_path.stem.lower():
                    continue

                summary = self._extract_summary_hint(text)
                results.append(
                    {
                        "source": "local_document",
                        "path": str(file_path.relative_to(self.workplaces_root)),
                        "department": hint,
                        "summary": summary,
                    }
                )

                if len(results) >= limit:
                    return results

        return results

    def add_document(self, name: str, content: str):
        """Save a document to the knowledge base."""
        doc_path = self.documents_dir / f"{name}.txt"
        doc_path.write_text(content, encoding="utf-8")
        logger.info(f"Added document to knowledge base: {doc_path}")
        return doc_path

    async def get_case_evidence(self, case_id: str) -> List[Dict[str, Any]]:
        """Read stored evidence links for a decision case."""
        evidence_path = self.raw_dir / f"evidence_{case_id}.json"
        if not evidence_path.exists():
            return []
        return self._read_json(evidence_path, default=[])

    async def get_decision_output(self, case_id: str) -> Dict[str, Any]:
        """Read final decision output for a decision case."""
        decision_path = self.decisions_dir / f"{case_id}.json"
        if not decision_path.exists():
            raise FileNotFoundError(f"Decision output not found for case '{case_id}'")
        return self._read_json(decision_path, default={})

    async def create_decision_case(
        self,
        question: str,
        context: str | None = None,
        target_type: str | None = None,
        target_id: int | None = None,
        submitted_by: str | None = None,
    ) -> Dict[str, Any]:
        """Create a local decision case record."""
        case_id = self._new_case_id()
        now = self._utc_now()

        case = {
            "case_id": case_id,
            "question": question,
            "context": context,
            "target_type": target_type,
            "target_id": target_id,
            "submitted_by": submitted_by,
            "status": "processing",
            "created_at": now,
            "updated_at": now,
        }

        self._write_json(self.cases_dir / f"{case_id}.json", case)
        return case

    async def save_case_evidence(
        self,
        case_id: str,
        source_table: str,
        record_id: int | str,
        relevance_score: float,
        retrieval_method: str = "filesystem",
        notes: str | None = None,
    ) -> Dict[str, Any]:
        """Append one evidence link entry to a local evidence file."""
        evidence_path = self.raw_dir / f"evidence_{case_id}.json"
        evidence = self._read_json(evidence_path, default=[])

        entry = {
            "case_id": case_id,
            "source_table": source_table,
            "record_id": record_id,
            "relevance_score": relevance_score,
            "retrieval_method": retrieval_method,
            "notes": notes,
            "created_at": self._utc_now(),
        }
        evidence.append(entry)

        self._write_json(evidence_path, evidence)
        return entry

    async def save_decision_output(
        self,
        case_id: str,
        recommendation: str,
        risk_level: str,
        confidence_score: float,
        rationale: str,
        conservative_view: str | None = None,
        aggressive_view: str | None = None,
        manager_persona: str = "balanced",
        ai_justification: str | None = None,
    ) -> Dict[str, Any]:
        """Persist final decision output and mark case completed."""
        now = self._utc_now()

        payload = {
            "case_id": case_id,
            "recommendation": recommendation,
            "risk_level": risk_level,
            "confidence_score": confidence_score,
            "rationale": rationale,
            "conservative_view": conservative_view,
            "aggressive_view": aggressive_view,
            "manager_persona": manager_persona,
            "ai_justification": ai_justification,
            "created_at": now,
            "updated_at": now,
        }

        self._write_json(self.decisions_dir / f"{case_id}.json", payload)
        self._update_case_status(case_id, status="completed")

        return payload

    def _knowledge_files(self) -> List[Path]:
        patterns = ("*.md", "*.json", "*.txt")
        files: List[Path] = []
        for root in [self.entities_dir, self.relationship_dir, self.raw_dir, self.documents_dir]:
            for pattern in patterns:
                files.extend(sorted(root.glob(pattern)))
        return files

    def _extract_hr_records(self, file_path: Path) -> List[Dict[str, Any]]:
        if file_path.suffix.lower() == ".json":
            return self._extract_hr_from_json(self._read_json(file_path, default={}))

        text = file_path.read_text(encoding="utf-8", errors="ignore")
        if self._looks_like_hr_markdown(text, file_path):
            record = self._parse_markdown_record(text)
            if record:
                return [record]
        return []

    def _extract_sales_records(self, file_path: Path) -> List[Dict[str, Any]]:
        if file_path.suffix.lower() == ".json":
            return self._extract_sales_from_json(self._read_json(file_path, default={}))

        text = file_path.read_text(encoding="utf-8", errors="ignore")
        if self._looks_like_sales_markdown(text, file_path):
            record = self._parse_markdown_record(text)
            if record:
                return [record]
        return []

    def _extract_hr_from_json(self, obj: Any) -> List[Dict[str, Any]]:
        records: List[Dict[str, Any]] = []
        for node in self._walk(obj):
            if not isinstance(node, dict):
                continue

            has_hr_markers = any(
                key in node
                for key in ["performance_score", "warning_count", "pip_status", "hr_id"]
            )
            is_hr_department = str(node.get("department", "")).lower() == "hr"
            if not (has_hr_markers or is_hr_department):
                continue

            normalized = {
                "hr_id": node.get("hr_id"),
                "employee_id": self._to_int(node.get("employee_id")),
                "period": node.get("period"),
                "performance_score": self._to_float(node.get("performance_score")),
                "warning_count": self._to_int(node.get("warning_count"), default=0),
                "pip_status": node.get("pip_status"),
            }
            records.append(normalized)
        return records

    def _extract_sales_from_json(self, obj: Any) -> List[Dict[str, Any]]:
        records: List[Dict[str, Any]] = []
        for node in self._walk(obj):
            if not isinstance(node, dict):
                continue

            has_sales_markers = any(
                key in node for key in ["sales_id", "deal_stage", "amount"]
            )
            is_sales_department = str(node.get("department", "")).lower() == "sales"
            if not (has_sales_markers or is_sales_department):
                continue

            normalized = {
                "sales_id": node.get("sales_id"),
                "employee_id": self._to_int(node.get("employee_id")),
                "period": node.get("period"),
                "deal_stage": node.get("deal_stage"),
                "amount": self._to_float(node.get("amount"), default=0.0),
            }
            records.append(normalized)
        return records

    def _parse_markdown_record(self, text: str) -> Dict[str, Any]:
        data: Dict[str, Any] = {}
        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                # Check for headers like "# Employee 102"
                if line.startswith("#"):
                    match = re.search(r"employee[_\s-]?(\d+)", line.lower())
                    if match and "employee_id" not in data:
                        data["employee_id"] = int(match.group(1))
                continue
            if ":" not in line:
                continue

            key, value = line.split(":", 1)
            norm_key = key.strip().lower().replace(" ", "_")
            data[norm_key] = self._coerce_scalar(value.strip())
        return data

    def _extract_department_hint(self, text: str) -> str:
        lower = text.lower()
        patterns = [
            r"department\s*context\s*:\s*([a-z_ ]+)",
            r"department\s*:\s*([a-z_ ]+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, lower)
            if match:
                return match.group(1).strip().replace(" ", "_")

        for dept in ["hr", "sales", "legal", "finance", "marketing", "supply_chain", "operations"]:
            if dept in lower:
                return dept

        return "unknown"

    def _extract_summary_hint(self, text: str) -> str:
        for line in text.splitlines():
            line = line.strip()
            if line.lower().startswith("summary:"):
                return line.split(":", 1)[1].strip()
        return text.strip().splitlines()[0] if text.strip() else ""

    def _looks_like_hr_markdown(self, text: str, file_path: Path) -> bool:
        lower = f"{file_path.name}\n{text}".lower()
        # Markers indicating this file contains HR/Performance data
        markers = [
            "performance_score", "pip_status", "warning_count", 
            "hr_policy", "hr_record", "performance review", 
            "attendance", "disciplinary"
        ]
        is_hr = any(marker in lower for marker in markers)
        if is_hr:
            logger.debug(f"File {file_path.name} marked as HR content")
        return is_hr

    def _looks_like_sales_markdown(self, text: str, file_path: Path) -> bool:
        lower = f"{file_path.name}\n{text}".lower()
        markers = ["deal_stage", "amount", "revenue", "sales"]
        return any(marker in lower for marker in markers)

    def _resolve_employee_id(self, record: Dict[str, Any], file_path: Path) -> int | None:
        candidate = self._to_int(record.get("employee_id"))
        if candidate is not None:
            return candidate

        # Try mapping identifiers like "Employee_102" or "employee 102"
        haystack = f"{file_path.name} {record.get('name', '')}".lower()
        match = re.search(r"employee[_\s-]?(\d+)", haystack)
        if match:
            return int(match.group(1))
        return None

    def _update_case_status(self, case_id: str, status: str) -> None:
        case_path = self.cases_dir / f"{case_id}.json"
        if not case_path.exists():
            return

        case_data = self._read_json(case_path, default={})
        case_data["status"] = status
        case_data["updated_at"] = self._utc_now()
        self._write_json(case_path, case_data)

    @staticmethod
    def _walk(obj: Any):
        if isinstance(obj, dict):
            yield obj
            for value in obj.values():
                yield from LocalKnowledgeService._walk(value)
        elif isinstance(obj, list):
            for item in obj:
                yield from LocalKnowledgeService._walk(item)

    @staticmethod
    def _to_int(value: Any, default: int | None = None) -> int | None:
        if value is None:
            return default
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _to_float(value: Any, default: float | None = None) -> float | None:
        if value is None:
            return default
        if isinstance(value, str):
            value = value.replace(",", "").replace("RM", "").strip()
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _coerce_scalar(value: str) -> Any:
        lower = value.lower()
        if lower in {"null", "none", "n/a", "na", ""}:
            return None
        if lower in {"true", "false"}:
            return lower == "true"

        cleaned = value.replace(",", "").replace("RM", "").strip()
        try:
            if "." in cleaned:
                return float(cleaned)
            return int(cleaned)
        except ValueError:
            return value

    @staticmethod
    def _read_json(path: Path, default: Any) -> Any:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return default

    @staticmethod
    def _write_json(path: Path, payload: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    @staticmethod
    def _new_case_id() -> str:
        stamp = datetime.now(tz=timezone.utc).strftime("%Y%m%dT%H%M%S%f")
        return f"case_{stamp}"

    @staticmethod
    def _utc_now() -> str:
        return datetime.now(tz=timezone.utc).isoformat()

    @staticmethod
    def _stable_record_id(file_path: Path, prefix: str) -> int:
        return abs(hash(f"{prefix}:{file_path.as_posix()}")) % 1_000_000_000

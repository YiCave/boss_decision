"""
LangChain tools for read-only access to company data in Supabase (PostgREST).
Marketing agent uses these alongside Tavily/News. Sales uses DatabaseService fetches
directly in retrieve_evidence to avoid a second tool-calling stack.
"""
import json
import logging
from typing import List, Optional, TYPE_CHECKING, Any

from langchain_core.tools import StructuredTool

if TYPE_CHECKING:
    from db import DatabaseService

logger = logging.getLogger(__name__)


def _dump(rows: List[dict], max_chars: int = 12000) -> str:
    s = json.dumps(rows, default=str, ensure_ascii=False)
    if len(s) > max_chars:
        return s[: max_chars - 20] + "\n…(truncated)…"
    return s


def build_marketing_supabase_tools(company_db: Any) -> List[StructuredTool]:
    """
    company_db: DatabaseService (typed as Any to avoid import cycles at load time).
    """
    if company_db is None:
        return []

    async def read_marketing_database(
        period: Optional[str] = None,
        limit: int = 40,
        campaign_name_contains: Optional[str] = None,
    ) -> str:
        try:
            lim = min(max(1, int(limit)), 100)
            rows = await company_db.fetch_marketing_records(
                limit=lim,
                period=period,
                campaign_name_contains=campaign_name_contains,
            )
            if not rows:
                return "No marketing_record rows returned (empty or filters too strict)."
            return _dump(rows)
        except Exception as e:
            logger.exception("read_marketing_database failed")
            return f"Error reading marketing data: {e!s}"

    async def read_supporting_company_data(
        scope: str,
        limit: int = 20,
        employee_id: Optional[int] = None,
        dept_id: Optional[int] = None,
    ) -> str:
        try:
            lim = min(max(1, int(limit)), 100)
            rows = await company_db.fetch_supporting_by_scope(
                scope, limit=lim, employee_id=employee_id, dept_id=dept_id
            )
            if not rows and (scope or "").lower().strip().startswith("hr"):
                return "hr_sketch / hr_light requires employee_id; none set or no rows found."
            if not rows:
                return f"No rows for scope={scope!r}."
            return _dump(rows)
        except Exception as e:
            logger.exception("read_supporting_company_data failed")
            return f"Error: {e!s}"

    t1 = StructuredTool.from_function(
        coroutine=read_marketing_database,
        name="read_marketing_database",
        description=(
            "PRIMARY internal data: table marketing_record — campaigns, channels, metrics, amounts, "
            "target_audience, links to source documents. Use first for in-company performance questions, "
            "then use web search for external benchmarks. Args: period (e.g. 2024-Q1), limit, campaign_name_contains."
        ),
    )
    t2 = StructuredTool.from_function(
        coroutine=read_supporting_company_data,
        name="read_supporting_company_data",
        description=(
            "Shallow read from whitelisted tables only (cross-checks, not deep specialist analysis). "
            "scope: employees | departments | finance | source_documents | supply_sketch | legal_policy | "
            "legal_cases | sales_sketch | decision_cases | hr_sketch (must pass employee_id). "
            "Optional: limit, employee_id, dept_id (for finance). "
        ),
    )
    return [t1, t2]

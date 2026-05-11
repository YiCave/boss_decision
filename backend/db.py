"""
Supabase database client and helper functions.
"""
import asyncio
import logging
from typing import Any, Dict, List, Optional

from supabase import create_client, Client
from functools import lru_cache
from config import get_settings

logger = logging.getLogger(__name__)


@lru_cache()
def get_supabase_client() -> Client:
    """Get cached Supabase client instance."""
    settings = get_settings()
    return create_client(
        settings.supabase_url,
        settings.supabase_service_key
    )


class DatabaseService:
    """Service class for database operations."""
    
    def __init__(self):
        self.client = get_supabase_client()
    
    async def get_employee(self, employee_id: int) -> Optional[Dict[str, Any]]:
        """Get employee with related records, or None if no row (uses maybe_single to avoid 406 on 0 rows)."""

        def _run():
            return (
                self.client.table("employee")
                .select("*, department:dept_id(*)")
                .eq("employee_id", employee_id)
                .maybe_single()
                .execute()
            )

        res = await self._to_thread(_run)
        return res.data
    
    async def get_employee_hr_records(self, employee_id: int):
        """Get HR performance records for an employee."""
        response = self.client.table('hr_record') \
            .select('*') \
            .eq('employee_id', employee_id) \
            .order('period', desc=True) \
            .execute()
        return response.data
    
    async def get_employee_sales_records(self, employee_id: int, period: str = None):
        """Get sales records for an employee."""
        query = self.client.table('sales_record') \
            .select('*') \
            .eq('employee_id', employee_id)
        
        if period:
            query = query.eq('period', period)
        
        response = query.order('period', desc=True).execute()
        return response.data
    
    async def get_legal_policies(self, category: str = None):
        """Get legal policies, optionally filtered by category."""
        query = self.client.table('legal_policy').select('*')
        
        if category:
            query = query.eq('policy_category', category)
        
        response = query.execute()
        return response.data

    async def get_supply_record(self, supply_id: int):
        """Get one supply record by supply_id."""
        response = self.client.table('supply_record') \
            .select('*') \
            .eq('supply_id', supply_id) \
            .limit(1) \
            .execute()

        records = response.data or []
        return records[0] if records else None

    async def get_all_supply_records(self):
        """Get all supply records."""
        response = self.client.table('supply_record') \
            .select('*') \
            .order('supply_id', desc=False) \
            .execute()
        return response.data or []

    async def get_supply_records_below_inventory(self, threshold: int = 1000):
        """Get supply records with inventory level below the given threshold."""
        response = self.client.table('supply_record') \
            .select('*') \
            .lt('inventory_level', threshold) \
            .order('inventory_level', desc=False) \
            .execute()
        return response.data

    async def get_supply_records_for_debate(
        self, item_name: Optional[str] = None, limit: int = 5
    ):
        """
        Get supply records used by the sales-vs-supply debate simulator.
        Returns a lean column set focused on item planning constraints.
        """
        safe_limit = max(1, min(limit, 20))
        query = self.client.table('supply_record') \
            .select('supply_id,item_name,inventory_level,demand_forecast,reorder_point,shortage_flag,supplier_name,unit_cost') \
            .order('supply_id', desc=False) \
            .limit(safe_limit)

        if item_name and item_name.strip():
            query = query.ilike('item_name', f"%{item_name.strip()}%")

        response = query.execute()
        return response.data or []
    
    async def get_case_evidence(self, case_id: int):
        """Get all evidence linked to a decision case."""
        response = self.client.table('case_evidence') \
            .select('*') \
            .eq('case_id', case_id) \
            .order('relevance_score', desc=True) \
            .execute()
        return response.data
    
    async def get_decision_output(self, case_id: int):
        """Get decision output for a case."""
        response = self.client.table('decision_output') \
            .select('*') \
            .eq('case_id', case_id) \
            .single() \
            .execute()
        return response.data
    
    async def create_decision_case(self, question: str, context: str = None, 
                                  target_type: str = None, target_id: int = None,
                                  submitted_by: str = None):
        """Create a new decision case."""
        response = self.client.table('decision_case') \
            .insert({
                'question': question,
                'context': context,
                'target_type': target_type,
                'target_id': target_id,
                'submitted_by': submitted_by,
                'status': 'processing'
            }) \
            .execute()
        return response.data[0]
    
    async def save_case_evidence(self, case_id: int, source_table: str, 
                                record_id: int, relevance_score: float,
                                retrieval_method: str = 'sql_query', notes: str = None):
        """Save evidence linking for a case."""
        response = self.client.table('case_evidence') \
            .insert({
                'case_id': case_id,
                'source_table': source_table,
                'record_id': record_id,
                'relevance_score': relevance_score,
                'retrieval_method': retrieval_method,
                'notes': notes
            }) \
            .execute()
        return response.data[0]
    
    async def save_decision_output(self, case_id: int, recommendation: str,
                                  risk_level: str, confidence_score: float,
                                  rationale: str, conservative_view: str = None,
                                  aggressive_view: str = None, 
                                  manager_persona: str = 'balanced',
                                  ai_justification: str = None):
        """Save final decision output."""
        response = self.client.table('decision_output') \
            .insert({
                'case_id': case_id,
                'recommendation': recommendation,
                'risk_level': risk_level,
                'confidence_score': confidence_score,
                'rationale': rationale,
                'conservative_view': conservative_view,
                'aggressive_view': aggressive_view,
                'manager_persona': manager_persona,
                'ai_justification': ai_justification
            }) \
            .execute()
        
        # Update case status to completed
        self.client.table('decision_case') \
            .update({'status': 'completed'}) \
            .eq('case_id', case_id) \
            .execute()
        
        return response.data[0]

    # ------------------------------------------------------------------
    # Read-only agent helpers (PostgREST, marketing / sales + shallow cross)
    # ------------------------------------------------------------------

    @staticmethod
    async def _to_thread(func):
        return await asyncio.to_thread(func)

    async def fetch_marketing_records(
        self,
        *,
        limit: int = 40,
        period: Optional[str] = None,
        campaign_name_contains: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Primary marketing domain: marketing_record (campaigns, channels, metrics)."""
        cap = min(max(1, limit), 100)

        def _run():
            q = self.client.table("marketing_record").select("*")
            if period:
                q = q.eq("period", period)
            if campaign_name_contains:
                q = q.ilike("campaign_name", f"%{campaign_name_contains}%")
            return q.order("created_at", desc=True).limit(cap).execute()

        res = await self._to_thread(_run)
        return res.data or []

    async def fetch_sales_records_for_agent(
        self,
        *,
        limit: int = 50,
        period: Optional[str] = None,
        employee_id: Optional[int] = None,
        deal_stage: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Primary sales domain: sales_record; pass employee_id to narrow to one rep when relevant."""
        cap = min(max(1, limit), 150)

        def _run():
            q = self.client.table("sales_record").select("*")
            if period:
                q = q.eq("period", period)
            if employee_id is not None:
                q = q.eq("employee_id", employee_id)
            if deal_stage:
                q = q.eq("deal_stage", deal_stage)
            return q.order("created_at", desc=True).limit(cap).execute()

        res = await self._to_thread(_run)
        return res.data or []

    async def fetch_employees_limited(self, limit: int = 80) -> List[Dict[str, Any]]:
        cap = min(max(1, limit), 200)

        def _run():
            return (
                self.client.table("employee")
                .select("employee_id,dept_id,name,role,email,hire_date,exit_date")
                .limit(cap)
                .execute()
            )

        res = await self._to_thread(_run)
        return res.data or []

    async def fetch_departments_all(self) -> List[Dict[str, Any]]:
        def _run():
            return self.client.table("department").select("*").execute()

        res = await self._to_thread(_run)
        return res.data or []

    async def fetch_finance_limited(
        self, *, limit: int = 40, dept_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        cap = min(max(1, limit), 100)

        def _run():
            q = self.client.table("finance_record").select("*")
            if dept_id is not None:
                q = q.eq("dept_id", dept_id)
            return q.order("period", desc=True).limit(cap).execute()

        res = await self._to_thread(_run)
        return res.data or []

    async def fetch_source_documents_limited(self, limit: int = 25) -> List[Dict[str, Any]]:
        cap = min(max(1, limit), 80)

        def _run():
            return (
                self.client.table("source_document")
                .select(
                    "source_id,doc_type,title,published_date,extracted_at,notes,created_at"
                )
                .order("created_at", desc=True)
                .limit(cap)
                .execute()
            )

        res = await self._to_thread(_run)
        return res.data or []

    async def fetch_hr_shallow_for_employee(
        self, employee_id: int, limit: int = 12
    ) -> List[Dict[str, Any]]:
        """Light read on hr_record; use for cross-checks only, not full HR review."""
        cap = min(max(1, limit), 50)

        def _run():
            return (
                self.client.table("hr_record")
                .select("*")
                .eq("employee_id", employee_id)
                .order("period", desc=True)
                .limit(cap)
                .execute()
            )

        res = await self._to_thread(_run)
        return res.data or []

    async def fetch_supply_limited(self, limit: int = 12) -> List[Dict[str, Any]]:
        cap = min(max(1, limit), 50)

        def _run():
            return (
                self.client.table("supply_record")
                .select("*")
                .order("period", desc=True)
                .limit(cap)
                .execute()
            )

        res = await self._to_thread(_run)
        return res.data or []

    async def fetch_legal_policies_limited(self, limit: int = 12) -> List[Dict[str, Any]]:
        cap = min(max(1, limit), 50)

        def _run():
            return (
                self.client.table("legal_policy")
                .select("legal_id,policy_category,policy_name,region,effective_date,rule_text")
                .order("created_at", desc=True)
                .limit(cap)
                .execute()
            )

        res = await self._to_thread(_run)
        return res.data or []

    async def fetch_legal_cases_limited(self, limit: int = 8) -> List[Dict[str, Any]]:
        cap = min(max(1, limit), 30)

        def _run():
            return (
                self.client.table("legal_cases")
                .select("case_id,employee_id,issue_type,description,created_at")
                .order("created_at", desc=True)
                .limit(cap)
                .execute()
            )

        res = await self._to_thread(_run)
        return res.data or []

    async def fetch_decision_case_recent(self, limit: int = 6) -> List[Dict[str, Any]]:
        cap = min(max(1, limit), 20)

        def _run():
            return (
                self.client.table("decision_case")
                .select("case_id,question,context,status,created_at,submitted_by")
                .order("created_at", desc=True)
                .limit(cap)
                .execute()
            )

        res = await self._to_thread(_run)
        return res.data or []

    async def fetch_supporting_by_scope(
        self,
        scope: str,
        *,
        limit: int = 20,
        employee_id: Optional[int] = None,
        dept_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Whitelist-driven shallow reads for marketing/sales tools.
        Scopes: employees, departments, finance, source_documents, hr_sketch, supply_sketch,
        legal_policy, legal_cases, sales_sketch, decision_cases
        """
        s = (scope or "").strip().lower().replace("-", "_")
        try:
            if s in ("employees", "employee"):
                return await self.fetch_employees_limited(limit=limit)
            if s in ("departments", "department"):
                return await self.fetch_departments_all()
            if s == "finance":
                return await self.fetch_finance_limited(limit=limit, dept_id=dept_id)
            if s in ("source_documents", "documents", "source_document"):
                return await self.fetch_source_documents_limited(limit=limit)
            if s in ("hr_sketch", "hr_light", "hr"):
                if employee_id is None:
                    return []
                return await self.fetch_hr_shallow_for_employee(employee_id, limit=limit)
            if s in ("supply_sketch", "supply", "supply_chain"):
                return await self.fetch_supply_limited(limit=limit)
            if s in ("legal_policy", "legal_policies", "legal"):
                return await self.fetch_legal_policies_limited(limit=limit)
            if s in ("legal_cases", "legal_case"):
                return await self.fetch_legal_cases_limited(limit=limit)
            if s in ("sales_sketch", "sales_pipeline", "sales_light"):
                return await self.fetch_sales_records_for_agent(
                    limit=limit, employee_id=employee_id, period=None
                )
            if s in ("decision_cases", "decisions", "recent_decision_cases"):
                return await self.fetch_decision_case_recent(limit=limit)
        except Exception as exc:  # noqa: BLE001
            logger.warning("fetch_supporting_by_scope failed scope=%s: %s", s, exc)
        return []

    # ------------------------------------------------------------------
    # HR / Legal / Finance agents (Zhipu path — full table reads)
    # ------------------------------------------------------------------

    async def search_employees_by_name(self, name: str, limit: int = 8) -> List[Dict[str, Any]]:
        q = (name or "").strip()
        if not q:
            return []
        cap = min(max(1, limit), 20)

        def _run():
            return (
                self.client.table("employee")
                .select("employee_id,name,email,dept_id,role,hire_date,exit_date")
                .ilike("name", f"%{q}%")
                .limit(cap)
                .execute()
            )

        res = await self._to_thread(_run)
        return res.data or []

    async def get_finance_records(
        self,
        employee_id: Optional[int] = None,
        dept_id: Optional[int] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        cap = min(max(1, limit), 200)

        def _run():
            q = self.client.table("finance_record").select("*")
            if employee_id is not None:
                q = q.eq("employee_id", employee_id)
            if dept_id is not None:
                q = q.eq("dept_id", dept_id)
            return q.order("created_at", desc=True).limit(cap).execute()

        res = await self._to_thread(_run)
        return res.data or []

    async def get_finance_records_employee_linked(
        self, limit: int = 80
    ) -> List[Dict[str, Any]]:
        """Finance rows with non-null employee_id (e.g. payroll); excludes platform rows with null employee."""
        cap = min(max(1, limit), 200)

        def _run():
            return (
                self.client.table("finance_record")
                .select("*")
                .not_.is_("employee_id", "null")
                .order("created_at", desc=True)
                .limit(cap)
                .execute()
            )

        res = await self._to_thread(_run)
        return res.data or []

    async def fetch_hr_records_company_sample(self, limit: int = 150) -> List[Dict[str, Any]]:
        """Company-wide hr_record rows, ordered by performance (for 'best employee' / workforce queries)."""
        cap = min(max(1, limit), 300)

        def _run():
            return (
                self.client.table("hr_record")
                .select("*")
                .order("performance_score", desc=True)
                .limit(cap)
                .execute()
            )

        res = await self._to_thread(_run)
        return res.data or []

    async def get_legal_contracts(self, employee_id: int) -> List[Dict[str, Any]]:
        def _run():
            return (
                self.client.table("legal_contract")
                .select("*")
                .eq("employee_id", employee_id)
                .order("created_at", desc=True)
                .execute()
            )

        res = await self._to_thread(_run)
        return res.data or []

    async def get_legal_cases(self, employee_id: int) -> List[Dict[str, Any]]:
        def _run():
            return (
                self.client.table("legal_cases")
                .select("*")
                .eq("employee_id", employee_id)
                .order("created_at", desc=True)
                .execute()
            )

        res = await self._to_thread(_run)
        return res.data or []

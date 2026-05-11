"""
Main FastAPI application for AI Boss Decision Engine.
Multi-agent decision support system with LangChain integration.
"""
import asyncio
import json
import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import uvicorn
import logging
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("boss_decision")

from config import get_settings
from db import DatabaseService
from services.local_knowledge_service import LocalKnowledgeService
from services.manager_document_ingestor import ManagerDocumentIngestor
from services.llm_client import UnifiedLLMClient
from services.sales_campaign_service import SalesCampaignService
from services.sales_supply_debate_service import SalesSupplyDebateService
from agents import (
    HRAgent,
    SalesAgent,
    LegalAgent,
    FinanceAgent,
    MarketingAgent,
    SupplyChainAgent,
    ManagerAgent,
)

# Import services lazily to avoid import-time configuration errors
# from services.cloudinary_service import get_cloudinary_service
# from services.document_service import DocumentIngestor  
# from services.data_writer_agent import get_data_writer_agent

# Initialize settings
settings = get_settings()

# Initialize FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.api_version,
    description="Multi-agent decision support system for strategic business questions"
)

# CORS middleware (allow frontend to call API)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080", "http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Local filesystem knowledge + shared Supabase client for company tables
knowledge = LocalKnowledgeService()
db = DatabaseService()
hr_agent = HRAgent(knowledge, company_db=db)
sales_agent = SalesAgent(knowledge, company_db=db)
legal_agent = LegalAgent(knowledge, company_db=db)
finance_agent = FinanceAgent(knowledge, company_db=db)
marketing_agent = MarketingAgent(knowledge, company_db=db)
supply_chain_agent = SupplyChainAgent(knowledge, company_db=db)
manager_agent = ManagerAgent([
    hr_agent,
    sales_agent,
    legal_agent,
    finance_agent,
    marketing_agent,
    supply_chain_agent,
])
manager_document_ingestor = ManagerDocumentIngestor()


# ============================================
# Request/Response Models
# ============================================

class AnalyzeRequest(BaseModel):
    """Request model for analyze endpoint."""
    query: str
    target_type: Optional[str] = None
    target_id: Optional[int] = None
    context: Optional[str] = None
    document_path: Optional[str] = None
    submitted_by: Optional[str] = None
    document_summary: Optional[str] = None
    # New fields for Group Chat modes
    mode: str = "hybrid"  # "hybrid" (dynamic) or "manual"
    forced_agents: Optional[List[str]] = None
    document_department: Optional[str] = None
    document_entities: Optional[List[Dict[str, Any]]] = None
    document_tags: Optional[List[str]] = None


class EmployeeResponse(BaseModel):
    """Response model for employee endpoint."""
    employee: Dict[str, Any]
    hr_records: List[Dict[str, Any]]
    sales_records: List[Dict[str, Any]]


# --- Simulator / sales feature branch (separate UI routes on frontend) ---
class SimulatorRequest(BaseModel):
    """Request model for simulator graph execution."""

    query: str
    structured_data: Optional[dict[str, Any]] = None
    documents: Optional[list[str]] = None
    business_context: Optional[dict[str, Any]] = None


class SalesCampaignRequest(BaseModel):
    """Request model for Tavily-powered sales campaign suggestions."""

    product: str = Field(..., min_length=2, max_length=120)
    region: Optional[str] = Field(default="Malaysia", max_length=80)


class DeepSimulatorRequest(BaseModel):
    """Request model for deep 2D simulator execution."""

    query: str
    max_ticks: int = 5
    seed: Optional[int] = None
    scenario_id: str = "pricing_war_v1"
    min_personas: int = 3
    max_personas: int = 6
    summary_cadence_ticks: int = 7


class NetworkSimulatorRequest(BaseModel):
    """Request model for network simulation execution."""

    query: str
    max_ticks: int = 16
    seed: Optional[int] = None
    min_nodes: int = 15
    max_nodes: int = 30
    scenario_id: str = "business_network_v1"
    allow_internet: bool = True
    data_context_path: Optional[str] = None


class NetworkShockRequest(BaseModel):
    """Request model for shock injection into an active network session."""

    shock_type: str
    summary: str
    severity: float
    targets: List[str] = Field(default_factory=list)


class ObserverChatRequest(BaseModel):
    """Request model for post-run observer chat."""

    question: str


class SalesSupplyDebateRequest(BaseModel):
    """Request model for sales-vs-supply debate simulator."""

    item_name: Optional[str] = None
    max_rounds: int = Field(default=4, ge=1, le=10)


def _ensure_simulator_import_path() -> None:
    simulator_root = Path(__file__).resolve().parent / "simulator_agent"
    simulator_root_str = str(simulator_root)
    if simulator_root_str not in sys.path:
        sys.path.insert(0, simulator_root_str)


def _get_simulator_agent():
    _ensure_simulator_import_path()
    from simulator_agent.src import agent as simulator_agent

    return simulator_agent


def _ensure_deep_simulator_import_path() -> None:
    backend_root = Path(__file__).resolve().parent
    backend_root_str = str(backend_root)
    if backend_root_str not in sys.path:
        sys.path.insert(0, backend_root_str)


def _get_deep_simulator_agent():
    _ensure_deep_simulator_import_path()
    from deep_simulation_agent.src import agent as deep_simulator_agent

    return deep_simulator_agent


def _ensure_network_simulator_import_path() -> None:
    backend_root = Path(__file__).resolve().parent
    backend_root_str = str(backend_root)
    if backend_root_str not in sys.path:
        sys.path.insert(0, backend_root_str)


def _get_network_simulator_agent():
    _ensure_network_simulator_import_path()
    from network_simulation_agent.src import agent as network_simulator_agent

    return network_simulator_agent


def _build_simulator_initial_state(request: SimulatorRequest) -> dict[str, Any]:
    return {
        "query": request.query,
        "structured_data": request.structured_data or {},
        "documents": request.documents or [],
        "business_context": request.business_context or {},
        "persona_results": [],
        "persona_stream_events": [],
        "scenario_branches": [],
    }


def _build_deep_simulator_initial_state(request: DeepSimulatorRequest) -> dict[str, Any]:
    return {
        "query": request.query,
        "max_ticks": request.max_ticks,
        "seed": request.seed,
        "scenario_id": request.scenario_id,
        "min_personas": request.min_personas,
        "max_personas": request.max_personas,
        "summary_cadence_ticks": request.summary_cadence_ticks,
    }


def _build_network_simulator_initial_state(request: NetworkSimulatorRequest) -> dict[str, Any]:
    return {
        "query": request.query,
        "max_ticks": request.max_ticks,
        "seed": request.seed,
        "min_nodes": request.min_nodes,
        "max_nodes": request.max_nodes,
        "scenario_id": request.scenario_id,
        "allow_internet": request.allow_internet,
        "data_context_path": request.data_context_path,
    }


def _ndjson_line(payload: dict[str, Any]) -> str:
    return json.dumps(payload, default=str) + "\n"


def _safe_json_payload(data: Any) -> Any:
    try:
        json.dumps(data, default=str)
        return data
    except Exception:
        return str(data)


# ============================================
# Routes
# ============================================

@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "online",
        "message": f"{settings.app_name} API",
        "version": settings.api_version
    }


@app.get("/api/health")
async def health_check():
    """Detailed health check with local knowledge workspace readiness."""
    try:
        required_dirs = [
            knowledge.workplaces_root,
            knowledge.documents_dir,
            knowledge.raw_dir,
            knowledge.entities_dir,
            knowledge.relationship_dir,
        ]

        missing = [str(path) for path in required_dirs if not path.exists()]
        if missing:
            raise RuntimeError(f"Missing required directories: {missing}")

        db_ok = True
        try:
            db.client.table("department").select("dept_id").limit(1).execute()
        except Exception:
            db_ok = False

        return {
            "status": "healthy",
            "storage": "local_filesystem",
            "workplaces_root": str(knowledge.workplaces_root),
            "supabase_probe": "ok" if db_ok else "unavailable",
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Service unhealthy: {str(e)}")


@app.get("/api/health/llm")
async def llm_health_check():
    """Check LLM connectivity and model availability without exposing secrets."""
    client = UnifiedLLMClient.from_settings()
    if client is None:
        raise HTTPException(status_code=503, detail="LLM not configured (missing API key)")

    try:
        response = client.complete_text(
            system_prompt="You are a health-check assistant.",
            user_prompt="Reply with exactly: ok",
            temperature=0.0,
            max_tokens=12,
        )
        return {
            "status": "healthy",
            "llm_model": client.model,
            "llm_response": (response.text or "")[:40],
        }
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail={
                "status": "unhealthy",
                "llm_model": client.model,
                "llm_endpoint": client.base_url,
                "error": str(exc),
            },
        )


@app.get("/api/employees/{employee_id}")
async def get_employee(employee_id: int):
    """Get employee profile with related records."""
    try:
        employee = await knowledge.get_employee(employee_id)
        hr_records = await knowledge.get_employee_hr_records(employee_id)
        sales_records = await knowledge.get_employee_sales_records(employee_id)
        
        return {
            "employee": employee,
            "hr_records": hr_records,
            "sales_records": sales_records
        }
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Employee not found: {str(e)}")


@app.get("/api/cases/{case_id}")
async def get_case(case_id: str):
    """Get decision case with evidence and output."""
    try:
        evidence = await knowledge.get_case_evidence(case_id)
        decision = await knowledge.get_decision_output(case_id)
        
        return {
            "case_id": case_id,
            "evidence": evidence,
            "decision": decision
        }
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Case not found: {str(e)}")


@app.post("/api/analyze")
async def analyze_query(request: AnalyzeRequest):
    """
    Main decision engine endpoint.
    Analyzes a business question using multi-agent system.
    
    Runs local multi-agent orchestration using file-based knowledge.
    """
    try:
        return await _run_analysis(
            query=request.query,
            context=request.context,
            target_type=request.target_type,
            target_id=request.target_id,
            submitted_by=request.submitted_by,
            mode=request.mode,
            forced_agents=request.forced_agents,
            document_analysis={
                "summary": request.document_summary,
                "department": request.document_department,
                "entities": request.document_entities or [],
                "tags": request.document_tags or [],
            } if request.document_summary or request.document_department else None,
            knowledge_service=knowledge,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@app.post("/api/analyze/upload")
async def analyze_query_with_upload(
    query: str = Form(...),
    context: Optional[str] = Form(default=None),
    target_type: Optional[str] = Form(default=None),
    target_id: Optional[int] = Form(default=None),
    submitted_by: Optional[str] = Form(default="frontend"),
    mode: str = Form(default="hybrid"),
    forced_agents_json: Optional[str] = Form(default=None, alias="forced_agents"),
    document: Optional[UploadFile] = File(default=None),
):
    """Analyze decision query with optional uploaded file context."""
    # Parse forced_agents from JSON if provided
    forced_agents = None
    if forced_agents_json:
        try:
            forced_agents = json.loads(forced_agents_json)
        except:
            forced_agents = [forced_agents_json] # fallback if it's just a comma string or single name

    try:
        extracted_document = None

        if document is not None:
            suffix = Path(document.filename or "upload.bin").suffix or ".bin"
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                data = await document.read()
                tmp.write(data)
                tmp_path = tmp.name

            try:
                extracted_document = await manager_document_ingestor.aprocess(tmp_path, knowledge_service=knowledge)
            finally:
                Path(tmp_path).unlink(missing_ok=True)

        logger.info("\n[API] Analyzing query: %s", query)
        if document:
            logger.info("[API] Uploaded file detected: %s", document.filename)

        response = await _run_analysis(
            query=query,
            context=context,
            target_type=target_type,
            target_id=target_id,
            submitted_by=submitted_by,
            mode=mode,
            forced_agents=forced_agents,
            document_analysis=extracted_document,
            knowledge_service=knowledge,
        )

        if extracted_document:
            response["document_analysis"] = extracted_document
        
        logger.info("[API] Analysis completed for case: %s", response.get('case_id'))
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload analysis failed: {str(e)}")


async def _run_analysis(
    *,
    query: str,
    context: Optional[str],
    target_type: Optional[str],
    target_id: Optional[int],
    submitted_by: Optional[str],
    document_analysis: Optional[Dict[str, Any]],
    knowledge_service: LocalKnowledgeService,
    mode: str = "hybrid",
    forced_agents: Optional[List[str]] = None,
):
    case = await knowledge.create_decision_case(
        question=query,
        context=context,
        target_type=target_type,
        target_id=target_id,
        submitted_by=submitted_by,
    )

    orchestration_context = {
        "target_type": target_type,
        "target_id": target_id,
        "context": context,
        "submitted_by": submitted_by,
        "force_simple_llm_subagents": False,
        "knowledge_paths": {
            "entities": str(knowledge.entities_dir),
            "relationships": str(knowledge.relationship_dir),
            "raw": str(knowledge.raw_dir),
        },
    }

    if document_analysis:
        orchestration_context["document_summary"] = document_analysis.get("summary")
        orchestration_context["document_department"] = document_analysis.get("department")
        orchestration_context["document_entities"] = document_analysis.get("entities", [])
        orchestration_context["document_tags"] = document_analysis.get("tags", [])
        orchestration_context["document_metadata"] = document_analysis.get("metadata", {})

    # 4. Orchestrate decision
    logger.info("[API] Running orchestration (mode=%s, forced=%s)", mode, forced_agents)
    orchestration = await manager_agent.orchestrate_dynamic(
        query=query,
        context=orchestration_context,
        forced_agents=forced_agents if mode == "manual" else None
    )
    final_decision = orchestration["final_decision"]

    for insight in orchestration.get("agent_insights", []):
        for evidence in insight.get("evidence_used", []):
            record_id = evidence.get("record_id") or evidence.get("path") or "unknown"
            source_table = evidence.get("source") or "local_knowledge"
            await knowledge.save_case_evidence(
                case_id=case["case_id"],
                source_table=str(source_table),
                record_id=str(record_id),
                relevance_score=0.8,
                retrieval_method="filesystem",
                notes=evidence.get("type") or insight.get("agent_name"),
            )

    await knowledge.save_decision_output(
        case_id=case["case_id"],
        recommendation=final_decision["recommendation"],
        risk_level=final_decision["risk_level"],
        confidence_score=final_decision["confidence_score"],
        rationale=final_decision["rationale"],
        conservative_view=orchestration.get("conservative_view"),
        aggressive_view=orchestration.get("aggressive_view"),
        manager_persona=final_decision.get("manager_persona", "balanced"),
    )

    return {
        "status": "completed",
        "case_id": case["case_id"],
        "query": query,
        "routing": orchestration.get("routing", {}),
        "final_decision": final_decision,
        "agent_insights": orchestration.get("agent_insights", []),
        "conservative_view": orchestration.get("conservative_view", ""),
        "aggressive_view": orchestration.get("aggressive_view", ""),
    }


@app.post("/api/documents/upload")
async def upload_document(
    file: UploadFile = File(...),
    custom_extraction: Optional[str] = Form(None)
):
    """
    Upload a document, extract data with AI, and write to database.
    
    Flow:
    1. Upload file to Cloudinary
    2. Create source_document record
    3. Extract data with Zhipu GLM (document_service.py)
    4. Write data to appropriate tables with Zhipu AI (data_writer_agent.py)
    
    Args:
        file: Document file to upload
        custom_extraction: Optional user-requested data to extract (will use ai_justification if not standard column)
    """
    print("\n" + "="*80)
    print("DOCUMENT UPLOAD PIPELINE STARTED")
    print("="*80)
    print(f"File: {file.filename}")
    print(f"Custom extraction requested: {custom_extraction if custom_extraction else 'None'}")
    print()
    
    try:
        # Validate file type
        print("[STEP 0] Validating file type...")
        allowed_extensions = {'.pdf', '.doc', '.docx', '.txt', '.md', '.png', '.jpg', '.jpeg', '.xlsx', '.csv'}
        file_ext = os.path.splitext(file.filename)[1].lower()
        
        if file_ext not in allowed_extensions:
            print(f"[STEP 0] FAILED - Unsupported file type: {file_ext}")
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type. Allowed: {', '.join(allowed_extensions)}"
            )
        
        print(f"[STEP 0] SUCCESS - File type validated: {file_ext}")
        
        # Read file content
        file_content = await file.read()
        print(f"[STEP 0] File read successfully, size: {len(file_content)} bytes")
        print()
        
        # Step 1: Upload to Cloudinary
        print("[STEP 1] CLOUDINARY UPLOAD - Starting upload to Cloudinary...")
        from services.cloudinary_service import get_cloudinary_service
        
        cloudinary_service = get_cloudinary_service()
        upload_result = cloudinary_service.upload_from_bytes(
            file_bytes=file_content,
            filename=file.filename,
            folder="documents",
            doc_type=None  # Will be determined by AI
        )
        
        if not upload_result["success"]:
            print(f"[STEP 1] FAILED - Cloudinary upload error: {upload_result.get('error')}")
            raise HTTPException(status_code=500, detail=f"Upload failed: {upload_result.get('error')}")
        
        file_url = upload_result["url"]
        print(f"[STEP 1] SUCCESS - File uploaded to Cloudinary")
        print(f"         URL: {file_url}")
        print()
        
        # Step 2: Generate next source_id
        print("[STEP 2] SOURCE DOCUMENT - Creating source_document record...")
        max_id_result = db.client.table("source_document")\
            .select("source_id")\
            .order("source_id", desc=True)\
            .limit(1)\
            .execute()
        
        if max_id_result.data and len(max_id_result.data) > 0:
            source_id = max_id_result.data[0]["source_id"] + 1
        else:
            source_id = 501  # Start from 501 if no records exist
        
        print(f"         Generated source_id: {source_id}")
        
        # Step 3: Create source_document record
        source_doc_data = {
            "source_id": source_id,  # Manually generated ID
            "doc_type": "Unknown",  # Will be updated after extraction
            "title": file.filename,
            "file_path": file_url,
            "extracted_at": None,  # Not yet processed
            "notes": f"Uploaded via API at {datetime.now().isoformat()}"
        }
        
        result = db.client.table("source_document")\
            .insert(source_doc_data)\
            .execute()
        
        if not result.data:
            print("[STEP 2] FAILED - Could not insert source_document record")
            raise HTTPException(status_code=500, detail="Failed to create source document record")
        
        print(f"[STEP 2] SUCCESS - source_document record created (ID: {source_id})")
        print()
        
        # Step 3: Extract data with document_service (Zhipu GLM)
        print("[STEP 3] DOCUMENT EXTRACTION - Starting AI extraction with Zhipu GLM...")
        extraction_json = None
        doc_type = "Unknown"
        
        try:
            # Save file temporarily for document service
            with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as temp_file:
                temp_file.write(file_content)
                temp_file_path = temp_file.name
            
            print(f"         Temp file created: {temp_file_path}")
            
            try:
                from services.document_service import DocumentIngestor
                
                document_ingestor = DocumentIngestor()
                print("         Calling document_service.process()...")
                extraction_json = document_ingestor.process(temp_file_path)
                doc_type = extraction_json.get("document_type", "Unknown")
                
                print(f"[STEP 3] SUCCESS - Document extracted")
                print(f"         Document Type: {doc_type}")
                print(f"         Department: {extraction_json.get('department', 'N/A')}")
                print(f"         Entities extracted: {len(extraction_json.get('entities', []))}")
                
                # If no entities, show full extraction JSON for debugging
                if len(extraction_json.get('entities', [])) == 0:
                    print(f"         ΓÜá∩╕Å  WARNING: No entities found!")
                    print(f"         Full extraction JSON:")
                    import json
                    print(f"         {json.dumps(extraction_json, indent=10)[:1000]}")
                print()
            finally:
                # Clean up temp file
                if os.path.exists(temp_file_path):
                    os.unlink(temp_file_path)
            
            # Update source_document with extracted doc_type
            print(f"         Updating source_document with doc_type: {doc_type}")
            db.client.table("source_document")\
                .update({
                    "doc_type": doc_type,
                    "extracted_at": datetime.now().isoformat()
                })\
                .eq("source_id", source_id)\
                .execute()
            print(f"         source_document updated successfully")
            print()
            
        except Exception as e:
            # Extraction failed, but document is uploaded
            print(f"[STEP 3] FAILED - Document extraction error:")
            print(f"         Error: {str(e)}")
            import traceback
            print(f"         Traceback:")
            print(traceback.format_exc())
            print()
            extraction_json = None
        
        # Step 4 & 5: Write extracted data to database with data_writer_agent (Zhipu AI)
        if extraction_json:
            print("[STEP 4-5] DATA WRITER AGENT - Starting intelligent SQL generation and database write...")
            try:
                from services.data_writer_agent import get_data_writer_agent
                
                data_writer = get_data_writer_agent()
                print("         Calling data_writer.process_document_extraction()...")
                write_result = data_writer.process_document_extraction(
                    extraction_json=extraction_json,
                    source_id=source_id,
                    custom_extraction=custom_extraction
                )
                
                if write_result["success"]:
                    print(f"[STEP 4-5] SUCCESS - Data written to database")
                    print(f"           Rows inserted: {write_result.get('execution_results', {}).get('rows_inserted', 0)}")
                    print()
                    print("="*80)
                    print("PIPELINE COMPLETED SUCCESSFULLY")
                    print("="*80)
                    print()
                else:
                    print(f"[STEP 4-5] PARTIAL FAILURE - Data write had issues")
                    exec_results = write_result.get('execution_results', {})
                    error_msg = exec_results.get('error') or write_result.get('error', 'Unknown error')
                    print(f"           Error: {error_msg}")
                    print(f"           Rows inserted: {exec_results.get('rows_inserted', 0)}/{exec_results.get('total_statements', 0)} statements")
                    
                    # Show failed statement details
                    failed_details = [d for d in exec_results.get('details', []) if not d.get('success', False)]
                    if failed_details:
                        print(f"           Failed statements:")
                        for detail in failed_details[:3]:  # Show up to 3 failures
                            print(f"             - {detail.get('statement', 'N/A')[:80]}...")
                            print(f"               Error: {detail.get('error', 'N/A')}")
                    print()
                
                return {
                    "success": write_result["success"],
                    "source_id": source_id,
                    "file_url": file_url,
                    "doc_type": doc_type,
                    "department": extraction_json.get("department"),
                    "extraction_status": "completed",
                    "data_written": write_result.get("execution_results", {}).get("rows_inserted", 0),
                    "details": write_result
                }
            
            except Exception as e:
                # Data writing failed, but extraction succeeded
                print(f"[STEP 4-5] FAILED - Data writer agent error:")
                print(f"           Error: {str(e)}")
                import traceback
                print(f"           Traceback:")
                print(traceback.format_exc())
                print()
                print("="*80)
                print("PIPELINE FAILED AT DATA WRITING STEP")
                print("="*80)
                print()
                
                return {
                    "success": False,
                    "source_id": source_id,
                    "file_url": file_url,
                    "doc_type": doc_type,
                    "extraction_status": "completed",
                    "write_status": "failed",
                    "error": f"Data writing failed: {str(e)}",
                    "extraction_data": extraction_json
                }
        else:
            # No extraction - just return upload success
            print("[STEP 3] WARNING - Extraction failed or was skipped")
            print("         Returning upload-only success (no data extraction/writing)")
            print()
            print("="*80)
            print("PIPELINE COMPLETED WITH WARNINGS (extraction skipped)")
            print("="*80)
            print()
            
            return {
                "success": True,
                "source_id": source_id,
                "file_url": file_url,
                "doc_type": doc_type,
                "extraction_status": "skipped",
                "message": "Document uploaded successfully. AI extraction skipped or failed."
            }
    
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"ERROR in upload: {error_trace}")
        raise HTTPException(status_code=500, detail=f"Upload process failed: {str(e)}")


@app.get("/api/documents")
async def list_documents(
    doc_type: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
):
    """
    Get list of uploaded documents with optional filtering.
    
    Query params:
    - doc_type: Filter by document type (HR, Sales, Finance, etc.)
    - limit: Max number of results (default 50)
    - offset: Pagination offset (default 0)
    """
    try:
        query = db.client.table("source_document")\
            .select("*")\
            .order("created_at", desc=True)
        
        # Apply filter if doc_type provided
        if doc_type:
            query = query.eq("doc_type", doc_type)
        
        # Apply pagination
        query = query.range(offset, offset + limit - 1)
        
        result = query.execute()
        
        # Get total count
        count_query = db.client.table("source_document").select("count", count="exact")
        if doc_type:
            count_query = count_query.eq("doc_type", doc_type)
        count_result = count_query.execute()
        total = count_result.count if hasattr(count_result, 'count') else len(result.data)
        
        return {
            "documents": result.data,
            "total": total,
            "limit": limit,
            "offset": offset
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list documents: {str(e)}")


@app.get("/api/documents/{source_id}")
async def get_document(source_id: int):
    """Get single document by ID with related records."""
    try:
        # Get document
        doc_result = db.client.table("source_document")\
            .select("*")\
            .eq("source_id", source_id)\
            .single()\
            .execute()
        
        if not doc_result.data:
            raise HTTPException(status_code=404, detail="Document not found")
        
        document = doc_result.data
        
        # Get related records from various tables
        related_records = {}
        
        # Check each table for records linked to this source_id
        tables = ["hr_record", "sales_record", "finance_record", "marketing_record", "supply_record", "legal_policy"]
        
        for table in tables:
            try:
                result = db.client.table(table)\
                    .select("*")\
                    .eq("source_id", source_id)\
                    .execute()
                if result.data:
                    related_records[table] = result.data
            except:
                pass
        
        return {
            "document": document,
            "related_records": related_records
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get document: {str(e)}")


@app.delete("/api/documents/{source_id}")
async def delete_document(source_id: int):
    """Delete a document and its related records."""
    try:
        # Get document to get Cloudinary public_id
        doc_result = db.client.table("source_document")\
            .select("file_path")\
            .eq("source_id", source_id)\
            .single()\
            .execute()
        
        if not doc_result.data:
            raise HTTPException(status_code=404, detail="Document not found")
        
        file_path = doc_result.data["file_path"]
        
        # Extract Cloudinary public_id from URL
        # URL format: https://res.cloudinary.com/cloud_name/resource_type/upload/v123/public_id.ext
        if "cloudinary.com" in file_path:
            try:
                parts = file_path.split("/upload/")
                if len(parts) > 1:
                    public_id_with_ext = "/".join(parts[1].split("/")[1:])
                    public_id = public_id_with_ext.rsplit(".", 1)[0]
                    
                    # Delete from Cloudinary
                    from services.cloudinary_service import get_cloudinary_service
                    cloudinary_service = get_cloudinary_service()
                    cloudinary_service.delete_document(public_id)
            except:
                pass  # Continue even if Cloudinary deletion fails
        
        # Delete from database (CASCADE will remove related records)
        db.client.table("source_document")\
            .delete()\
            .eq("source_id", source_id)\
            .execute()
        
        return {
            "success": True,
            "message": f"Document {source_id} deleted successfully"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete document: {str(e)}")


# --- Routes from feature/salesAgent: campaign, simulators, supply APIs, debate (separate frontend pages) ---


@app.post("/api/sales/campaign-suggestions")
async def get_sales_campaign_suggestions(request: SalesCampaignRequest):
    """
    Suggest campaign/event ideas for the next week based on Tavily news search.
    """
    product = request.product.strip()
    region = (request.region or "Malaysia").strip() or "Malaysia"

    if len(product) < 2:
        raise HTTPException(status_code=422, detail="Product name must be at least 2 characters")

    if not settings.tavily_api_key:
        raise HTTPException(
            status_code=503,
            detail="TAVILY_API_KEY is not configured. Add it to backend/.env first.",
        )

    service = SalesCampaignService(settings.tavily_api_key)

    try:
        result = await service.suggest_campaigns(product=product, region=region)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sales suggestion failed: {str(e)}")


@app.post("/api/simulator/run")
async def run_simulator(request: SimulatorRequest):
    """
    Execute simulator graph and return final result in one response.
    """
    try:
        simulator_agent = _get_simulator_agent()
        initial_state = _build_simulator_initial_state(request)
        result = await asyncio.to_thread(simulator_agent.invoke, initial_state)
        return {"status": "ok", "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Simulator run failed: {str(e)}")


@app.post("/api/simulator/stream")
async def stream_simulator(request: SimulatorRequest):
    """
    Stream simulator updates and tokens as NDJSON.
    """
    simulator_agent = _get_simulator_agent()
    initial_state = _build_simulator_initial_state(request)

    async def event_stream():
        latest_values: dict[str, Any] | None = None
        try:
            yield _ndjson_line({"type": "status", "message": "Simulator stream started."})
            async for part in simulator_agent.astream(
                initial_state,
                stream_mode=["updates", "values", "custom"],
                version="v2",
            ):
                part_type = part.get("type")
                if part_type == "updates":
                    updates = part.get("data", {})
                    nodes = list(updates.keys()) if isinstance(updates, dict) else []
                    if nodes:
                        yield _ndjson_line(
                            {
                                "type": "update",
                                "nodes": nodes,
                                "updates": _safe_json_payload(updates),
                            }
                        )
                elif part_type == "values":
                    values = part.get("data")
                    if isinstance(values, dict):
                        latest_values = values
                elif part_type == "custom":
                    custom_data = part.get("data")
                    if isinstance(custom_data, dict):
                        yield _ndjson_line(
                            {
                                "type": "custom",
                                "event": custom_data.get("event"),
                                "data": _safe_json_payload(custom_data),
                            }
                        )

            if latest_values is not None:
                yield _ndjson_line(
                    {"type": "final", "response": latest_values.get("response"), "state": latest_values}
                )
            else:
                yield _ndjson_line({"type": "final", "response": "Simulation completed."})
        except Exception as e:
            yield _ndjson_line({"type": "error", "error": str(e)})
        finally:
            yield _ndjson_line({"type": "done"})

    return StreamingResponse(event_stream(), media_type="application/x-ndjson")


@app.get("/api/supply-chain/{supply_id}/availability")
async def get_supply_chain_availability(supply_id: int):
    """
    Check a supply record by supply_id and trigger low-inventory notification.
    """
    try:
        insight = await supply_chain_agent.run(
            query="Check supply availability and restock risk",
            context={"supply_id": supply_id, "target_type": "supply_record"},
        )

        if not insight.evidence_used:
            raise HTTPException(status_code=404, detail=f"Supply record {supply_id} not found")

        record = insight.evidence_used[0]["data"]
        threshold = SupplyChainAgent.LOW_INVENTORY_THRESHOLD
        inventory_level = record.get("inventory_level")
        supplier_name = record.get("supplier_name")
        item_name = record.get("item_name")
        unit_cost = record.get("unit_cost")

        is_low_inventory = (
            isinstance(inventory_level, (int, float)) and inventory_level < threshold
        )

        notification = {
            "triggered": is_low_inventory,
            "message": (
                f"Restock required for ongoing finish item '{item_name}'. "
                f"Supplier: {supplier_name}. Unit price: RM {float(unit_cost):,.2f}. "
                f"Inventory available: {inventory_level} (threshold: {threshold})."
                if is_low_inventory
                else "Inventory level is sufficient. Restock notification not triggered."
            ),
            "item_name": item_name,
            "supplier_name": supplier_name,
            "unit_price_per_unit": float(unit_cost) if unit_cost is not None else None,
            "inventory_available": inventory_level,
            "threshold": threshold,
        }

        return {
            "supply_id": supply_id,
            "availability": {
                "item_name": item_name,
                "supplier_name": supplier_name,
                "inventory_available": inventory_level,
                "unit_price_per_unit": float(unit_cost) if unit_cost is not None else None,
            },
            "notification": notification,
            "agent_insight": insight.model_dump(),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Supply-chain availability check failed: {str(e)}")


@app.get("/api/supply-chain/availability")
async def get_all_supply_chain_availability():
    """
    Retrieve all supply records and evaluate inventory threshold notification.
    """
    try:
        threshold = SupplyChainAgent.LOW_INVENTORY_THRESHOLD
        records = await db.get_all_supply_records()

        evaluations = []
        low_inventory_count = 0

        for record in records:
            inventory_level = record.get("inventory_level")
            supplier_name = record.get("supplier_name")
            item_name = record.get("item_name")
            unit_cost = record.get("unit_cost")
            supply_rid = record.get("supply_id")

            is_low_inventory = (
                isinstance(inventory_level, (int, float)) and inventory_level < threshold
            )
            if is_low_inventory:
                low_inventory_count += 1

            evaluations.append(
                {
                    "supply_id": supply_rid,
                    "item_name": item_name,
                    "supplier_name": supplier_name,
                    "inventory_available": inventory_level,
                    "unit_price_per_unit": float(unit_cost) if unit_cost is not None else None,
                    "notification": {
                        "triggered": is_low_inventory,
                        "message": (
                            f"Restock required for ongoing finish item '{item_name}'. "
                            f"Supplier: {supplier_name}. Unit price: RM {float(unit_cost):,.2f}. "
                            f"Inventory available: {inventory_level} (threshold: {threshold})."
                            if is_low_inventory
                            else "Inventory level is sufficient. Restock notification not triggered."
                        ),
                        "threshold": threshold,
                    },
                }
            )

        return {
            "threshold": threshold,
            "total_records": len(evaluations),
            "low_inventory_records": low_inventory_count,
            "records": evaluations,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Supply-chain availability list check failed: {str(e)}")


@app.post("/api/deep-simulator/run")
async def run_deep_simulator(request: DeepSimulatorRequest):
    """
    Execute deep 2D simulator and return final result in one response.
    """
    try:
        deep_simulator_agent = _get_deep_simulator_agent()
        initial_state = _build_deep_simulator_initial_state(request)
        result = await asyncio.to_thread(deep_simulator_agent.invoke, initial_state)
        return {"status": "ok", "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Deep simulator run failed: {str(e)}")


@app.post("/api/deep-simulator/stream")
async def stream_deep_simulator(request: DeepSimulatorRequest):
    """
    Stream deep simulator world updates and subagent chunks as NDJSON.
    """
    deep_simulator_agent = _get_deep_simulator_agent()
    initial_state = _build_deep_simulator_initial_state(request)

    async def event_stream():
        try:
            async for event in deep_simulator_agent.astream(initial_state):
                yield _ndjson_line(_safe_json_payload(event))
        except Exception as e:
            yield _ndjson_line({"type": "error", "error": str(e)})
            yield _ndjson_line({"type": "done"})

    return StreamingResponse(event_stream(), media_type="application/x-ndjson")


@app.post("/api/network-simulator/run")
async def run_network_simulator(request: NetworkSimulatorRequest):
    """
    Execute network simulation and return final response in one payload.
    """
    try:
        network_simulator_agent = _get_network_simulator_agent()
        initial_state = _build_network_simulator_initial_state(request)
        result = await asyncio.to_thread(network_simulator_agent.invoke, initial_state)
        return {"status": "ok", "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Network simulator run failed: {str(e)}")


@app.post("/api/simulator/sales-supply-debate")
async def run_sales_supply_debate_simulator(request: SalesSupplyDebateRequest):
    """
    Simulate a debate loop between Sales agent (AI-1) and Supply Chain agent (AI-2)
    based on supply_record.item_name and inventory constraints.
    """
    try:
        service = SalesSupplyDebateService(db)
        result = await service.run(
            max_rounds=request.max_rounds,
            item_name=request.item_name,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sales-supply debate simulation failed: {str(e)}")


@app.post("/api/network-simulator/stream")
async def stream_network_simulator(request: NetworkSimulatorRequest):
    """
    Stream network simulation events as NDJSON.
    """
    network_simulator_agent = _get_network_simulator_agent()
    initial_state = _build_network_simulator_initial_state(request)

    async def event_stream():
        try:
            async for event in network_simulator_agent.astream(initial_state):
                yield _ndjson_line(_safe_json_payload(event))
        except Exception as e:
            yield _ndjson_line({"type": "error", "error": str(e)})
            yield _ndjson_line({"type": "done"})

    return StreamingResponse(event_stream(), media_type="application/x-ndjson")


@app.post("/api/network-simulator/{session_id}/shock")
async def add_network_simulator_shock(session_id: str, request: NetworkShockRequest):
    """
    Queue shock event for the next stream tick of the given session.
    """
    try:
        _ensure_network_simulator_import_path()
        from network_simulation_agent.src.engine import SESSION_STORE
        from network_simulation_agent.src.schema import ShockEvent

        shock = ShockEvent(
            shock_type=request.shock_type,
            summary=request.summary,
            severity=request.severity,
            targets=request.targets,
        )
        SESSION_STORE.queue_shock(session_id, shock)
        return {"status": "ok", "session_id": session_id, "queued_shock": shock.model_dump(mode="json")}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to queue shock: {str(e)}")


@app.post("/api/network-simulator/{session_id}/observer-chat")
async def network_simulator_observer_chat(session_id: str, request: ObserverChatRequest):
    """
    Return observer answer grounded to persisted session artifacts.
    """
    try:
        _ensure_network_simulator_import_path()
        from network_simulation_agent.src.engine import SESSION_STORE
        from network_simulation_agent.src.observer import build_observer_answer

        summary = SESSION_STORE.get_observer_report(session_id)
        backend_root = Path(__file__).resolve().parent
        base_dir = backend_root / "network_simulation_agent"
        response = build_observer_answer(
            base_dir=base_dir,
            session_id=session_id,
            question=request.question,
            summary=summary or "",
        )
        return {"status": "ok", "session_id": session_id, **response}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Observer chat failed: {str(e)}")


@app.get("/api/network-simulator/{session_id}/storyline")
async def download_network_simulator_storyline(session_id: str):
    """
    Download final storyline markdown artifact for a completed network simulation session.
    """
    try:
        _ensure_network_simulator_import_path()
        from network_simulation_agent.src.observer import storyline_path

        backend_root = Path(__file__).resolve().parent
        base_dir = backend_root / "network_simulation_agent"
        target = storyline_path(base_dir=base_dir, session_id=session_id)
        if not target.exists():
            raise HTTPException(status_code=404, detail="Storyline artifact not found for this session.")
        return FileResponse(
            path=target,
            filename=f"{session_id}_storyline.md",
            media_type="text/markdown; charset=utf-8",
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Storyline download failed: {str(e)}")


# ============================================
# Run Server
# ============================================

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.port,
        reload=True  # Auto-reload on code changes (development only)
    )

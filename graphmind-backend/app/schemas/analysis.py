from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, Field

class GraphNodeMetrics(BaseModel):
    dependency_count: int = 0
    dependents_count: int = 0
    call_count: int = 0
    complexity: Optional[float] = None
    line_count: int = 0

class GraphNodeFlags(BaseModel):
    is_dead_code: bool = False
    has_circular_dep: bool = False
    is_entry_point: bool = False

class GraphNode(BaseModel):
    id: str
    label: str
    type: str
    file_path: str
    qualified_name: Optional[str] = None
    metrics: GraphNodeMetrics
    flags: GraphNodeFlags

class GraphEdge(BaseModel):
    id: str
    source: str
    target: str
    type: str
    weight: int = 1

class GraphResponse(BaseModel):
    nodes: List[GraphNode]
    edges: List[GraphEdge]
    circular_cycles: List[List[str]] = []
    stats: dict

class GraphNodeDetail(BaseModel):
    id: str
    label: str
    type: str
    file_path: str
    qualified_name: Optional[str] = None
    signature: Optional[str] = None
    docstring: Optional[str] = None
    metrics: GraphNodeMetrics
    flags: GraphNodeFlags
    dependencies: List[GraphNode] = []
    dependents: List[GraphNode] = []

class PathResponse(BaseModel):
    path: List[str]
    distance: int

class ImpactAnalysisResponse(BaseModel):
    symbol_id: str
    risk_score: float
    risk_level: str
    directly_affected: List[str]
    all_affected: List[str]
    affected_routes: List[str]
    affected_files: List[str]
    critical_paths: dict
    summary: str

class DeadCodeReport(BaseModel):
    dead_functions: List[GraphNode]
    dead_classes: List[GraphNode]
    dead_files: List[GraphNode]
    circular_cycles: List[List[str]]
    estimated_removal_savings: int

class RepositorySummary(BaseModel):
    statistics: dict
    architecture_type: str
    key_modules: List[str]

class RepositoryStats(BaseModel):
    total_files: int
    total_symbols: int
    language_breakdown: dict
    avg_complexity: Optional[float] = None
    max_complexity_symbol: Optional[dict] = None
    total_relationships: int
    circular_dep_count: int
    dead_code_count: int
    entry_points: int
    most_depended_on: List[dict]
    most_complex: List[dict]

class RefactoringIssue(BaseModel):
    id: str
    type: str
    severity: str
    symbol_id: str
    symbol_name: str
    file_path: str
    metrics: dict
    ai_explanation: Optional[str] = None
    ai_suggestion: Optional[str] = None

class RefactoringReport(BaseModel):
    issues: List[RefactoringIssue]
    summary: str

class AnalysisReportResponse(BaseModel):
    id: UUID
    repository_id: UUID
    report_type: str
    content: dict
    generated_at: str
    class Config:
        from_attributes = True

class ChatRequest(BaseModel):
    message: str
    user_id: UUID

class ChatResponse(BaseModel):
    message: str
    context_symbols: List[str] = []

class ChatHistoryResponse(BaseModel):
    messages: List[dict]
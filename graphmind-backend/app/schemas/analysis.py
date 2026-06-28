from datetime import datetime
from typing import Optional
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
    metrics: GraphNodeMetrics
    flags: GraphNodeFlags


class GraphEdge(BaseModel):
    id: str
    source: str
    target: str
    type: str
    weight: int = 1


class GraphResponse(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    circular_cycles: list[list[str]] = []
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
    dependencies: list[GraphNode] = []
    dependents: list[GraphNode] = []


class PathResponse(BaseModel):
    path: list[str]
    distance: int


class ImpactAnalysisResponse(BaseModel):
    symbol_id: str
    risk_score: float
    risk_level: str
    directly_affected: list[str]
    all_affected: list[str]
    affected_routes: list[str]
    affected_files: list[str]
    critical_paths: dict[str, list[str]]
    summary_text: str


class DeadCodeReport(BaseModel):
    dead_functions: list[GraphNode]
    dead_classes: list[GraphNode]
    dead_files: list[GraphNode]
    circular_cycles: list[list[str]]
    estimated_removal_savings: int


class RepositorySummary(BaseModel):
    stats: RepositoryStats
    ai_narrative: str
    architecture_type: str
    key_modules: list[str]
    key_observations: list[str]
    technology_stack: list[str]


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
    most_depended_on: list[dict]
    most_complex: list[dict]


class RefactoringIssue(BaseModel):
    id: str
    type: str  # god_class | high_coupling | long_method | low_cohesion
    severity: str  # critical | high | medium | low
    symbol_id: str
    symbol_name: str
    file_path: str
    metrics: dict
    ai_explanation: Optional[str] = None
    ai_suggestion: Optional[str] = None


class RefactoringReport(BaseModel):
    issues: list[RefactoringIssue]
    summary: str


class AnalysisReportResponse(BaseModel):
    id: UUID
    repository_id: UUID
    report_type: str
    content: dict
    generated_at: datetime

    class Config:
        from_attributes = True
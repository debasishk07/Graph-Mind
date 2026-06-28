import asyncio
from uuid import UUID
from typing import List, Dict, Set, Optional
from dataclasses import dataclass

from celery import shared_task
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

import networkx as nx

from app.config import get_settings
from app.database import async_session_maker
from app.models.repository import Repository, RepositoryStatus
from app.models.symbol import Symbol, SymbolType
from app.models.relationship import Relationship, RelationshipType
from app.models.analysis_report import AnalysisReport, ReportType
from app.workers.celery_app import celery_app
from app.utils.socketio import emit_progress

settings = get_settings()


@dataclass
class ImpactResult:
    symbol_id: str
    risk_score: float
    risk_level: str
    directly_affected: List[str]
    all_affected: List[str]
    affected_routes: List[str]
    affected_files: List[str]
    critical_paths: Dict[str, List[str]]
    summary: str


@dataclass
class DeadCodeResult:
    dead_functions: List[Dict]
    dead_classes: List[Dict]
    dead_files: List[Dict]
    circular_cycles: List[List[str]]
    estimated_savings: int


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def analyze_repository_task(self, repository_id: str):
    """Run all analysis tasks for a repository."""
    asyncio.run(_analyze_repository_async(UUID(repository_id)))


async def _analyze_repository_async(repository_id: UUID):
    """Run all analyses for a repository."""
    async with async_session_maker() as db:
        # Get repository
        result = await db.execute(
            select(Repository).where(Repository.id == repository_id)
        )
        repository = result.scalar_one_or_none()
        if not repository:
            return

        # Build graph
        G = await build_graph(db, repository_id)
        
        # Run analyses
        await run_dead_code_analysis(db, repository, G)
        await run_circular_dep_analysis(db, repository, G)
        await run_impact_analysis(db, repository, G)
        await generate_summary_report(db, repository, G)

        # Update repository
        repository.status = RepositoryStatus.READY
        repository.status_message = "All analyses complete"
        repository.analysis_progress = 100
        await db.commit()

        await emit_progress(str(repository_id), "analysis", 100, "All analyses complete")


async def build_graph(db: AsyncSession, repository_id: UUID) -> nx.DiGraph:
    """Build NetworkX graph from repository relationships."""
    G = nx.DiGraph()
    
    # Get all symbols
    result = await db.execute(
        select(Symbol).where(Symbol.repository_id == repository_id)
    )
    symbols = result.scalars().all()
    
    for symbol in symbols:
        G.add_node(
            str(symbol.id),
            name=symbol.name,
            qualified_name=symbol.qualified_name,
            type=symbol.symbol_type.value,
            file_id=str(symbol.file_id),
            complexity=symbol.complexity_score or 1.0,
            is_exported=symbol.is_exported,
            is_dead_code=symbol.is_dead_code,
        )
    
    # Get all relationships
    result = await db.execute(
        select(Relationship).where(Relationship.repository_id == repository_id)
    )
    relationships = result.scalars().all()
    
    for rel in relationships:
        G.add_edge(
            str(rel.source_symbol_id),
            str(rel.target_symbol_id),
            type=rel.relationship_type.value,
            weight=rel.weight,
            is_dynamic=rel.is_dynamic,
        )
    
    return G


async def run_dead_code_analysis(db: AsyncSession, repository: Repository, G: nx.DiGraph):
    """Detect dead code (unreachable from entry points)."""
    await emit_progress(str(repository.id), "dead_code", 5, "Finding entry points...")
    
    # Find entry points: routes, exported symbols, main functions, test files
    entry_points = set()
    for node_id, data in G.nodes(data=True):
        if data["type"] in ("route", "model") or data["is_exported"]:
            entry_points.add(node_id)
    
    # Also add symbols from test files as entry points (they call the code)
    # And any symbol with no incoming edges but has outgoing (potential library entry)
    for node_id in G.nodes():
        if G.in_degree(node_id) == 0 and G.out_degree(node_id) > 0:
            entry_points.add(node_id)
    
    # Find all reachable nodes from entry points
    reachable = set()
    for ep in entry_points:
        if ep in G:
            reachable.update(nx.descendants(G, ep))
            reachable.add(ep)
    
    # Dead code = nodes not reachable from any entry point
    all_nodes = set(G.nodes())
    dead_nodes = all_nodes - reachable
    
    # Categorize dead code
    dead_functions = []
    dead_classes = []
    
    for node_id in dead_nodes:
        data = G.nodes[node_id]
        if data["type"] in ("function", "method"):
            dead_functions.append({
                "symbol_id": node_id,
                "name": data["name"],
                "qualified_name": data["qualified_name"],
                "type": data["type"],
                "file_id": data["file_id"],
                "complexity": data["complexity"],
            })
        elif data["type"] == "class":
            dead_classes.append({
                "symbol_id": node_id,
                "name": data["name"],
                "qualified_name": data["qualified_name"],
                "type": data["type"],
                "file_id": data["file_id"],
                "complexity": data["complexity"],
            })
    
    # Find orphan files (files with only dead code)
    file_dead_counts = {}
    for node_id in dead_nodes:
        file_id = G.nodes[node_id]["file_id"]
        file_dead_counts[file_id] = file_dead_counts.get(file_id, 0) + 1
    
    # Get file info for dead files
    dead_files = []
    for file_id, count in file_dead_counts.items():
        result = await db.execute(select(Symbol).where(Symbol.file_id == UUID(file_id)).limit(1))
        symbol = result.scalar_one_or_none()
        if symbol and symbol.file:
            total_symbols = sum(1 for n in G.nodes() if G.nodes[n]["file_id"] == file_id)
            if count == total_symbols:
                dead_files.append({
                    "file_id": file_id,
                    "path": symbol.file.path,
                    "symbol_count": count,
                })
    
    # Calculate estimated line savings
    estimated_savings = sum(
        s["complexity"] * 10 for s in dead_functions + dead_classes
    )
    
    # Detect circular dependencies
    await emit_progress(str(repository.id), "dead_code", 50, "Detecting circular dependencies...")
    cycles = list(nx.simple_cycles(G))
    circular_cycles = [cycle for cycle in cycles if len(cycle) > 1][:50]  # Limit to 50
    
    # Save report
    report = AnalysisReport(
        repository_id=repository.id,
        report_type=ReportType.DEAD_CODE,
        content={
            "dead_functions": dead_functions,
            "dead_classes": dead_classes,
            "dead_files": dead_files,
            "circular_cycles": circular_cycles,
            "estimated_savings": int(estimated_savings),
            "entry_points_count": len(entry_points),
            "total_symbols": len(all_nodes),
            "reachable_symbols": len(reachable),
            "dead_symbols": len(dead_nodes),
        },
    )
    db.add(report)
    await db.commit()
    
    await emit_progress(str(repository.id), "dead_code", 100, f"Found {len(dead_nodes)} dead symbols")


async def run_circular_dep_analysis(db: AsyncSession, repository: Repository, G: nx.DiGraph):
    """Analyze circular dependencies in detail."""
    await emit_progress(str(repository.id), "circular_deps", 10, "Analyzing circular dependencies...")
    
    # Find strongly connected components
    sccs = list(nx.strongly_connected_components(G))
    circular_sccs = [scc for scc in sccs if len(scc) > 1]
    
    # Get details for each SCC
    scc_details = []
    for scc in circular_sccs:
        nodes_data = []
        for node_id in scc:
            data = G.nodes[node_id]
            nodes_data.append({
                "symbol_id": node_id,
                "name": data["name"],
                "qualified_name": data["qualified_name"],
                "type": data["type"],
                "file_id": data["file_id"],
            })
        
        # Find edges within SCC
        internal_edges = []
        for u in scc:
            for v in scc:
                if G.has_edge(u, v):
                    edge_data = G.get_edge_data(u, v)
                    internal_edges.append({
                        "source": u,
                        "target": v,
                        "type": edge_data["type"],
                    })
        
        scc_details.append({
            "size": len(scc),
            "nodes": nodes_data,
            "internal_edges": internal_edges,
        })
    
    # Save report
    report = AnalysisReport(
        repository_id=repository.id,
        report_type=ReportType.IMPACT,  # Reuse for circular deps
        content={
            "circular_sccs": scc_details,
            "total_circular_groups": len(circular_sccs),
            "total_symbols_in_cycles": sum(len(scc) for scc in circular_sccs),
        },
    )
    db.add(report)
    await db.commit()
    
    await emit_progress(str(repository.id), "circular_deps", 100, f"Found {len(circular_sccs)} circular dependency groups")


async def run_impact_analysis(db: AsyncSession, repository: Repository, G: nx.DiGraph):
    """Pre-compute impact analysis for high-value symbols."""
    await emit_progress(str(repository.id), "impact", 10, "Computing impact scores...")
    
    # Calculate impact for all symbols (or just important ones)
    # Focus on: classes, routes, exported functions
    important_nodes = [
        n for n, d in G.nodes(data=True)
        if d["type"] in ("class", "route", "function") and (d["is_exported"] or d["type"] == "route")
    ]
    
    impact_results = {}
    for node_id in important_nodes:
        try:
            # Downstream impact (what this affects)
            downstream = nx.descendants(G, node_id)
            
            # Upstream dependencies (what depends on this)
            upstream = nx.ancestors(G, node_id)
            
            # Categorize affected nodes
            affected_routes = [
                n for n in downstream 
                if G.nodes[n]["type"] == "route"
            ]
            affected_files = list(set(
                G.nodes[n]["file_id"] for n in downstream
            ))
            
            # Risk score
            risk_score = min(10.0, (
                len(downstream) * 0.1 + 
                len(affected_routes) * 2.0 + 
                len(upstream) * 0.05
            ))
            
            if risk_score > 2.0:  # Only save significant impacts
                impact_results[node_id] = {
                    "symbol_id": node_id,
                    "name": G.nodes[node_id]["name"],
                    "risk_score": round(risk_score, 2),
                    "risk_level": "critical" if risk_score > 7 else "high" if risk_score > 4 else "medium" if risk_score > 2 else "low",
                    "directly_affected": list(G.successors(node_id))[:20],
                    "all_affected_count": len(downstream),
                    "affected_routes": affected_routes[:10],
                    "affected_files": affected_files[:10],
                    "dependents_count": len(upstream),
                }
        except Exception as e:
            print(f"Impact analysis error for {node_id}: {e}")
            continue
    
    # Save top impacts
    report = AnalysisReport(
        repository_id=repository.id,
        report_type=ReportType.IMPACT,
        content={
            "high_impact_symbols": sorted(
                impact_results.values(), 
                key=lambda x: x["risk_score"], 
                reverse=True
            )[:50],
            "total_analyzed": len(important_nodes),
        },
    )
    db.add(report)
    await db.commit()
    
    await emit_progress(str(repository.id), "impact", 100, f"Computed impact for {len(impact_results)} symbols")


async def generate_summary_report(db: AsyncSession, repository: Repository, G: nx.DiGraph):
    """Generate AI-powered repository summary."""
    await emit_progress(str(repository.id), "summary", 10, "Generating summary...")
    
    # Collect statistics
    stats = {
        "total_nodes": G.number_of_nodes(),
        "total_edges": G.number_of_edges(),
        "node_types": {},
        "avg_complexity": 0,
        "max_complexity": 0,
        "most_connected": [],
        "languages": {},
    }
    
    complexities = []
    for node_id, data in G.nodes(data=True):
        ntype = data["type"]
        stats["node_types"][ntype] = stats["node_types"].get(ntype, 0) + 1
        complexities.append(data["complexity"])
    
    stats["avg_complexity"] = round(sum(complexities) / len(complexities), 2) if complexities else 0
    stats["max_complexity"] = round(max(complexities), 2) if complexities else 0
    
    # Most connected nodes (by degree)
    degrees = [(n, G.degree(n)) for n in G.nodes()]
    top_connected = sorted(degrees, key=lambda x: x[1], reverse=True)[:10]
    stats["most_connected"] = [
        {"symbol_id": n, "degree": d, "name": G.nodes[n]["name"]}
        for n, d in top_connected
    ]
    
    # Detect architecture pattern
    architecture = detect_architecture(G)
    
    # Save summary report
    report = AnalysisReport(
        repository_id=repository.id,
        report_type=ReportType.SUMMARY,
        content={
            "statistics": stats,
            "architecture_type": architecture,
            "key_modules": identify_modules(G),
        },
    )
    db.add(report)
    
    # Update repository with computed values
    repository.complexity_score = stats["avg_complexity"]
    repository.architecture_type = architecture
    await db.commit()
    
    await emit_progress(str(repository.id), "summary", 100, "Summary generated")


def detect_architecture(G: nx.DiGraph) -> str:
    """Detect architecture pattern from graph structure."""
    # Simple heuristics
    node_types = {}
    for _, data in G.nodes(data=True):
        node_types[data["type"]] = node_types.get(data["type"], 0) + 1
    
    route_count = node_types.get("route", 0)
    model_count = node_types.get("model", 0)
    service_count = node_types.get("class", 0)  # Approximate
    
    if route_count > 10 and model_count > 5:
        return "MVC"
    elif route_count > 20:
        return "Microservices"
    elif service_count > 30:
        return "Layered"
    else:
        return "Modular"


def identify_modules(G: nx.DiGraph) -> List[str]:
    """Identify key modules from graph structure."""
    # Group by file path prefix
    modules = {}
    for node_id, data in G.nodes(data=True):
        file_id = data.get("file_id", "")
        if file_id:
            # Extract top-level directory
            parts = file_id.split("/")
            if parts:
                module = parts[0]
                modules[module] = modules.get(module, 0) + 1
    
    # Return top modules
    return sorted(modules.keys(), key=lambda k: modules[k], reverse=True)[:10]
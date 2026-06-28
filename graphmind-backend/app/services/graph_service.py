from typing import List, Dict, Optional, Set
from uuid import UUID
from dataclasses import dataclass

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

import networkx as nx

from app.models.repository import Repository
from app.models.symbol import Symbol, SymbolType
from app.models.relationship import Relationship, RelationshipType
from app.models.file import File
from app.models.analysis_report import AnalysisReport, ReportType


@dataclass
class GraphNode:
    id: str
    label: str
    type: str
    file_path: str
    qualified_name: Optional[str]
    metrics: Dict
    flags: Dict


@dataclass
class GraphEdge:
    id: str
    source: str
    target: str
    type: str
    weight: int


class GraphService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def build_graph(self, repository_id: UUID) -> nx.DiGraph:
        """Build NetworkX graph from repository data."""
        G = nx.DiGraph()
        
        # Get all symbols with file info
        result = await self.db.execute(
            select(Symbol)
            .options(selectinload(Symbol.file))
            .where(Symbol.repository_id == repository_id)
        )
        symbols = result.scalars().all()
        
        for symbol in symbols:
            G.add_node(
                str(symbol.id),
                name=symbol.name,
                qualified_name=symbol.qualified_name,
                type=symbol.symbol_type.value,
                file_id=str(symbol.file_id),
                file_path=symbol.file.path if symbol.file else "unknown",
                language=symbol.file.language if symbol.file else "unknown",
                complexity=symbol.complexity_score or 1.0,
                is_exported=symbol.is_exported,
                is_dead_code=symbol.is_dead_code,
                is_entry_point=symbol.file.is_entry_point if symbol.file else False,
                start_line=symbol.start_line,
                end_line=symbol.end_line,
                signature=symbol.signature,
                docstring=symbol.docstring,
            )
        
        # Get all relationships
        result = await self.db.execute(
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
                line_number=rel.line_number,
            )
        
        return G

    async def get_graph_data(
        self,
        repository_id: UUID,
        depth: int = 2,
        focus: Optional[str] = None,
        filter_types: Optional[List[str]] = None,
    ) -> Dict:
        """Get graph data for visualization."""
        G = await self.build_graph(repository_id)
        
        # Filter nodes
        nodes_to_include = set()
        if focus and focus in G:
            # Include focus node and its neighbors up to depth
            nodes_to_include.add(focus)
            for d in range(1, depth + 1):
                # Successors (dependencies)
                for node in nx.single_source_shortest_path_length(G, focus, cutoff=d):
                    nodes_to_include.add(node)
                # Predecessors (dependents)
                for node in nx.single_source_shortest_path_length(G.reverse(), focus, cutoff=d):
                    nodes_to_include.add(node)
        else:
            nodes_to_include = set(G.nodes())
        
        # Apply type filter
        if filter_types:
            nodes_to_include = {
                n for n in nodes_to_include 
                if G.nodes[n]["type"] in filter_types
            }
        
        # Build subgraph
        subgraph = G.subgraph(nodes_to_include)
        
        # Convert to response format
        nodes = []
        for node_id, data in subgraph.nodes(data=True):
            in_degree = subgraph.in_degree(node_id)
            out_degree = subgraph.out_degree(node_id)
            
            nodes.append(GraphNode(
                id=node_id,
                label=data["name"],
                type=data["type"],
                file_path=data["file_path"],
                qualified_name=data.get("qualified_name"),
                metrics={
                    "dependency_count": out_degree,
                    "dependents_count": in_degree,
                    "call_count": 0,  # TODO: compute from CALLS edges
                    "complexity": data["complexity"],
                    "line_count": (data.get("end_line", 0) or 0) - (data.get("start_line", 0) or 0) + 1,
                },
                flags={
                    "is_dead_code": data["is_dead_code"],
                    "has_circular_dep": self._in_cycle(subgraph, node_id),
                    "is_entry_point": data["is_entry_point"] or data["type"] == "route",
                },
            ))
        
        edges = []
        for u, v, data in subgraph.edges(data=True):
            edges.append(GraphEdge(
                id=f"{u}->{v}",
                source=u,
                target=v,
                type=data["type"],
                weight=data["weight"],
            ))
        
        # Find circular dependencies
        cycles = list(nx.simple_cycles(subgraph))
        circular_cycles = [list(cycle) for cycle in cycles if len(cycle) > 1][:20]
        
        return {
            "nodes": [n.__dict__ for n in nodes],
            "edges": [e.__dict__ for e in edges],
            "circular_cycles": circular_cycles,
            "stats": {
                "total_nodes": len(nodes),
                "total_edges": len(edges),
                "avg_complexity": sum(n.metrics["complexity"] for n in nodes) / len(nodes) if nodes else 0,
                "circular_dep_count": len(circular_cycles),
                "dead_code_count": sum(1 for n in nodes if n.flags["is_dead_code"]),
            },
        }

    def _in_cycle(self, G: nx.DiGraph, node: str) -> bool:
        """Check if node is part of a cycle."""
        try:
            return nx.has_path(G, node, node) and any(
                nx.has_path(G, node, succ) and nx.has_path(G, succ, node)
                for succ in G.successors(node)
            )
        except:
            return False

    async def get_node_detail(self, repository_id: UUID, symbol_id: str) -> Optional[Dict]:
        """Get detailed info for a single node."""
        G = await self.build_graph(repository_id)
        
        if symbol_id not in G:
            return None
        
        data = G.nodes[symbol_id]
        
        # Get dependencies (outgoing)
        dependencies = []
        for succ in G.successors(symbol_id):
            succ_data = G.nodes[succ]
            dependencies.append({
                "id": succ,
                "label": succ_data["name"],
                "type": succ_data["type"],
                "file_path": succ_data["file_path"],
                "relationship_type": G.edges[symbol_id, succ]["type"],
            })
        
        # Get dependents (incoming)
        dependents = []
        for pred in G.predecessors(symbol_id):
            pred_data = G.nodes[pred]
            dependents.append({
                "id": pred,
                "label": pred_data["name"],
                "type": pred_data["type"],
                "file_path": pred_data["file_path"],
                "relationship_type": G.edges[pred, symbol_id]["type"],
            })
        
        return {
            "id": symbol_id,
            "label": data["name"],
            "type": data["type"],
            "file_path": data["file_path"],
            "qualified_name": data.get("qualified_name"),
            "signature": data.get("signature"),
            "docstring": data.get("docstring"),
            "metrics": {
                "dependency_count": G.out_degree(symbol_id),
                "dependents_count": G.in_degree(symbol_id),
                "complexity": data["complexity"],
            },
            "flags": {
                "is_dead_code": data["is_dead_code"],
                "has_circular_dep": self._in_cycle(G, symbol_id),
                "is_entry_point": data["is_entry_point"] or data["type"] == "route",
            },
            "dependencies": dependencies,
            "dependents": dependents,
        }

    async def find_path(self, repository_id: UUID, from_id: str, to_id: str) -> Optional[List[str]]:
        """Find shortest path between two nodes."""
        G = await self.build_graph(repository_id)
        
        if from_id not in G or to_id not in G:
            return None
        
        try:
            path = nx.shortest_path(G, from_id, to_id)
            return path
        except nx.NetworkXNoPath:
            return None

    async def get_impact_analysis(self, repository_id: UUID, symbol_id: str) -> Optional[Dict]:
        """Get impact analysis for a symbol."""
        G = await self.build_graph(repository_id)
        
        if symbol_id not in G:
            return None
        
        # Downstream (what this affects)
        downstream = nx.descendants(G, symbol_id)
        
        # Upstream (what depends on this)
        upstream = nx.ancestors(G, symbol_id)
        
        # Categorize
        affected_routes = [n for n in downstream if G.nodes[n]["type"] == "route"]
        affected_files = list(set(G.nodes[n]["file_id"] for n in downstream))
        
        # Critical paths to routes
        critical_paths = {}
        for route in affected_routes[:5]:
            try:
                path = nx.shortest_path(G, symbol_id, route)
                critical_paths[route] = path
            except nx.NetworkXNoPath:
                pass
        
        # Risk score
        risk_score = min(10.0, len(downstream) * 0.1 + len(affected_routes) * 2.0 + len(upstream) * 0.05)
        
        return {
            "symbol_id": symbol_id,
            "risk_score": round(risk_score, 2),
            "risk_level": "critical" if risk_score > 7 else "high" if risk_score > 4 else "medium" if risk_score > 2 else "low",
            "directly_affected": list(G.successors(symbol_id)),
            "all_affected": list(downstream),
            "affected_routes": affected_routes,
            "affected_files": affected_files,
            "critical_paths": critical_paths,
            "summary": f"This symbol affects {len(downstream)} downstream symbols including {len(affected_routes)} routes.",
        }

    async def get_dead_code_report(self, repository_id: UUID) -> Dict:
        """Get dead code analysis report."""
        # Try to get from cached report first
        result = await self.db.execute(
            select(AnalysisReport)
            .where(AnalysisReport.repository_id == repository_id)
            .where(AnalysisReport.report_type == ReportType.DEAD_CODE)
            .order_by(AnalysisReport.generated_at.desc())
            .limit(1)
        )
        report = result.scalar_one_or_none()
        
        if report:
            return report.content
        
        # Compute on the fly
        G = await self.build_graph(repository_id)
        
        # Find entry points
        entry_points = {
            n for n, d in G.nodes(data=True)
            if d["type"] == "route" or d["is_exported"] or d["is_entry_point"]
        }
        
        # Find reachable
        reachable = set()
        for ep in entry_points:
            if ep in G:
                reachable.update(nx.descendants(G, ep))
                reachable.add(ep)
        
        dead_nodes = set(G.nodes()) - reachable
        
        dead_functions = []
        dead_classes = []
        for node_id in dead_nodes:
            data = G.nodes[node_id]
            if data["type"] in ("function", "method"):
                dead_functions.append({
                    "id": node_id,
                    "label": data["name"],
                    "type": data["type"],
                    "file_path": data["file_path"],
                })
            elif data["type"] == "class":
                dead_classes.append({
                    "id": node_id,
                    "label": data["name"],
                    "type": data["type"],
                    "file_path": data["file_path"],
                })
        
        return {
            "dead_functions": dead_functions,
            "dead_classes": dead_classes,
            "dead_files": [],
            "circular_cycles": [list(c) for c in nx.simple_cycles(G) if len(c) > 1][:20],
            "estimated_removal_savings": len(dead_nodes) * 10,
        }

    async def get_layers(self, repository_id: UUID) -> Dict:
        """Get architecture layer view."""
        G = await self.build_graph(repository_id)
        
        # Classify nodes into layers
        layers = {
            "presentation": [],
            "service": [],
            "repository": "repository": [],
            "model": [],
            "utility": [],
            "unknown": [],
        }
        
        LAYER_PATTERNS = {
            "presentation": ["controller", "handler", "resolver", "view", "page", "component", "route"],
            "service": ["service", "manager", "orchestrator", "usecase", "interactor", "business"],
            "repository": ["repository", "repo", "dao", "store", "gateway", "data"],
            "model": ["model", "entity", "schema", "dto", "entity"],
            "utility": ["util", "helper", "lib", "common", "shared", "config"],
        }
        
        for node_id, data in G.nodes(data=True):
            qualified = (data.get("qualified_name") or "").lower()
            file_path = data.get("file_path", "").lower()
            classified = False
            
            for layer, patterns in LAYER_PATTERNS.items():
                if any(p in qualified or p in file_path for p in patterns):
                    layers[layer].append({
                        "id": node_id,
                        "label": data["name"],
                        "type": data["type"],
                        "file_path": data["file_path"],
                    })
                    classified = True
                    break
            
            if not classified:
                layers["unknown"].append({
                    "id": node_id,
                    "label": data["name"],
                    "type": data["type"],
                    "file_path": data["file_path"],
                })
        
        # Build cross-layer edges
        cross_edges = []
        for u, v, data in G.edges(data=True):
            u_layer = self._get_layer(layers, u)
            v_layer = self._get_layer(layers, v)
            if u_layer != v_layer:
                cross_edges.append({
                    "source": u,
                    "target": v,
                    "source_layer": u_layer,
                    "target_layer": v_layer,
                    "type": data["type"],
                })
        
        return {
            "layers": layers,
            "cross_layer_edges": cross_edges,
        }
    
    def _get_layer(self, layers: Dict, node_id: str) -> str:
        for layer, nodes in layers.items():
            if any(n["id"] == node_id for n in nodes):
                return layer
        return "unknown"
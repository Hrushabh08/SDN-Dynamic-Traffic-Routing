"""Routing engine: candidate paths and selection policies."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

import networkx as nx

from topology import NetworkTopology

Algorithm = Literal["Minimum Hop Count", "Minimum Link Cost"]


@dataclass
class PathMetrics:
    path: list[str]
    hops: int
    total_cost: float
    total_base_cost: float
    total_latency: float
    avg_utilization: float
    status: str
    selected: bool = False

    def path_label(self) -> str:
        return " → ".join(self.path)

    def as_dict(self) -> dict:
        return {
            "Path": self.path_label(),
            "Hops": self.hops,
            "Cost": round(self.total_cost, 2),
            "Latency (ms)": round(self.total_latency, 2),
            "Utilization (%)": round(self.avg_utilization, 2),
            "Status": self.status,
            "Selected": "Yes" if self.selected else "No",
        }


@dataclass
class RoutingResult:
    source: str
    destination: str
    algorithm: Algorithm
    candidates: list[PathMetrics] = field(default_factory=list)
    best_path: PathMetrics | None = None
    message: str = ""

    @property
    def has_route(self) -> bool:
        return self.best_path is not None and self.best_path.status == "AVAILABLE"


class RoutingEngine:
    """Compute paths from the live topology. No hardcoded routes."""

    def __init__(self, topology: NetworkTopology, max_paths: int = 12) -> None:
        self.topology = topology
        self.max_paths = max_paths

    def calculate_path_metrics(self, path: list[str]) -> PathMetrics:
        hops = max(0, len(path) - 1)
        if hops == 0:
            return PathMetrics(
                path=path,
                hops=0,
                total_cost=0.0,
                total_base_cost=0.0,
                total_latency=0.0,
                avg_utilization=0.0,
                status="AVAILABLE",
            )

        total_effective = 0.0
        total_base = 0.0
        total_latency = 0.0
        utilizations: list[float] = []
        available = True
        for u, v in zip(path, path[1:]):
            info = self.topology.get_link_info(u, v)
            if info["status"] != "UP":
                available = False
            total_effective += info["effective_cost"]
            total_base += info["cost"]
            total_latency += info["latency"]
            utilizations.append(info["utilization"])

        avg_util = sum(utilizations) / len(utilizations) if utilizations else 0.0
        return PathMetrics(
            path=path,
            hops=hops,
            total_cost=total_effective,
            total_base_cost=total_base,
            total_latency=total_latency,
            avg_utilization=avg_util,
            status="AVAILABLE" if available else "UNAVAILABLE",
        )

    def find_candidate_paths(self, source: str, destination: str) -> list[PathMetrics]:
        if source == destination:
            return [self.calculate_path_metrics([source])]

        active = self.topology.get_active_graph()
        if source not in active or destination not in active:
            return []
        if not nx.has_path(active, source, destination):
            return []

        raw_paths: list[list[str]] = []
        try:
            for path in nx.shortest_simple_paths(active, source, destination):
                raw_paths.append(path)
                if len(raw_paths) >= self.max_paths:
                    break
        except nx.NetworkXNoPath:
            return []

        metrics = [self.calculate_path_metrics(path) for path in raw_paths]
        return [item for item in metrics if item.status == "AVAILABLE"]

    def select_best_path(
        self,
        candidates: list[PathMetrics],
        algorithm: Algorithm,
    ) -> PathMetrics | None:
        available = [path for path in candidates if path.status == "AVAILABLE"]
        if not available:
            return None

        if algorithm == "Minimum Hop Count":
            available.sort(key=lambda p: (p.hops, p.total_cost, p.total_latency, p.path_label()))
        else:
            available.sort(key=lambda p: (p.total_cost, p.hops, p.total_latency, p.path_label()))

        best = available[0]
        for candidate in candidates:
            candidate.selected = candidate.path == best.path
        return best

    def compute_route(
        self,
        source: str,
        destination: str,
        algorithm: Algorithm,
    ) -> RoutingResult:
        if not self.topology.has_node(source) or not self.topology.has_node(destination):
            return RoutingResult(
                source=source,
                destination=destination,
                algorithm=algorithm,
                message="Invalid source or destination node.",
            )

        candidates = self.find_candidate_paths(source, destination)
        best = self.select_best_path(candidates, algorithm)
        if best is None:
            return RoutingResult(
                source=source,
                destination=destination,
                algorithm=algorithm,
                candidates=candidates,
                message="No valid route available.",
            )
        return RoutingResult(
            source=source,
            destination=destination,
            algorithm=algorithm,
            candidates=candidates,
            best_path=best,
            message="Route calculated from current network state.",
        )

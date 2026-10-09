"""Centralized SDN controller for simulated traffic routing."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from monitor import NetworkMonitor
from routing import Algorithm, PathMetrics, RoutingEngine, RoutingResult
from topology import NetworkTopology


class SDNController:
    """Control plane: observe topology, choose routes, log events, reroute."""

    def __init__(self, topology: NetworkTopology) -> None:
        self.topology = topology
        self.monitor = NetworkMonitor(topology)
        self.routing = RoutingEngine(topology)
        self.source: str | None = None
        self.destination: str | None = None
        self.algorithm: Algorithm = "Minimum Link Cost"
        self.active_route: PathMetrics | None = None
        self.last_result: RoutingResult | None = None
        self.event_log: list[dict[str, Any]] = []

    def _now(self) -> str:
        return datetime.now().strftime("%H:%M:%S")

    def log_event(
        self,
        event_type: str,
        message: str,
        old_route: list[str] | None = None,
        new_route: list[str] | None = None,
    ) -> None:
        self.event_log.insert(
            0,
            {
                "timestamp": self._now(),
                "event_type": event_type,
                "message": message,
                "old_route": " → ".join(old_route) if old_route else "",
                "new_route": " → ".join(new_route) if new_route else "",
            },
        )

    def calculate_route(
        self,
        source: str,
        destination: str,
        algorithm: Algorithm,
    ) -> RoutingResult:
        self.source = source
        self.destination = destination
        self.algorithm = algorithm
        old_path = self.active_route.path if self.active_route else None

        if source == destination:
            result = self.routing.compute_route(source, destination, algorithm)
            self.last_result = result
            self.active_route = result.best_path
            self.log_event(
                "ROUTE",
                "Source and destination are the same node. No forwarding required.",
                old_route=old_path,
                new_route=[source],
            )
            return result

        result = self.routing.compute_route(source, destination, algorithm)
        self.last_result = result
        self.active_route = result.best_path

        if result.has_route and result.best_path:
            self.log_event(
                "ROUTE",
                f"Route calculated ({algorithm}): {result.best_path.path_label()}",
                old_route=old_path,
                new_route=result.best_path.path,
            )
        else:
            self.active_route = None
            self.log_event(
                "NO_ROUTE",
                result.message or "No valid route available.",
                old_route=old_path,
            )
        return result

    def recalculate(self, reason: str = "Network condition changed.") -> RoutingResult | None:
        """Re-run routing on the current topology if a flow is installed."""
        if not self.source or not self.destination:
            self.log_event("MONITOR", reason)
            return None

        old_path = self.active_route.path if self.active_route else None
        was_valid = self.monitor.path_is_valid(old_path)
        self.log_event("MONITOR", reason, old_route=old_path)

        result = self.routing.compute_route(self.source, self.destination, self.algorithm)
        self.last_result = result
        new_path = result.best_path.path if result.best_path else None

        if not result.has_route:
            self.active_route = None
            self.log_event(
                "NO_ROUTE",
                "No valid route available after recalculation.",
                old_route=old_path,
            )
            return result

        self.active_route = result.best_path
        if old_path != new_path:
            event = "REROUTE" if old_path else "ROUTE"
            detail = "Automatic rerouting performed." if old_path else "Route installed."
            if old_path and not was_valid:
                detail = "Current route became invalid. Automatic rerouting performed."
            self.log_event(
                event,
                f"{detail} New route: {result.best_path.path_label()}",
                old_route=old_path,
                new_route=new_path,
            )
        else:
            self.log_event(
                "ROUTE",
                "Controller recalculated route. Active path remains optimal.",
                old_route=old_path,
                new_route=new_path,
            )
        return result

    def current_route_summary(self) -> dict[str, Any]:
        if not self.source or not self.destination:
            return {
                "Source": "-",
                "Destination": "-",
                "Routing Algorithm": self.algorithm,
                "Current Path": "Not calculated",
                "Hop Count": "-",
                "Total Cost": "-",
                "Total Latency": "-",
                "Average Utilization": "-",
                "Route Status": "IDLE",
            }
        if not self.active_route:
            return {
                "Source": self.source,
                "Destination": self.destination,
                "Routing Algorithm": self.algorithm,
                "Current Path": "No valid route available",
                "Hop Count": "-",
                "Total Cost": "-",
                "Total Latency": "-",
                "Average Utilization": "-",
                "Route Status": "UNAVAILABLE",
            }
        route = self.active_route
        return {
            "Source": self.source,
            "Destination": self.destination,
            "Routing Algorithm": self.algorithm,
            "Current Path": route.path_label(),
            "Hop Count": route.hops,
            "Total Cost": round(route.total_cost, 2),
            "Total Latency": f"{round(route.total_latency, 2)} ms",
            "Average Utilization": f"{round(route.avg_utilization, 2)}%",
            "Route Status": "ACTIVE",
        }

    def comparison(self) -> dict[str, dict[str, Any]]:
        """Compare both algorithms on the current topology for the active flow."""
        if not self.source or not self.destination:
            return {}
        hop = self.routing.compute_route(self.source, self.destination, "Minimum Hop Count")
        cost = self.routing.compute_route(self.source, self.destination, "Minimum Link Cost")
        table: dict[str, dict[str, Any]] = {}
        for name, result in (("Minimum Hop Count", hop), ("Minimum Link Cost", cost)):
            if result.best_path:
                table[name] = {
                    "Selected Path": result.best_path.path_label(),
                    "Hop Count": result.best_path.hops,
                    "Total Cost": round(result.best_path.total_cost, 2),
                    "Latency": f"{round(result.best_path.total_latency, 2)} ms",
                }
            else:
                table[name] = {
                    "Selected Path": "No valid route available",
                    "Hop Count": "-",
                    "Total Cost": "-",
                    "Latency": "-",
                }
        return table

"""Network monitoring: congestion classification from live metrics."""

from __future__ import annotations

from typing import Any

from topology import NetworkTopology


class NetworkMonitor:
    """Classify links using utilization thresholds from the topology config."""

    def __init__(self, topology: NetworkTopology) -> None:
        self.topology = topology

    def congestion_state(self, utilization: float, status: str = "UP") -> str:
        if status == "DOWN":
            return "FAILED"
        normal_max = self.topology.thresholds["normal_max"]
        moderate_max = self.topology.thresholds["moderate_max"]
        if utilization <= normal_max:
            return "NORMAL"
        if utilization <= moderate_max:
            return "MODERATE"
        return "CONGESTED"

    def inspect_link(self, source: str, destination: str) -> dict[str, Any]:
        info = self.topology.get_link_info(source, destination)
        info["congestion"] = self.congestion_state(info["utilization"], info["status"])
        return info

    def inspect_all_links(self) -> list[dict[str, Any]]:
        return [self.inspect_link(link["source"], link["destination"]) for link in self.topology.get_links()]

    def congested_links(self) -> list[dict[str, Any]]:
        return [link for link in self.inspect_all_links() if link["congestion"] == "CONGESTED"]

    def failed_links(self) -> list[dict[str, Any]]:
        return [link for link in self.inspect_all_links() if link["status"] == "DOWN"]

    def path_is_valid(self, path: list[str] | None) -> bool:
        if not path or len(path) < 2:
            return bool(path)
        for u, v in zip(path, path[1:]):
            try:
                info = self.topology.get_link_info(u, v)
            except KeyError:
                return False
            if info["status"] != "UP":
                return False
        return True

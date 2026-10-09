"""Runtime network condition simulation for the SDN prototype."""

from __future__ import annotations

from topology import NetworkTopology


class NetworkSimulator:
    """Mutate live link metrics. Routing is recalculated by the controller."""

    def __init__(self, topology: NetworkTopology) -> None:
        self.topology = topology

    def _links_on_path(self, path: list[str] | None) -> list[tuple[str, str]]:
        if not path or len(path) < 2:
            return []
        return [(u, v) for u, v in zip(path, path[1:])]

    def _busiest_up_link(self, path: list[str] | None) -> tuple[str, str] | None:
        candidates = []
        for u, v in self._links_on_path(path):
            info = self.topology.get_link_info(u, v)
            if info["status"] == "UP":
                candidates.append((info["utilization"], u, v))
        if candidates:
            candidates.sort(reverse=True)
            _, u, v = candidates[0]
            return u, v

        # Fall back to the busiest UP link in the whole network.
        all_up = []
        for link in self.topology.get_links():
            if link["status"] == "UP":
                all_up.append((link["utilization"], link["source"], link["destination"]))
        if not all_up:
            return None
        all_up.sort(reverse=True)
        _, u, v = all_up[0]
        return u, v

    def increase_traffic(self, path: list[str] | None, amount: float = 15.0) -> list[tuple[str, str]]:
        updated = []
        targets = self._links_on_path(path) or [
            (link["source"], link["destination"])
            for link in self.topology.get_links()
            if link["status"] == "UP"
        ]
        for u, v in targets:
            info = self.topology.get_link_info(u, v)
            if info["status"] != "UP":
                continue
            self.topology.update_link_utilization(u, v, info["utilization"] + amount)
            updated.append((u, v))
        return updated

    def decrease_traffic(self, path: list[str] | None, amount: float = 15.0) -> list[tuple[str, str]]:
        updated = []
        targets = self._links_on_path(path) or [
            (link["source"], link["destination"])
            for link in self.topology.get_links()
            if link["status"] == "UP"
        ]
        for u, v in targets:
            info = self.topology.get_link_info(u, v)
            self.topology.update_link_utilization(u, v, info["utilization"] - amount)
            updated.append((u, v))
        return updated

    def simulate_congestion(
        self,
        path: list[str] | None,
        utilization: float = 95.0,
    ) -> tuple[str, str] | None:
        """Raise utilization on a live path link so the monitor marks it CONGESTED."""
        target = self._busiest_up_link(path)
        if target is None:
            return None
        u, v = target
        self.topology.update_link_utilization(u, v, utilization)
        return u, v

    def simulate_link_failure(self, path: list[str] | None) -> tuple[str, str] | None:
        """Take down an UP link on the current path (or any UP link)."""
        target = self._busiest_up_link(path)
        if target is None:
            return None
        u, v = target
        self.topology.set_link_status(u, v, "DOWN")
        return u, v

    def restore_failed_links(self) -> list[tuple[str, str]]:
        restored = []
        for link in self.topology.get_links():
            if link["status"] == "DOWN":
                self.topology.restore_link(link["source"], link["destination"])
                restored.append((link["source"], link["destination"]))
        return restored

    def restore_network(self) -> None:
        """Bring failed links back UP and ease congestion without full config reset."""
        self.restore_failed_links()
        for link in self.topology.get_links():
            if link["utilization"] > 60:
                self.topology.update_link_utilization(
                    link["source"],
                    link["destination"],
                    min(45.0, link["utilization"] * 0.4),
                )

    def reset_network(self) -> None:
        self.topology.reset()

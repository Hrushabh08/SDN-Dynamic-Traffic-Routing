"""Unit tests for topology, routing, congestion, failure, and recalculation."""

from __future__ import annotations

from pathlib import Path

import pytest

from controller import SDNController
from monitor import NetworkMonitor
from routing import RoutingEngine
from simulation import NetworkSimulator
from topology import NetworkTopology

CONFIG = Path(__file__).resolve().parents[1] / "data" / "network_config.json"


@pytest.fixture
def topology() -> NetworkTopology:
    return NetworkTopology(CONFIG)


@pytest.fixture
def engine(topology: NetworkTopology) -> RoutingEngine:
    return RoutingEngine(topology)


@pytest.fixture
def controller(topology: NetworkTopology) -> SDNController:
    return SDNController(topology)


def test_topology_creation(topology: NetworkTopology) -> None:
    assert topology.graph.number_of_nodes() >= 6
    assert topology.graph.number_of_edges() >= 8
    for node in ("S1", "S2", "S3", "S4", "S5", "S6"):
        assert topology.has_node(node)
    info = topology.get_link_info("S1", "S2")
    assert info["status"] == "UP"
    assert info["capacity"] > 0
    assert 0 <= info["utilization"] <= 100
    assert info["latency"] > 0


def test_minimum_hop_routing(engine: RoutingEngine) -> None:
    result = engine.compute_route("S1", "S6", "Minimum Hop Count")
    assert result.has_route
    assert result.best_path is not None
    hops = result.best_path.hops
    assert hops == min(item.hops for item in result.candidates)
    assert hops <= 3
    for item in result.candidates:
        if item.hops < hops:
            pytest.fail("A shorter hop path existed but was not selected")


def test_minimum_cost_routing(engine: RoutingEngine) -> None:
    result = engine.compute_route("S1", "S6", "Minimum Link Cost")
    assert result.has_route
    assert result.best_path is not None
    best_cost = result.best_path.total_cost
    assert best_cost == min(item.total_cost for item in result.candidates)
    expected = ["S1", "S2", "S4", "S6"]
    assert result.best_path.path == expected


def test_alternative_paths_exist(engine: RoutingEngine) -> None:
    result = engine.compute_route("S1", "S6", "Minimum Link Cost")
    labels = {tuple(item.path) for item in result.candidates}
    assert ("S1", "S2", "S4", "S6") in labels
    assert ("S1", "S3", "S5", "S6") in labels
    assert len(result.candidates) >= 3


def test_failed_link_is_excluded(topology: NetworkTopology, engine: RoutingEngine) -> None:
    topology.set_link_status("S2", "S4", "DOWN")
    result = engine.compute_route("S1", "S6", "Minimum Link Cost")
    assert result.has_route
    for item in result.candidates:
        hops = list(zip(item.path, item.path[1:]))
        assert ("S2", "S4") not in hops and ("S4", "S2") not in hops
    active = topology.get_active_graph()
    assert not active.has_edge("S2", "S4")


def test_congestion_increases_effective_cost(topology: NetworkTopology, engine: RoutingEngine) -> None:
    before = topology.effective_cost("S2", "S4")
    topology.update_link_utilization("S2", "S4", 95)
    after = topology.effective_cost("S2", "S4")
    assert after > before
    monitor = NetworkMonitor(topology)
    state = monitor.congestion_state(95, "UP")
    assert state == "CONGESTED"
    result = engine.compute_route("S1", "S6", "Minimum Link Cost")
    assert result.best_path is not None
    assert result.best_path.path != ["S1", "S2", "S4", "S6"]


def test_dynamic_cost_change_selects_cheaper_path(
    topology: NetworkTopology,
    engine: RoutingEngine,
) -> None:
    initial = engine.compute_route("S1", "S6", "Minimum Link Cost")
    assert initial.best_path is not None
    topology.update_link_cost("S2", "S4", 50)
    updated = engine.compute_route("S1", "S6", "Minimum Link Cost")
    assert updated.best_path is not None
    assert updated.best_path.path != initial.best_path.path
    assert updated.best_path.total_cost == min(p.total_cost for p in updated.candidates)


def test_no_available_route(topology: NetworkTopology, engine: RoutingEngine) -> None:
    for link in topology.get_links():
        topology.set_link_status(link["source"], link["destination"], "DOWN")
    result = engine.compute_route("S1", "S6", "Minimum Hop Count")
    assert not result.has_route
    assert result.best_path is None
    assert "No valid route" in result.message


def test_source_equals_destination(engine: RoutingEngine) -> None:
    result = engine.compute_route("S1", "S1", "Minimum Hop Count")
    assert result.has_route
    assert result.best_path is not None
    assert result.best_path.path == ["S1"]
    assert result.best_path.hops == 0


def test_route_recalculation_after_failure(controller: SDNController) -> None:
    first = controller.calculate_route("S1", "S6", "Minimum Link Cost")
    assert first.has_route
    old = first.best_path.path[:]
    u, v = old[0], old[1]
    controller.topology.set_link_status(u, v, "DOWN")
    second = controller.recalculate(f"Link {u}-{v} failed.")
    assert second is not None
    assert second.has_route
    assert second.best_path.path != old
    types = [event["event_type"] for event in controller.event_log]
    assert "REROUTE" in types or "ROUTE" in types


def test_congestion_simulation_reroutes(controller: SDNController) -> None:
    simulator = NetworkSimulator(controller.topology)
    first = controller.calculate_route("S1", "S6", "Minimum Link Cost")
    assert first.best_path is not None
    old = first.best_path.path[:]
    target = simulator.simulate_congestion(old, utilization=95)
    assert target is not None
    second = controller.recalculate("Congestion simulated on active path.")
    assert second is not None
    assert second.has_route
    assert second.best_path.path != old


def test_restore_and_reset(controller: SDNController) -> None:
    simulator = NetworkSimulator(controller.topology)
    controller.calculate_route("S1", "S6", "Minimum Link Cost")
    simulator.simulate_link_failure(controller.active_route.path)
    simulator.restore_network()
    assert all(link["status"] == "UP" for link in controller.topology.get_links())
    simulator.reset_network()
    info = controller.topology.get_link_info("S2", "S4")
    assert info["status"] == "UP"
    assert info["cost"] == 2

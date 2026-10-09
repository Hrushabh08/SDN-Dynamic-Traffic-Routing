"""Comprehensive verification script for the SDN Dynamic Traffic Routing project.

Tests all mandatory scenarios from the specification.
"""
import sys
import json
from pathlib import Path

# Force stdout to UTF-8 for Windows console support
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from topology import NetworkTopology
from routing import RoutingEngine
from controller import SDNController
from monitor import NetworkMonitor
from simulation import NetworkSimulator

CONFIG = Path(__file__).resolve().parent / "data" / "network_config.json"

def separator(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

def check(condition, msg):
    status = "[PASS]" if condition else "[FAIL]"
    print(f"  {status}: {msg}")
    return condition

def main():
    all_passed = True

    # ============================================================
    separator("TEST 1: Normal routing S1 -> S6")
    # ============================================================
    topo = NetworkTopology(CONFIG)
    ctrl = SDNController(topo)
    result = ctrl.calculate_route("S1", "S6", "Minimum Link Cost")
    all_passed &= check(result.has_route, "A valid route is calculated")
    all_passed &= check(result.best_path is not None, "Best path exists")
    all_passed &= check(len(result.best_path.path) >= 2, "Path has at least 2 nodes")
    print(f"    Path: {result.best_path.path_label()}")
    print(f"    Hops: {result.best_path.hops}")
    print(f"    Cost: {result.best_path.total_cost:.2f}")

    # ============================================================
    separator("TEST 2: Minimum-hop routing")
    # ============================================================
    topo = NetworkTopology(CONFIG)
    engine = RoutingEngine(topo)
    result = engine.compute_route("S1", "S6", "Minimum Hop Count")
    all_passed &= check(result.has_route, "Min-hop route found")
    min_hops = min(c.hops for c in result.candidates)
    all_passed &= check(result.best_path.hops == min_hops, 
                        f"Selected path has minimum hops ({result.best_path.hops})")
    print(f"    Path: {result.best_path.path_label()}")

    # ============================================================
    separator("TEST 3: Minimum-cost routing")
    # ============================================================
    topo = NetworkTopology(CONFIG)
    engine = RoutingEngine(topo)
    result = engine.compute_route("S1", "S6", "Minimum Link Cost")
    all_passed &= check(result.has_route, "Min-cost route found")
    min_cost = min(c.total_cost for c in result.candidates)
    all_passed &= check(abs(result.best_path.total_cost - min_cost) < 0.01,
                        f"Selected path has minimum cost ({result.best_path.total_cost:.2f})")
    all_passed &= check(result.best_path.path == ["S1", "S2", "S4", "S6"],
                        "Expected S1->S2->S4->S6 under normal load")
    print(f"    Path: {result.best_path.path_label()}")

    # ============================================================
    separator("TEST 4: Congestion changes routing")
    # ============================================================
    topo = NetworkTopology(CONFIG)
    ctrl = SDNController(topo)
    sim = NetworkSimulator(topo)
    monitor = NetworkMonitor(topo)

    # Calculate initial route
    initial = ctrl.calculate_route("S1", "S6", "Minimum Link Cost")
    initial_path = initial.best_path.path[:]
    print(f"    Initial path: {' -> '.join(initial_path)}")

    # Get initial effective cost of S2-S4
    before_cost = topo.effective_cost("S2", "S4")
    before_util = topo.get_link_info("S2", "S4")["utilization"]
    print(f"    S2-S4 utilization before: {before_util}%")
    print(f"    S2-S4 effective cost before: {before_cost:.2f}")

    # Simulate congestion on the active path
    target = sim.simulate_congestion(initial_path, utilization=95.0)
    all_passed &= check(target is not None, "Congestion simulated on a link")
    u, v = target
    after_util = topo.get_link_info(u, v)["utilization"]
    after_cost = topo.effective_cost(u, v)
    state = monitor.congestion_state(after_util, "UP")
    print(f"    {u}-{v} utilization after: {after_util}%")
    print(f"    {u}-{v} effective cost after: {after_cost:.2f}")
    print(f"    {u}-{v} congestion state: {state}")

    all_passed &= check(after_util > before_util, "Utilization increased")
    all_passed &= check(after_cost > before_cost, "Effective cost increased")
    all_passed &= check(state == "CONGESTED", "Link classified as CONGESTED")

    # Recalculate
    new_result = ctrl.recalculate("Congestion simulated")
    all_passed &= check(new_result is not None and new_result.has_route, "New route found")
    if new_result.best_path:
        new_path = new_result.best_path.path
        all_passed &= check(new_path != initial_path, 
                           "Route changed after congestion")
        print(f"    New path: {' -> '.join(new_path)}")

    # ============================================================
    separator("TEST 5: Link failure")
    # ============================================================
    topo = NetworkTopology(CONFIG)
    ctrl = SDNController(topo)

    initial = ctrl.calculate_route("S1", "S6", "Minimum Link Cost")
    initial_path = initial.best_path.path[:]
    print(f"    Initial path: {' → '.join(initial_path)}")

    # Fail the first link on the path
    u, v = initial_path[0], initial_path[1]
    topo.set_link_status(u, v, "DOWN")
    print(f"    Failed link: {u}-{v}")

    link_info = topo.get_link_info(u, v)
    all_passed &= check(link_info["status"] == "DOWN", "Link status is DOWN")

    # Check active graph excludes it
    active = topo.get_active_graph()
    all_passed &= check(not active.has_edge(u, v), "Failed link excluded from active graph")

    # Recalculate
    result = ctrl.recalculate(f"Link {u}-{v} failed")
    all_passed &= check(result.has_route, "Alternative route found")
    if result.best_path:
        new_path = result.best_path.path
        hops = list(zip(new_path, new_path[1:]))
        all_passed &= check((u, v) not in hops and (v, u) not in hops,
                           "Failed link not used in new route")
        print(f"    New path: {' → '.join(new_path)}")

    # ============================================================
    separator("TEST 6: No route scenario")
    # ============================================================
    topo = NetworkTopology(CONFIG)
    engine = RoutingEngine(topo)

    # Fail all links
    for link in topo.get_links():
        topo.set_link_status(link["source"], link["destination"], "DOWN")

    result = engine.compute_route("S1", "S6", "Minimum Hop Count")
    all_passed &= check(not result.has_route, "No route when all links DOWN")
    all_passed &= check(result.best_path is None, "Best path is None")
    all_passed &= check("No valid route" in result.message, "Proper no-route message")
    print(f"    Message: {result.message}")

    # ============================================================
    separator("TEST 7: Restore network")
    # ============================================================
    topo = NetworkTopology(CONFIG)
    sim = NetworkSimulator(topo)

    # Fail some links
    topo.set_link_status("S2", "S4", "DOWN")
    topo.set_link_status("S4", "S6", "DOWN")
    all_passed &= check(topo.get_link_info("S2", "S4")["status"] == "DOWN", "Links are DOWN")

    # Restore
    sim.restore_network()
    all_passed &= check(topo.get_link_info("S2", "S4")["status"] == "UP", 
                        "Links restored to UP")
    all_passed &= check(topo.get_link_info("S4", "S6")["status"] == "UP",
                        "All links restored")

    # ============================================================
    separator("TEST 8: Reset network")
    # ============================================================
    topo = NetworkTopology(CONFIG)
    sim = NetworkSimulator(topo)

    # Modify the network
    topo.update_link_utilization("S1", "S2", 95)
    topo.update_link_cost("S2", "S4", 50)
    topo.set_link_status("S3", "S5", "DOWN")

    # Verify modifications
    all_passed &= check(topo.get_link_info("S1", "S2")["utilization"] == 95, "Utilization modified")
    all_passed &= check(topo.get_link_info("S2", "S4")["cost"] == 50, "Cost modified")
    all_passed &= check(topo.get_link_info("S3", "S5")["status"] == "DOWN", "Status modified")

    # Reset
    sim.reset_network()
    all_passed &= check(topo.get_link_info("S1", "S2")["utilization"] == 25, 
                        "Utilization reset to initial")
    all_passed &= check(topo.get_link_info("S2", "S4")["cost"] == 2, 
                        "Cost reset to initial")
    all_passed &= check(topo.get_link_info("S3", "S5")["status"] == "UP", 
                        "Status reset to UP")

    # ============================================================
    separator("Additional checks")
    # ============================================================

    # Check topology has at least 6 nodes
    topo = NetworkTopology(CONFIG)
    all_passed &= check(topo.graph.number_of_nodes() >= 6, f"At least 6 nodes ({topo.graph.number_of_nodes()})")
    all_passed &= check(all(topo.has_node(n) for n in ["S1", "S2", "S3", "S4", "S5", "S6"]),
                        "All required nodes exist")

    # Check all link attributes
    info = topo.get_link_info("S1", "S2")
    all_passed &= check("cost" in info, "Link has cost attribute")
    all_passed &= check("capacity" in info, "Link has capacity attribute")
    all_passed &= check("utilization" in info, "Link has utilization attribute")
    all_passed &= check("latency" in info, "Link has latency attribute")
    all_passed &= check("status" in info, "Link has status attribute")
    all_passed &= check("effective_cost" in info, "Link has effective_cost attribute")

    # Check multiple paths exist
    engine = RoutingEngine(topo)
    result = engine.compute_route("S1", "S6", "Minimum Link Cost")
    all_passed &= check(len(result.candidates) >= 3, 
                        f"Multiple alternative paths ({len(result.candidates)} candidates)")

    # Check source equals destination
    result = engine.compute_route("S1", "S1", "Minimum Hop Count")
    all_passed &= check(result.best_path.path == ["S1"], "Source==destination handled")
    all_passed &= check(result.best_path.hops == 0, "Zero hops for same node")

    # Check invalid nodes
    result = engine.compute_route("S1", "S99", "Minimum Hop Count")
    all_passed &= check(not result.has_route, "Invalid destination handled")

    # Check event log
    ctrl = SDNController(topo)
    ctrl.calculate_route("S1", "S6", "Minimum Link Cost")
    all_passed &= check(len(ctrl.event_log) >= 1, "Event log records events")
    all_passed &= check("timestamp" in ctrl.event_log[0], "Events have timestamps")
    all_passed &= check("event_type" in ctrl.event_log[0], "Events have types")

    # Check add_node method exists
    all_passed &= check(hasattr(topo, 'add_node'), "add_node method exists")
    all_passed &= check(hasattr(topo, 'fail_link'), "fail_link method exists")

    # Check config file
    config_path = Path(__file__).resolve().parent / "data" / "network_config.json"
    all_passed &= check(config_path.exists(), "network_config.json exists")
    with open(config_path) as f:
        config = json.load(f)
    all_passed &= check("nodes" in config, "Config has nodes")
    all_passed &= check("links" in config, "Config has links")
    all_passed &= check("thresholds" in config, "Config has thresholds")
    all_passed &= check("congestion_model" in config, "Config has congestion_model")

    # ============================================================
    separator("FINAL RESULT")
    # ============================================================
    if all_passed:
        print("  [PASS] ALL TESTS PASSED - Project is complete and functional!")
    else:
        print("  [FAIL] SOME TESTS FAILED - Review the output above.")

    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())

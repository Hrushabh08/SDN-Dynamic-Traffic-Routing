# SDN-Based Dynamic Traffic Routing Using Python

A Python-based SDN (Software Defined Networking) simulation and prototype for centralized, programmable network traffic management.

> **Disclaimer:** This is a **software-based SDN simulation/prototype** built with Python and NetworkX. It does **not** control real physical switches, routers, or OpenFlow hardware. The SDN controller, topology, data plane, and traffic are all simulated in software.

---

## 1. Project Title

**SDN-Based Dynamic Traffic Routing Using Python**

---

## 2. Project Overview

This project demonstrates how a logically centralized SDN controller can:

1. Maintain a global view of the network topology
2. Measure simulated link conditions (cost, capacity, utilization, latency, status)
3. Compute multiple candidate paths between source and destination
4. Select the optimal route using **Minimum Hop Count** or **Minimum Link Cost** algorithms
5. Detect congestion or link failure in real-time
6. Recalculate routes dynamically from the **current** graph state
7. Reroute traffic to a better remaining path automatically

All routing decisions are computed dynamically from the live NetworkX graph. Nothing is hardcoded — simulation changes modify the graph, and the routing engine recalculates paths based on the new state.

---

## 3. Problem Statement

In traditional IP networks, forwarding decisions are distributed across individual routers. Each router has only a limited view of the network (typically its immediate neighbours). When a link becomes congested or fails, recovery depends on protocol convergence timers and local routing tables, resulting in slow and suboptimal responses.

This project studies a simpler SDN-style approach: a centralized controller holds a **global view** of the entire topology and recomputes the best path whenever network conditions change, enabling faster and more intelligent routing decisions.

---

## 4. Objectives

- Programmatic network topology creation using NetworkX
- Centralized SDN controller architecture
- Source-to-destination path calculation
- Minimum-hop routing algorithm
- Minimum-link-cost routing algorithm
- Multiple alternative path discovery
- Network monitoring with congestion classification
- Link utilization, latency, capacity, and cost tracking
- Link UP/DOWN status management
- Congestion simulation
- Link failure simulation
- Dynamic route recalculation
- Automatic rerouting when the active path becomes poor or unavailable
- Interactive network visualization using Plotly
- Streamlit-based dashboard for demonstration
- Timestamped event/routing logs
- Automated tests with pytest
- Clear documentation

---

## 5. SDN Concept

**Software Defined Networking (SDN)** separates the network into two planes:

- **Control Plane:** Makes forwarding decisions (where traffic should go)
- **Data Plane:** Forwards packets according to the control plane's decisions

The control plane is **logically centralized** and **programmable**, giving it a global view of the network.

In this project:

```
User / Dashboard (Streamlit)
        ↓
SDN Controller (controller.py)
        ↓
Global Topology (NetworkX graph)
        ↓
Routing Engine (routing.py)
        ↓
Selected Path (simulated forwarding)
        ↓
Network Monitor (monitor.py)
        ↓
Detect Change → Recalculate → New Path
```

### Traditional Networking vs SDN

| Aspect | Traditional Networking | SDN (This Prototype) |
|--------|----------------------|---------------------|
| Control | Distributed across routers | Centralized controller |
| Network View | Local neighbour state | Global topology |
| Policy Change | Device-by-device configuration | Single controller decision |
| Reaction to Congestion | Slow / protocol timers | Immediate recalculation |
| Implementation | Physical routers/switches | Python simulation |

**Honesty note:** There is no OpenFlow, Ryu, or hardware switch in this project. The data plane is the NetworkX graph.

---

## 6. System Architecture

```
┌─────────────────────────────────────────────────────┐
│                 Streamlit Dashboard (app.py)         │
│  Source/Destination selection, Algorithm selection,  │
│  Simulation buttons, Visualization, Event Log       │
└──────────────────────┬──────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────┐
│              SDN Controller (controller.py)          │
│  - Maintains active route                           │
│  - Triggers routing calculations                    │
│  - Detects congestion / failures                    │
│  - Performs automatic rerouting                     │
│  - Maintains timestamped event log                  │
├──────────┬──────────────┬───────────────────────────┤
│          │              │                           │
│  Topology│   Routing    │   Network                 │
│   Store  │   Engine     │   Monitor                 │
│          │              │                           │
└──────────┴──────────────┴───────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────┐
│         Network Simulator (simulation.py)            │
│  - Increase/decrease traffic                        │
│  - Simulate congestion                              │
│  - Simulate link failure                            │
│  - Restore / Reset network                          │
└──────────────────────┬──────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────┐
│       NetworkX Graph (topology.py)                   │
│  Nodes: S1, S2, S3, S4, S5, S6                     │
│  Edges with: cost, capacity, utilization,            │
│              latency, status, effective_cost         │
└─────────────────────────────────────────────────────┘
```

---

## 7. Technologies Used

| Technology | Purpose |
|-----------|---------|
| **Python 3** | Core programming language |
| **NetworkX** | Graph data structure and path algorithms |
| **Streamlit** | Interactive web dashboard |
| **Plotly** | Network topology visualization |
| **Pandas** | Data tables and formatting |
| **pytest** | Automated testing |

No cloud APIs, Docker, Kubernetes, or external databases are required.

---

## 8. Project Structure

```
SDN-Dynamic-Traffic-Routing/
├── app.py                      # Streamlit dashboard (main entry point)
├── controller.py               # Centralized SDN controller
├── topology.py                 # Network topology management
├── routing.py                  # Routing engine (min-hop, min-cost)
├── monitor.py                  # Network monitoring & congestion classification
├── simulation.py               # Network condition simulation
├── visualization.py            # Plotly network visualization
├── requirements.txt            # Python dependencies
├── pytest.ini                  # pytest configuration
├── README.md                   # Project documentation
├── data/
│   └── network_config.json     # Initial network topology configuration
└── tests/
    ├── __init__.py
    └── test_routing.py          # Automated test suite
```

---

## 9. How Routing Works

The routing engine operates on the **live** NetworkX graph:

1. The controller receives a source, destination, and algorithm selection
2. The topology generates an **active graph** (containing only UP links)
3. The engine enumerates candidate simple paths using `nx.shortest_simple_paths()`
4. For each candidate path, it computes metrics: hop count, total effective cost, total latency, average utilization, and availability
5. Paths are ranked according to the selected algorithm
6. The best path is installed as the active route
7. If network conditions change, the controller recalculates from step 2

---

## 10. Minimum-Hop Routing

Selects the path with the **fewest number of links (hops)** between source and destination.

- Tie-breaking: effective cost → latency → path label
- Example: `S1 → S3 → S6` (2 hops) is preferred over `S1 → S2 → S4 → S6` (3 hops)
- DOWN links are excluded from the active graph before path computation

---

## 11. Minimum-Cost Routing

Selects the path with the **smallest total effective cost**.

The effective cost includes congestion penalties, so congested paths become more expensive:

```
effective_cost = base_cost + (utilization / 100) × penalty_weight
```

- Tie-breaking: hop count → latency → path label
- Example: Under normal load, `S1 → S2 → S4 → S6` (effective cost = 14.30) is cheaper than `S1 → S3 → S6` (effective cost = 18.50)
- DOWN links are excluded from the active graph before path computation

---

## 12. Congestion Model

Every link stores a configured **base cost** and a live **utilization** (0–100%).

### Formula

```
effective_cost = base_cost + (utilization / 100) × penalty_weight
```

Where `penalty_weight = 10.0` (configurable in `data/network_config.json`).

### Example

| Base Cost | Utilization | Penalty | Effective Cost |
|-----------|------------|---------|----------------|
| 2 | 25% | 2.5 | 4.5 |
| 2 | 50% | 5.0 | 7.0 |
| 2 | 80% | 8.0 | 10.0 |
| 2 | 95% | 9.5 | 11.5 |

### Monitor Thresholds

| Utilization Range | Classification |
|------------------|----------------|
| 0–60% | NORMAL |
| 61–80% | MODERATE |
| 81–100% | CONGESTED |
| Status = DOWN | FAILED |

When a link becomes congested, its effective cost increases significantly, potentially making an alternative path cheaper. The routing engine always uses **effective cost** for Minimum Link Cost routing, so congestion naturally influences routing decisions without any hardcoded logic.

---

## 13. Dynamic Rerouting

This is the core feature of the project:

1. **Simulation** modifies link attributes (utilization, status) on the live NetworkX graph
2. **Monitor** classifies the new link state (NORMAL, MODERATE, CONGESTED, FAILED)
3. **Controller** checks if the currently installed route is still valid and optimal
4. **Routing Engine** recomputes all candidate paths on the updated graph
5. **Best remaining path** is selected and installed
6. **Event log** records the rerouting decision with timestamp

### Key Principle

No route changes are hardcoded. For example, the code does **NOT** contain:

```python
# WRONG - This is what we do NOT do
if congestion:
    route = ["S1", "S3", "S5", "S6"]
```

Instead, the simulation changes the graph, and the routing engine dynamically computes the new best path:

```python
# CORRECT - What the project actually does
simulator.simulate_congestion(active_path)  # Modifies graph
result = controller.recalculate()           # Recomputes from live state
# result.best_path is whatever the algorithm finds optimal
```

---

## 14. Link Failure Handling

When a link failure is simulated:

1. The link's status is set to `DOWN` in the NetworkX graph
2. `get_active_graph()` excludes all DOWN links
3. The routing engine only searches paths through UP links
4. If the current active route used the failed link, the controller detects it as invalid
5. A new route is calculated from the remaining topology
6. If no route exists (all paths are broken), the dashboard displays: **"No valid route available"** — no crash occurs

---

## 15. Dashboard Features

The Streamlit dashboard includes:

### Title Section
- Project title: **SDN-Based Dynamic Traffic Routing Using Python**
- Brief description

### Network Controls (Sidebar)
- **Source Node** dropdown: S1, S2, S3, S4, S5, S6
- **Destination Node** dropdown
- **Routing Algorithm** dropdown: Minimum Hop Count, Minimum Link Cost
- **Calculate Route** button
- **Simulation buttons:** Increase Traffic, Decrease Traffic, Simulate Congestion, Simulate Link Failure, Restore Network, Reset Network

### Network Overview
- Total Nodes, Total Links, Active Links, Failed Links, Congested Links

### Current Route Display
- Path (e.g., S1 → S2 → S4 → S6)
- Hop Count, Total Cost, Total Latency, Average Utilization, Route Status

### Network Topology Visualization
- Interactive Plotly graph generated from the live NetworkX topology
- Color-coded links: Blue (active route), Gray (healthy), Yellow (moderate), Red (congested), Dashed red (failed)
- Hover tooltips with full link metrics
- Stable node positions

### Available/Alternative Paths
- Table of all candidate paths with metrics
- Indicates which path is selected

### Routing Performance Comparison
- Side-by-side comparison of both algorithms

### Link Status Table
- All links with: Source, Destination, Cost, Effective Cost, Capacity, Utilization, Latency, Status, Congestion state

### Event Log
- Timestamped entries: Route calculated, Congestion simulated, Link failure, Rerouting, Network restored/reset

---

## 16. Installation Instructions

### Prerequisites
- Python 3.9 or higher
- pip (Python package manager)

### Setup (Windows PowerShell)

```powershell
cd SDN-Dynamic-Traffic-Routing
pip install -r requirements.txt
```

Or with a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

---

## 17. How to Run Tests

```powershell
python -m pytest tests/test_routing.py -v
```

Expected output: All 12 tests should pass.

Tests cover:
1. Topology creation and node/link verification
2. Minimum-hop routing correctness
3. Minimum-cost routing correctness
4. Alternative path existence
5. Failed link exclusion from routing
6. Congestion increases effective cost
7. Dynamic cost changes select different paths
8. No-route scenario handling
9. Source equals destination edge case
10. Route recalculation after link failure
11. Congestion simulation triggers rerouting
12. Network restore and reset functionality

---

## 18. How to Start Streamlit

```powershell
python -m streamlit run app.py
```

The dashboard will open in your default browser at `http://localhost:8501`.

---

## 19. Demonstration Steps

Follow this procedure to demonstrate all features:

### Step 1: Initial Route Calculation
1. Start the application: `python -m streamlit run app.py`
2. Set **Source = S1**, **Destination = S6**
3. Set **Routing Algorithm = Minimum Link Cost**
4. Click **Calculate Route**
5. Observe: Route `S1 → S2 → S4 → S6` is selected (lowest effective cost under normal load)

### Step 2: Simulate Congestion
6. Click **Simulate Congestion**
7. Observe: Utilization on a path link increases to 95%
8. Observe: Effective cost of the congested link increases significantly
9. Observe: The controller **automatically recalculates** and may select an alternative route
10. Check the Event Log for the rerouting event

### Step 3: Simulate Link Failure
11. Click **Simulate Link Failure**
12. Observe: A link on the active path is set to DOWN
13. Observe: The failed link appears as a dashed red line in the visualization
14. Observe: The controller reroutes traffic through remaining UP links
15. Verify the failed link is NOT part of the new route

### Step 4: No Route Scenario
16. Click **Simulate Link Failure** multiple times until no path exists
17. Observe: Dashboard displays "No valid route available" without crashing

### Step 5: Restore and Reset
18. Click **Restore Network** — failed links come back UP, congestion is eased
19. Click **Calculate Route** — a valid route is calculated again
20. Click **Reset Network** — all link attributes return to their original values from `network_config.json`

### Step 6: Compare Algorithms
21. With a route calculated, observe the **Routing Performance Comparison** table
22. Change algorithm to **Minimum Hop Count** and click **Calculate Route**
23. Observe: The minimum-hop path (e.g., `S1 → S3 → S6`) is selected even though it has higher cost

---

## 20. Limitations

- **Simulated data plane only:** No actual packets are forwarded. The "data plane" is the NetworkX graph.
- **No OpenFlow/Mininet:** This project does not use any real SDN protocols or tools.
- **Utilization is a scalar:** Each link has a single utilization value, not a traffic matrix.
- **Bounded path enumeration:** At most 12 candidate simple paths are computed.
- **Single controller:** No controller redundancy or failover.
- **In-memory state:** Refreshing the browser creates a new session (topology reloads from JSON).
- **No real-time traffic generation:** Traffic changes are triggered manually via simulation buttons.

---

## 21. Future Scope

This project lays the foundation for more advanced SDN research. Future work could integrate:

- **Mininet** for realistic virtual network emulation
- **Ryu / ONOS / OpenDaylight** for production-grade SDN controllers
- **OpenFlow** protocol for switch-controller communication
- **Open vSwitch (OVS)** for virtual switch implementation
- **Machine Learning** for predictive traffic routing
- **Reinforcement Learning** for adaptive routing policies
- **Multi-controller architectures** for scalability
- **Real-time telemetry** from live switches
- **QoS-aware routing** with traffic class differentiation
- **Cloud or campus deployment** for practical use

These extensions are intentionally **not** required to run this academic project.

---

## Network Topology

Six switches (S1–S6) with 9 links, providing multiple alternative paths:

```
            S2 -------- S4
          / |  \        | \
        /   |    \      |   \
      S1    |     \     |    S6
        \   |      \    |   /
          \ |       \   | /
            S3 -------- S5
              \       /
                \   /
                  S6
```

Key paths from S1 to S6:
- `S1 → S2 → S4 → S6` (3 hops, lowest cost under normal load)
- `S1 → S3 → S5 → S6` (3 hops, alternative)
- `S1 → S3 → S6` (2 hops, fewest hops but highest cost)
- `S1 → S2 → S5 → S6` (3 hops, via S2-S5)
- Several more paths through S4-S5 and other combinations

---

## Quick Reference

### Congestion Formula
```
effective_cost = base_cost + (utilization / 100) × penalty_weight
penalty_weight = 10.0  (configurable in network_config.json)
```

### Run Commands
```powershell
# Install dependencies
pip install -r requirements.txt

# Run tests
python -m pytest tests/test_routing.py -v

# Start dashboard
python -m streamlit run app.py
```

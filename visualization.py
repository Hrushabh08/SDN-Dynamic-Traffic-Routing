"""Plotly visualization generated from the live NetworkX topology."""

from __future__ import annotations

import plotly.graph_objects as go

from monitor import NetworkMonitor
from topology import NetworkTopology

NODE_POSITIONS = {
    "S1": (0.0, 1.0),
    "S2": (1.2, 2.15),
    "S3": (1.2, -0.15),
    "S4": (2.6, 2.15),
    "S5": (2.6, -0.15),
    "S6": (3.8, 1.0),
}


def _pair_on_path(u: str, v: str, path: list[str] | None) -> bool:
    if not path or len(path) < 2:
        return False
    hops = list(zip(path, path[1:]))
    return (u, v) in hops or (v, u) in hops


def build_network_figure(
    topology: NetworkTopology,
    monitor: NetworkMonitor,
    active_path: list[str] | None = None,
) -> go.Figure:
    fig = go.Figure()

    for u, v, data in topology.graph.edges(data=True):
        x0, y0 = NODE_POSITIONS.get(u, (0, 0))
        x1, y1 = NODE_POSITIONS.get(v, (0, 0))
        status = data.get("status", "UP")
        utilization = float(data.get("utilization", 0))
        congestion = monitor.congestion_state(utilization, status)
        on_route = _pair_on_path(u, v, active_path)

        if status == "DOWN":
            color = "#c0392b"
            width = 2
            dash = "dash"
        elif on_route:
            color = "#1f6feb"
            width = 6
            dash = "solid"
        elif congestion == "CONGESTED":
            color = "#e74c3c"
            width = 4
            dash = "solid"
        elif congestion == "MODERATE":
            color = "#f1c40f"
            width = 3
            dash = "solid"
        else:
            color = "#7f8c8d"
            width = 2
            dash = "solid"

        hover = (
            f"{u}–{v}<br>"
            f"Cost: {data['cost']}<br>"
            f"Effective cost: {data.get('effective_cost', data['cost']):.2f}<br>"
            f"Capacity: {data['capacity']} Mbps<br>"
            f"Utilization: {utilization:.1f}%<br>"
            f"Latency: {data['latency']} ms<br>"
            f"Status: {status}<br>"
            f"Congestion: {congestion}"
        )
        fig.add_trace(
            go.Scatter(
                x=[x0, x1],
                y=[y0, y1],
                mode="lines",
                line=dict(color=color, width=width, dash=dash),
                hoverinfo="text",
                text=hover,
                showlegend=False,
            )
        )
        mid_x, mid_y = (x0 + x1) / 2, (y0 + y1) / 2
        label = f"{data['cost']} | {utilization:.0f}%"
        if status == "DOWN":
            label = "DOWN"
        fig.add_trace(
            go.Scatter(
                x=[mid_x],
                y=[mid_y],
                mode="text",
                text=[label],
                textfont=dict(size=11, color="#0f172a"),
                hoverinfo="skip",
                showlegend=False,
            )
        )

    node_x, node_y, node_text, node_color = [], [], [], []
    path_set = set(active_path or [])
    for node in topology.get_nodes():
        x, y = NODE_POSITIONS.get(node, (0, 0))
        node_x.append(x)
        node_y.append(y)
        node_text.append(node)
        node_color.append("#1f6feb" if node in path_set else "#34495e")

    fig.add_trace(
        go.Scatter(
            x=node_x,
            y=node_y,
            mode="markers+text",
            text=node_text,
            textposition="top center",
            textfont=dict(size=14, color="#0f172a", family="sans-serif"),
            marker=dict(size=28, color=node_color, line=dict(width=2, color="white")),
            hoverinfo="text",
            showlegend=False,
        )
    )

    fig.add_trace(go.Scatter(x=[None], y=[None], mode="lines", line=dict(color="#1f6feb", width=6), name="Active route"))
    fig.add_trace(go.Scatter(x=[None], y=[None], mode="lines", line=dict(color="#7f8c8d", width=2), name="Healthy link"))
    fig.add_trace(go.Scatter(x=[None], y=[None], mode="lines", line=dict(color="#f1c40f", width=3), name="Moderate"))
    fig.add_trace(go.Scatter(x=[None], y=[None], mode="lines", line=dict(color="#e74c3c", width=4), name="Congested"))
    fig.add_trace(go.Scatter(x=[None], y=[None], mode="lines", line=dict(color="#c0392b", width=2, dash="dash"), name="Failed"))

    fig.update_layout(
        title=dict(
            text="Live SDN Topology (generated from NetworkX)",
            font=dict(color="#0f172a", size=16),
        ),
        font=dict(color="#0f172a", family="sans-serif"),
        xaxis=dict(visible=False),
        yaxis=dict(visible=False, scaleanchor="x", scaleratio=1),
        plot_bgcolor="#f8fafc",
        paper_bgcolor="#ffffff",
        margin=dict(l=20, r=20, t=50, b=20),
        legend=dict(orientation="h", y=-0.08, font=dict(color="#0f172a")),
        height=520,
    )
    return fig

import networkx as nx
import numpy as np

def compute_s4_hub_modularization(H: nx.Graph):
    """
    Custom S4-like metric:
    ratio of nodes that have a path to at least one detected hub node.

    Note:
    This is NOT the official EASI S4 definition.
    It is a reachability/blast-radius style metric.
    """

    if H.number_of_nodes() <= 1:
        return {
            "S4": 0.0,
            "num_hub_nodes": 0,
            "hub_degree_threshold": 0.0
        }

    G = H.to_directed() if not H.is_directed() else H
    node_scores = {}

    for a in G.nodes():
        layer_a = G.nodes[a].get("ArchimateLayer", "")
        cluster = {a}

        for _, b, _ in G.out_edges(a, data=True):
            if not layer_a or G.nodes[b].get("ArchimateLayer", "") == layer_a:
                cluster.add(b)

        for b, _, _ in G.in_edges(a, data=True):
            if not layer_a or G.nodes[b].get("ArchimateLayer", "") == layer_a:
                cluster.add(b)

        fanout = sum(
            1
            for m in cluster
            for _, n, _ in G.out_edges(m, data=True)
            if n not in cluster
        )

        fanin = sum(
            1
            for n in cluster
            for m, _, _ in G.in_edges(n, data=True)
            if m not in cluster
        )

        node_scores[a] = min(fanin, fanout)

    score_values = list(node_scores.values())
    if len(score_values) <= 1:
        return {
            "S4": 0.0,
            "num_hub_nodes": 0,
            "hub_degree_threshold": 0.0
        }

    hub_threshold = float(np.percentile(score_values, 85))
    hub_nodes = [n for n, s in node_scores.items() if s >= hub_threshold and s > 0]
    num_hub_nodes = len(hub_nodes)

    if not hub_nodes:
        return {
            "S4": 0.0,
            "num_hub_nodes": 0,
            "hub_degree_threshold": hub_threshold
        }

    nodes_reaching_hub = set()

    for node in G.nodes():
        if node in hub_nodes:
            nodes_reaching_hub.add(node)
            continue

        for hub in hub_nodes:
            if nx.has_path(G, node, hub):
                nodes_reaching_hub.add(node)
                break

    S4 = len(nodes_reaching_hub) / G.number_of_nodes()

    return {
        "S4": float(S4),
        "num_hub_nodes": num_hub_nodes,
        "hub_degree_threshold": hub_threshold
    }
    
    
##############################
#مدل سختگیرانه که کلاستر ها را بر اساس روابط خاصی می سنجد نه هر رابطه


# def compute_s4_hub_modularization(H: nx.Graph):
#     """
#     S4: Hub-like Modularization
#     Fallback-friendly version for ArchiMate models where most relations are Serving.
#     Expected node attr: ArchimateLayer
#     Expected edge attr: Label or type
#     """

#     STRUCTURAL_LABELS = ("Aggregation", "Realization", "Composition", "Assignment")
#     SERVICE_FLOW_LABELS = ("Serving",)

#     def edge_label(data):
#         return (data.get("Label") or data.get("type") or "").strip()

#     def has_any(label, labels):
#         label = label.lower()
#         return any(x.lower() in label for x in labels)

#     if H.number_of_nodes() <= 1:
#         return {
#             "S4": 0.0,
#             "num_hub_nodes": 0,
#             "hub_degree_threshold": 0.0
#         }

#     G = H.to_directed() if not H.is_directed() else H
#     node_scores = {}

#     for a in G.nodes():
#         layer_a = G.nodes[a].get("ArchimateLayer", "")
#         cluster = {a}

#         for _, b, data in G.out_edges(a, data=True):
#             lbl = edge_label(data)
#             if has_any(lbl, STRUCTURAL_LABELS) and G.nodes[b].get("ArchimateLayer", "") == layer_a:
#                 cluster.add(b)

#         for b, _, data in G.in_edges(a, data=True):
#             lbl = edge_label(data)
#             if has_any(lbl, STRUCTURAL_LABELS) and G.nodes[b].get("ArchimateLayer", "") == layer_a:
#                 cluster.add(b)

#         if len(cluster) == 1:
#             for _, b, data in G.out_edges(a, data=True):
#                 lbl = edge_label(data)
#                 if has_any(lbl, SERVICE_FLOW_LABELS) and G.nodes[b].get("ArchimateLayer", "") == layer_a:
#                     cluster.add(b)

#             for b, _, data in G.in_edges(a, data=True):
#                 lbl = edge_label(data)
#                 if has_any(lbl, SERVICE_FLOW_LABELS) and G.nodes[b].get("ArchimateLayer", "") == layer_a:
#                     cluster.add(b)

#         fanout = 0
#         for m in cluster:
#             for _, n, data in G.out_edges(m, data=True):
#                 if n not in cluster:
#                     fanout += 1

#         fanin = 0
#         for n in cluster:
#             for m, _, data in G.in_edges(n, data=True):
#                 if m not in cluster:
#                     fanin += 1

#         node_scores[a] = min(fanin, fanout)

#     score_values = list(node_scores.values())
#     if len(score_values) <= 1:
#         return {
#             "S4": 0.0,
#             "num_hub_nodes": 0,
#             "hub_degree_threshold": 0.0
#         }

#     hub_threshold = float(np.percentile(score_values, 85))
#     hub_nodes = [n for n, s in node_scores.items() if s > hub_threshold]

#     return {
#         "S4": len(hub_nodes) / G.number_of_nodes(),
#         "num_hub_nodes": len(hub_nodes),
#         "hub_degree_threshold": hub_threshold
#     }
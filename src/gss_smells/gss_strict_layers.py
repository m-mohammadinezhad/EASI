import networkx as nx


def compute_s3_strict_layers(G: nx.DiGraph, layer_attr="layer"):
    """
    S3: Strict Layers Violation
    Ratio of edges that violate allowed layer dependencies.
    """

    allowed_layer_pairs = {
        ("Strategy", "Strategy"),
        ("Business", "Business"),
        ("Application", "Application"),
        ("Technology", "Technology"),
        ("Motivation", "Business"),
        ("Business", "Motivation"),
        ("Strategy", "Business"),
        ("Business", "Application"),
        ("Application", "Technology"),
        ("Technology", "Application"),
        ("Application", "Business")
    }

    violating_edges = 0
    inter_layer_edges = 0

    for u, v in G.edges():

        lu = G.nodes[u].get(layer_attr)
        lv = G.nodes[v].get(layer_attr)

        if lu is None or lv is None:
            continue
        if lu == "Other" or lv == "Other":
            continue
        if lu != lv:
            inter_layer_edges += 1
            if (lu, lv) not in allowed_layer_pairs:
                violating_edges += 1

    S3 = violating_edges / inter_layer_edges if inter_layer_edges > 0 else 0.0

    return {
        "S3": S3,
        "num_strict_viol_edges": violating_edges,
        "num_inter_layer_edges": inter_layer_edges
    }

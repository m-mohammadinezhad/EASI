import networkx as nx
import numpy as np


def compute_s2_dense_structure(H: nx.Graph):
    """
    S2: Dense Structure
    Ratio of nodes whose clustering coefficient is
    above the 90th percentile.
    """

    S2 = 0.0
    num_dense_nodes = 0
    threshold_dense = 0.0

    if H.number_of_nodes() > 2:

        clustering = nx.clustering(H)
        values = list(clustering.values())

        if len(values) > 1:

            threshold_dense = float(np.percentile(values, 90))

            dense_nodes = [
                n for n, c in clustering.items()
                if c >= threshold_dense
            ]

            num_dense_nodes = len(dense_nodes)

            S2 = num_dense_nodes / H.number_of_nodes()

    return {
        "S2": S2,
        "num_dense_nodes": num_dense_nodes,
        "dense_threshold": threshold_dense
    }

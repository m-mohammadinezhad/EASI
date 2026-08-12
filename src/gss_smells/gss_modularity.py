import networkx as nx
import community as community_louvain


def compute_s1_modularity(H: nx.Graph):
    """
    S1: Weak / Low Modularity
    S1 = 1 - Q
    where Q is Louvain modularity.
    """

    S1 = 0.0
    Q = 0.0
    num_communities = 0

    if H.number_of_nodes() > 1 and H.number_of_edges() > 0:
        partition = community_louvain.best_partition(H)
        Q = community_louvain.modularity(partition, H)
        S1 = 1.0 - Q
        num_communities = len(set(partition.values()))

    return {
        "S1": S1,
        "Q_modularity": Q,
        "num_communities": num_communities
    }

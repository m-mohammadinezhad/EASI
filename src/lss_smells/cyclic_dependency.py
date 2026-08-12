from collections import defaultdict
import networkx as nx

def detect_cyclic_dependencies(G, element_details):
    cycles_info = defaultdict(list)
    for scc in nx.strongly_connected_components(G):
        if len(scc) <= 1 or len(scc) > 10:
            continue
        cycle = list(scc)
        cycle_with_names = [
            f"{element_details.get(node_id, {}).get('name', node_id)} ({node_id})"
            for node_id in cycle
        ]
        for node_id in cycle:
            cycles_info[node_id].append(cycle_with_names)
    return dict(cycles_info)
def detect_dead_element(G, element_details, smells):
    orphaned = []
    for node in G.nodes():
        if G.in_degree(node) == 0 and G.out_degree(node) == 0:
            smells[node].append("DeadElement")
            orphaned.append((node, element_details.get(node, {}).get("name", node)))
    return orphaned
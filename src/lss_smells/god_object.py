def detect_god_object(G, element_details, smells, function_threshold=3, service_threshold=2):
    god_candidates = []
    for node in G.nodes():
        node_type = element_details.get(node, {}).get("type", "").lower()
        if "applicationcomponent" not in node_type:
            continue

        services = set()
        functions = set()

        for nbr in set(G.successors(node)).union(set(G.predecessors(node))):
            nbr_type = element_details.get(nbr, {}).get("type", "").lower()
            if "applicationservice" in nbr_type or "applicationinterface" in nbr_type:
                services.add(nbr)
            if "applicationfunction" in nbr_type:
                functions.add(nbr)

        service_count = len(services)
        function_count = len(functions)

        if service_count <= service_threshold and function_count > function_threshold:
            smells[node].append("GodObject")
            name = element_details.get(node, {}).get("name", node)
            god_candidates.append((node, name, service_count, function_count))

    return god_candidates
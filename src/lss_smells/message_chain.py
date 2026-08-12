def is_service_type(elem_type: str) -> bool:
    t = (elem_type or "").lower()
    return any(s in t for s in ["businessservice", "applicationservice", "technologyservice"])

def detect_message_chain(G, element_details, allowed_rel_types, min_len=2, max_len=15):
    mcnodes = set()

    def is_service_node(n):
        return is_service_type(element_details.get(n, {}).get("type", ""))

    service_nodes = [n for n in G.nodes() if is_service_node(n)]
    if not service_nodes:
        return mcnodes

    for start in service_nodes:
        stack = [(start, [start])]
        while stack:
            current, path = stack.pop()
            if min_len <= len(path) <= max_len:
                mcnodes.update(path)
            if len(path) >= max_len:
                continue
            for succ in G.successors(current):
                rel_type = G[current][succ].get("type", "")
               # if rel_type not in allowed_rel_types:
                #    continue
                if not is_service_node(succ):
                    continue
                if succ in path:
                    continue
                stack.append((succ, path + [succ]))

    return mcnodes
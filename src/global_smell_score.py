# -*- coding: utf-8 -*-


import os
import xml.etree.ElementTree as ET
from typing import Dict, Any

import networkx as nx
import community as community_louvain  # python-louvain
import pandas as pd
import numpy as np

from gss_smells.gss_dense_structure import compute_s2_dense_structure
from gss_smells.gss_hub_modularization import compute_s4_hub_modularization
from gss_smells.gss_modularity import compute_s1_modularity
from gss_smells.gss_strict_layers import compute_s3_strict_layers


W_WEAK_MODULARITY = 0.36
W_DENSE_STRUCTURE = 0.22
W_STRICT_LAYERS = 0.14
W_HUB_MODULARIZATION = 0.28

ARCHIMATE_NS = "{http://www.opengroup.org/xsd/archimate}"


def compute_global_smell_score(G: nx.Graph, layer_attr="layer"):
    if G.is_directed():
        H = G.to_undirected()
        D = G
    else:
        H = G
        D = G.to_directed()

    if H.number_of_nodes() == 0:
        return {
            "num_nodes": 0,
            "num_edges": 0,
            "Q_modularity": 0.0,
            "num_communities": 0,
            "num_dense_nodes": 0,
            "dense_threshold": 0.0,
            "num_strict_viol_edges": 0,
            "num_hub_nodes": 0,
            "hub_degree_threshold": 0.0,
            "S1_weakened_modularity": 0.0,
            "S2_dense_structure": 0.0,
            "S3_strict_layers_violation": 0.0,
            "S4_hub_like_modularization": 0.0,
            "weight_modularity": 0.0,
            "weight_dense": 0.0,
            "weight_strict": 0.0,
            "weight_hub": 0.0,
            "Global_SmellScore": 0.0,
        }

    s1 = compute_s1_modularity(H)
    s2 = compute_s2_dense_structure(H)
    s3 = compute_s3_strict_layers(D, layer_attr)
    s4 = compute_s4_hub_modularization(H)

    S1 = float(s1["S1"])
    S2 = float(s2["S2"])
    S3 = float(s3["S3"])
    S4 = float(s4["S4"])

    w_sum = (
        W_WEAK_MODULARITY
        + W_DENSE_STRUCTURE
        + W_STRICT_LAYERS
        + W_HUB_MODULARIZATION
    )

    w1 = W_WEAK_MODULARITY / w_sum
    w2 = W_DENSE_STRUCTURE / w_sum
    w3 = W_STRICT_LAYERS / w_sum
    w4 = W_HUB_MODULARIZATION / w_sum

    global_smell_score = w1 * S1 + w2 * S2 + w3 * S3 + w4 * S4

    return {
        "num_nodes": H.number_of_nodes(),
        "num_edges": H.number_of_edges(),
        "Q_modularity": float(s1.get("Q_modularity", 0.0)),
        "num_communities": int(s1.get("num_communities", 0)),
        "num_dense_nodes": int(s2.get("num_dense_nodes", 0)),
        "dense_threshold": float(s2.get("dense_threshold", 0.0)),
        "num_strict_viol_edges": int(s3.get("num_strict_viol_edges", 0)),
        "num_hub_nodes": int(s4.get("num_hub_nodes", 0)),
        "hub_degree_threshold": float(s4.get("hub_degree_threshold", 0.0)),
        "S1_weakened_modularity": S1,
        "S2_dense_structure": S2,
        "S3_strict_layers_violation": S3,
        "S4_hub_like_modularization": S4,
        "weight_modularity": w1,
        "weight_dense": w2,
        "weight_strict": w3,
        "weight_hub": w4,
        "Global_SmellScore": float(global_smell_score),
    }


def infer_layer_from_xsi_type(xsi_type: str | None) -> str | None:
    t = xsi_type.lower() if xsi_type else ""
    if "capability" in t or "resource" in t or "courseofaction" in t or "strategy" in t:
        return "Strategy"
    if "business" in t:
        return "Business"
    if "application" in t:
        return "Application"
    if (
        "technology" in t
        or "node" in t
        or "device" in t
        or "systemsoftware" in t
        or "artifact" in t
        or "path" in t
        or "network" in t
    ):
        return "Technology"
    return None


def build_graph_from_xml(xml_path: str) -> nx.DiGraph:
    tree = ET.parse(xml_path)
    root = tree.getroot()

    if "{" in root.tag:
        ns = root.tag.split("}")[0] + "}"
    else:
        ns = ARCHIMATE_NS

    G = nx.DiGraph()

    elements_parent = root.find(f"{ns}elements")
    if elements_parent is not None:
        for elem in elements_parent.findall(f"{ns}element"):
            elem_id = elem.attrib.get("identifier") or elem.attrib.get("id")
            xsi_type = elem.attrib.get("{http://www.w3.org/2001/XMLSchema-instance}type")
            layer = infer_layer_from_xsi_type(xsi_type)
            name_el = elem.find(f"{ns}name")
            name = name_el.text.strip() if name_el is not None and name_el.text else None
            if elem_id:
                G.add_node(elem_id, layer=layer, xsi_type=xsi_type, name=name)

    rels_parent = root.find(f"{ns}relationships")
    if rels_parent is not None:
        for rel in rels_parent.findall(f"{ns}relationship"):
            src = rel.attrib.get("source")
            tgt = rel.attrib.get("target")
            rel_type = rel.attrib.get("{http://www.w3.org/2001/XMLSchema-instance}type")
            if src in G.nodes and tgt in G.nodes:
                G.add_edge(src, tgt, rel_type=rel_type)

    return G


def build_smell_dataset_from_folder(folder_path: str) -> pd.DataFrame:
    rows = []

    for root_dir, _, files in os.walk(folder_path):
        for filename in files:
            if not filename.lower().endswith(".xml"):
                continue

            xml_path = os.path.join(root_dir, filename)
            model_id = os.path.basename(xml_path)
            print(f"\n[INFO] Processing XML model: {xml_path}")

            try:
                G = build_graph_from_xml(xml_path)
                metrics = compute_global_smell_score(G, layer_attr="layer")

                rows.append({
                    "model_id": model_id,
                    "num_nodes": metrics["num_nodes"],
                    "num_edges": metrics["num_edges"],
                    "S1": metrics["S1_weakened_modularity"],
                    "S2": metrics["S2_dense_structure"],
                    "S3": metrics["S3_strict_layers_violation"],
                    "S4": metrics["S4_hub_like_modularization"],
                    "Global_SmellScore": metrics["Global_SmellScore"],
                })

                print(
                    f"[OK] Global_SmellScore={metrics['Global_SmellScore']:.4f} "
                    f"(S1={metrics['S1_weakened_modularity']:.4f}, "
                    f"S2={metrics['S2_dense_structure']:.4f}, "
                    f"S3={metrics['S3_strict_layers_violation']:.4f}, "
                    f"S4={metrics['S4_hub_like_modularization']:.4f})"
                )

            except Exception as e:
                print(f"[ERROR] Failed to process {xml_path}: {e}")

    if not rows:
        raise ValueError("No XML files processed in the folder (including subfolders).")

    return pd.DataFrame(rows)


if __name__ == "__main__":
    XML_FOLDER = r"D:\TestDatasets\01"
    print("=== Building smell dataset (S1..S4 + Global_SmellScore) ===")
    df = build_smell_dataset_from_folder(XML_FOLDER)
    print(f"\nNumber of EA models: {len(df)}\n")
    print("First rows of smell dataset:")
    print(df.head())
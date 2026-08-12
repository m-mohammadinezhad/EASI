import os
import xml.etree.ElementTree as ET
from collections import defaultdict
from typing import Dict, List, Any, Tuple

import networkx as nx
import numpy as np
import pandas as pd

from lss_smells.god_object import detect_god_object
from lss_smells.dead_element import detect_dead_element
from lss_smells.message_chain import detect_message_chain
from lss_smells.cyclic_dependency import detect_cyclic_dependencies
from lss_smells.chatty_service import detect_chatty_services


EA_SMELL_WEIGHTS = {
   "GodObject": 0.06,
    "CyclicDependency": 0.14,
    "MessageChain": 0.36,
    "DeadElement": 0.09,
    "ChattyService": 0.35,
}

LAMBDA_C = 1.0
SEED = 42

ALLOWED_REL_TYPES_FOR_MC = {
    "TriggeringRelation",
    "FlowRelationship",
    "AssociationRelationship",
    "AssignmentRelationship",
    "ServingRelationship",
}


def safe_sheet_name(name: str) -> str:
    return name[:31]


def infer_layer_from_xsi_type(xsi_type: str | None) -> str:
    if not xsi_type:
        return "Other"
    t = xsi_type.lower()
    if "business" in t:
        return "Business"
    if "application" in t:
        return "Application"
    if "technology" in t or "node" in t or "device" in t or "artifact" in t:
        return "Technology"
    if "data" in t:
        return "Data"
    return "Other"


def parse_archimate_model(xml_file_path: str):
    tree = ET.parse(xml_file_path)
    root = tree.getroot()

    ns = root.tag.split("}")[0] + "}" if "}" in root.tag else ""

    G = nx.DiGraph()
    layer_info = {}
    element_details = {}
    elements_rows = []
    relationships_rows = []

    elements_parent = root.find(f"{ns}elements")
    if elements_parent is not None:
        for elem in elements_parent.findall(f"{ns}element"):
            elem_id = elem.attrib.get("identifier") or elem.attrib.get("id")
            if not elem_id:
                continue

            xsi_type = elem.attrib.get("{http://www.w3.org/2001/XMLSchema-instance}type")
            name_el = elem.find(f"{ns}name")
            name = name_el.text.strip() if name_el is not None and name_el.text else None
            layer = infer_layer_from_xsi_type(xsi_type)

            G.add_node(elem_id, name=name, xsi_type=xsi_type, layer=layer)
            layer_info[elem_id] = layer
            element_details[elem_id] = {
                "name": name,
                "type": xsi_type,
                "layer": layer,
            }

            elements_rows.append({
                "id": elem_id,
                "name": name,
                "type": xsi_type,
                "layer": layer,
            })

    rels_parent = root.find(f"{ns}relationships")
    if rels_parent is not None:
        for rel in rels_parent.findall(f"{ns}relationship"):
            src = rel.attrib.get("source")
            tgt = rel.attrib.get("target")
            rel_type = rel.attrib.get("{http://www.w3.org/2001/XMLSchema-instance}type")
            rel_id = rel.attrib.get("identifier") or rel.attrib.get("id")

            if src in G and tgt in G:
                G.add_edge(src, tgt, rel_type=rel_type, id=rel_id)
                relationships_rows.append({
                    "id": rel_id,
                    "source": src,
                    "target": tgt,
                    "type": rel_type,
                })

    return G, layer_info, element_details, elements_rows, relationships_rows


def detect_local_smells(G: nx.DiGraph, layer_info: Dict[str, str], element_details: Dict[str, Dict[str, Any]]):
    smells = defaultdict(list)

    detect_god_object(G, element_details, smells, function_threshold=3, service_threshold=2)
    detect_dead_element(G, element_details, smells)

    mc_nodes = detect_message_chain(
        G,
        element_details,
        allowed_rel_types=ALLOWED_REL_TYPES_FOR_MC,
        min_len=4,
        max_len=10,
    )
    for node_id in mc_nodes:
        smells[node_id].append("MessageChain")

    cycles = detect_cyclic_dependencies(G, element_details)
    for node_id in cycles.keys():
        smells[node_id].append("CyclicDependency")

    chatty_nodes = detect_chatty_services(G, element_details)
    for node_id in chatty_nodes:
        smells[node_id].append("ChattyService")

    return dict(smells), cycles


def calculate_local_smell_score(G: nx.DiGraph, smells: Dict[str, List[str]], element_details: Dict[str, Dict[str, Any]]):
    n = G.number_of_nodes()
    if n == 0:
        return 0.0, {}

    if n <= 50:
        centrality = nx.betweenness_centrality(G, normalized=True)
    else:
        k = min(50, max(10, int(np.sqrt(n))))
        centrality = nx.betweenness_centrality(G, k=k, seed=SEED, normalized=True)

    max_c = max(centrality.values()) if centrality else 0.0
    if max_c > 0:
        centrality = {node: val / max_c for node, val in centrality.items()}
    else:
        centrality = {node: 0.0 for node in G.nodes()}

    node_rows = []
    node_scores = {}

    for node in G.nodes():
        smell_list = smells.get(node, [])
        # smell_score = sum(EA_SMELL_WEIGHTS.get(s, 0.0) for s in smell_list)
        # final_score = LAMBDA_C * centrality.get(node, 0.0) + smell_score
        smell_intensity = sum(EA_SMELL_WEIGHTS.get(s, 0.0) for s in smell_list)
        centrality_val = centrality.get(node, 0.0)

        # LSS(n) = B(n) * (1 + lambda * C(n))
        #فرمول قدیمی 
        # final_score = smell_intensity * (1 + LAMBDA_C * centrality_val
        final_score = smell_intensity + (LAMBDA_C * centrality_val * smell_intensity * (1 - smell_intensity))

        
        node_scores[node] = float(final_score)

        node_rows.append({
            "node_id": node,
            "name": element_details.get(node, {}).get("name"),
            "type": element_details.get(node, {}).get("type"),
            "layer": element_details.get(node, {}).get("layer"),
            "in_degree": G.in_degree(node),
            "out_degree": G.out_degree(node),
            "betweenness_centrality": centrality.get(node, 0.0),
            "smells": ", ".join(smell_list),
            "smell_score": smell_intensity,
            "final_node_score": final_score,
        })

    local_smell_score = float(np.mean(list(node_scores.values()))) if node_scores else 0.0
    return local_smell_score, node_scores, pd.DataFrame(node_rows)


def build_local_smell_dataset(folder_path: str, output_excel_path: str):
    model_summary_rows = []
    all_node_score_frames = []
    all_smell_rows = []
    all_cycle_rows = []

    for root_dir, _, files in os.walk(folder_path):
        for filename in files:
            if not filename.lower().endswith(".xml"):
                continue

            xml_path = os.path.join(root_dir, filename)

            try:
                G, layer_info, element_details, elements_rows, relationships_rows = parse_archimate_model(xml_path)
                smells, cycles = detect_local_smells(G, layer_info, element_details)
                local_score, node_scores, node_df = calculate_local_smell_score(G, smells, element_details)

                model_summary_rows.append({
                    "model_id": filename,
                    "num_nodes": G.number_of_nodes(),
                    "num_edges": G.number_of_edges(),
                    "num_smelly_nodes": len(smells),
                    "Local_SmellScore": local_score,
                })

                node_df.insert(0, "model_id", filename)
                all_node_score_frames.append(node_df)

                for node_id, smell_list in smells.items():
                    for smell in smell_list:
                        all_smell_rows.append({
                            "model_id": filename,
                            "node_id": node_id,
                            "name": element_details.get(node_id, {}).get("name"),
                            "smell_type": smell,
                        })

                for node_id, cycle_list in cycles.items():
                    for cycle_members in cycle_list:
                        all_cycle_rows.append({
                            "model_id": filename,
                            "node_id": node_id,
                            "name": element_details.get(node_id, {}).get("name"),
                            "cycle_members": " | ".join(cycle_members),
                        })

            except Exception as e:
                print(f"[ERROR] {filename}: {e}")

    if not model_summary_rows:
        raise ValueError("No XML files processed.")

    df_summary = pd.DataFrame(model_summary_rows)
    df_nodes = pd.concat(all_node_score_frames, ignore_index=True) if all_node_score_frames else pd.DataFrame()
    df_smells = pd.DataFrame(all_smell_rows)
    df_cycles = pd.DataFrame(all_cycle_rows)

    with pd.ExcelWriter(output_excel_path, engine="openpyxl") as writer:
        df_summary.to_excel(writer, sheet_name=safe_sheet_name("Model_Summary"), index=False)
        df_nodes.to_excel(writer, sheet_name=safe_sheet_name("Node_Scores"), index=False)
        df_smells.to_excel(writer, sheet_name=safe_sheet_name("Detected_Smells"), index=False)
        df_cycles.to_excel(writer, sheet_name=safe_sheet_name("Cycles"), index=False)

    return df_summary, df_nodes, df_smells, df_cycles


if __name__ == "__main__":
    XML_FOLDER = r"D:\TestDatasets\01"
    OUTPUT_EXCEL = r"D:\TestDatasets\01\local_smell_report.xlsx"

    df_summary, df_nodes, df_smells, df_cycles = build_local_smell_dataset(XML_FOLDER, OUTPUT_EXCEL)

    print("Done.")
    print(df_summary.head())

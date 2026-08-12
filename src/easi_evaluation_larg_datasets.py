import os
import math
import pandas as pd

from local_smell_score import (
    parse_archimate_model,
    detect_local_smells,
    calculate_local_smell_score,
)

from global_smell_score import compute_global_smell_score


ALPHA = 0.6


LOCAL_SMELL_WEIGHTS = {
    "GodObject": 0.14,
    "CyclicDependency": 0.03,
    "MessageChain": 0.33,
    "DeadElement": 0.16,
    "ChattyService": 0.34,
}

LAMBDA_C = 1.0


def is_archimate_file(filename):
    filename = filename.lower()
    return filename.endswith(".xml") or filename.endswith(".archimate")


def prepare_local_rows(model_id, node_df):
    rows = []

    for _, row in node_df.iterrows():
        smells_raw = row.get("smells", [])

        if isinstance(smells_raw, str):
            smell_list = [
                s.strip()
                for s in smells_raw.replace("[", "").replace("]", "").replace("'", "").split(",")
                if s.strip()
            ]
        elif isinstance(smells_raw, list):
            smell_list = smells_raw
        else:
            smell_list = []

        god = 1 if "GodObject" in smell_list else 0
        cyclic = 1 if "CyclicDependency" in smell_list else 0
        message = 1 if "MessageChain" in smell_list else 0
        dead = 1 if "DeadElement" in smell_list else 0
        chatty = 1 if "ChattyService" in smell_list else 0

        smell_score = (
            god * LOCAL_SMELL_WEIGHTS["GodObject"] +
            cyclic * LOCAL_SMELL_WEIGHTS["CyclicDependency"] +
            message * LOCAL_SMELL_WEIGHTS["MessageChain"] +
            dead * LOCAL_SMELL_WEIGHTS["DeadElement"] +
            chatty * LOCAL_SMELL_WEIGHTS["ChattyService"]
        )

        bet_cent = row.get("betweenness_centrality", 0.0)

        final_node_score = smell_score + (
            LAMBDA_C * bet_cent * smell_score * (1 - smell_score)
        )

        rows.append({
            "model_id": model_id,
            "node_id": row.get("node_id", ""),
            "name": row.get("name", ""),
            "type": row.get("type", ""),
            "layer": row.get("layer", ""),
            "in_degree": row.get("in_degree", 0),
            "out_degree": row.get("out_degree", 0),
            "betweenness_centrality": bet_cent,
            "GodObject": god,
            "CyclicDependency": cyclic,
            "MessageChain": message,
            "DeadElement": dead,
            "ChattyService": chatty,
            "smell_score": smell_score,
            "final_node_score": final_node_score,
        })

    return rows


def prepare_global_row(model_id, gss_result):
    s1 = gss_result.get("S1_weakened_modularity", 0)
    s2 = gss_result.get("S2_dense_structure", 0)
    s3 = gss_result.get("S3_strict_layers_violation", 0)
    s4 = gss_result.get("S4_hub_like_modularization", 0)

    w1 = gss_result.get("weight_modularity", 0.43)
    w2 = gss_result.get("weight_dense", 0.10)
    w3 = gss_result.get("weight_strict", 0.10)
    w4 = gss_result.get("weight_hub", 0.37)

    global_smell_score = (w1 * s1) + (w2 * s2) + (w3 * s3) + (w4 * s4)

    return {
        "model_id": model_id,
        "num_nodes": gss_result.get("num_nodes", 0),
        "num_edges": gss_result.get("num_edges", 0),
        "Q_modularity": gss_result.get("Q_modularity", 0),
        "num_communities": gss_result.get("num_communities", 0),
        "num_dense_nodes": gss_result.get("num_dense_nodes", 0),
        "dense_threshold": gss_result.get("dense_threshold", 0),
        "num_strict_viol_edges": gss_result.get("num_strict_viol_edges", 0),
        "num_hub_nodes": gss_result.get("num_hub_nodes", 0),
        "hub_degree_threshold": gss_result.get("hub_degree_threshold", 0),
        "S1_weakened_modularity": s1,
        "S2_dense_structure": s2,
        "S3_strict_layers_violation": s3,
        "S4_hub_like_modularization": s4,
        "weight_modularity": w1,
        "weight_dense": w2,
        "weight_strict": w3,
        "weight_hub": w4,
        "Global_SmellScore": global_smell_score,
    }


def compute_lss_metrics_from_rows(local_rows):
    """
    Calculate the LSS metrics entirely numerically in Python.
    """
    if not local_rows:
        return 0.0, 0.0, 0.0

    final_scores = []
    smelly_final_scores = []

    for row in local_rows:
        final_node_score = row.get("final_node_score", 0.0)
        smell_score = row.get("smell_score", 0.0)

        final_scores.append(final_node_score)

        if smell_score > 0:
            smelly_final_scores.append(final_node_score)

    lss_mean = sum(final_scores) / len(final_scores) if final_scores else 0.0

    lss_smelly = (
        sum(smelly_final_scores) / len(smelly_final_scores)
        if smelly_final_scores
        else 0.0
    )

    count = len(final_scores)
    n_top = max(1, math.ceil(count * 0.1))
    sorted_scores = sorted(final_scores, reverse=True)
    top_scores = sorted_scores[:n_top]
    lss_top10 = sum(top_scores) / len(top_scores) if top_scores else 0.0

    return lss_mean, lss_top10, lss_smelly


def evaluate_model(xml_path):
    model_id = os.path.basename(xml_path)

    G, layer_info, element_details, elements_rows, relationships_rows = parse_archimate_model(xml_path)

    gss_result = compute_global_smell_score(G)

    smells, cycles = detect_local_smells(
        G,
        layer_info,
        element_details,
    )

    local_smell_score, node_scores, node_df = calculate_local_smell_score(
        G,
        smells,
        element_details,
    )

    local_rows = prepare_local_rows(model_id, node_df)
    global_row = prepare_global_row(model_id, gss_result)

    smell_rows = []
    for node_id, smell_list in smells.items():
        # Convert the list of smells into a single comma-separated string
        if isinstance(smell_list, list):
            all_smells = ", ".join(smell_list)
        else:
            all_smells = str(smell_list)
        smell_rows.append({
            "model_id": model_id,
            "node_id": node_id,
            "smell_type": all_smells,
        })

    cycle_rows = []
    for cycle in cycles:
        cycle_rows.append({
            "model_id": model_id,
            "cycle": " -> ".join(map(str, cycle)),
        })

    element_rows = []
    for row in elements_rows:
        r = dict(row)
        r["model_id"] = model_id
        element_rows.append(r)

    relationship_rows = []
    for row in relationships_rows:
        r = dict(row)
        r["model_id"] = model_id
        relationship_rows.append(r)

    return {
        "model_id": model_id,
        "local_rows": local_rows,
        "global_row": global_row,
        "smell_rows": smell_rows,
        "cycle_rows": cycle_rows,
        "element_rows": element_rows,
        "relationship_rows": relationship_rows,
    }


def evaluate_folder(input_folder):
    summary_rows = []
    local_rows = []
    global_rows = []
    smell_rows = []
    cycle_rows = []
    element_rows = []
    relationship_rows = []
    counter = 1

    for filename in os.listdir(input_folder):
        if not is_archimate_file(filename):
            continue

        print(counter, "Selected:", filename)
        counter += 1
        xml_path = os.path.join(input_folder, filename)

        try:
            result = evaluate_model(xml_path)
            model_id = result["model_id"]

            lss_mean, lss_top10, lss_smelly = compute_lss_metrics_from_rows(
                result["local_rows"]
            )

            global_score = result["global_row"].get("Global_SmellScore", 0.0)

            easi_mean = ALPHA * global_score + (1 - ALPHA) * (1 - lss_mean)
            easi_top10 = ALPHA * global_score + (1 - ALPHA) * (1 - lss_top10)
            easi_smelly = ALPHA * global_score + (1 - ALPHA) * (1 - lss_smelly)

            summary_rows.append({
                "model_id": model_id,
                "Global_SmellScore": global_score,
                "Local_SmellScore_mean": lss_mean,
                "Local_SmellScore_top10": lss_top10,
                "Local_SmellScore_smelly": lss_smelly,
                "EASI_mean": easi_mean,
                "EASI_top10": easi_top10,
                "EASI_smelly": easi_smelly,
            })

            local_rows.extend(result["local_rows"])
            global_rows.append(result["global_row"])
            smell_rows.extend(result["smell_rows"])
            cycle_rows.extend(result["cycle_rows"])
            element_rows.extend(result["element_rows"])
            relationship_rows.extend(result["relationship_rows"])

            print("     Processed:", filename)

        except Exception as e:
            print("ERROR processing", filename, ":", e)

    return (
        pd.DataFrame(summary_rows),
        pd.DataFrame(local_rows),
        pd.DataFrame(global_rows),
        pd.DataFrame(smell_rows),
        pd.DataFrame(cycle_rows),
        pd.DataFrame(element_rows),
        pd.DataFrame(relationship_rows),
    )


def export_excel(
    output_file,
    df_summary,
    df_local,
    df_global,
    df_smells,
    df_cycles,
    df_elements,
    df_relationships,
):
    print("export_excel")

    ranking = df_summary.sort_values("EASI_mean", ascending=False).copy()
    ranking["Rank"] = range(1, len(ranking) + 1)

    with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
        df_summary.to_excel(writer, sheet_name="Summary", index=False)
        ranking.to_excel(writer, sheet_name="EASI_Ranking", index=False)
        df_local.to_excel(writer, sheet_name="Local_Smell_Calculation", index=False)
        df_global.to_excel(writer, sheet_name="Global_Smell_Calculation", index=False)
        df_smells.to_excel(writer, sheet_name="Detected_Smells", index=False)
        df_cycles.to_excel(writer, sheet_name="Cycles", index=False)
        df_elements.to_excel(writer, sheet_name="Elements", index=False)
        df_relationships.to_excel(writer, sheet_name="Relationships", index=False)


if __name__ == "__main__":
    # INPUT_FOLDER = r"D:\TestDatasets\02"
    INPUT_FOLDER = r"D:\TestDatasets\290"
    OUTPUT_FILE = r"E:\01_PhD.Papers\paper2_easi-v02\07_results\easi_results_290.xlsx"

    (
        df_summary,
        df_local,
        df_global,
        df_smells,
        df_cycles,
        df_elements,
        df_relationships,
    ) = evaluate_folder(INPUT_FOLDER)

    export_excel(
        OUTPUT_FILE,
        df_summary,
        df_local,
        df_global,
        df_smells,
        df_cycles,
        df_elements,
        df_relationships,
    )

    print("\nFinished.")
    print("Output file:", OUTPUT_FILE)

    os.startfile(OUTPUT_FILE)

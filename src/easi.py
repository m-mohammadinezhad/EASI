import os
import math
import pandas as pd
import argparse

from local_smell_score import (
    parse_archimate_model,
    detect_local_smells,
    calculate_local_smell_score,
)

from global_smell_score import compute_global_smell_score


ALPHA = 0.6


LOCAL_SMELL_WEIGHTS = {
    "GodObject": 0.06,
    "CyclicDependency": 0.14,
    "MessageChain": 0.36,
    "DeadElement": 0.09,
    "ChattyService": 0.35,
}

LAMBDA_C = 1.0


def is_archimate_file(filename):
    filename = filename.lower()
    return filename.endswith(".xml") or filename.endswith(".archimate")


def prepare_local_formula_rows(model_id, node_df):
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

        rows.append({
            "model_id": model_id,
            "node_id": row.get("node_id", ""),
            "name": row.get("name", ""),
            "type": row.get("type", ""),
            "layer": row.get("layer", ""),
            "in_degree": row.get("in_degree", 0),
            "out_degree": row.get("out_degree", 0),
            "betweenness_centrality": row.get("betweenness_centrality", 0.0),
            "GodObject": 1 if "GodObject" in smell_list else 0,
            "CyclicDependency": 1 if "CyclicDependency" in smell_list else 0,
            "MessageChain": 1 if "MessageChain" in smell_list else 0,
            "DeadElement": 1 if "DeadElement" in smell_list else 0,
            "ChattyService": 1 if "ChattyService" in smell_list else 0,
            "smell_score": "",
            "final_node_score": "",
        })
    return rows


def prepare_global_formula_row(model_id, gss_result):
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
        "S1_weakened_modularity": gss_result.get("S1_weakened_modularity", 0),
        "S2_dense_structure": gss_result.get("S2_dense_structure", 0),
        "S3_strict_layers_violation": gss_result.get("S3_strict_layers_violation", 0),
        "S4_hub_like_modularization": gss_result.get("S4_hub_like_modularization", 0),
        "weight_modularity": gss_result.get("weight_modularity", 0.43),
        "weight_dense": gss_result.get("weight_dense", 0.10),
        "weight_strict": gss_result.get("weight_strict", 0.10),
        "weight_hub": gss_result.get("weight_hub", 0.37),
        "Global_SmellScore": "",
    }


def compute_lss_metrics_from_rows(local_rows):
    if not local_rows:
        return 0.0, 0.0, 0.0

    final_scores = []
    smelly_final_scores = []

    for row in local_rows:
        god = row.get("GodObject", 0)
        cyclic = row.get("CyclicDependency", 0)
        message = row.get("MessageChain", 0)
        dead = row.get("DeadElement", 0)
        chatty = row.get("ChattyService", 0)

        # Calculate the Smell Score according to the Excel logic
        smell_score = (
            god * LOCAL_SMELL_WEIGHTS["GodObject"] +
            cyclic * LOCAL_SMELL_WEIGHTS["CyclicDependency"] +
            message * LOCAL_SMELL_WEIGHTS["MessageChain"] +
            dead * LOCAL_SMELL_WEIGHTS["DeadElement"] +
            chatty * LOCAL_SMELL_WEIGHTS["ChattyService"]
        )

        bet_cent = row.get("betweenness_centrality", 0.0)
        final_node_score = LAMBDA_C * bet_cent + smell_score  # Old formula
        final_node_score = smell_score + (LAMBDA_C * bet_cent * smell_score * (1 - smell_score))

        final_scores.append(final_node_score)

        # Include the node if it has an architectural smell
        if smell_score > 0:
            smelly_final_scores.append(final_node_score)

    # 1. Mean LSS
    lss_mean = sum(final_scores) / len(final_scores) if final_scores else 0.0

    # 2. Mean LSS of smelly nodes
    lss_smelly = sum(smelly_final_scores) / len(smelly_final_scores) if smelly_final_scores else 0.0

    # 3. Mean LSS of the top 10% of nodes (equivalent to the ROUNDUP and LARGE functions)
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

    local_rows = prepare_local_formula_rows(model_id, node_df)
    global_row = prepare_global_formula_row(model_id, gss_result)

    smell_rows = []
    for node_id, smell_list in smells.items():
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

        print(counter, " Selected:", filename)
        counter += 1
        xml_path = os.path.join(input_folder, filename)

        try:
            result = evaluate_model(xml_path)
            model_id = result["model_id"]

            # Accurately calculate the metrics in Python
            lss_mean, lss_top10, lss_smelly = compute_lss_metrics_from_rows(result["local_rows"])

            summary_rows.append({
                "model_id": model_id,
                "Global_SmellScore": "",
                "Local_SmellScore_mean": lss_mean,
                "Local_SmellScore_top10": lss_top10,
                "Local_SmellScore_smelly": lss_smelly,
                "EASI_mean": "",
                "EASI_top10": "",
                "EASI_smelly": "",
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


def add_local_excel_formulas(df_local):
    if df_local.empty:
        return df_local

    df_local = df_local.copy()
    for idx in range(len(df_local)):
        print("add_local_excel_formulas")
        r = idx + 2
        df_local.loc[idx, "smell_score"] = (
            f"={LOCAL_SMELL_WEIGHTS['GodObject']}*I{r}"
            f"+{LOCAL_SMELL_WEIGHTS['CyclicDependency']}*J{r}"
            f"+{LOCAL_SMELL_WEIGHTS['MessageChain']}*K{r}"
            f"+{LOCAL_SMELL_WEIGHTS['DeadElement']}*L{r}"
            f"+{LOCAL_SMELL_WEIGHTS['ChattyService']}*M{r}"
        )
        # df_local.loc[idx, "final_node_score"] = (f"={LAMBDA_C}*H{r}+N{r}")  # Old formula
        df_local.loc[idx, "final_node_score"] = f"= N{r} + ({LAMBDA_C}*H{r}*N{r})*(1-N{r})"

    return df_local


def add_global_excel_formulas(df_global):
    if df_global.empty:
        return df_global

    df_global = df_global.copy()
    for idx in range(len(df_global)):
        print("add_global_excel_formulas")
        r = idx + 2
        df_global.loc[idx, "Global_SmellScore"] = (
            f"=O{r}*K{r}+P{r}*L{r}+Q{r}*M{r}+R{r}*N{r}"
        )
    return df_global


def compute_numeric_summary_values(df_summary, df_global):
    """
    Calculate numeric values in Python to sort the DataFrames reliably
    before applying the final formulas.
    """
    df_summary = df_summary.copy()

    # Create a mapping for the Global Smell Score
    global_gss_map = {}
    for _, row in df_global.iterrows():
        m_id = row["model_id"]
        # Calculate the numeric value equivalent to the Excel formula
        val = (
            row["S1_weakened_modularity"] * row["weight_modularity"] +
            row["S2_dense_structure"] * row["weight_dense"] +
            row["S3_strict_layers_violation"] * row["weight_strict"] +
            row["S4_hub_like_modularization"] * row["weight_hub"]
        )
        global_gss_map[m_id] = val

    for idx, row in df_summary.iterrows():
        m_id = row["model_id"]
        gss_val = global_gss_map.get(m_id, 0.0)

        lss_mean = row["Local_SmellScore_mean"]
        lss_top10 = row["Local_SmellScore_top10"]
        lss_smelly = row["Local_SmellScore_smelly"]

        # Store numeric values in temporary helper columns for reliable sorting
        df_summary.loc[idx, "_gss_num"] = gss_val

        df_summary.loc[idx, "_easi_mean_num"] = ALPHA * lss_mean + (1 - ALPHA) * gss_val
        df_summary.loc[idx, "_easi_top10_num"] = ALPHA * lss_top10 + (1 - ALPHA) * gss_val
        df_summary.loc[idx, "_easi_smelly_num"] = ALPHA * lss_smelly + (1 - ALPHA) * gss_val

    return df_summary


def add_summary_excel_formulas(df_summary):
    if df_summary.empty:
        return df_summary

    df_summary = df_summary.copy()
    # Reset the index so the formulas exactly match the current order of the worksheet rows
    df_summary = df_summary.reset_index(drop=True)

    for idx in range(len(df_summary)):
        r = idx + 2  # Actual row number in Excel

        # 1. Global Smell Score: use a flexible VLOOKUP to keep rankings valid in all cases
        df_summary.loc[idx, "Global_SmellScore"] = (
            f"=IFERROR(VLOOKUP(A{r},Global_Smell_Calculation!$A:$S,19,FALSE), 0)"
        )

        # 2. EASI metrics: calculate dynamically using cells in the same row
        df_summary.loc[idx, "EASI_mean"] = f"={ALPHA}*C{r}+(1-{ALPHA})*B{r}"
        df_summary.loc[idx, "EASI_top10"] = f"={ALPHA}*D{r}+(1-{ALPHA})*B{r}"
        df_summary.loc[idx, "EASI_smelly"] = f"={ALPHA}*E{r}+(1-{ALPHA})*B{r}"

    # Remove the temporary Python helper columns before generating the final output
    temp_cols = ["_gss_num", "_easi_mean_num", "_easi_top10_num", "_easi_smelly_num"]
    df_summary = df_summary.drop(columns=[c for c in temp_cols if c in df_summary.columns])

    return df_summary


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
    # 1. Apply formulas to the base calculation worksheets
    df_local = add_local_excel_formulas(df_local)
    df_global = add_global_excel_formulas(df_global)

    # 2. Calculate summary values numerically in Python for mathematically accurate sorting
    df_summary_numeric = compute_numeric_summary_values(df_summary, df_global)

    # 3. Generate the final formulas for the main Summary worksheet
    df_summary_final = add_summary_excel_formulas(df_summary_numeric)

    # 4. Generate the EASI_Ranking worksheet dynamically and without errors
    # First, sort the rows based on the numeric calculations
    ranking_numeric = df_summary_numeric.sort_values("_easi_mean_num", ascending=False)
    # Add sequential ranks
    ranking_numeric["Rank"] = range(1, len(ranking_numeric) + 1)
    # Reapply dynamic formulas to the sorted worksheet using the correct row numbers
    ranking_final = add_summary_excel_formulas(ranking_numeric)

    print("export_excel")

    # 5. Save the data as an Excel file
    with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
        df_summary_final.to_excel(writer, sheet_name="Summary", index=False)
        ranking_final.to_excel(writer, sheet_name="EASI_Ranking", index=False)
        df_local.to_excel(writer, sheet_name="Local_Smell_Calculation", index=False)
        df_global.to_excel(writer, sheet_name="Global_Smell_Calculation", index=False)
        df_smells.to_excel(writer, sheet_name="Detected_Smells", index=False)
        df_cycles.to_excel(writer, sheet_name="Cycles", index=False)
        df_elements.to_excel(writer, sheet_name="Elements", index=False)
        df_relationships.to_excel(writer, sheet_name="Relationships", index=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Evaluate EASI metrics for a folder of ArchiMate models."
    )
    parser.add_argument(
        "--input",
        required=True,
        help="Path to the folder containing ArchiMate model files.",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Path of the output Excel file.",
    )
    args = parser.parse_args()

    INPUT_FOLDER = args.input
    OUTPUT_FILE = args.output

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

    print(f"EASI evaluation completed successfully: {OUTPUT_FILE}")


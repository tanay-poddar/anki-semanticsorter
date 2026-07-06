from aqt import mw
from .constants import CLOZE_RE, HTML_RE, DELIMITER_RE, PUNCT_RE, SPACES_RE, MEDICAL_STOP_WORDS
import time
import os
import json
from datetime import datetime

BENCHMARK_DIR = os.path.join(os.path.dirname(__file__), "benchmarks")
BENCHMARK_FILE = os.path.join(BENCHMARK_DIR, "runtime.json")

def load_benchmarks():
    if not os.path.exists(BENCHMARK_DIR):
        os.makedirs(BENCHMARK_DIR, exist_ok=True)
    if not os.path.exists(BENCHMARK_FILE):
        return []
    try:
        with open(BENCHMARK_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return []


def save_benchmark(entry):
    if not os.path.exists(BENCHMARK_DIR):
        os.makedirs(BENCHMARK_DIR, exist_ok=True)
    data = load_benchmarks()
    data.append(entry)

    BIN_SIZE = 200
    MAX_PER_BIN = 3

    current_mode = entry.get("mode")
    current_count = entry.get("count", 0)
    current_bin = current_count // BIN_SIZE

    matching_bin_runs = []
    other_runs = []
    
    for r in data:
        if r.get("mode") == current_mode and (r.get("count", 0) // BIN_SIZE) == current_bin:
            matching_bin_runs.append(r)
        else:
            other_runs.append(r)

    matching_bin_runs.append(entry)
    
    # If the bin is too crowded, eject the oldest run (first in the list)
    if len(matching_bin_runs) > MAX_PER_BIN:
        matching_bin_runs = matching_bin_runs[-MAX_PER_BIN:]
        
    # Recombine the datasets
    optimized_data = other_runs + matching_bin_runs

    with open(BENCHMARK_FILE, "w") as f:
        json.dump(optimized_data, f)

def extract_and_clean_texts(deck_name, field_name):
    query = f'deck:"{deck_name}" is:new -is:suspended'
    card_ids = mw.col.find_cards(query)
    if not card_ids:
        return None, "No unsuspended new cards found."

    all_texts, all_cids = [], []
    id_string = ",".join(str(cid) for cid in card_ids)
    db_data = mw.col.db.all(f"""
        SELECT c.id, n.flds, n.tags, n.mid 
        FROM cards c 
        JOIN notes n ON c.nid = n.id 
        WHERE c.id IN ({id_string})
    """)

    model_cache = {}
    for cid, flds, tags_str, mid in db_data:
        if mid not in model_cache:
            model = mw.col.models.get(mid)
            field_map = {f['name']: f['ord'] for f in model['flds']}
            model_cache[mid] = {
                'target_idx': field_map.get(field_name, 0),
                'extra_idx': field_map.get('Extra', None)
            }
        
        cfg = model_cache[mid]
        fields_list = flds.split("\x1f")
        t_idx, e_idx = cfg['target_idx'], cfg['extra_idx']
        
        text = fields_list[t_idx] if t_idx < len(fields_list) else ""
        if e_idx is not None and e_idx < len(fields_list):
            text += " " + fields_list[e_idx]

        tags = [t for t in tags_str.strip().split() if t and t.lower() != "notak"]
        tags = [t.split("::")[-1] for t in tags]
        if tags:
            text += " " + " ".join(tags)

        text = CLOZE_RE.sub('', text)
        text = HTML_RE.sub(' ', text)
        text = DELIMITER_RE.sub(' ', text)
        text = PUNCT_RE.sub(' ', text)
        text = SPACES_RE.sub(' ', text).strip()

        all_texts.append(text)
        all_cids.append(cid)

    if not all_texts:
        return None, f"No cards found with field '{field_name}'."
        
    return (all_texts, all_cids), None

def profile_deck_complexity(all_texts):
    import numpy as np

    n_cards = len(all_texts)
    if n_cards <= 0:
        return 0.0, 0.0

    history = load_benchmarks()
    coeff_fast = np.array([0.1, 0.5])       # [a, b]
    coeff_precision = np.array([0.1, 0.5, 2.0])  # [a, b, c]

    # Split history by mode to prevent cross-contamination
    fast_runs = [r for r in history if r.get("mode") == "fast" and r.get("count", 0) > 0 and r.get("elapsed", 0.0) > 0]
    precision_runs = [r for r in history if r.get("mode") == "precision" and r.get("count", 0) > 0 and r.get("elapsed", 0.0) > 0]

    # Fit Fast Mode Model
    if len(fast_runs) >= 2:
        A_fast, B_fast = [], []
        for run in fast_runs:
            x = run["count"] 
            A_fast.append([x, x ** 2])
            B_fast.append(run["elapsed"])
        
        try:
            x_opt, _, _, _ = np.linalg.lstsq(A_fast, B_fast, rcond=None)
            coeff_fast[0] = max(x_opt[0], 1e-4)
            coeff_fast[1] = max(x_opt[1], 1e-6)
        except Exception:
            pass # Fallback to default coefficients on numerical failure
    
    # Fit Precision Mode Model
    if len(precision_runs) >= 3:
        A_prec, B_prec = [], []
        for run in precision_runs:
            x = run["count"]
            A_prec.append([x, x ** 2, x ** 3])
            B_prec.append(run["elapsed"])
            
        try:
            x_opt, _, _, _ = np.linalg.lstsq(A_prec, B_prec, rcond=None)
            coeff_precision[0] = max(x_opt[0], 1e-4)
            coeff_precision[1] = max(x_opt[1], 1e-6)
            coeff_precision[2] = max(x_opt[2], 1e-8)
        except Exception:
            pass
    
    est_fast = (coeff_fast[0] * n_cards) + (coeff_fast[1] * (n_cards ** 2))
    est_precision = (coeff_precision[0] * n_cards) + (coeff_precision[1] * (n_cards ** 2)) + (coeff_precision[2] * (n_cards ** 3))

    return est_fast, est_precision

def execute_sorting_background(all_texts, all_cids, mode_choice):
    from scipy.cluster.hierarchy import linkage, optimal_leaf_ordering, leaves_list
    from sklearn.feature_extraction.text import TfidfVectorizer, ENGLISH_STOP_WORDS
    from sklearn.metrics.pairwise import pairwise_distances
    import numpy as np

    start_time = time.time()
    custom_stop_words = ENGLISH_STOP_WORDS.union(MEDICAL_STOP_WORDS)

    try:
        vec = TfidfVectorizer(
                stop_words=list(custom_stop_words),
                ngram_range=(1, 3),
                token_pattern=r'(?u)\b\w+\b',
                min_df=2,
                max_df=0.90
            )
        X_reduced = vec.fit_transform(all_texts)
        amplify_factor = np.log1p(vec.idf_)
        X_reduced.data *= amplify_factor[X_reduced.indices]
    except Exception as e:
        return {"success": False, "error": f"TF-IDF vectorization failed: {e}"}

    try:
        dist_matrix = pairwise_distances(X_reduced, metric='cosine')
        link = linkage(dist_matrix, method="ward")
        
        if mode_choice == 0:
            use_fallback = "TF-IDF (Precision Mode)"
            ordered_link = optimal_leaf_ordering(link, dist_matrix)
            order = leaves_list(ordered_link)
        else:
            use_fallback = "TF-IDF (Fast Mode)"
            order = leaves_list(link)
                
        if len(order) != len(all_cids):
            return {"success": False, "error": "Unsuccessful clustering parameters calculated."}
            
    except Exception as e:
        return {"success": False, "error": f"Clustering failed: {e}"}

    ordered_cids = [all_cids[idx] for idx in order]
    result =  {
        "success": True, 
        "ordered_cids": ordered_cids,
        "use_fallback": use_fallback, 
        "elapsed": time.time() - start_time,
        "count": len(order)
    }

    save_benchmark({
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "mode": "precision" if mode_choice == 0 else "fast",
        "count": result['count'],
        "elapsed": result['elapsed']
    })
    return result
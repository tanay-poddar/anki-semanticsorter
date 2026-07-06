import json
import pandas as pd
import matplotlib.pyplot as plt
import os
import numpy as np

# Read the file path from file location
current_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(current_dir)

# Read the JSON file

with open('runtime.json', 'r') as f:
    data = json.load(f)

# Convert the JSON data to a DataFrame
df = pd.DataFrame(data)
print(df)

if len(df) >= 3:
    A_mat, B_mat = [], []
    for run in df.itertuples(index=False):
        num_cards = run.count
        elapsed_time = run.elapsed
        mode = run.mode
        
        if num_cards <= 0 or elapsed_time <= 0.0:
            continue
            
        if mode == "precision":
            A_mat.append([num_cards, num_cards ** 2, num_cards ** 3])
        else:
            A_mat.append([num_cards, num_cards ** 2, 0.0])
        B_mat.append(elapsed_time)
        
    if len(A_mat) >= 3:
        try:
            x_opt, _, _, _ = np.linalg.lstsq(A_mat, B_mat, rcond=None)
            
            a = max(x_opt[0], 1e-6)
            b = max(x_opt[1], 1e-9)
            c = max(x_opt[2], 1e-12)
        except Exception:
            pass

fast_direct = lambda n: (a * n) + (b * (n ** 2))
precision_total = lambda n: (a * n) + (b * (n ** 2)) + (c * (n ** 3))

# Plot the count (x) vs elapsed time (y) for both modes
plt.figure(figsize=(10, 6))
for run in df.itertuples(index=False):
    color = 'blue' if run.mode == 'fast' else 'orange'
    plt.scatter(run.count, run.elapsed, label=f'Mode: {run.mode}', alpha=0.6, color=color)

# Plot the fitted curves
n_values = np.linspace(0, df['count'].max(), 100)

# Give 3 points that are evenly spaced that fall along the fitted curves
n_points = np.linspace(0, df['count'].max(), 3)
# For each these points, we want to store it in a new json file called fitted_points.json, with the following structure:
fitted_points = {
    "timestamp": [],
    "mode": [],
    "count": [],
    "elapsed": []
}
for n in n_points:
    fitted_points["timestamp"].append(pd.Timestamp.now().isoformat())
    fitted_points["mode"].append("fast")
    fitted_points["count"].append(n)
    fitted_points["elapsed"].append(fast_direct(n))
    
    fitted_points["timestamp"].append(pd.Timestamp.now().isoformat())
    fitted_points["mode"].append("precision")
    fitted_points["count"].append(n)
    fitted_points["elapsed"].append(precision_total(n))

# Save the fitted points to a new JSON file
with open('fitted_points.json', 'w') as f:
    json.dump(fitted_points, f, indent=4)
    

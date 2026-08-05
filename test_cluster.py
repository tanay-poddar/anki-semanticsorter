import numpy as np
from scipy.sparse import random as sparse_random
from sklearn.metrics import pairwise_distances_chunked
from scipy.spatial.distance import pdist

# 1. Generate "Noise" (Synthetic Sparse Data)
n_samples = 1000
n_features = 500
density = 0.05  # 5% of elements are non-zero

print(f"Generating {n_samples}x{n_features} sparse matrix (density: {density})...")
# CSR format is highly recommended for scikit-learn's distance metrics
X_reduced = sparse_random(
    n_samples, 
    n_features, 
    density=density, 
    format='csr', 
    data_rvs=np.random.randn, 
    random_state=42
)

# 2. Run Your Optimized Chunked Method
print("Running chunked condensed distance calculation...")
condensed_size = n_samples * (n_samples - 1) // 2

# Changed to float64 to match standard pdist output precision for the test
dist_condensed = np.empty(condensed_size, dtype=np.float64) 
col_indices = np.arange(n_samples)

current_idx = 0
row_start = 0

for D_chunk in pairwise_distances_chunked(X_reduced, metric='euclidean', n_jobs=-1):
    chunk_size = D_chunk.shape[0]
    row_idx = np.arange(row_start, row_start + chunk_size)[:, None]
    valid_dists = D_chunk[col_indices > row_idx]
    end_idx = current_idx + valid_dists.shape[0]
    dist_condensed[current_idx:end_idx] = valid_dists
    current_idx = end_idx
    row_start += chunk_size

# 3. Validate Against Standard Method
print("Running standard scipy pdist for validation...")
X_dense = X_reduced.toarray() 
expected_dist_condensed = pdist(X_dense, metric='euclidean')

# Compare the two arrays
print("Comparing results...")
np.testing.assert_allclose(dist_condensed, expected_dist_condensed, rtol=1e-6, atol=1e-6)

print("Success! Your chunked logic perfectly matches the standard condensed distance matrix.")
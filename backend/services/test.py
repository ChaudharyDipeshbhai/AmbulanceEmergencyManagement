import numpy as np
import time
from math import radians, sin, cos, sqrt, atan2
import pandas as pd
import sys
import os
sys.path.append(os.path.dirname(__file__))
from excel_service import load_and_prepare_data

# Try to import KDTree (sklearn). If unavailable, fallback to a simple implementation.
try:
    from sklearn.neighbors import KDTree
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

# Haversine distance function
def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0  # Earth radius in km
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    return R * c

# Load ambulance coordinates from CSV
ambulance_df = load_and_prepare_data("data/AMBULANCE - Copy.csv", ['State', 'Lat', 'Long', 'Emergency_Level', 'availibility'])
# Filter available ambulances
available_df = ambulance_df[ambulance_df['Status'] == 'Available']
ambulances = available_df[['Latitude', 'Longitude']].values  # numpy array of shape (n, 2)

# Random patient location
patient = np.array([23.0205, 72.5714])  # Example: Ahmedabad

# ------------------------------
# Haversine brute-force benchmark
# ------------------------------
start = time.time()

distances = np.array([
    haversine(patient[0], patient[1], amb[0], amb[1]) 
    for amb in ambulances
])

nearest_haversine_idx = np.argmin(distances)
nearest_haversine_dist = distances[nearest_haversine_idx]

haversine_time = time.time() - start

# ------------------------------
# KD-Tree benchmark
# ------------------------------
if SKLEARN_AVAILABLE:
    start = time.time()
    tree = KDTree(ambulances, leaf_size=40)
    kd_dist, kd_idx = tree.query([patient], k=1)
    kd_time = time.time() - start

    kd_available = True
    kd_nearest_dist = kd_dist[0][0]
    kd_nearest_idx = kd_idx[0][0]
else:
    kd_available = False
    kd_time = None
    kd_nearest_dist = None
    kd_nearest_idx = None

# ------------------------------
# Build final result summary
# ------------------------------
results = {
    "Haversine_Distance_km": float(nearest_haversine_dist),
    "Haversine_Execution_Time_sec": haversine_time,
    "KDTree_Available": kd_available,
}

if kd_available:
    results.update({
        "KDTree_Distance_Approx_km": float(kd_nearest_dist),
        "KDTree_Execution_Time_sec": kd_time
    })

print(results)
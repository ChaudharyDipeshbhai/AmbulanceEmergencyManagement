import os
import time
import requests
import numpy as np
import pandas as pd
from services.report_service import save_report
import logging
import concurrent.futures

logger = logging.getLogger(__name__)
logging.basicConfig(
    level = logging.INFO,
    format = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

ORS_API_KEY = os.getenv("ORS_API_KEY", "eyJvcmciOiI1YjNjZTM1OTc4NTExMTAwMDFjZjYyNDgiLCJpZCI6ImEzMTJjM2YzNWUwODQ4NjRiZGMwOWI1OTllMWZlZmRiIiwiaCI6Im11cm11cjY0In0=")

def haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371
    lat1_rad, lon1_rad = np.radians(lat1), np.radians(lon1)
    lat2_rad, lon2_rad = np.radians(lat2), np.radians(lon2)
    dlon = lon2_rad - lon1_rad
    dlat = lat2_rad - lat1_rad
    a = np.sin(dlat/2)**2 + np.cos(lat1_rad)*np.cos(lat2_rad)*np.sin(dlon/2)**2
    c = 2* np.arctan2(np.sqrt(a), np.sqrt(1-a))
    return R*c

def ors_route_distance(start_lat, start_lon, end_lat, end_lon):
    """Call ORS API to get driving route distance (km) and duration (minutes)."""
    url = "https://api.openrouteservice.org/v2/directions/driving-car"
    headers = {
        "Authorization": ORS_API_KEY,
        "Content-Type": "application/json"
    }
    body = {
        "coordinates": [[start_lon, start_lat], [end_lon, end_lat]],
        "radiuses": [200000, 200000]  # allow up to 2 km snapping to nearest road
    }

    try:
        resp = requests.post(url, json=body, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        if "routes" not in data or not data["routes"]:
            logger.error(f"ORS unexpected response: {data}")
            return None, None

        summary = data["routes"][0]["summary"]
        dist_km = summary["distance"] / 1000  # meters → km
        eta_min = summary["duration"] / 60    # seconds → minutes

        return round(dist_km, 2), round(eta_min, 1)

    except requests.exceptions.RequestException as e:
        logger.error(
            f"ORS API request error: {e} | Response: "
            f"{resp.text if 'resp' in locals() else 'no response'}"
        )
        return None, None

    except requests.exceptions.RequestException as e:
        logger.error(
            f"ORS API request error: {e} | Response: "
            f"{resp.text if 'resp' in locals() else 'no response'}"
        )
        return None, None
    except Exception as e:
        logger.exception(f"Unexpected error in ors_route_distance: {e}")
        return None, None


    
def dispatch_ambulance(report, ambualance_df: pd.DataFrame):
    if ambualance_df.empty:
        return {"error": "Ambulance Data not available"}, None
    
    total_start_time = time.perf_counter()
    patient_lat, patient_lon, patient_level = (
        report.location.lat,
        report.location.lng,
        report.emergency_level
    )
    
    # Ensure patient lat/lon exist
    if patient_lat is None or patient_lon is None:
        return {"error": "Invalid patient location (lat/lon missing)."}, None
    
    available = ambualance_df[ambualance_df["Status"]== "Available"].copy()
    if available.empty:
        return {"error":"No available Ambulances."}, None
    
    qualified = available[available["Emergency_Level"] >= patient_level].copy()
    qualified = qualified.dropna(subset=["Latitude", "Longitude"]).copy()
    if qualified.empty:
        return {'error':f"No available ambulance for emergency level {patient_level}"}
    
    # sortlisting using haversine
    start_time = time.perf_counter()
    qualified['haversine_km'] = haversine_distance(
        patient_lat, patient_lon, qualified['Latitude'], qualified['Longitude']
    ).round(2)
    end_time = time.perf_counter()
    calc_time = (end_time - start_time)*1000
    shortlisted = qualified.sort_values("haversine_km").head(10).copy()
    
    def ors_task(amb):
        start = time.perf_counter()
        dist_km, eta_min = ors_route_distance(
            amb["Latitude"], amb["Longitude"],
            patient_lat, patient_lon
        )
        elapsed = (time.perf_counter() - start)*1000
        return {
            "Ambulance_ID": amb["Ambulance_ID"],
            "Route_Distance_km": dist_km,
            "ETA_min": eta_min,
            "api_time" : elapsed
        }
        
    ors_results = []
    ors_api_start = time.perf_counter()
        
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = [executor.submit(ors_task, amb) for _, amb in shortlisted.iterrows()]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]
    ors_api_time = (time.perf_counter() - ors_api_start)*1000
    ors_results = [
        {
            "Ambulance_ID": r["Ambulance_ID"],
            "Route_Distance_km": r["Route_Distance_km"],
            "ETA_min": r["ETA_min"]
        }
        for r in results if r["Route_Distance_km"] is not None
    ]
        
    total_end_time = time.perf_counter()
    total_dispatch_time = (total_end_time - total_start_time)*1000
            
    if not ors_results:
        return {"error": "Routing service unavailable. No dispatch possible."},None
    
    ors_df = pd.DataFrame(ors_results)
    ors_df = ors_df.sort_values("Route_Distance_km").reset_index(drop=True)
    best_id = ors_df.iloc[0]["Ambulance_ID"]
    
    best_ambulance = shortlisted[shortlisted["Ambulance_ID"] == best_id].iloc[0].to_dict()
    best_ambulance.update(
        {
            "Route_Distance_km": float(ors_df.loc[ors_df["Ambulance_ID"] == best_id, "Route_Distance_km"].values[0]),
            "ETA_min": float(ors_df.loc[ors_df["Ambulance_ID"] == best_id, "ETA_min"].values[0]),
        }
    )
    
    logger.info(
        f"Dispatched ambulance {best_ambulance['Ambulance_ID']} | "
        f"Route Distance : {best_ambulance['Route_Distance_km']} km | "
        f"ETA : {best_ambulance['ETA_min']} | "
        f"Patient Location : ({patient_lat}, {patient_lon})"
    )
    
    # status update
    ambualance_df.loc[ambualance_df["Ambulance_ID"]== best_id, "Status"] = "Dispatched"
    
    # save report 
    report_content = save_report(report, best_ambulance, shortlisted, calc_time,ors_df, ors_api_time, total_dispatch_time)
    return best_ambulance, report_content
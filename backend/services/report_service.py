import os
import pandas as pd

def save_report(report, dispatched_ambulance, shortlisted_df, calc_time, ors_df, ors_api_time=None, total_dispatch_time=None):
    timestamp = pd.Timestamp.now()
    report_filename = f"report_{timestamp.strftime('%Y%m%d_%H%M%S')}.txt"
    reports_dir = os.path.join(os.path.dirname(__file__), "..", "reports")
    os.makedirs(reports_dir, exist_ok=True)
    report_path = os.path.join(reports_dir, report_filename)

    report_content = f"""

AMBULANCE DISPATCH REPORT

Date and Time: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}

--- Patient Information ---
Caller ID:       {report.caller_id}
Location:        Lat: {report.location.lat}, Lng: {report.location.lng}
Emergency Level: {report.emergency_level}

--- Dispatch Analysis ---
Haversine Calculation Time: {calc_time:.4f} ms
Qualified Ambulances Found: {len(shortlisted_df)}

--- Shortlisted Ambulances (Top 10 by Haversine Distance) ---
{shortlisted_df[['Ambulance_ID', 'Emergency_Level', 'haversine_km']].to_string(index=False)}

--- ORS Route Distance & ETA (for shortlisted ambulances) ---
{ors_df[['Ambulance_ID', 'Route_Distance_km', 'ETA_min']].to_string(index=False)}

ORS API Total Time: {ors_api_time:.4f} ms
Total Dispatch Time: {total_dispatch_time:.4f} ms

--- FINAL DISPATCH DECISION ---
Dispatched Unit ID: {dispatched_ambulance['Ambulance_ID']}
Emergency Level:    {dispatched_ambulance['Emergency_Level']}
Haversine Dist:     {dispatched_ambulance['haversine_km']} km
Route Distance:     {dispatched_ambulance['Route_Distance_km']} km
Estimated ETA:      {dispatched_ambulance['ETA_min']} min
--------------------------------------------------
"""
    with open(report_path, 'w') as f:
        f.write(report_content)

    return report_content

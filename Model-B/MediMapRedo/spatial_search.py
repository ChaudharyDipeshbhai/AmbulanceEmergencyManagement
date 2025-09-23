import math
import logging
from typing import List, Dict, Any, Optional
from geopy.distance import geodesic

class SpatialHospitalSearch:
    """Enhanced spatial search for hospitals with triage-based recommendations"""
    
    def __init__(self):
        self.hospitals: List[Dict[str, Any]] = []
        self.hospital_index: Dict[str, Dict[str, Any]] = {}
        
        logging.info("Initialized SpatialHospitalSearch")
    
    def update_hospitals(self, hospitals_data: List[Dict[str, Any]]):
        """Update hospital data and rebuild spatial index"""
        try:
            self.hospitals = hospitals_data
            self._build_spatial_index()
            logging.info(f"Updated hospital database with {len(self.hospitals)} hospitals")
        except Exception as e:
            logging.error(f"Error updating hospitals: {str(e)}")
    
    def _build_spatial_index(self):
        """Build spatial index for efficient searching"""
        self.hospital_index = {}
        for hospital in self.hospitals:
            hospital_id = hospital.get('id')
            if hospital_id:
                self.hospital_index[hospital_id] = hospital
    
    def find_nearest_hospitals(
        self,
        user_lat: float,
        user_lng: float,
        max_distance: Optional[float] = 50,
        hospital_levels: List[int] = None,
        required_facilities: List[str] = None,
        required_specialties: List[str] = None
    ) -> List[Dict[str, Any]]:
        """Find hospitals within specified distance and criteria"""
        
        if hospital_levels is None:
            hospital_levels = [1, 2, 3, 4]
        if required_facilities is None:
            required_facilities = []
        if required_specialties is None:
            required_specialties = []
        
        user_location = (user_lat, user_lng)
        matching_hospitals = []
        
        for hospital in self.hospitals:
            try:
                # Check hospital level (coerce to int for robustness)
                raw_level = hospital.get('level')
                try:
                    level_value = int(raw_level)
                except (TypeError, ValueError):
                    # Skip hospitals with unrecognized level
                    continue
                if level_value not in hospital_levels:
                    continue
                
                # Calculate distance if coordinates available
                hosp_lat = hospital.get('latitude')
                hosp_lng = hospital.get('longitude')
                distance = None
                if hosp_lat is not None and hosp_lng is not None:
                    hospital_location = (hosp_lat, hosp_lng)
                    distance = geodesic(user_location, hospital_location).kilometers
                    # If max_distance is provided, filter; otherwise include all and just compute distance
                    if max_distance is not None and distance > max_distance:
                        continue
                else:
                    # If no coords and distance filtering is requested, we cannot include
                    if max_distance is not None:
                        continue
                
                # Check facilities
                hospital_facilities = hospital.get('facilities', [])
                if required_facilities and not all(
                    any(req_fac.lower() in hosp_fac.lower() for hosp_fac in hospital_facilities)
                    for req_fac in required_facilities
                ):
                    continue
                
                # Check specialties
                hospital_specialties = hospital.get('specialties', [])
                if required_specialties and not all(
                    any(req_spec.lower() in hosp_spec.lower() for hosp_spec in hospital_specialties)
                    for req_spec in required_specialties
                ):
                    continue
                
                # Add distance info
                hospital_with_distance = hospital.copy()
                # Ensure normalized level in result
                hospital_with_distance['level'] = level_value
                hospital_with_distance['distance_km'] = round(distance, 2) if isinstance(distance, (int, float)) else None
                hospital_with_distance['travel_time_minutes'] = self._estimate_travel_time(distance) if isinstance(distance, (int, float)) else None
                
                matching_hospitals.append(hospital_with_distance)
                
            except Exception as e:
                logging.warning(f"Error processing hospital {hospital.get('name', 'Unknown')}: {str(e)}")
                continue
        
        # Sort by distance
        matching_hospitals.sort(key=lambda x: x.get('distance_km', float('inf')))
        
        logging.debug(f"Found {len(matching_hospitals)} matching hospitals")
        return matching_hospitals
    
    def find_recommended_hospitals(
        self,
        user_lat: float,
        user_lng: float,
        triage_level: str,
        symptoms: List[str] = None,
        max_distance: float = 50
    ) -> List[Dict[str, Any]]:
        """Find hospitals recommended based on triage assessment"""
        
        if symptoms is None:
            symptoms = []
        
        # Define requirements based on triage level
        triage_requirements = self._get_triage_requirements(triage_level, symptoms)
        
        user_location = (user_lat, user_lng)
        recommended_hospitals = []
        
        for hospital in self.hospitals:
            try:
                # Check if hospital meets triage requirements
                if not self._meets_triage_requirements(hospital, triage_requirements):
                    continue
                
                # Calculate distance
                hospital_location = (hospital.get('latitude'), hospital.get('longitude'))
                distance = geodesic(user_location, hospital_location).kilometers
                
                if distance > max_distance:
                    continue
                
                # Calculate priority score
                priority_score = self._calculate_priority_score(hospital, triage_level, distance, symptoms)
                
                # Add recommendation info
                hospital_with_rec = hospital.copy()
                hospital_with_rec['distance_km'] = round(distance, 2)
                hospital_with_rec['travel_time_minutes'] = self._estimate_travel_time(distance)
                hospital_with_rec['priority_score'] = priority_score
                hospital_with_rec['triage_match'] = triage_requirements
                hospital_with_rec['recommendation_reason'] = self._get_recommendation_reason(
                    hospital, triage_level, symptoms
                )
                
                recommended_hospitals.append(hospital_with_rec)
                
            except Exception as e:
                logging.warning(f"Error processing hospital recommendation {hospital.get('name', 'Unknown')}: {str(e)}")
                continue
        
        # Sort by priority score (higher is better)
        recommended_hospitals.sort(key=lambda x: x.get('priority_score', 0), reverse=True)
        
        logging.debug(f"Found {len(recommended_hospitals)} recommended hospitals for triage level {triage_level}")
        return recommended_hospitals
    
    def _get_triage_requirements(self, triage_level: str, symptoms: List[str]) -> Dict[str, Any]:
        """Get hospital requirements based on triage level"""
        requirements = {
            'critical': {
                'min_level': 1,  # Allow PHCs for critical cases if needed
                'required_facilities': [],  # Relax requirements for PHC compatibility
                'preferred_facilities': ['Emergency Room', 'ICU', 'Surgery', '24/7 Services'],
                'required_specialties': [],
                'emergency_services': True  # Prefer 24/7 services
            },
            'urgent': {
                'min_level': 1,  # Allow PHCs
                'required_facilities': [],  # No strict requirements
                'preferred_facilities': ['Emergency Care', 'Laboratory', '24/7 Services'],
                'required_specialties': [],
                'emergency_services': False  # Don't require emergency services strictly
            },
            'semi-urgent': {
                'min_level': 1,
                'required_facilities': [],
                'preferred_facilities': ['Outpatient', 'Primary Care'],
                'required_specialties': [],
                'emergency_services': False
            },
            'non-urgent': {
                'min_level': 1,
                'required_facilities': [],
                'preferred_facilities': ['Outpatient', 'Primary Care'],
                'required_specialties': [],
                'emergency_services': False
            }
        }
        
        base_req = requirements.get(triage_level, requirements['non-urgent'])
        
        # Add specialty requirements based on symptoms
        if symptoms:
            specialty_map = {
                'chest pain': ['Cardiology', 'Emergency Medicine'],
                'heart attack': ['Cardiology', 'Emergency Medicine'],
                'stroke': ['Neurology', 'Emergency Medicine'],
                'broken bone': ['Orthopedics', 'Radiology'],
                'pregnancy': ['Obstetrics', 'Gynecology'],
                'mental health': ['Psychiatry', 'Psychology'],
                'eye problems': ['Ophthalmology'],
                'skin problems': ['Dermatology']
            }
            
            for symptom in symptoms:
                if symptom.lower() in specialty_map:
                    base_req['preferred_specialties'] = base_req.get('preferred_specialties', []) + specialty_map[symptom.lower()]
        
        return base_req
    
    def _meets_triage_requirements(self, hospital: Dict[str, Any], requirements: Dict[str, Any]) -> bool:
        """Check if hospital meets triage requirements"""
        # Check minimum level
        if hospital.get('level', 1) < requirements.get('min_level', 1):
            return False
        
        # For critical cases, prefer emergency services but don't require strictly
        if requirements.get('emergency_services') and hospital.get('emergency_services', False):
            return True  # Prioritize 24/7 facilities
        
        # Check required facilities (only strict requirements)
        hospital_facilities = [f.lower() for f in hospital.get('facilities', [])]
        required_facilities = [f.lower() for f in requirements.get('required_facilities', [])]
        
        for req_facility in required_facilities:
            if not any(req_facility in hosp_fac for hosp_fac in hospital_facilities):
                return False
        
        # Check required specialties (only strict requirements)
        hospital_specialties = [s.lower() for s in hospital.get('specialties', [])]
        required_specialties = [s.lower() for s in requirements.get('required_specialties', [])]
        
        for req_specialty in required_specialties:
            if not any(req_specialty in hosp_spec for hosp_spec in hospital_specialties):
                return False
        
        # If no strict requirements failed, accept the hospital
        return True
    
    def _calculate_priority_score(
        self,
        hospital: Dict[str, Any],
        triage_level: str,
        distance: float,
        symptoms: List[str]
    ) -> float:
        """Calculate priority score for hospital recommendation"""
        score = 100  # Start with base score
        
        # Distance penalty (closer is better) - more weight to distance
        distance_penalty = distance * 5  # 5 points per km penalty
        score -= distance_penalty
        
        # Emergency services bonus for urgent cases
        if hospital.get('emergency_services', False):
            if triage_level in ['critical', 'urgent']:
                score += 20  # High bonus for 24/7 services in urgent cases
            else:
                score += 5   # Small bonus for non-urgent cases
        
        # Triage level urgency multiplier
        urgency_multipliers = {
            'critical': 2.0,
            'urgent': 1.8,
            'semi-urgent': 1.3,
            'non-urgent': 1.0
        }
        score *= urgency_multipliers.get(triage_level, 1.0)
        
        # Hospital level bonus (higher level = better equipped)
        level_bonus = {1: 0, 2: 10, 3: 20, 4: 30}
        score += level_bonus.get(hospital.get('level', 1), 0)
        
        # Facility bonus
        hospital_facilities = [f.lower() for f in hospital.get('facilities', [])]
        phc_facilities = ['emergency care', '24/7 services', 'emergency room', 'laboratory', 'primary care']
        
        for facility in phc_facilities:
            if any(facility in hosp_fac for hosp_fac in hospital_facilities):
                score += 3
        
        # Specialty bonus for symptom matching
        hospital_specialties = [s.lower() for s in hospital.get('specialties', [])]
        for symptom in symptoms:
            specialty_matches = {
                'chest pain': ['general medicine', 'emergency medicine'],
                'fever': ['general medicine', 'family medicine'],
                'breathing difficulty': ['general medicine', 'emergency medicine'],
                'stomach pain': ['general medicine'],
                'headache': ['general medicine', 'family medicine'],
                'broken bone': ['general medicine'],
                'pregnancy': ['general medicine', 'family medicine']
            }
            
            if symptom.lower() in specialty_matches:
                for specialty in specialty_matches[symptom.lower()]:
                    if any(specialty in hosp_spec for hosp_spec in hospital_specialties):
                        score += 5
        
        return max(score, 0)
    
    def _get_recommendation_reason(
        self,
        hospital: Dict[str, Any],
        triage_level: str,
        symptoms: List[str]
    ) -> str:
        """Generate human-readable recommendation reason"""
        reasons = []
        
        # Level-based reason
        level_reasons = {
            1: "Primary healthcare facility",
            2: "Secondary care hospital",
            3: "Tertiary care hospital with advanced facilities",
            4: "Quaternary care hospital with specialized services"
        }
        reasons.append(level_reasons.get(hospital.get('level', 1), "Healthcare facility"))
        
        # Emergency services
        if hospital.get('emergency_services'):
            reasons.append("24/7 emergency services available")
        
        # Specialty matching
        hospital_specialties = hospital.get('specialties', [])
        for symptom in symptoms:
            if symptom.lower() in ['chest pain', 'heart attack'] and any('cardiology' in s.lower() for s in hospital_specialties):
                reasons.append("Cardiology specialization for heart conditions")
            elif symptom.lower() == 'stroke' and any('neurology' in s.lower() for s in hospital_specialties):
                reasons.append("Neurology specialization for stroke care")
        
        return "; ".join(reasons)
    
    def _estimate_travel_time(self, distance_km: float) -> int:
        """Estimate travel time in minutes based on distance"""
        # Assume average speed of 30 km/h in urban areas
        return int(distance_km * 2)
    
    def get_hospital_stats(self) -> Dict[str, Any]:
        """Get statistics about loaded hospitals"""
        if not self.hospitals:
            return {'total_hospitals': 0}
        
        stats = {
            'total_hospitals': len(self.hospitals),
            'by_level': {},
            'with_emergency_services': 0,
            'average_bed_count': 0,
            'unique_facilities': set(),
            'unique_specialties': set()
        }
        
        bed_counts = []
        for hospital in self.hospitals:
            level = hospital.get('level', 1)
            stats['by_level'][level] = stats['by_level'].get(level, 0) + 1
            
            if hospital.get('emergency_services'):
                stats['with_emergency_services'] += 1
            
            bed_count = hospital.get('bed_count')
            if bed_count:
                bed_counts.append(bed_count)
            
            stats['unique_facilities'].update(hospital.get('facilities', []))
            stats['unique_specialties'].update(hospital.get('specialties', []))
        
        if bed_counts:
            stats['average_bed_count'] = sum(bed_counts) / len(bed_counts)
        
        # Convert sets to lists for JSON serialization
        stats['unique_facilities'] = sorted(list(stats['unique_facilities']))
        stats['unique_specialties'] = sorted(list(stats['unique_specialties']))
        
        return stats

import pandas as pd
import logging
import os
from typing import List, Dict, Any, Tuple, Set
import numpy as np
from openpyxl import load_workbook
import json
import re

class ExcelHospitalProcessor:
    """Process Excel files containing hospital data with optimized indexing"""
    
    def __init__(self):
        self.processed_hospitals: List[Dict[str, Any]] = []
        self.available_facilities: Set[str] = set()
        self.available_specialties: Set[str] = set()
        self.processing_errors: List[str] = []
        
        logging.info("Initialized ExcelHospitalProcessor")
    
    def process_excel_file(self, filepath: str) -> Tuple[bool, str, int]:
        """Process Excel file and extract hospital data"""
        try:
            self.processing_errors = []
            
            # Check if file exists
            if not os.path.exists(filepath):
                return False, "File not found", 0
            
            # Determine file type and read accordingly
            if filepath.endswith('.xlsx'):
                df = pd.read_excel(filepath, engine='openpyxl')
            elif filepath.endswith('.xls'):
                df = pd.read_excel(filepath, engine='xlrd')
            else:
                return False, "Unsupported file format", 0
            
            # Normalize column names to lower-case for flexible schema mapping
            df.columns = [str(c).strip().lower() for c in df.columns]
            
            # Map common synonyms to internal names
            rename_map = {}
            if 'lat' in df.columns and 'latitude' not in df.columns:
                rename_map['lat'] = 'latitude'
            if 'long' in df.columns and 'longitude' not in df.columns:
                rename_map['long'] = 'longitude'
            if 'address' not in df.columns and 'address' in [c.lower() for c in df.columns]:
                # Already normalized, nothing to do
                pass
            if 'address' not in df.columns and 'address' not in rename_map:
                # Try mapping 'Address' capitalization case already handled by lower()
                # No action needed
                pass
            if 'availability' in df.columns:
                rename_map['availability'] = 'availability'
            if 'area' in df.columns:
                rename_map['area'] = 'area'
            if 'state' in df.columns:
                rename_map['state'] = 'state'
            # Apply renames
            if rename_map:
                df = df.rename(columns=rename_map)
            
            # Validate required columns (relaxed: only name and level are mandatory)
            required_columns = ['name', 'level']
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                return False, f"Missing required columns: {', '.join(missing_columns)}", 0
            
            # Process each row
            hospitals = []
            for idx, row in df.iterrows():
                try:
                    hospital = self._process_hospital_row(row, idx)
                    if hospital:
                        hospitals.append(hospital)
                except Exception as e:
                    self.processing_errors.append(f"Row {idx + 1}: {str(e)}")
                    continue
            
            self.processed_hospitals = hospitals
            
            # Extract unique facilities and specialties
            self._extract_metadata()
            
            success_message = f"Successfully processed {len(hospitals)} hospitals"
            if self.processing_errors:
                success_message += f" ({len(self.processing_errors)} errors encountered)"
            
            logging.info(success_message)
            return True, success_message, len(hospitals)
            
        except Exception as e:
            error_msg = f"Failed to process Excel file: {str(e)}"
            logging.error(error_msg)
            return False, error_msg, 0
    
    def _process_hospital_row(self, row: pd.Series, row_idx: int) -> Dict[str, Any]:
        """Process individual hospital row"""
        # Generate hospital ID
        hospital_id = f"hospital_{row_idx + 1}"
        
        # Extract basic information
        name = str(row['name']).strip()
        if not name or name.lower() == 'nan':
            raise ValueError("Hospital name is required")
        
        # Safely read coordinates (optional)
        latitude = self._safe_extract_float(row, 'latitude')
        longitude = self._safe_extract_float(row, 'longitude')
        # Range-check if present
        if latitude is not None and not (-90 <= latitude <= 90):
            latitude = None
        if longitude is not None and not (-180 <= longitude <= 180):
            longitude = None
        
        # Validate hospital level
        try:
            level = int(row['level'])
            if level not in [1, 2, 3, 4]:
                raise ValueError("Hospital level must be 1, 2, 3, or 4")
        except (ValueError, TypeError):
            raise ValueError("Invalid hospital level")
        
        # Extract address and phone (optional in the new format)
        address = None
        if 'address' in row and not pd.isna(row['address']):
            address = str(row['address']).strip()
        phone = None
        if 'phone' in row and not pd.isna(row['phone']):
            phone = str(row['phone']).strip()
        
        # Process optional fields
        email = self._safe_extract_string(row, 'email')
        website = self._safe_extract_string(row, 'website')
        state = self._safe_extract_string(row, 'state')
        area = self._safe_extract_string(row, 'area')
        availability = self._safe_extract_string(row, 'availability')
        
        # Process facilities (comma-separated or pipe-separated)
        facilities = self._extract_list_field(row, 'facilities')
        
        # Process specialties
        specialties = self._extract_list_field(row, 'specialties')
        
        # Extract emergency services
        emergency_services = self._safe_extract_boolean(row, 'emergency_services', default=True)
        
        # Extract bed count
        bed_count = self._safe_extract_integer(row, 'bed_count')
        
        return {
            'id': hospital_id,
            'name': name,
            'latitude': latitude,
            'longitude': longitude,
            'level': level,
            'address': address,
            'phone': phone,
            'email': email,
            'website': website,
            'facilities': facilities,
            'specialties': specialties,
            'emergency_services': emergency_services,
            'bed_count': bed_count,
            'state': state,
            'area': area,
            'availability': availability
        }
    
    def _safe_extract_string(self, row: pd.Series, column: str) -> str:
        """Safely extract string value from row"""
        if column not in row or pd.isna(row[column]):
            return None
        
        value = str(row[column]).strip()
        return value if value and value.lower() != 'nan' else None
    
    def _safe_extract_integer(self, row: pd.Series, column: str) -> int:
        """Safely extract integer value from row"""
        if column not in row or pd.isna(row[column]):
            return None
        
        try:
            return int(float(row[column]))
        except (ValueError, TypeError):
            return None

    def _safe_extract_float(self, row: pd.Series, column: str) -> float:
        """Safely extract float value from row"""
        if column not in row or pd.isna(row[column]):
            return None
        try:
            value_str = str(row[column]).strip()
            if value_str == '':
                return None
            return float(value_str)
        except (ValueError, TypeError):
            return None
    
    def _safe_extract_boolean(self, row: pd.Series, column: str, default: bool = False) -> bool:
        """Safely extract boolean value from row"""
        if column not in row or pd.isna(row[column]):
            return default
        
        value = str(row[column]).lower().strip()
        return value in ['true', '1', 'yes', 'y', 'enabled', 'on']
    
    def _extract_list_field(self, row: pd.Series, column: str) -> List[str]:
        """Extract and parse comma or pipe separated list field"""
        if column not in row or pd.isna(row[column]):
            return []
        
        value = str(row[column]).strip()
        if not value or value.lower() == 'nan':
            return []
        
        # Split by comma or pipe, clean up items
        items = re.split(r'[,|;]', value)
        cleaned_items = []
        
        for item in items:
            cleaned = item.strip()
            if cleaned and cleaned.lower() != 'nan':
                cleaned_items.append(cleaned)
        
        return cleaned_items
    
    def _extract_metadata(self):
        """Extract unique facilities and specialties from processed hospitals"""
        self.available_facilities = set()
        self.available_specialties = set()
        
        for hospital in self.processed_hospitals:
            self.available_facilities.update(hospital.get('facilities', []))
            self.available_specialties.update(hospital.get('specialties', []))
        
        logging.info(f"Extracted {len(self.available_facilities)} unique facilities and "
                    f"{len(self.available_specialties)} unique specialties")
    
    def get_processed_hospitals(self) -> List[Dict[str, Any]]:
        """Get processed hospital data"""
        return self.processed_hospitals
    
    def get_available_facilities(self) -> List[str]:
        """Get list of all available facilities"""
        return sorted(list(self.available_facilities))
    
    def get_available_specialties(self) -> List[str]:
        """Get list of all available specialties"""
        return sorted(list(self.available_specialties))
    
    def get_processing_errors(self) -> List[str]:
        """Get list of processing errors"""
        return self.processing_errors
    
    def validate_excel_template(self, filepath: str) -> Tuple[bool, List[str]]:
        """Validate Excel file structure without processing data"""
        try:
            df = pd.read_excel(filepath)
            
            required_columns = ['name', 'latitude', 'longitude', 'level', 'address', 'phone']
            optional_columns = ['email', 'website', 'facilities', 'specialties', 
                              'emergency_services', 'bed_count']
            
            issues = []
            
            # Check required columns
            for col in required_columns:
                if col not in df.columns:
                    issues.append(f"Missing required column: {col}")
            
            # Check data types and ranges
            if 'level' in df.columns:
                invalid_levels = df[~df['level'].isin([1, 2, 3, 4])]['level'].dropna()
                if not invalid_levels.empty:
                    issues.append(f"Invalid hospital levels found: {list(invalid_levels.unique())}")
            
            # Check coordinate ranges
            if 'latitude' in df.columns:
                invalid_lat = df[(df['latitude'] < -90) | (df['latitude'] > 90)]['latitude'].dropna()
                if not invalid_lat.empty:
                    issues.append("Invalid latitude values found (must be between -90 and 90)")
            
            if 'longitude' in df.columns:
                invalid_lng = df[(df['longitude'] < -180) | (df['longitude'] > 180)]['longitude'].dropna()
                if not invalid_lng.empty:
                    issues.append("Invalid longitude values found (must be between -180 and 180)")
            
            return len(issues) == 0, issues
            
        except Exception as e:
            return False, [f"Error validating file: {str(e)}"]
    
    def create_excel_template(self, filepath: str) -> bool:
        """Create an Excel template file with proper column headers"""
        try:
            template_data = {
                'name': ['City General Hospital', 'Regional Medical Center'],
                'latitude': [40.7128, 34.0522],
                'longitude': [-74.0060, -118.2437],
                'level': [3, 4],
                'address': ['123 Main St, New York, NY 10001', '456 Health Ave, Los Angeles, CA 90210'],
                'phone': ['+1-555-0123', '+1-555-0456'],
                'email': ['info@citygeneral.com', 'contact@regionalmedical.com'],
                'website': ['https://www.citygeneral.com', 'https://www.regionalmedical.com'],
                'facilities': ['Emergency Room, ICU, Surgery', 'Emergency Room, ICU, Surgery, Cardiology, Oncology'],
                'specialties': ['General Medicine, Emergency Medicine', 'Cardiology, Oncology, Neurology, Emergency Medicine'],
                'emergency_services': [True, True],
                'bed_count': [200, 450],
                }
            
            df = pd.DataFrame(template_data)
            df.to_excel(filepath, index=False)
            
            logging.info(f"Created Excel template at {filepath}")
            return True
            
        except Exception as e:
            logging.error(f"Error creating Excel template: {str(e)}")
            return False

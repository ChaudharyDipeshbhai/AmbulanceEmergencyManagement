import os
import logging
from flask import Flask, render_template, request, jsonify, flash, redirect, url_for, send_from_directory


# ...existing code...

from flask_cors import CORS
import pandas as pd
from werkzeug.utils import secure_filename
from werkzeug.middleware.proxy_fix import ProxyFix
from spatial_search import SpatialHospitalSearch
from data_processor import ExcelHospitalProcessor
import json

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Create the app

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-key-change-in-production")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Route to download the hospital details template (now correctly placed)
@app.route('/download/template')
def download_template():
    template_filename = 'hospitals_details.xlsx'
    template_dir = os.path.join(app.root_path, 'uploads')
    return send_from_directory(template_dir, template_filename, as_attachment=True)

# Enable CORS for API endpoints
CORS(app)

# Configure upload settings
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'xlsx', 'xls'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Ensure upload directory exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Initialize components
spatial_search = SpatialHospitalSearch()
excel_processor = ExcelHospitalProcessor()

# Load hospital data at startup (prefer provided Excel path)
STARTUP_EXCEL_PATH = r"C:\\Users\\Aayush raj thakur\\Desktop\\MediMapRedo\\attached_assets\\hospitals_details.xlsx"

def _load_startup_hospitals():
    # 1) Try Excel at the provided path
    try:
        if os.path.exists(STARTUP_EXCEL_PATH):
            success, message, count = excel_processor.process_excel_file(STARTUP_EXCEL_PATH)
            if success:
                hospitals_data = excel_processor.get_processed_hospitals()
                spatial_search.update_hospitals(hospitals_data)
                logging.info(f"Loaded {count} hospitals from Excel: {STARTUP_EXCEL_PATH}")
                return True
            else:
                logging.warning(f"Excel processing failed: {message}")
        else:
            logging.warning(f"Startup Excel file not found: {STARTUP_EXCEL_PATH}")
    except Exception as e:
        logging.error(f"Error processing startup Excel: {str(e)}")

    # 2) Fallback to JSON files in priority order
    try:
        with open('phc_india_hospitals.json', 'r') as f:
            phc_data = json.load(f)
            spatial_search.update_hospitals(phc_data)
            logging.info(f"Loaded {len(phc_data)} Indian PHC hospitals from JSON")
            return True
    except FileNotFoundError:
        try:
            with open('phc_hospitals.json', 'r') as f:
                phc_data = json.load(f)
                spatial_search.update_hospitals(phc_data)
                logging.info(f"Loaded {len(phc_data)} PHC hospitals from JSON")
                return True
        except FileNotFoundError:
            logging.warning("No JSON hospital data files found")
        except Exception as e:
            logging.error(f"Error loading PHC JSON data: {str(e)}")
    except Exception as e:
        logging.error(f"Error loading PHC JSON data: {str(e)}")
    return False

_load_startup_hospitals()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    """Main page with hospital finder and triage interface"""
    return render_template('index.html')

@app.route('/api/hospitals/search', methods=['POST'])
def search_hospitals():
    """API endpoint for searching hospitals based on location and filters"""
    try:
        data = request.get_json()
        
        # Extract parameters
        user_lat = float(data.get('latitude', 0))
        user_lng = float(data.get('longitude', 0))
        # Distance is optional; if not provided, don't filter by distance
        max_distance_raw = data.get('max_distance')
        max_distance = float(max_distance_raw) if max_distance_raw is not None else None
        hospital_level = data.get('hospital_level', [1, 2, 3, 4])
        facilities = data.get('facilities', [])
        specialties = data.get('specialties', [])
        
        logging.debug(f"Search parameters: lat={user_lat}, lng={user_lng}, max_distance={max_distance}")
        
        # Perform spatial search
        hospitals = spatial_search.find_nearest_hospitals(
            user_lat, user_lng, max_distance, hospital_level, facilities, specialties
        )
        
        return jsonify({
            'success': True,
            'hospitals': hospitals,
            'count': len(hospitals)
        })
        
    except Exception as e:
        logging.error(f"Error in hospital search: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/hospitals/upload', methods=['POST'])
def upload_hospital_data():
    """API endpoint for uploading Excel hospital data"""
    try:
        if 'files' not in request.files:
            return jsonify({'success': False, 'error': 'No files provided'}), 400

        files = request.files.getlist('files')
        if not files or all(f.filename == '' for f in files):
            return jsonify({'success': False, 'error': 'No files selected'}), 400

        total_hospitals = 0
        messages = []
        errors = []
        all_hospitals = []

        for file in files:
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                try:
                    success, message, hospital_count = excel_processor.process_excel_file(filepath)
                    if success:
                        hospitals_data = excel_processor.get_processed_hospitals()
                        all_hospitals.extend(hospitals_data)
                        total_hospitals += hospital_count
                        messages.append(f"{filename}: {message}")
                    else:
                        errors.append(f"{filename}: {message}")
                except Exception as e:
                    errors.append(f"{filename}: {str(e)}")
            else:
                errors.append(f"{file.filename}: Invalid file type")

        if all_hospitals:
            spatial_search.update_hospitals(all_hospitals)

        response = {
            'success': len(all_hospitals) > 0,
            'message': '\n'.join(messages) if messages else 'No valid files processed.',
            'hospital_count': total_hospitals,
            'errors': errors
        }
        status_code = 200 if len(all_hospitals) > 0 else 400
        return jsonify(response), status_code

    except Exception as e:
        logging.error(f"Error uploading hospital data: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/hospitals/facilities')
def get_facilities():
    """Get available facilities for filtering"""
    facilities = excel_processor.get_available_facilities()
    return jsonify({'facilities': facilities})

@app.route('/api/hospitals/specialties')
def get_specialties():
    """Get available specialties for filtering"""
    specialties = excel_processor.get_available_specialties()
    return jsonify({'specialties': specialties})

@app.route('/api/hospitals/stats')
def get_hospital_stats():
    """Get hospital statistics"""
    stats = spatial_search.get_hospital_stats()
    return jsonify(stats)


@app.errorhandler(413)
def too_large(e):
    return jsonify({'success': False, 'error': 'File too large. Maximum size is 16MB.'}), 413

@app.errorhandler(404)
def not_found(e):
    return render_template('index.html'), 404

@app.errorhandler(500)
def internal_error(e):
    logging.error(f"Internal server error: {str(e)}")
    return jsonify({'success': False, 'error': 'Internal server error'}), 500

if __name__ == '__main__':
    # Load hospitals (Excel preferred), then fallback to sample if still empty
    loaded = _load_startup_hospitals()
    if not loaded:
        try:
            with open('sample_hospitals.json', 'r') as f:
                sample_data = json.load(f)
                spatial_search.update_hospitals(sample_data)
                logging.info(f"Loaded {len(sample_data)} sample hospitals")
        except FileNotFoundError:
            logging.warning("No hospital data found")
        except Exception as e:
            logging.error(f"Error loading sample data: {str(e)}")
    
    app.run(host='localhost', port=5000, debug=True)

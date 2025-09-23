// Global variables
let userLocation = { latitude: null, longitude: null };
let availableSymptoms = [];

// Initialize application
function initializeApp() {
    console.log('Initializing MediMap application...');
    
    // Load initial data
    loadHospitalStats();
    
    // Setup event listeners
    setupEventListeners();
}

// Setup event listeners
function setupEventListeners() {
    // Triage submission not used anymore
    
    // File upload form submission
    document.getElementById('uploadForm').addEventListener('submit', handleFileUpload);
    
    // Location buttons
    const getLocationBtn = document.getElementById('getLocationBtn');
    if (getLocationBtn) {
        getLocationBtn.addEventListener('click', function() {
            getCurrentLocation('triage');
        });
    }
    // Nearest hospitals button
    const nearestBtn = document.getElementById('nearestHospitalsBtn');
    if (nearestBtn) {
        nearestBtn.addEventListener('click', findNearestHospitals);
    }
    
    // Download template button
    document.getElementById('downloadTemplate').addEventListener('click', downloadTemplate);
}

// Get user's current location
function getCurrentLocation(context) {
    if ('geolocation' in navigator) {
        showLoading(true);
        
        navigator.geolocation.getCurrentPosition(
            function(position) {
                userLocation.latitude = position.coords.latitude;
                userLocation.longitude = position.coords.longitude;
                
                console.log('Location obtained:', userLocation);
                
                document.getElementById('getLocationBtn').innerHTML = 
                    '<i class="fas fa-check-circle me-2"></i>Location Obtained';
                document.getElementById('getLocationBtn').classList.remove('btn-outline-secondary');
                document.getElementById('getLocationBtn').classList.add('btn-success');
                
                showLoading(false);
                showAlert('Location obtained successfully', 'success');
            },
            function(error) {
                console.error('Geolocation error:', error);
                showLoading(false);
                showAlert('Could not get your location. Please enable location services.', 'warning');
            },
            {
                enableHighAccuracy: true,
                timeout: 10000,
                maximumAge: 300000
            }
        );
    } else {
        showAlert('Geolocation is not supported by your browser', 'error');
    }
}

// Find and display top 5 nearest hospitals based on current location and optional level
async function findNearestHospitals() {
    if (!userLocation.latitude || !userLocation.longitude) {
        showAlert('Please obtain your location first', 'warning');
        return;
    }
    showLoading(true);
    try {
        const levelEl = document.getElementById('hospitalLevel');
        let hospital_level = [1, 2, 3, 4];
        let chosenLevel = null;
        if (levelEl && levelEl.value) {
            const chosen = parseInt(levelEl.value);
            if (!isNaN(chosen)) {
                chosenLevel = chosen;
                hospital_level = [chosen]; // strict filter by selected level only
            }
        }
        const payload = {
            latitude: userLocation.latitude,
            longitude: userLocation.longitude,
            hospital_level
        };
        const res = await fetch('/api/hospitals/search', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const result = await res.json();
        if (!result.success) {
            showAlert('Search failed: ' + (result.error || 'Unknown error'), 'error');
            return;
        }
        let hospitals = (result.hospitals || []);
        // Fallback: if nothing found, retry with larger radius (still same level constraint)
        const userChoseSpecificLevel = !!chosenLevel;
        let didFallback = false; // no distance fallback anymore
        // Sort by distance only
        hospitals.sort((a, b) => {
            const aDist = typeof a.distance_km === 'number' ? a.distance_km : Infinity;
            const bDist = typeof b.distance_km === 'number' ? b.distance_km : Infinity;
            return aDist - bDist;
        });
        // Render into triage results area
        const resultsContainer = document.getElementById('triageResults');
        const resultsHeader = document.getElementById('triageResultsHeader');
        const resultsBody = document.getElementById('triageResultsBody');
        if (resultsHeader) {
            resultsHeader.className = 'card-header py-3';
            let subtitle = '';
            if (userChoseSpecificLevel) {
                subtitle = `<div class=\"mt-1 text-muted small\">Showing only level ${chosenLevel} hospitals</div>`;
            }
            let warning = '';
            if (didFallback) {
                warning = '<div class=\"mt-2 alert alert-warning py-2 mb-0\">No hospitals within 50 km. Expanded search radius.</div>';
            }
            resultsHeader.innerHTML = `<h4 class=\"mb-0\"><i class=\"fas fa-hospital me-2\"></i>Nearest Hospitals</h4>${subtitle}${warning}`;
        }
        if (resultsBody) {
            if (hospitals.length === 0) {
                resultsBody.innerHTML = '<p class="text-muted mb-0">No hospitals found nearby.</p>';
            } else {
                let html = '';
                hospitals.forEach(h => {
                    html += `
                        <div class="recommendation-card filtered-level">
                            <div class="d-flex justify-content-between align-items-start mb-2">
                                <h6 class="hospital-name mb-0">${h.name}</h6>
                                <span class="distance-badge">${h.distance_km} km</span>
                            </div>
                            <p class="text-muted mb-2">${h.address || ''}</p>
                            <p class="text-sm mb-1"><strong>Level ${h.level || ''}</strong> ${h.travel_time_minutes ? `• ${h.travel_time_minutes} min` : ''}</p>
                            <p class="text-sm mb-1"><strong>Area:</strong> ${h.area || 'N/A'}</p>
                            <p class="text-sm mb-1"><strong>Availability:</strong> ${h.availability || 'N/A'}</p>
                            <div class="mt-2">
                                ${h.phone ? `<a href="tel:${h.phone}" class="btn btn-sm btn-medical-primary me-2"><i class=\"fas fa-phone me-1\"></i>Call</a>` : ''}
                                <a href="https://maps.google.com/?q=${h.latitude},${h.longitude}" target="_blank" class="btn btn-sm btn-outline-primary">
                                    <i class="fas fa-directions me-1"></i>Directions
                                </a>
                            </div>
                        </div>
                    `;
                });
                resultsBody.innerHTML = html;
            }
        }
        if (resultsContainer) {
            resultsContainer.style.display = 'block';
            resultsContainer.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
    } catch (error) {
        console.error('Nearest hospitals error:', error);
        showAlert('Error finding nearest hospitals', 'error');
    } finally {
        showLoading(false);
    }
}

// Symptoms UI removed



// Triage submission removed

// Collect triage form data
// Triage data collection removed

// Display triage results
// Triage results UI removed




// Handle file upload
async function handleFileUpload(event) {
    event.preventDefault();
    
    const fileInput = document.getElementById('hospitalFile');
    const files = fileInput.files;
    if (!files || files.length === 0) {
        showAlert('Please select at least one file to upload', 'warning');
        return;
    }
    showLoading(true);
    const formData = new FormData();
    for (let i = 0; i < files.length; i++) {
        formData.append('files', files[i]);
    }
    
    try {
        const response = await fetch('/api/hospitals/upload', {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        
        if (result.success) {
            showAlert(`Successfully uploaded hospital data: ${result.message}`, 'success');
            // Reload data
            loadHospitalStats();
            // Clear form
            fileInput.value = '';
        } else {
            showAlert('Upload failed: ' + result.error, 'error');
        }
    } catch (error) {
        console.error('Upload error:', error);
        showAlert('Error uploading file', 'error');
    } finally {
        showLoading(false);
    }
}

// Load hospital statistics
async function loadHospitalStats() {
    try {
        const response = await fetch('/api/hospitals/stats');
        const stats = await response.json();
        
        displayHospitalStats(stats);
    } catch (error) {
        console.error('Error loading hospital stats:', error);
    }
}

// Display hospital statistics
function displayHospitalStats(stats) {
    const statsContainer = document.getElementById('statsContent');
    
    if (!stats || stats.total_hospitals === 0) {
        statsContainer.innerHTML = '<p class="text-muted">No hospital data loaded</p>';
        return;
    }
    
    let statsHTML = `
        <div class="row g-3">
            <div class="col-sm-6 col-md-3">
                <div class="text-center">
                    <div class="h4 text-medical-primary">${stats.total_hospitals}</div>
                    <small class="text-muted">Total Hospitals</small>
                </div>
            </div>
            <div class="col-sm-6 col-md-3">
                <div class="text-center">
                    <div class="h4 text-medical-secondary">${stats.with_emergency_services || 0}</div>
                    <small class="text-muted">Emergency Services</small>
                </div>
            </div>
            <div class="col-sm-6 col-md-3">
                <div class="text-center">
                    <div class="h4 text-success">${stats.unique_facilities ? stats.unique_facilities.length : 0}</div>
                    <small class="text-muted">Unique Facilities</small>
                </div>
            </div>
            <div class="col-sm-6 col-md-3">
                <div class="text-center">
                    <div class="h4 text-info">${stats.unique_specialties ? stats.unique_specialties.length : 0}</div>
                    <small class="text-muted">Specialties</small>
                </div>
            </div>
        </div>
    `;
    
    if (stats.by_level) {
        statsHTML += `
            <div class="mt-3">
                <h6 class="text-medical-primary">By Hospital Level</h6>
                <div class="row g-2">
        `;
        
        for (let level = 1; level <= 4; level++) {
            const count = stats.by_level[level] || 0;
            statsHTML += `
                <div class="col-3">
                    <div class="text-center p-2 bg-light rounded">
                        <div class="fw-bold text-medical-dark">${count}</div>
                        <small class="text-muted">Level ${level}</small>
                    </div>
                </div>
            `;
        }
        
        statsHTML += `
                </div>
            </div>
        `;
    }
    
    statsContainer.innerHTML = statsHTML;
}

// Download template file
function downloadTemplate() {
    // Trigger download of the template file from the backend
    window.location.href = '/download/template';
}

// Utility functions
function showLoading(show) {
    const overlay = document.getElementById('loadingOverlay');
    overlay.style.display = show ? 'flex' : 'none';
}

function showAlert(message, type) {
    // Create alert element
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type === 'error' ? 'danger' : type} alert-dismissible fade show position-fixed`;
    alertDiv.style.top = '20px';
    alertDiv.style.right = '20px';
    alertDiv.style.zIndex = '9999';
    alertDiv.style.minWidth = '300px';
    
    let icon = 'info-circle';
    if (type === 'success') icon = 'check-circle';
    if (type === 'error') icon = 'exclamation-triangle';
    if (type === 'warning') icon = 'exclamation-circle';
    
    alertDiv.innerHTML = `
        <i class="fas fa-${icon} me-2"></i>
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    document.body.appendChild(alertDiv);
    
    // Auto remove after 5 seconds
    setTimeout(() => {
        if (alertDiv.parentNode) {
            alertDiv.remove();
        }
    }, 5000);
}

// Console log for debugging
console.log('MediMap application JavaScript loaded');


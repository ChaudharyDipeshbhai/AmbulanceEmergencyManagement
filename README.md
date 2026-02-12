Ambulance Emergency Management - Setup & Run Guide
This project consists of three main components that need to be run simultaneously:

Backend (Ambulance Dispatch API - Python/FastAPI)
Frontend (Ambulance Dispatch UI - React/Vite)
Hospital Management System (Model-B/MediMapRedo - Python/Flask)
Prerequisites
Python 3.11+ installed.
Node.js 18+ installed.
Git (optional, for cloning).
1. Backend Setup (Ambulance Dispatch)
This service handles the logic for ambulance dispatching.

Navigate to the backend directory:

bash
cd backend
Create a virtual environment (recommended):

bash
python -m venv venv
Activate the virtual environment:

Windows:
bash
venv\Scripts\activate
macOS/Linux:
bash
source venv/bin/activate
Install dependencies:

bash
pip install -r requirements.txt
Run the server:

bash
uvicorn app:app --reload
The backend will start at http://127.0.0.1:8000.

2. Frontend Setup (Ambulance Dispatch UI)
This is the user interface for the dispatch system.

Open a new terminal and navigate to the frontend directory:

bash
cd frontend
Install dependencies:

bash
npm install
Run the development server:

bash
npm run dev
The frontend will be available at http://localhost:5173.

3. Hospital Management System (Model-B/MediMapRedo)
This is a separate module for managing hospital data.

Open a new terminal and navigate to the project root.

Navigate to the MediMapRedo directory:

bash
cd Model-B/MediMapRedo
Create a virtual environment (recommended):

bash
python -m venv venv
Activate the virtual environment:

Windows:
bash
venv\Scripts\activate
macOS/Linux:
bash
source venv/bin/activate
Install dependencies: This project uses 
pyproject.toml
 (managed by tools like pdm, poetry, or uv), but you can install dependencies directly if you extract them or have a requirements file. It seems to rely on Flask and scientific libraries.

Start by installing the core dependencies:

bash
pip install flask flask-cors flask-sqlalchemy gunicorn psycopg2-binary pandas geopy openpyxl xlrd numpy werkzeug
Note: If a 
requirements.txt
 is missing here, you may need to install based on import errors or use a tool that supports 
pyproject.toml
 natively.

Run the application:

bash
python app.py
The application will start at http://localhost:5000.

Summary of URLs
Ambulance Dispatch Frontend: http://localhost:5173
Ambulance Dispatch Backend: http://localhost:8000
Hospital Management System: http://localhost:5000
Troubleshooting
Port Conflicts: Ensure ports 5000, 8000, and 5173 are free before starting.
Dependency Issues: If pip install -r requirements.txt fails, try upgrading pip: python -m pip install --upgrade pip.
CORS Errors: The backend is configured to allow http://localhost:5173. If you run the frontend on a different port, update 
backend/app.py
.

Backend (backend/)
Create/Update requirements.txt with:

fastapi==0.111.0
uvicorn[standard]==0.30.0
pandas==2.2.2
numpy==1.26.4
pydantic==2.8.2
requests
openrouteservice



python-dotenv (Suggested for environment variable management)
MediMapRedo (Model-B/MediMapRedo/)


Create requirements.txt based on pyproject.toml and code analysis:

flask>=3.1.2
flask-cors>=6.0.1
pandas>=2.3.2
numpy>=2.3.2
geopy>=2.4.1
openpyxl>=3.1.5
xlrd>=2.0.2
werkzeug>=3.1.3
gunicorn>=23.0.0
flask-sqlalchemy>=3.1.1
psycopg2-binary>=2.9.10
email-validator>=2.3.0
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import calls

app = FastAPI()

# --- CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Routers ---
app.include_router(calls.router)

@app.get("/")
def read_root():
    return {"status": "Ambulance Management Backend is running!"}

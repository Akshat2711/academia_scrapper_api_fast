from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from studentinfo_scrap import AcademiaClient
from fastapi.middleware.cors import CORSMiddleware
from tools.fallback_mock_attendance_data import generate_mock_attendance_from_timetable

app = FastAPI(title="Academia Scraper API")

origins = [
    "http://localhost",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "*",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class LoginRequest(BaseModel):
    email: str
    password: str


@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.post("/scrape")
async def scrape_portal(request: LoginRequest):
    client = None
    try:
        client = AcademiaClient(request.email, request.password)

        if not client.lookup_user() or not client.login():
            raise HTTPException(status_code=401, detail="Login failed")

        # 1. Fetch Day Order
        day_order = None
        try:
            day_order = client.get_day_order()
        except Exception:
            day_order = 1  # Default to 1 if fails

        # 2. Fetch Attendance (Initial attempt)
        attendance_data = None
        try:
            attendance_data = client.get_attendance()
        except Exception as e:
            print(f"✗ Attendance scrape failed: {e}")
            attendance_data = None # Explicitly set to None for fallback check

        # 3. Fetch Timetable
        timetable_data = None
        try:
            timetable_data = client.get_timetable()
        except Exception as e:
            print(f"✗ Timetable scrape failed: {e}")

        # --- THE FIX: Robust Fallback Logic ---
        # We trigger fallback if attendance is missing, an empty dict, or contains an error
        is_attendance_invalid = (
            attendance_data is None or 
            (isinstance(attendance_data, dict) and (not attendance_data or "error" in attendance_data))
        )

        if is_attendance_invalid and timetable_data and "error" not in timetable_data:
            print("ℹ Found timetable! Mimicking attendance format with zero values...")
            attendance_data = generate_mock_attendance_from_timetable(timetable_data)
            

        # Final Response Construction
        response_data = {
            "status": "success",
            "attendance": attendance_data,
            "timetable": timetable_data,
        }

        client.logout()
        return response_data

    except Exception as e:
        if client: client.logout()
        raise HTTPException(status_code=500, detail=str(e))

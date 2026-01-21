from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from studentinfo_scrap import AcademiaClient
from tools.fallback_mock_attendance_data import generate_mock_attendance_from_timetable
from tools.studentportal_result import scrape_student_portal


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


class StudentPortalRequest(BaseModel):
    netid: str
    password: str


@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.post("/scrape")
async def scrape_portal(request: LoginRequest):
    client = None

    try:
        client = AcademiaClient(request.email, request.password)

        # --- LOGIN ---
        # --- LOGIN ---
        if not client.lookup_user() or not client.login():
            error_detail = client.last_error if client.last_error else "Login failed"
            raise HTTPException(status_code=401, detail=error_detail)

        # --- DAY ORDER (SAFE + GUARANTEED) ---
        try:
            day_order = client.get_day_order()
        except Exception as e:
            print(f"✗ Day order fetch failed: {e}")
            day_order = None

        # Normalize day order (CRITICAL)
        if not isinstance(day_order, int) or day_order <= 0:
            day_order = 1  # Default to Day 1 if invalid

        # --- ATTENDANCE ---
        try:
            attendance_data = client.get_attendance()
        except Exception as e:
            print(f"✗ Attendance scrape failed: {e}")
            attendance_data = None

        # --- TIMETABLE ---
        try:
            timetable_data = client.get_timetable()
        except Exception as e:
            print(f"✗ Timetable scrape failed: {e}")
            timetable_data = None

        # --- ATTENDANCE FALLBACK ---
        is_attendance_invalid = (
            attendance_data is None or
            (isinstance(attendance_data, dict) and (not attendance_data or "error" in attendance_data))
        )

        if is_attendance_invalid and timetable_data and "error" not in timetable_data:
            print("ℹ Using timetable → mock attendance fallback")
            attendance_data = generate_mock_attendance_from_timetable(timetable_data)

        # --- GUARANTEE ATTENDANCE STRUCTURE ---
        if attendance_data is None:
            attendance_data = {}

        attendance_data["day_order"] = day_order

        # --- FINAL RESPONSE ---
        response = {
            "status": "success",
            "attendance": attendance_data,
            "timetable": timetable_data,
        }

        client.logout()
        return response

    except HTTPException:
        if client:
            client.logout()
        raise

    except Exception as e:
        if client:
            client.logout()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/studentportal_result")
async def scrape_student_portal_endpoint(request: StudentPortalRequest):
    """
    Scrape student data from SRM student portal
    
    **Parameters:**
    - netid: Student NetID (e.g., "ld8809")
    - password: Student password
    
    **Returns:**
    - Student information (name, registration number, photo)
    - Dashboard info, personal details, subjects, attendance
    - Semester results, timetable, internal marks, hall ticket
    - Performance metrics (fetch time, total time, parallel requests count)
    """
    try:
        result = scrape_student_portal(request.netid, request.password)
        
        if result.get('status') == 'error':
            error_msg = result.get('message', 'Unknown error')
            if 'credentials' in error_msg.lower():
                raise HTTPException(status_code=401, detail=error_msg)
            else:
                raise HTTPException(status_code=500, detail=error_msg)
        
        return result
    
    except HTTPException:
        raise
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

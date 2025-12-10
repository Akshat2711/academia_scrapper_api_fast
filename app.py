from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from studentinfo_scrap import AcademiaClient
from fastapi.middleware.cors import CORSMiddleware

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

        # Step 1: Lookup user
        if not client.lookup_user():
            raise HTTPException(status_code=401, detail="User lookup failed")

        # Step 2: Login
        if not client.login():
            raise HTTPException(status_code=401, detail="Login failed")

        # ---------- Step 3a: Day order ----------
        day_order = None
        try:
            day_order = client.get_day_order()
        except Exception as e:
            print(f"✗ Failed to fetch day order: {e}")

        # ---------- Step 3b: Attendance ----------
        attendance_data = None
        try:
            attendance_data = client.get_attendance()
        except Exception as e:
            # Log and keep going, don't crash the whole endpoint
            print(f"✗ Failed to fetch attendance: {e}")
            attendance_data = {
                "error": "Failed to fetch attendance",
                "details": str(e),
            }

        # Make sure attendance_data is a dict
        if attendance_data is None:
            attendance_data = {}

        # Always set some day_order value
        attendance_data["day_order"] = day_order if day_order is not None else 3

        # ---------- Step 4: Timetable ----------
        timetable_data = None
        try:
            timetable_data = client.get_timetable()
        except Exception as e:
            print(f"✗ Failed to fetch timetable: {e}")
            timetable_data = {
                "error": "Failed to fetch timetable",
                "details": str(e),
            }

        response_data = {
            "status": "success",
            "attendance": attendance_data,
            "timetable": timetable_data,
        }

        # Step 5: Auto-logout after scraping
        logout_success = client.logout()
        response_data["logout_status"] = "success" if logout_success else "failed"

        return response_data

    except HTTPException:
        if client:
            client.logout()
        raise
    except Exception as e:
        if client:
            client.logout()
        # For debugging you might want to log e here too
        raise HTTPException(status_code=500, detail=str(e))

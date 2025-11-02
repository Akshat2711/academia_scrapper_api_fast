from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from studentinfo_scrap import AcademiaClient
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Academia Scraper API")

# Configure CORS
origins = [
    "http://localhost",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "*",  # allow all origins (for development only)
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
    """Scrape portal data and automatically logout after completion"""
    client = None
    try:
        client = AcademiaClient(request.email, request.password)

        # Step 1: Lookup user
        if not client.lookup_user():
            raise HTTPException(status_code=401, detail="User lookup failed")

        # Step 2: Login
        if not client.login():
            raise HTTPException(status_code=401, detail="Login failed")

        # Step 3a: Fetch day order
        day_order = client.get_day_order()

        # Step 3b: Fetch and parse attendance
        attendance_data = client.get_attendance()
        if attendance_data and day_order is not None:
            attendance_data['day_order'] = day_order
        else:
            attendance_data['day_order'] = 4  # default day order

        # Step 4: Fetch timetable
        timetable_data = client.get_timetable()

        # Prepare response
        response_data = {
            "status": "success",
            "attendance": attendance_data,
            "timetable": timetable_data
        }

        # Step 5: Auto-logout after scraping
        logout_success = client.logout()
        response_data["logout_status"] = "success" if logout_success else "failed"

        return response_data

    except HTTPException:
        # Re-raise HTTP exceptions
        if client:
            client.logout()  # Attempt logout even on error
        raise
    except Exception as e:
        # Attempt logout on any error
        if client:
            client.logout()
        raise HTTPException(status_code=500, detail=str(e))



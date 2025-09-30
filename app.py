from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from studentinfo_scrap import AcademiaClient



app = FastAPI(title="academia Scraper API")


class LoginRequest(BaseModel):
    email: str
    password: str


@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.post("/scrape")
async def scrape_portal(request: LoginRequest):
    try:
        client = AcademiaClient(request.email, request.password)

        # Step 1: Lookup user
        if not client.lookup_user():
            raise HTTPException(status_code=401, detail="User lookup failed")

        # Step 2: Login
        if not client.login():
            raise HTTPException(status_code=401, detail="Login failed")

        # Step 3: Fetch attendance
        attendance_data = client.get_attendance()

        # Step 4: Fetch timetable
        timetable_data = client.get_timetable()

        return {
            "status": "success",
            "attendance": attendance_data,
            "timetable": timetable_data
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
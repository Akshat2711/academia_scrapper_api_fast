from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from studentinfo_scrap import AcademiaClient
from fastapi.middleware.cors import CORSMiddleware



app = FastAPI(title="academia Scraper API")

# Configure CORS
origins = [
    "http://localhost",
    "http://localhost:3000",  # frontend URL
    "http://127.0.0.1:3000",
    "*",  # allow all origins (for development only)
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,      # list of allowed origins
    allow_credentials=True,
    allow_methods=["*"],        # allow all HTTP methods
    allow_headers=["*"],        # allow all headers
)


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
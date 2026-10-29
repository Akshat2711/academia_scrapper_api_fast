import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from studentinfo_scrap import AcademiaClient
from tools.native_srm_scraper import scrape_srm_student_portal
from typing import Optional
from concurrent.futures import ThreadPoolExecutor
import time
import re

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
    student_portal_password: Optional[str] = None
    session_data: Optional[dict] = None


class StudentPortalRequest(BaseModel):
    netid: str
    password: str


@app.post("/scrape")
async def scrape_portal(request: LoginRequest):
    clean_net_id = request.email.strip().split('@')[0].strip()
    sp_password = (request.student_portal_password or request.password).strip()

    print("\n" + "="*60)
    print(f"[SCRAPE] Starting concurrent fetch for {clean_net_id}...")
    print("="*60)
    start_time = time.time()

    client = AcademiaClient(request.email, request.password)
    session_authenticated = False
    session_reused = False

    def _fetch_sp():
        """Worker 1: Fetch attendance and marks live from Student Portal"""
        t0 = time.time()
        res, err = scrape_srm_student_portal(clean_net_id, sp_password, max_retries=2)
        elapsed = time.time() - t0
        print(f"[SP WORKER] Finished in {elapsed:.2f}s, Success: {res is not None and res.get('status') == 'success'}")
        return res, err

    def _fetch_academia():
        """Worker 2: Fetch timetable and day order live from Academia"""
        nonlocal session_authenticated, session_reused
        t0 = time.time()
        day_order = 4
        timetable = None

        try:
            if request.session_data:
                print("[ACADEMIA] Validating existing session...")
                client.load_session_data(request.session_data)
                if client.validate_session():
                    session_authenticated = True
                    session_reused = True
                    print("✓ [ACADEMIA] Session reused successfully")
                else:
                    client.session.cookies.clear()
                    client._setup_session()

            if not session_authenticated:
                print("[ACADEMIA] Performing fresh login...")
                if client.lookup_user():
                    login_res = client.login()
                    if login_res.get("success"):
                        session_authenticated = True
                        print("✓ [ACADEMIA] Fresh login successful")

            if session_authenticated:
                fetched_do = client.get_day_order()
                if isinstance(fetched_do, int) and fetched_do > 0:
                    day_order = fetched_do
                timetable = client.get_timetable()
        except Exception as e:
            print(f"⚠ [ACADEMIA] Error during Academia fetch: {e}")

        elapsed = time.time() - t0
        print(f"[ACADEMIA WORKER] Finished in {elapsed:.2f}s, Authenticated: {session_authenticated}")
        return day_order, timetable

    # Concurrently execute Student Portal and Academia flows
    with ThreadPoolExecutor(max_workers=2) as executor:
        sp_future = executor.submit(_fetch_sp)
        acad_future = executor.submit(_fetch_academia)

        sp_result, sp_error = sp_future.result()
        day_order, timetable_data = acad_future.result()

    total_elapsed = time.time() - start_time
    print(f"✓ [SCRAPE] Both workers completed in {total_elapsed:.2f}s total")

    # If neither succeeded, raise error
    has_sp_data = sp_result is not None and sp_result.get("status") == "success"
    has_acad_data = session_authenticated and timetable_data is not None

    if not has_sp_data and not has_acad_data:
        err_msg = sp_error or "Authentication failed on both Student Portal and Academia"
        print(f"✗ [SCRAPE] Both services failed: {err_msg}")
        raise HTTPException(status_code=401, detail=err_msg)

    # 1. Build Student Info (merged from both)
    student_info = {
        "name": clean_net_id,
        "reg_no": clean_net_id,
        "batch": "1",
        "program": "B.Tech",
        "department": "Computer Science and Engineering",
        "semester": "3"
    }

    if sp_result and sp_result.get("student_info"):
        for k, v in sp_result["student_info"].items():
            if v:
                student_info[k] = v

    if timetable_data and isinstance(timetable_data, dict) and timetable_data.get("student_info"):
        for k, v in timetable_data["student_info"].items():
            if v:
                student_info[k] = v

    # 2. Build Attendance & Marks (100% from Student Portal as requested)
    if has_sp_data:
        att_courses = sp_result.get("attendance", {}).get("courses", {})
        attendance_payload = {
            "attendance": sp_result.get("attendance", {}),
            "student_info": student_info,
            "day_order": day_order,
            "attendance_unavailable": False if len(att_courses) > 0 else True,
            "marks": sp_result.get("marks", {}),
        }
    else:
        attendance_payload = {
            "attendance": {},
            "student_info": student_info,
            "day_order": day_order,
            "attendance_unavailable": True,
            "marks": {},
        }

    # 3. Build Timetable (from Academia; do not overwrite with empty slot dummies)
    if timetable_data and isinstance(timetable_data, dict) and len(timetable_data.get("courses", [])) > 0:
        final_timetable = timetable_data
        if not final_timetable.get("student_info"):
            final_timetable["student_info"] = student_info
    else:
        final_timetable = {
            "courses": [],
            "student_info": student_info
        }

    session_data = client.get_session_data() if session_authenticated else None

    return {
        "status": "success",
        "attendance": attendance_payload,
        "timetable": final_timetable,
        "session_data": session_data,
        "session_info": {
            "session_reused": session_reused,
            "session_type": "existing" if session_reused else ("new" if session_authenticated else "none")
        }
    }


@app.post("/studentportal_result")
async def scrape_student_portal_endpoint(request: StudentPortalRequest):
    """Scrape student data natively from SRM student portal (sp.srmist.edu.in)"""
    try:
        clean_net_id = request.netid.strip().split('@')[0].strip()
        print(f"ℹ [NATIVE] Scraping student portal directly for {clean_net_id}...")
        result, error = scrape_srm_student_portal(clean_net_id, request.password, max_retries=2)
        if result and result.get('status') == 'success':
            return result

        if error:
            if 'credential' in error.lower() or 'password' in error.lower() or 'lock' in error.lower() or 'attempt' in error.lower():
                raise HTTPException(status_code=401, detail=error)
            raise HTTPException(status_code=400, detail=error)

        raise HTTPException(status_code=500, detail="Failed to scrape student portal")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/logout")
async def logout_session(request: LoginRequest):
    """Logout endpoint to invalidate session"""
    try:
        client = AcademiaClient(request.email, request.password)
        if request.session_data:
            client.load_session_data(request.session_data)
        if client.logout():
            return {"status": "success", "message": "Logged out successfully"}
        return {"status": "success", "message": "Logged out"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Logout error: {str(e)}")


@app.get("/health")
async def health_check():
    return {"status": "ok"}

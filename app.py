from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from studentinfo_scrap import AcademiaClient
from tools.fallback_mock_attendance_data import generate_mock_attendance_from_timetable
from tools.studentportal_result import scrape_student_portal
from tools.retry_fetch_failed_login import fetch_all_data_with_retry  # ADD THIS
from typing import Optional
import time  # ADD THIS


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
    session_data: Optional[dict] = None


class StudentPortalRequest(BaseModel):
    netid: str
    password: str


@app.post("/scrape")
async def scrape_portal(request: LoginRequest):
    client = None
    session_authenticated = False
    session_reused = False

    try:
        client = AcademiaClient(request.email, request.password)
                
        # --- ATTEMPT SESSION REUSE ---
        if request.session_data:
            print("\n" + "="*60)
            print("[SESSION] Attempting to reuse existing session...")
            print("="*60)
            client.load_session_data(request.session_data)
            
            try:
                print("[SESSION] Validating session with lightweight request...")
                test_response = client.get_attendance()
                
                if test_response is not None and (
                    not isinstance(test_response, dict) or 
                    (test_response.get("error") != "Could not parse HTML" and "error" not in test_response)
                ):
                    print("✓ [SESSION] Session is VALID - Reusing existing session")
                    session_authenticated = True
                    session_reused = True
                else:
                    print("⚠ [SESSION] Session EXPIRED or INVALID - Falling back to fresh login")
                    print("[SESSION] Clearing old session data before fresh login...")
                    client.session.cookies.clear()
                    client._setup_session()
            except Exception as e:
                print(f"⚠ [SESSION] Session validation FAILED: {str(e)}")
                print("⚠ [SESSION] Falling back to fresh login")
                print("[SESSION] Clearing old session data before fresh login...")
                client.session.cookies.clear()
                client._setup_session()
        else:
            print("\n" + "="*60)
            print("[SESSION] No session data provided - Starting fresh login")
            print("="*60)

        # --- FALLBACK TO LOGIN ---
        if not session_authenticated:
            print("\n[LOGIN] Initiating fresh login flow...")
            result_lookup = client.lookup_user()
            result_login = client.login()
            if not result_lookup or not result_login["success"]:
                if not result_lookup:
                    print("✗ [LOGIN] User lookup failed - Cannot proceed with login")
                    raise HTTPException(status_code=401, detail="User lookup failed check your email id")
                else:
                    print(f"✗ [LOGIN] Login failed - {result_login.get('message', 'Unknown error')}")
                    raise HTTPException(status_code=401, detail=result_login.get('message', 'Login failed'))
            print("✓ [LOGIN] Fresh login successful - New session created\n")
            
            # Small delay for session stability after fresh login
            time.sleep(0.5)

        # --- FETCH DATA WITH RETRY LOGIC ---
        if session_reused and 'test_response' in locals():
            # Use cached attendance from session validation
            print("[DATA] Using attendance from session validation + fetching remaining data...")
            
            day_order = client.get_day_order()
            if not isinstance(day_order, int) or day_order <= 0:
                day_order = 3
            
            timetable_data = client.get_timetable()
            
            # Check if timetable parse failed
            timetable_failed = (
                timetable_data and 
                isinstance(timetable_data, dict) and 
                timetable_data.get('error') == "Could not parse HTML"
            )
            
            if timetable_failed:
                print("[RETRY] Parse failure detected - refetching all data with retry logic...")
                result = fetch_all_data_with_retry(client, max_retries=2, save_debug_html=False)
                day_order = result['day_order']
                attendance_data = result['attendance_data']
                timetable_data = result['timetable_data']
            else:
                attendance_data = test_response
        else:
            # Fresh login - fetch all data with retry logic
            result = fetch_all_data_with_retry(client, max_retries=2, save_debug_html=False)
            day_order = result['day_order']
            attendance_data = result['attendance_data']
            timetable_data = result['timetable_data']

        # --- ATTENDANCE FALLBACK ---
        is_attendance_invalid = (
            attendance_data is None or
            (isinstance(attendance_data, dict) and (
                not attendance_data or 
                attendance_data.get("error") == "Could not parse HTML"
            ))
        )

        if is_attendance_invalid and timetable_data and "error" not in timetable_data:
            print("[DATA] Generating mock attendance from timetable...")
            attendance_data = generate_mock_attendance_from_timetable(timetable_data)
            print("✓ [DATA] Mock attendance generated")

        # --- GUARANTEE ATTENDANCE STRUCTURE ---
        if attendance_data is None:
            attendance_data = {}

        attendance_data["day_order"] = day_order

        # Return session data for reuse
        session_data = client.get_session_data()
        
        print("\n" + "="*60)
        if session_reused:
            print("[SESSION] Response ready - Returning EXISTING session data")
        else:
            print("[SESSION] Response ready - Returning NEW session data")
        print("="*60 + "\n")
        
        return {
            "status": "success",
            "attendance": attendance_data,
            "timetable": timetable_data,
            "session_data": session_data,
            "session_info": {
                "session_reused": session_reused,
                "session_type": "existing" if session_reused else "new"
            }
        }

    except HTTPException:
        if client:
            print("[ERROR] HTTPException occurred - Session NOT logged out (kept alive)")
        raise

    except Exception as e:
        if client:
            print(f"[ERROR] Exception occurred: {str(e)} - Session NOT logged out (kept alive)")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/studentportal_result")
async def scrape_student_portal_endpoint(request: StudentPortalRequest):
    """Scrape student data from SRM student portal"""
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


@app.post("/logout")
async def logout_session(request: LoginRequest):
    """Logout endpoint to invalidate session"""
    try:
        client = AcademiaClient(request.email, request.password)
        
        if request.session_data:
            client.load_session_data(request.session_data)
        
        if client.logout():
            return {
                "status": "success",
                "message": "Logged out successfully"
            }
        else:
            raise HTTPException(status_code=500, detail="Logout failed")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Logout error: {str(e)}")


@app.get("/health")
async def health_check():
    return {"status": "ok"}
"""retries login when login flow fails to get correct resp (when page was not able to load completly),
this function resuses session details of failed to retry login"""



import time
from typing import Dict, Any


def fetch_all_data_with_retry(client, max_retries: int = 2) -> Dict[str, Any]:
    """
    Fetch all data (day_order, attendance, timetable) with retry on parse failures.
    On retry, reuses existing session cookies instead of full re-authentication.
    
    Args:
        client: Authenticated AcademiaClient instance
        max_retries: Maximum number of retry attempts (default: 2)
    
    Returns:
        dict with keys: success, day_order, attendance_data, timetable_data, error (if failed)
    """
    
    for attempt in range(max_retries):
        if attempt > 0:
            print(f"\n{'='*60}")
            print(f"[RETRY] Attempt {attempt + 1}/{max_retries}")
            print("="*60)
            
            # SMART: Reuse session instead of logout/login
            print("[RETRY] Refreshing session using existing cookies...")
            try:
                # Get current session data
                session_data = client.get_session_data()
                
                # Clear and reload the session (refresh without re-auth)
                client.session.cookies.clear()
                client.load_session_data(session_data)
                
                print("✓ [RETRY] Session refreshed with existing cookies")
                time.sleep(0.8)  # Small delay for session stability
                
            except Exception as e:
                print(f"⚠ [RETRY] Session refresh error: {e}")
                print("[RETRY] Attempting fresh login as fallback...")
                
                # Fallback to full re-auth only if session refresh fails
                try:
                    client.session.cookies.clear()
                    client._setup_session()
                    
                    if not client.lookup_user():
                        return {
                            "success": False,
                            "error": "Lookup failed during retry",
                            "day_order": None,
                            "attendance_data": None,
                            "timetable_data": None
                        }
                    
                    login_result = client.login()
                    if not login_result.get("success"):
                        return {
                            "success": False,
                            "error": f"Login failed during retry: {login_result.get('message')}",
                            "day_order": None,
                            "attendance_data": None,
                            "timetable_data": None
                        }
                    
                    print("✓ [RETRY] Fallback login successful")
                    time.sleep(0.5)
                    
                except Exception as login_error:
                    print(f"✗ [RETRY] Fallback login failed: {login_error}")
                    return {
                        "success": False,
                        "error": f"Retry authentication failed: {str(login_error)}",
                        "day_order": None,
                        "attendance_data": None,
                        "timetable_data": None
                    }
        
        try:
            # --- DAY ORDER ---
            print("[DATA] Fetching day order...")
            day_order = client.get_day_order()
            if day_order is not None:
                print(f"✓ [DATA] Day order retrieved: {day_order}")
            else:
                print("⚠ [DATA] Day order not available from server")
            
            # Normalize day order
            if not isinstance(day_order, int) or day_order <= 0:
                print(f"⚠ [DATA] Invalid day order ({day_order}), defaulting to Day 4")
                day_order = 4

            # --- ATTENDANCE ---
            print("[DATA] Fetching attendance data...")
            attendance_data = client.get_attendance()
            
            # --- TIMETABLE ---
            print("[DATA] Fetching timetable data...")
            timetable_data = client.get_timetable()
            
            # --- VALIDATE PARSING ---
            attendance_failed = (
                attendance_data and 
                isinstance(attendance_data, dict) and 
                attendance_data.get('error') == "Could not parse HTML"
            )
            timetable_failed = (
                timetable_data and 
                isinstance(timetable_data, dict) and 
                timetable_data.get('error') == "Could not parse HTML"
            )
            
            if attendance_failed or timetable_failed:
                print("\n" + "⚠"*30)
                print("[PARSE ERROR] Data corruption detected!")
                if attendance_failed:
                    print("✗ [DATA] Attendance parsing failed")
                if timetable_failed:
                    print("✗ [DATA] Timetable parsing failed")
                print("⚠"*30 + "\n")
                
                if attempt < max_retries - 1:
                    print(f"[RETRY] Will retry with session refresh (attempt {attempt + 2}/{max_retries})...")
                    continue
                else:
                    print("[RETRY] Max retries reached - returning partial data")
                    return {
                        "success": False,
                        "error": "Parse failures after retries",
                        "day_order": day_order,
                        "attendance_data": attendance_data,
                        "timetable_data": timetable_data
                    }
            
            # --- SUCCESS ---
            print("✓ [DATA] All data retrieved and parsed successfully")
            return {
                "success": True,
                "day_order": day_order,
                "attendance_data": attendance_data,
                "timetable_data": timetable_data
            }
        
        except Exception as e:
            print(f"✗ [DATA] Fetch error on attempt {attempt + 1}: {e}")
            if attempt < max_retries - 1:
                continue
            else:
                return {
                    "success": False,
                    "error": f"Data fetch failed: {str(e)}",
                    "day_order": None,
                    "attendance_data": None,
                    "timetable_data": None
                }
    
    return {
        "success": False,
        "error": "Max retries exceeded",
        "day_order": None,
        "attendance_data": None,
        "timetable_data": None
    }
import time
from typing import Dict, Any


def fetch_all_data_with_retry(client, max_retries: int = 2, save_debug_html: bool = False) -> Dict[str, Any]:
    """
    Fetch all data (day_order, attendance, timetable) with retry on parse failures.
    On retry, reuses existing session cookies instead of full re-authentication.
    
    Args:
        client: Authenticated AcademiaClient instance
        max_retries: Maximum number of retry attempts (default: 2)
        save_debug_html: If True, saves failed HTML responses to files for debugging
    
    Returns:
        dict with keys: success, day_order, attendance_data, timetable_data, error (if failed)
    """
    
    for attempt in range(max_retries):
        if attempt > 0:
            print(f"\n{'='*60}")
            print(f"[RETRY] Attempt {attempt + 1}/{max_retries}")
            print("="*60)
            
            # Try full re-authentication instead of just session refresh
            print("[RETRY] Performing FULL re-authentication...")
            try:
                # Clear everything
                client.session.cookies.clear()
                client._setup_session()
                
                # Fresh lookup and login
                if not client.lookup_user():
                    print("✗ [RETRY] Lookup failed on retry")
                    return {
                        "success": False,
                        "error": "Lookup failed during retry",
                        "day_order": None,
                        "attendance_data": None,
                        "timetable_data": None
                    }
                
                login_result = client.login()
                if not login_result.get("success"):
                    print(f"✗ [RETRY] Login failed on retry: {login_result.get('message')}")
                    return {
                        "success": False,
                        "error": f"Login failed during retry: {login_result.get('message')}",
                        "day_order": None,
                        "attendance_data": None,
                        "timetable_data": None
                    }
                
                print("✓ [RETRY] Full re-authentication successful")
                time.sleep(1.0)  # Longer delay after re-auth
                
            except Exception as e:
                print(f"✗ [RETRY] Re-authentication error: {e}")
                return {
                    "success": False,
                    "error": f"Re-authentication failed: {str(e)}",
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
                
                # DEBUG: Save HTML to file if debugging is enabled
                if save_debug_html:
                    try:
                        import os
                        os.makedirs("debug_html", exist_ok=True)
                        
                        if attendance_failed:
                            # Re-fetch to get raw HTML
                            url = f'{client.BASE_URL}/srm_university/academia-academic-services/page/My_Attendance'
                            response = client.session.get(url, headers=client._get_page_headers())
                            with open(f"debug_html/attendance_failed_attempt_{attempt + 1}.html", "w", encoding="utf-8") as f:
                                f.write(response.text)
                            print(f"[DEBUG] Saved attendance HTML to debug_html/attendance_failed_attempt_{attempt + 1}.html")
                        
                        if timetable_failed:
                            url = f'{client.BASE_URL}/srm_university/academia-academic-services/page/My_Time_Table_2023_24'
                            response = client.session.get(url, headers=client._get_page_headers())
                            with open(f"debug_html/timetable_failed_attempt_{attempt + 1}.html", "w", encoding="utf-8") as f:
                                f.write(response.text)
                            print(f"[DEBUG] Saved timetable HTML to debug_html/timetable_failed_attempt_{attempt + 1}.html")
                    except Exception as debug_error:
                        print(f"[DEBUG] Failed to save HTML: {debug_error}")
                
                if attempt < max_retries - 1:
                    print(f"[RETRY] Will retry with FULL re-authentication (attempt {attempt + 2}/{max_retries})...")
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
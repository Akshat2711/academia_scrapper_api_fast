import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
import requests

import json

import re

from typing import Dict, Optional, Any

import time

import random



# importing parser utility functions

from utils.parser import *

#login error handler

from tools.handle_login_error_codes import handle_login_response





class AcademiaClient:

    """Client for interacting with SRM Academia portal"""

    

    BASE_URL = "https://academia.srmist.edu.in"

    

    

    def __init__(self, email: str, password: str):

        """

        Initialize the Academia client

        

        Args:

            email: User email address

            password: User password

        """

        self.email = email

        self.password = password

        self.session = requests.Session()

        self.identifier = None

        self.digest = None

        self.csrf_token = None

        self._resolved_timetable_url = None

        self._setup_session()

    

    def _setup_session(self):

        """Set up session with base cookies and fresh tokens (Hybrid Approach)"""

        print("[DEBUG] Starting session setup...")

        USER_AGENTS = [

        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',

        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',

        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',

        ]   

        

        # Enhanced browser headers

        print("[DEBUG] Setting up headers and cookies...")

        self.session.headers.update({

            'User-Agent': random.choice(USER_AGENTS),

            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',

            'Accept-Language': 'en-US,en;q=0.9',

            'Accept-Encoding': 'gzip, deflate, br',

            'DNT': '1',

            'Connection': 'keep-alive',

            'Upgrade-Insecure-Requests': '1',

            'Sec-Fetch-Dest': 'document',

            'Sec-Fetch-Mode': 'navigate',

            'Sec-Fetch-Site': 'none',

            'Sec-Fetch-User': '?1',

            'Cache-Control': 'max-age=0'

        })

        

        # Dynamic client region

        self.session.cookies.set('cli_rgn', 'IN', domain='academia.srmist.edu.in')

        print(f"[DEBUG] Session cookie jar initialized cleanly")

        

        # Add slight delay to simulate human behavior

        time.sleep(random.uniform(0.5, 1.5))

        

        # Visit login page to get fresh CSRF token and session cookies

        print("[DEBUG] Attempting to fetch login page for CSRF token...")

        try:

            login_page_url = f'{self.BASE_URL}/accounts/p/10002227248/signin'

            params = {

                'hide_fp': 'true',

                'orgtype': '40',

                'service_language': 'en',

                'css_url': '/49910842/academia-academic-services/downloadPortalCustomCss/login',

                'dcc': 'true',

                'serviceurl': f'{self.BASE_URL}/portal/academia-academic-services/redirectFromLogin'

            }

            

            response = self.session.get(login_page_url, params=params)

            print(f"[DEBUG] Login page response status: {response.status_code}")

            response.raise_for_status()

            

            # Extract CSRF token from cookies

            """ print(f"[DEBUG] Current cookies: {list(self.session.cookies.keys())}") """

            if 'iamcsr' in self.session.cookies:

                self.csrf_token = self.session.cookies.get('iamcsr')

                print("✓ CSRF Token obtained")

                """ print(f"[DEBUG] CSRF Token value: {self.csrf_token[:20]}..." if len(self.csrf_token) > 20 else f"[DEBUG] CSRF Token value: {self.csrf_token}") """

            else:

                print("⚠ Warning: No CSRF token found in cookies")

                """ print(f"[DEBUG] Available cookies: {dict(self.session.cookies)}") """

            

            # Extract JSESSIONID if present

            if 'JSESSIONID' in self.session.cookies:

                print("✓ Session ID obtained")

                """ print(f"[DEBUG] JSESSIONID: {self.session.cookies.get('JSESSIONID')[:20]}...") """

            else:

                print("[DEBUG] JSESSIONID not found in cookies")

                

        except Exception as e:

            print(f"⚠ Warning: Failed to initialize session: {str(e)}")

            print(f"[DEBUG] Exception type: {type(e).__name__}")

            print(f"[DEBUG] Exception details: {repr(e)}")

    

    def _get_common_headers(self) -> Dict[str, str]:

        """Get common headers for requests"""

        headers = {

            'Accept': '*/*',

            'Accept-Encoding': 'gzip, deflate, br, zstd',

            'Accept-Language': 'en-US,en;q=0.9,en-IN;q=0.8',

            'Connection': 'keep-alive',

            'Origin': self.BASE_URL,

            'Referer': f'{self.BASE_URL}/accounts/p/10002227248/signin',

            'Sec-Fetch-Dest': 'empty',

            'Sec-Fetch-Mode': 'cors',

            'Sec-Fetch-Site': 'same-origin',

            'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8'

        }

        

        # Add CSRF token if available

        if self.csrf_token:

            headers['X-ZCSRF-TOKEN'] = f'iamcsrcoo={self.csrf_token}'

        

        return headers

    

    def lookup_user(self) -> bool:

        """Perform user lookup to get identifier and digest"""

        print("Step 1: Performing user lookup...")

        # print(f"[DEBUG] Email: {self.email}")

        

        url = f'{self.BASE_URL}/accounts/p/40-10002227248/signin/v2/lookup/{self.email}'

        """ print(f"[DEBUG] Lookup URL: {url}") """

        

        cli_time = str(int(time.time() * 1000))

        print(f"[DEBUG] CLI time: {cli_time}")

        

        data = {

            'mode': 'primary',

            'cli_time': cli_time,

            'orgtype': '40',

            'service_language': 'en',

            'serviceurl': f'{self.BASE_URL}/portal/academia-academic-services/redirectFromLogin'

        }

        

        try:

            print("[DEBUG] Sending POST request for user lookup...")

            response = self.session.post(url, headers=self._get_common_headers(), data=data)

            # print(f"[DEBUG] Response status code: {response.status_code}")

            # print(f"[DEBUG] Response headers: {dict(response.headers)}")

            response.raise_for_status()

            

            # print(f"[DEBUG] Attempting to parse response as JSON...")

            lookup_data = response.json()

            # print(f"[DEBUG] JSON parsed successfully. Keys: {lookup_data.keys()}")

            # print(f"[DEBUG] Full response data: {json.dumps(lookup_data, indent=2)}")

            self.identifier = lookup_data.get('lookup', {}).get('identifier')

            self.digest = lookup_data.get('lookup', {}).get('digest')

            # print(f"✓ User identifier: {self.identifier}")

            # print(f"[DEBUG] Identifier extracted: {self.identifier is not None}")

            # print(f"✓ User digest: {self.digest}")

            # print(f"[DEBUG] Digest extracted: {self.digest is not None}")

            

            if self.identifier and self.digest:

                print("✓ Lookup successful")

                print("✓ Digest obtained\n")

                return True

            else:

                print("ℹ Lookup did not return digest (e.g. SI503 daily signin limit) - will use direct portal authentication\n")

                return True

                

        except json.JSONDecodeError as e:

            print(f"⚠ Lookup JSON parsing error: {e} - will attempt direct portal authentication\n")

            return True

        except Exception as e:

            print(f"⚠ Lookup request warning: {e} - will attempt direct portal authentication\n")

            return True

    

    def _close_active_sessions(self, redirect_uri: str, service_url: str, service_language: str, orgtype: str) -> bool:

        """Close active sessions when prompted by the portal"""

        print("Step 2b: Closing active sessions...")

        

        # First, visit the announcement page to get proper session state

        try:

            response = self.session.get(redirect_uri)

            response.raise_for_status()

            print("✓ Visited sessions reminder page")

        except Exception as e:

            print(f"⚠ Warning: Failed to visit announcement page: {str(e)}")

        

        # Now close active sessions

        delete_url = f'{self.BASE_URL}/accounts/p/40-10002227248/webclient/v1/account/self/user/self/activesessions'

        

        headers = self._get_common_headers()

        headers['Referer'] = redirect_uri

        

        try:

            response = self.session.delete(delete_url, headers=headers)

            response.raise_for_status()

            print(f"✓ Active sessions deleted (Status: {response.status_code})")

        except Exception as e:

            print(f"⚠ Warning: Failed to delete sessions: {str(e)}")

            # Continue anyway as this might not be critical

        

        # Visit the /next endpoint to confirm session closure

        print("Step 2c: Confirming session closure...")

        next_url = f'{self.BASE_URL}/accounts/p/40-10002227248/announcement/sessions-reminder/next'

        next_params = {

            'status': '2',  # Status 2 = sessions closed

            'serviceurl': service_url,

            'service_language': service_language,

            'orgtype': orgtype

        }

        

        next_headers = {

            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',

            'Accept-Language': 'en-US,en;q=0.9,en-IN;q=0.8',

            'Connection': 'keep-alive',

            'Referer': redirect_uri,

            'Sec-Fetch-Dest': 'document',

            'Sec-Fetch-Mode': 'navigate',

            'Sec-Fetch-Site': 'same-origin',

            'Sec-Fetch-User': '?1',

            'Upgrade-Insecure-Requests': '1',

            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'

        }

        

        try:

            response = self.session.get(next_url, params=next_params, headers=next_headers)

            response.raise_for_status()

            print(f"✓ Session closure confirmed (Status: {response.status_code})\n")

            return True

                

        except Exception as e:

            print(f"✗ Failed to confirm session closure: {str(e)}\n")

            return False

        



    def _close_blocked_sessions(self, redirect_uri: str) -> bool:

        """Close blocked sessions when prompted by the portal"""

        print("Step 2b: Closing blocked sessions...")

        

        # Visit the block-sessions page

        try:

            response = self.session.get(redirect_uri)

            response.raise_for_status()

            print("✓ Visited blocked sessions page")

        except Exception as e:

            print(f"⚠ Warning: Failed to visit announcement page: {str(e)}")

        

        # Delete blocked sessions

        delete_url = f'{self.BASE_URL}/accounts/p/40-10002227248/webclient/v1/announcement/pre/blocksessions'

        

        headers = self._get_common_headers()

        headers['Referer'] = redirect_uri

        

        try:

            response = self.session.delete(delete_url, headers=headers)

            response.raise_for_status()

            print(f"✓ Blocked sessions deleted (Status: {response.status_code})\n")

            return True

        except Exception as e:

            print(f"✗ Failed to delete blocked sessions: {str(e)}\n")

            return False

        







    def _login_portal_direct(self) -> dict:

        """Direct portal authentication via signin.ac (client portal endpoint)"""

        url = f'{self.BASE_URL}/accounts/signin.ac'

        payload = {

            'username': self.email,

            'password': self.password,

            'client_portal': 'true',

            'portal': '10002227248',

            'servicename': 'ZohoCreator',

            'serviceurl': f'{self.BASE_URL}/',

            'is_ajax': 'true',

            'grant_type': 'password',

            'service_language': 'en'

        }

        headers = {

            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',

            'Origin': self.BASE_URL,

            'Referer': f'{self.BASE_URL}/',

            'Accept': '*/*',

            'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8'

        }

        try:

            response = self.session.post(url, headers=headers, data=payload)

            if response.status_code == 200:

                data = response.json()

                if 'data' in data:

                    inner = data['data']

                    oauthorize_uri = inner.get('oauthorize_uri')

                    access_token = inner.get('access_token')

                    if oauthorize_uri and access_token:

                        auth_url = f"{oauthorize_uri}&access_token={access_token}"

                        r_auth = self.session.get(auth_url)

                        print(f"[DIAG AUTH] r_auth status: {r_auth.status_code}, final_url: {r_auth.url.split('?')[0]}")

                        for h in r_auth.history:

                            print(f"[DIAG AUTH] Redirect: {h.status_code} -> {h.headers.get('Location', '').split('?')[0]}")

                        cookie_summary = [f"{c.name}(d={c.domain},p={c.path})" for c in self.session.cookies]

                        print(f"[DIAG AUTH] Cookies in session: {cookie_summary}")

                        if r_auth.status_code in [200, 302]:

                            try:

                                self.session.get(f"{self.BASE_URL}/portal/academia-academic-services/redirectFromLogin")

                            except Exception:

                                pass

                            print("✓ Direct portal login successful!\n")

                            return {"success": True}

                elif 'error' in data or 'status_code' in data:

                    error_msg = data.get('message') or data.get('error', {}).get('message', 'Login failed')

                    return {"success": False, "message": error_msg, "credentials_error": True}

        except Exception as e:

            print(f"⚠ Direct portal login exception: {e}")

        return {"success": False}



    def login(self) -> dict:

        """Login to Academia portal using direct portal signin or fallback v2"""

        print("Step 2: Logging in...")

        

        # 1. Try direct portal login first

        direct_result = self._login_portal_direct()

        if direct_result.get("success"):

            return direct_result

        if direct_result.get("credentials_error"):

            return direct_result



        # 2. Fall back to v2 password auth if identifier & digest were obtained

        if self.identifier and self.digest:

            return self._login_v2()



        return {

            "success": False,

            "message": direct_result.get("message", "Login failed. Please check credentials.")

        }



    def _login_v2(self) -> dict:

        """Login with password using digest from lookup"""

        if not self.identifier or not self.digest:

            print("✗ No identifier/digest found. Run lookup_user() first.\n")

            return {

                "success": False,

                "message": "No identifier/digest found"

            }



        url = f'{self.BASE_URL}/accounts/p/40-10002227248/signin/v2/primary/{self.identifier}/password'

        cli_time = str(int(time.time() * 1000))



        params = {

            'digest': self.digest,

            'cli_time': cli_time,

            'orgtype': '40',

            'service_language': 'en',

            'serviceurl': f'{self.BASE_URL}/portal/academia-academic-services/redirectFromLogin'

        }



        body = json.dumps({

            "passwordauth": {

                "password": self.password

            }

        })



        headers = self._get_common_headers()

        headers['Content-Type'] = 'application/json;charset=UTF-8'



        try:

            response = self.session.post(url, headers=headers, params=params, data=body)

            response.raise_for_status()



            if response.status_code == 200:

                login_data = response.json()



                # -------------------------------------------------

                # centralized error handler 

                # -------------------------------------------------

                handled = handle_login_response(login_data)

                if handled.get("success") is False:

                    self.last_error = handled.get("message")

                    print(f"✗ Login failed: {self.last_error}\n")



                    return {

                        "success": False,

                        "message": handled.get("message"),

                        "type": handled.get("type"),

                        "code": handled.get("code"),

                        "raw": handled.get("raw"),

                    }



                # ---------------- LOGIN LOGIC ----------------



                code = login_data.get('code')

                passwordauth = login_data.get('passwordauth', {})

                inner_code = passwordauth.get('code')



                # Handle successful login

                if code in ['SI200', 'SIGIN_SUCCESS'] or inner_code == 'SIGIN_SUCCESS':

                    print("✓ Login successful!\n")

                    return {"success": True}



                # Handle post-announcement redirection

                elif (

                    code in ['POST_ANNOUCEMENT_REDIRECTION', 'SI302', 'SI303']

                    or inner_code == 'POST_ANNOUCEMENT_REDIRECTION'

                ):

                    print(f"✓ Login successful - handling redirect (code: {code})...")

                    redirect_uri = passwordauth.get('redirect_uri')



                    if redirect_uri:

                        is_block_sessions = 'block-sessions' in redirect_uri



                        service_url = params.get('serviceurl')

                        service_language = params.get('service_language')

                        orgtype = params.get('orgtype')



                        if is_block_sessions:

                            success = self._close_blocked_sessions(redirect_uri)

                        else:

                            success = self._close_active_sessions(

                                redirect_uri,

                                service_url,

                                service_language,

                                orgtype

                            )



                        if success:

                            print("Step 2d: Completing login flow...")



                            redirect_headers = {

                                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',

                                'Accept-Language': 'en-US,en;q=0.9,en-IN;q=0.8',

                                'Connection': 'keep-alive',

                                'Referer': redirect_uri,

                                'Sec-Fetch-Dest': 'document',

                                'Sec-Fetch-Mode': 'navigate',

                                'Sec-Fetch-Site': 'same-origin',

                                'Sec-Fetch-User': '?1',

                                'Upgrade-Insecure-Requests': '1',

                                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'

                            }



                            try:

                                final_response = self.session.get(

                                    service_url,

                                    headers=redirect_headers

                                )



                                if final_response.status_code == 200:

                                    print("✓ Login flow completed successfully!\n")

                                    return {"success": True}

                                else:

                                    print(f"⚠ Warning: Unusual status code: {final_response.status_code}")

                                    return {"success": True}



                            except Exception as e:

                                print(f"⚠ Warning: Final redirect failed: {str(e)}")

                                return {"success": True}



                        else:

                            print("✗ Failed to close sessions\n")

                            return {"success": False}



                    else:

                        print("✗ No redirect_uri found in response\n")

                        return {"success": False}



                # Handle legacy error block 

                elif 'error' in login_data:

                    error_msg = login_data.get('error', {}).get('message', 'Unknown error')

                    self.last_error = error_msg

                    print(f"✗ Login failed: {error_msg}\n")

                    return {

                        "success": False,

                        "message": error_msg

                    }



                else:

                    print(f"⚠ Unexpected response code: {code}")

                    print(f"Response: {json.dumps(login_data, indent=2)}\n")

                    return {

                        "success": False,

                        "message": "Unexpected login response",

                        "raw": login_data

                    }



            else:

                print(f"✗ Login failed with status code: {response.status_code}\n")

                return {

                    "success": False,

                    "message": f"HTTP {response.status_code}"

                }



        except Exception as e:

            print(f"✗ Login failed: {str(e)}\n")

            return {

                "success": False,

                "message": str(e)

            }



    

    def logout(self) -> bool:

        """Logout from the academia portal"""

        print("Logging out...")

        

        url = f'{self.BASE_URL}/accounts/p/10002227248/logout'

        params = {

            'servicename': 'ZohoCreator',

            'serviceurl': self.BASE_URL

        }

        

        headers = {

            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',

            'Accept-Language': 'en-US,en;q=0.9,en-IN;q=0.8',

            'Connection': 'keep-alive',

            'Referer': f'{self.BASE_URL}/',

            'Sec-Fetch-Dest': 'document',

            'Sec-Fetch-Mode': 'navigate',

            'Sec-Fetch-Site': 'same-origin',

            'Sec-Fetch-User': '?1',

            'Upgrade-Insecure-Requests': '1',

            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'

        }

        

        try:

            response = self.session.get(url, headers=headers, params=params)

            if response.status_code in [200, 302, 303]:

                print("✓ Logout successful!\n")

                self.session.cookies.clear()  # NOW we clear cookies

                self.identifier = None

                self.digest = None

                self.csrf_token = None

                return True

            else:

                print(f"✗ Logout failed with status: {response.status_code}\n")

                return False

                

        except Exception as e:

            print(f"✗ Logout failed: {str(e)}\n")

            return False

    

    def _get_page_headers(self) -> Dict[str, str]:

        """Get headers for page requests"""

        return {

            'Accept': '*/*',

            'Accept-Encoding': 'gzip, deflate, br, zstd',

            'Accept-Language': 'en-US,en;q=0.9,en-IN;q=0.8',

            'Referer': f'{self.BASE_URL}/',

            'Sec-Fetch-Dest': 'empty',

            'Sec-Fetch-Mode': 'cors',

            'Sec-Fetch-Site': 'same-origin',

            'X-Requested-With': 'XMLHttpRequest'

        }

    

    def validate_session(self) -> bool:

        """Validate if existing session cookies are still accepted by the portal"""

        url = f'{self.BASE_URL}/srm_university/academia-academic-services/page/WELCOME'

        try:

            resp = self.session.get(url, headers=self._get_page_headers(), allow_redirects=False, timeout=5)

            if resp.status_code == 200 and 'signin' not in resp.text.lower():

                return True

        except Exception:

            pass

        return False



    def get_attendance(self) -> Optional[Dict[str, Any]]:
        """Fast check for attendance data on Academia"""
        candidates = []
        if self._resolved_timetable_url:
            candidates.append(self._resolved_timetable_url)
        candidates.append(f"{self.BASE_URL}/srm_university/academia-academic-services/page/My_Time_Table_2023_24")

        for url in candidates:
            try:
                response = self.session.get(url, headers=self._get_page_headers(), timeout=5)
                if response.status_code == 200:
                    parsed = parse_attendance(response.text)
                    if parsed and "error" not in parsed:
                        raw_c = parsed.get("attendance", {}).get("courses", {})
                        valid_c = {k: v for k, v in raw_c.items() if re.match(r'^[0-9]{2}[A-Z]{3,4}[0-9]{3}[A-Z0-9]*$', (v.get('course_code') or k[:9]).strip())}
                        if len(valid_c) > 0:
                            parsed["attendance"]["courses"] = valid_c
                            return parsed
            except Exception:
                pass
        return None

    def _get_timetable_candidates(self) -> List[str]:

        """Generate candidate timetable URLs based on portal discovery and academic calendar"""

        candidates = []

        

        # 1. Live discovery from portal navigation

        try:

            portal_resp = self.session.get(

                f"{self.BASE_URL}/portal/academia-academic-services",

                headers=self._get_page_headers(),

                timeout=5

            )

            if portal_resp.status_code == 200:

                idx = portal_resp.text.find('My_Time_Table_Attendance')

                if idx != -1:

                    snippet = portal_resp.text[max(0, idx-100):min(len(portal_resp.text), idx+150)]

                    print(f"[DIAG TAB] Around My_Time_Table_Attendance: {snippet}")

                idx_att = portal_resp.text.find('My_Attendance')

                if idx_att != -1:

                    snippet_att = portal_resp.text[max(0, idx_att-50):min(len(portal_resp.text), idx_att+100)]

                    print(f"[DIAG ARR] Around My_Attendance: {snippet_att}")



                components = re.findall(r'#(Page|View|Form|Report):([A-Za-z0-9_]+)', portal_resp.text, re.IGNORECASE)

                print(f"[DIAG PORTAL] All components in portal HTML: {sorted(list(set(components)))}")

                all_pages = re.findall(r'#Page:([A-Za-z0-9_]+)', portal_resp.text, re.IGNORECASE)

                print(f"[DIAG PORTAL] All portal navigation pages: {sorted(list(set(all_pages)))}")

                

                # Prioritize active portal pages (especially Unified_Time_Table and 2025 batches)

                for page in all_pages:

                    url = f"{self.BASE_URL}/srm_university/academia-academic-services/page/{page}"

                    if any(k in page.lower() for k in ['unified', '2025', '2024_25']):

                        if url not in candidates:

                            candidates.insert(0, url)

                    elif any(k in page.lower() for k in ['time_table', 'timetable']):

                        if url not in candidates:

                            candidates.append(url)

        except Exception as e:

            print(f"⚠ Portal navigation timetable discovery skipped: {e}")



        # 2. Known active and recent semester endpoints

        known_urls = [
            f"{self.BASE_URL}/srm_university/academia-academic-services/page/My_Time_Table_2023_24",
            f"{self.BASE_URL}/srm_university/academia-academic-services/page/My_Time_Table_2024_25",
            f"{self.BASE_URL}/srm_university/academia-academic-services/page/Unified_Time_Table_2025_Batch_1",
            f"{self.BASE_URL}/srm_university/academia-academic-services/page/Unified_Time_Table_2025_batch_2",
            f"{self.BASE_URL}/srm_university/academia-academic-services/page/My_Time_Table",
        ]

        for u in known_urls:

            if u not in candidates:

                candidates.append(u)



        # 3. Calendar based candidates

        from datetime import datetime

        now = datetime.now()

        year = now.year

        month = now.month

        if 1 <= month <= 6:

            cal = [

                f"{self.BASE_URL}/srm_university/academia-academic-services/page/My_Time_Table_{year - 1}_{str(year)[-2:]}",

                f"{self.BASE_URL}/srm_university/academia-academic-services/page/My_Time_Table_{year - 2}_{str(year - 1)[-2:]}"

            ]

        else:

            cal = [

                f"{self.BASE_URL}/srm_university/academia-academic-services/page/My_Time_Table_{year}_{str(year + 1)[-2:]}",

                f"{self.BASE_URL}/srm_university/academia-academic-services/page/My_Time_Table_{year - 1}_{str(year)[-2:]}"

            ]

        for u in cal:

            if u not in candidates:

                candidates.append(u)



        return candidates



    def get_timetable(self) -> Optional[Dict[str, Any]]:

        """Fetch and parse timetable data using dynamic semester URL resolution"""

        print("[BACKEND DATA] Fetching timetable data...")

        

        candidates = self._get_timetable_candidates()

        urls_to_try = []

        if self._resolved_timetable_url:

            urls_to_try.append(self._resolved_timetable_url)

        for u in candidates:

            if u not in urls_to_try:

                urls_to_try.append(u)

        

        fallback_parsed = None

        for url in urls_to_try:

            try:

                response = self.session.get(url, headers=self._get_page_headers())

                if response.status_code == 200:

                    text = response.text

                    if ('error-message-text' in text and 'Page not found' in text) or 'Page is not accessible' in text:

                        continue

                    

                    parsed = parse_timetable(text)

                    if parsed and "error" not in parsed:

                        courses = parsed.get('courses', [])

                        student_info = parsed.get('student_info', {})

                        # Must have courses to be the active timetable

                        if len(courses) > 0:

                            self._resolved_timetable_url = url

                            print(f"✓ [BACKEND DATA] Active timetable retrieved from {url.split('/')[-1]} with {len(courses)} courses (Status: {response.status_code})\n")

                            return parsed

                        elif fallback_parsed is None and student_info.get('name'):

                            fallback_parsed = parsed

            except Exception as e:

                print(f"⚠ [BACKEND DATA] Failed to fetch timetable candidate {url.split('/')[-1]}: {str(e)}")

                continue

                

        if fallback_parsed:

            print("⚠ [BACKEND DATA] Returning fallback timetable without courses\n")

            return fallback_parsed



        print("✗ [BACKEND DATA] Failed to fetch timetable from any candidate endpoint\n")

        return None

        

    def get_day_order(self) -> Optional[int]:

        """Fetch current day order from welcome page"""

        print("Fetching day order...")

        

        url = f'{self.BASE_URL}/srm_university/academia-academic-services/page/WELCOME'

        

        try:

            response = self.session.get(url, headers=self._get_page_headers())

            response.raise_for_status()

            

            # Search for day order pattern in the response

            match = re.search(r'Day Order:\s*(\d+)', response.text)

            

            if match:

                day_order = int(match.group(1))

                print(f"✓ Day Order retrieved: {day_order}\n")

                return day_order

            else:

                print("✗ Could not find day order in response\n")

                return None

                

        except Exception as e:

            print(f"✗ Failed to fetch day order: {str(e)}\n")

            return None

    

#for loading and saving session data

    def get_session_data(self) -> dict:

        """Export session data for reuse"""

        return {

            'cookies': self.session.cookies.get_dict(),

            'identifier': self.identifier,

            'digest': self.digest,

            'csrf_token': self.csrf_token,

            'resolved_timetable_url': self._resolved_timetable_url

        }



    def load_session_data(self, session_data: dict) -> None:

        """Load previously saved session data"""

        if session_data.get('cookies'):

            self.session.cookies.update(session_data['cookies'])

        self.identifier = session_data.get('identifier')

        self.digest = session_data.get('digest')

        self.csrf_token = session_data.get('csrf_token')

        self._resolved_timetable_url = session_data.get('resolved_timetable_url')





# Testing logic main function

def main():

    """Main execution function"""

    

    # Configuration

    EMAIL = "as0711@srmist.edu.in"

    PASSWORD = "pass"

    

    # Create client instance

    client = AcademiaClient(EMAIL, PASSWORD)

    

    try:

        # Step 1: Lookup user

        if not client.lookup_user():

            return

        print("succesfully completed lookup")

        

        # Step 2: Login

        result_login = client.login()

        if not result_login["success"]:

            print("error msg:",result_login["message"])

            return

        

        # Step 3a: Fetch day order

        day_order = client.get_day_order()



        # Step 3b: Fetch and parse attendance

        attendance_data = client.get_attendance()

        if attendance_data and day_order is not None:

            attendance_data['day_order'] = day_order

            

        if attendance_data:

            print("\n" + "="*50)

            print("✓ Attendance data retrieved successfully")

            print("="*50)

        

        # Step 4: Fetch and parse timetable

        timetable_data = client.get_timetable()

        if timetable_data:

            print("\n" + "="*50)

            print("✓ Timetable data retrieved successfully")

            print("="*50)

    

    finally:

        # Always logout at the end

        client.logout()





if __name__ == "__main__":

    main()
import requests
import json
import re
from typing import Dict, Optional, Any, List
from bs4 import BeautifulSoup

# importing parser utility functions
from utils.parser import *


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
        self._setup_session()
    
    def _setup_session(self):
        """Set up session with base cookies and fresh tokens (Hybrid Approach)"""
        import time
        import random
        
        # Enhanced browser headers
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36',
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
        
        # Use working cookies as base template with updated timestamps
        current_time = int(time.time())
        
        initial_cookies = {
            # Static cookies that worked before
            '_uetvid': 'b3000840e89c11ef8036e75565fa990c',
            'zalb_74c3a1eecc': '62cd2f9337f58b07cdaa2f90f0ac1087',
            'zccpn': 'da3eb9d9-c3f1-418c-a4a7-30a74a3aec85',
            '_zcsr_tmp': 'da3eb9d9-c3f1-418c-a4a7-30a74a3aec85',
            'cli_rgn': 'IN',
            'zalb_f0e8db9d3d': '983d6a65b2f29022f18db52385bfc639',
            
            # Dynamic cookies with updated timestamps
            '_ga': f'GA1.3.390342211.{current_time - 86400}',  # Yesterday
            '_gid': f'GA1.3.{random.randint(1000000000, 9999999999)}.{current_time}',
            '_ga_S234BK01XY': f'GS1.3.{current_time}.1.0.{current_time}.60.0.0',
            '_ga_QNCRQG0GFE': f'GS2.1.s{current_time}$o13$g1$t{current_time + 271}$j58$l0$h0',
            '_ga_HQWPLLNMKY': f'GS2.3.s{current_time}$o23$g0$t{current_time}$j60$l0$h0',
        }
        
        self.session.cookies.update(initial_cookies)
        
        # Add slight delay to simulate human behavior
        time.sleep(random.uniform(0.5, 1.5))
        
        # Visit login page to get fresh CSRF token and session cookies
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
            response.raise_for_status()
            
            # Extract CSRF token from cookies
            if 'iamcsr' in self.session.cookies:
                self.csrf_token = self.session.cookies.get('iamcsr')
                print(f"✓ CSRF Token obtained: {self.csrf_token[:50]}...")
            else:
                print("⚠ Warning: No CSRF token found in cookies")
            
            # Extract JSESSIONID if present
            if 'JSESSIONID' in self.session.cookies:
                print(f"✓ Session ID obtained: {self.session.cookies.get('JSESSIONID')[:20]}...")
                
        except Exception as e:
            print(f"⚠ Warning: Failed to initialize session: {str(e)}")
    
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
        
        url = f'{self.BASE_URL}/accounts/p/40-10002227248/signin/v2/lookup/{self.email}'
        
        import time
        cli_time = str(int(time.time() * 1000))
        
        data = {
            'mode': 'primary',
            'cli_time': cli_time,
            'orgtype': '40',
            'service_language': 'en',
            'serviceurl': f'{self.BASE_URL}/portal/academia-academic-services/redirectFromLogin'
        }
        
        try:
            response = self.session.post(url, headers=self._get_common_headers(), data=data)
            response.raise_for_status()
            
            lookup_data = response.json()
            self.identifier = lookup_data.get('lookup', {}).get('identifier')
            self.digest = lookup_data.get('lookup', {}).get('digest')
            
            if self.identifier and self.digest:
                print(f"✓ Lookup successful (identifier: {self.identifier})")
                print(f"✓ Digest obtained: {self.digest[:50]}...\n")
                return True
            else:
                print("✗ Failed to get user identifier or digest")
                print(f"Response: {json.dumps(lookup_data, indent=2)}\n")
                return False
                
        except Exception as e:
            print(f"✗ Lookup failed: {str(e)}\n")
            return False
    
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
    
    def login(self) -> bool:
        """Login with password using digest from lookup"""
        if not self.identifier or not self.digest:
            print("✗ No identifier/digest found. Run lookup_user() first.\n")
            return False
        
        print("Step 2: Logging in...")
        
        url = f'{self.BASE_URL}/accounts/p/40-10002227248/signin/v2/primary/{self.identifier}/password'
        
        import time
        cli_time = str(int(time.time() * 1000))
        
        params = {
            'digest': self.digest,
            'cli_time': cli_time,
            'orgtype': '40',
            'service_language': 'en',
            'serviceurl': f'{self.BASE_URL}/portal/academia-academic-services/redirectFromLogin'
        }
        
        # Create the password auth payload
        body = json.dumps({
            "passwordauth": {
                "password": self.password
            }
        })
        
        # Update headers for JSON content
        headers = self._get_common_headers()
        headers['Content-Type'] = 'application/json;charset=UTF-8'
        
        try:
            response = self.session.post(url, headers=headers, params=params, data=body)
            response.raise_for_status()
            
            if response.status_code == 200:
                login_data = response.json()
                passwordauth = login_data.get('passwordauth', {})
                code = passwordauth.get('code')
                
                # Handle successful login
                if code == 'SIGIN_SUCCESS':
                    print("✓ Login successful!\n")
                    return True
                
                # Handle post-announcement redirection (active sessions)
                elif code == 'POST_ANNOUCEMENT_REDIRECTION':
                    print("✓ Login successful - handling active sessions...")
                    redirect_uri = passwordauth.get('redirect_uri')
                    
                    if redirect_uri and 'sessions-reminder' in redirect_uri:
                        # Close active sessions with proper flow
                        service_url = params.get('serviceurl')
                        service_language = params.get('service_language')
                        orgtype = params.get('orgtype')
                        
                        if self._close_active_sessions(redirect_uri, service_url, service_language, orgtype):
                            # After closing sessions and confirming, visit the final redirect
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
                                final_response = self.session.get(service_url, headers=redirect_headers)
                                
                                if final_response.status_code == 200:
                                    print("✓ Login flow completed successfully!\n")
                                    return True
                                else:
                                    print(f"⚠ Warning: Unusual status code: {final_response.status_code}")
                                    # Still might be logged in, so return True
                                    return True
                            except Exception as e:
                                print(f"⚠ Warning: Final redirect failed: {str(e)}")
                                # Session might still be valid, return True
                                return True
                        else:
                            print("✗ Failed to close active sessions\n")
                            return False
                    else:
                        print(f"✓ Login successful with redirect: {redirect_uri}\n")
                        return True
                
                # Handle errors
                elif 'error' in login_data:
                    error_msg = login_data.get('error', {}).get('message', 'Unknown error')
                    print(f"✗ Login failed: {error_msg}\n")
                    return False
                
                else:
                    print(f"⚠ Unexpected response code: {code}")
                    print(f"Response: {json.dumps(login_data, indent=2)}\n")
                    return False
            else:
                print(f"✗ Login failed with status code: {response.status_code}\n")
                return False
                
        except Exception as e:
            print(f"✗ Login failed: {str(e)}\n")
            return False
    
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
                self.session.cookies.clear()
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
    
    def get_attendance(self) -> Optional[Dict[str, Any]]:
        """Fetch and parse attendance data"""
        print("Fetching attendance data...")
        
        url = f'{self.BASE_URL}/srm_university/academia-academic-services/page/My_Attendance'
        
        try:
            response = self.session.get(url, headers=self._get_page_headers())
            response.raise_for_status()
            
            print(f"✓ Attendance data retrieved (Status: {response.status_code})\n")
            return parse_attendance(response.text)
                
        except Exception as e:
            print(f"✗ Failed to fetch attendance: {str(e)}\n")
            return None
    
    def get_timetable(self) -> Optional[Dict[str, Any]]:
        """Fetch and parse timetable data"""
        print("Fetching timetable data...")
        
        url = f'{self.BASE_URL}/srm_university/academia-academic-services/page/My_Time_Table_2023_24'
        
        try:
            response = self.session.get(url, headers=self._get_page_headers())
            response.raise_for_status()
            
            print(f"✓ Timetable data retrieved (Status: {response.status_code})\n")
            return parse_timetable(response.text)
                
        except Exception as e:
            print(f"✗ Failed to fetch timetable: {str(e)}\n")
            return None
        
    def get_day_order(self) -> Optional[int]:
        """Fetch current day order from welcome page"""
        print("Fetching day order...")
        
        url = f'{self.BASE_URL}/srm_university/academia-academic-services/page/WELCOME'
        
        try:
            response = self.session.get(url, headers=self._get_page_headers())
            response.raise_for_status()
            
            # Search for day order pattern in the response
            match = re.search(r'Day\\x20Order\\x3A(\d+)', response.text)
            
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


# Testing logic main function
def main():
    """Main execution function"""
    
    # Configuration
    EMAIL = "your_email@srmist.edu.in"
    PASSWORD = "password123"
    
    # Create client instance
    client = AcademiaClient(EMAIL, PASSWORD)
    
    try:
        # Step 1: Lookup user
        if not client.lookup_user():
            return
        
        # Step 2: Login
        if not client.login():
            return
        
        # Step 3a: Fetch day order
        day_order = client.get_day_order()

        # Step 3b: Fetch and parse attendance
        attendance_data = client.get_attendance()
        if attendance_data and day_order is not None:
            attendance_data['day_order'] = day_order
            
        if attendance_data:
            print("\n" + "="*50)
            print("COMPLETE STUDENT DATA")
            print("="*50)
            print(json.dumps(attendance_data, indent=2))
        
        # Step 4: Fetch and parse timetable
        timetable_data = client.get_timetable()
        if timetable_data:
            print("\n" + "="*50)
            print("TIMETABLE DATA")
            print("="*50)
            print(json.dumps(timetable_data, indent=2))
    
    finally:
        # Always logout at the end
        client.logout()


if __name__ == "__main__":
    main()
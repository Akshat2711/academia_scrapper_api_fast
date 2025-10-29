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
        self._setup_session()
    
    def _setup_session(self):
        """Set up session with user agent and initial cookies"""
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        initial_cookies = {
            '_uetvid': 'b3000840e89c11ef8036e75565fa990c',
            '_ga_S234BK01XY': 'GS1.3.1745294863.2.0.1745294863.60.0.0',
            '_ga_QNCRQG0GFE': 'GS2.1.s1756038219$o13$g1$t1756038490$j58$l0$h0',
            '_ga': 'GA1.3.390342211.1722929679',
            '_gid': 'GA1.3.2113967629.1759126016',
            'zalb_74c3a1eecc': '62cd2f9337f58b07cdaa2f90f0ac1087',
            'zccpn': 'da3eb9d9-c3f1-418c-a4a7-30a74a3aec85',
            '_zcsr_tmp': 'da3eb9d9-c3f1-418c-a4a7-30a74a3aec85',
            'JSESSIONID': '7A17742FC60777CB72F1A41EE40E757F',
            'cli_rgn': 'IN',
            'zalb_f0e8db9d3d': '983d6a65b2f29022f18db52385bfc639',
            'iamcsr': '391788bd-2546-4716-8132-fe456c9b066a',
            'stk': 'c799c6752fa5adf5621357e8bbc0b925',
            '_ga_HQWPLLNMKY': 'GS2.3.s1759165956$o23$g0$t1759165956$j60$l0$h0'
        }
        self.session.cookies.update(initial_cookies)
    
    def _get_common_headers(self) -> Dict[str, str]:
        """Get common headers for requests"""
        return {
            'Accept': '*/*',
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'Accept-Language': 'en-US,en;q=0.9,en-IN;q=0.8',
            'Origin': f'{self.BASE_URL}',
            'Referer': f'{self.BASE_URL}/accounts/p/10002227248/signin',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
            'X-ZCSRF-TOKEN': 'iamcsrcoo=391788bd-2546-4716-8132-fe456c9b066a',
            'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8'
        }
    
    def lookup_user(self) -> bool:
        """Perform user lookup to get identifier and digest"""
        print("Step 1: Performing user lookup...")
        
        url = f'{self.BASE_URL}/accounts/p/40-10002227248/signin/v2/lookup/{self.email}'
        data = {
            'mode': 'primary',
            'cli_time': '1759165956409',
            'orgtype': '40',
            'servicename': 'ZohoCreator',
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
                print(f"✓ Lookup successful\n")
                return True
            else:
                print("✗ Failed to get user identifier or digest\n")
                return False
                
        except Exception as e:
            print(f"✗ Lookup failed: {str(e)}\n")
            return False
    
    def login(self) -> bool:
        """Login with password using digest from lookup"""
        if not self.identifier or not self.digest:
            print("✗ No identifier/digest found. Run lookup_user() first.\n")
            return False
        
        print("Step 2: Logging in...")
        
        url = f'{self.BASE_URL}/accounts/p/40-10002227248/signin/v2/primary/{self.identifier}/password'
        params = {
            'digest': self.digest,
            'cli_time': '1759165956409',
            'orgtype': '40',
            'servicename': 'ZohoCreator',
            'service_language': 'en',
            'serviceurl': f'{self.BASE_URL}/portal/academia-academic-services/redirectFromLogin'
        }
        
        body = json.dumps({
            "passwordauth": {
                "password": self.password
            }
        })
        
        try:
            response = self.session.post(url, headers=self._get_common_headers(), params=params, data=body)
            response.raise_for_status()
            
            login_data = response.json()
            
            if login_data.get('passwordauth', {}).get('code') == 'SIGIN_SUCCESS':
                print("✓ Login successful!\n")
                return True
            else:
                print("✗ Login failed!\n")
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
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
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
            # Logout typically returns 200 or redirects
            if response.status_code in [200, 302, 303]:
                print("✓ Logout successful!\n")
                # Clear session cookies
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
import requests
import sys
import json
from datetime import datetime

class HRMSAPITester:
    def __init__(self, base_url="https://onboard-id-gen.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []

    def log_test(self, name, success, details=""):
        """Log test result"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
        
        result = {
            "test": name,
            "status": "PASS" if success else "FAIL",
            "details": details
        }
        self.test_results.append(result)
        
        status_icon = "✅" if success else "❌"
        print(f"{status_icon} {name}: {details}")
        return success

    def test_api_health(self):
        """Test if API is running"""
        try:
            response = requests.get(f"{self.api_url}/", timeout=10)
            success = response.status_code == 200
            details = f"Status: {response.status_code}, Response: {response.json()}"
            return self.log_test("API Health Check", success, details)
        except Exception as e:
            return self.log_test("API Health Check", False, f"Error: {str(e)}")

    def test_company_settings(self):
        """Test company settings endpoint"""
        try:
            response = requests.get(f"{self.api_url}/company/settings", timeout=10)
            success = response.status_code == 200
            if success:
                data = response.json()
                company_name = data.get('company_name', '')
                details = f"Company: {company_name}"
            else:
                details = f"Status: {response.status_code}, Error: {response.text}"
            return self.log_test("Company Settings", success, details)
        except Exception as e:
            return self.log_test("Company Settings", False, f"Error: {str(e)}")

    def test_login_id_preview(self):
        """Test Login ID preview generation"""
        try:
            params = {
                'first_name': 'Test',
                'last_name': 'User',
                'year_of_joining': 2025
            }
            response = requests.post(f"{self.api_url}/auth/preview-login-id", params=params, timeout=10)
            success = response.status_code == 200
            if success:
                data = response.json()
                login_id = data.get('login_id', '')
                # Validate format: CC+FN+LN+YYYY+SSSS
                expected_pattern = "ODTEUS2025"  # OD (Odoo) + TE (Test) + US (User) + 2025
                format_valid = login_id.startswith(expected_pattern)
                details = f"Generated: {login_id}, Format Valid: {format_valid}"
            else:
                details = f"Status: {response.status_code}, Error: {response.text}"
            return self.log_test("Login ID Preview", success and format_valid if success else success, details)
        except Exception as e:
            return self.log_test("Login ID Preview", False, f"Error: {str(e)}")

    def test_employee_signup(self):
        """Test employee signup with auto-generated Login ID"""
        try:
            # Use unique email to avoid conflicts
            timestamp = datetime.now().strftime("%H%M%S")
            signup_data = {
                'first_name': 'Test',
                'last_name': 'Employee',
                'email': f'test.employee.{timestamp}@example.com',
                'password': 'TestPass123!',
                'year_of_joining': 2025
            }
            
            response = requests.post(f"{self.api_url}/auth/signup", json=signup_data, timeout=10)
            success = response.status_code == 200
            if success:
                data = response.json()
                self.token = data.get('token')
                employee = data.get('employee', {})
                login_id = employee.get('login_id', '')
                # Validate Login ID format
                expected_start = "ODTEEM2025"  # OD + TE + EM + 2025
                format_valid = login_id.startswith(expected_start)
                details = f"Created employee with Login ID: {login_id}, Token received: {bool(self.token)}, Format Valid: {format_valid}"
            else:
                details = f"Status: {response.status_code}, Error: {response.text}"
            return self.log_test("Employee Signup", success and format_valid if success else success, details)
        except Exception as e:
            return self.log_test("Employee Signup", False, f"Error: {str(e)}")

    def test_employee_login(self):
        """Test employee login using Login ID"""
        if not hasattr(self, 'created_login_id'):
            # First create an employee to test login
            timestamp = datetime.now().strftime("%H%M%S")
            signup_data = {
                'first_name': 'Login',
                'last_name': 'Test',
                'email': f'login.test.{timestamp}@example.com',
                'password': 'LoginTest123!',
                'year_of_joining': 2025
            }
            
            try:
                signup_response = requests.post(f"{self.api_url}/auth/signup", json=signup_data, timeout=10)
                if signup_response.status_code == 200:
                    signup_data_resp = signup_response.json()
                    self.created_login_id = signup_data_resp['employee']['login_id']
                    self.created_password = 'LoginTest123!'
                else:
                    return self.log_test("Employee Login", False, "Failed to create test employee for login")
            except Exception as e:
                return self.log_test("Employee Login", False, f"Setup error: {str(e)}")

        try:
            login_data = {
                'login_id': self.created_login_id,
                'password': self.created_password
            }
            
            response = requests.post(f"{self.api_url}/auth/login", json=login_data, timeout=10)
            success = response.status_code == 200
            if success:
                data = response.json()
                token = data.get('token')
                employee = data.get('employee', {})
                details = f"Login successful with ID: {self.created_login_id}, Token received: {bool(token)}"
                self.token = token  # Update token for subsequent tests
            else:
                details = f"Status: {response.status_code}, Error: {response.text}"
            return self.log_test("Employee Login", success, details)
        except Exception as e:
            return self.log_test("Employee Login", False, f"Error: {str(e)}")

    def test_authenticated_endpoints(self):
        """Test endpoints that require authentication"""
        if not self.token:
            return self.log_test("Authenticated Endpoints", False, "No token available")

        headers = {'Authorization': f'Bearer {self.token}'}
        
        # Test /auth/me
        try:
            response = requests.get(f"{self.api_url}/auth/me", headers=headers, timeout=10)
            me_success = response.status_code == 200
            me_details = f"Current user endpoint: {response.status_code}"
            if me_success:
                user_data = response.json()
                me_details += f", User: {user_data.get('first_name')} {user_data.get('last_name')}"
        except Exception as e:
            me_success = False
            me_details = f"Error: {str(e)}"

        # Test /employees
        try:
            response = requests.get(f"{self.api_url}/employees", headers=headers, timeout=10)
            emp_success = response.status_code == 200
            emp_details = f"Employees list endpoint: {response.status_code}"
            if emp_success:
                employees = response.json()
                emp_details += f", Count: {len(employees)}"
        except Exception as e:
            emp_success = False
            emp_details = f"Error: {str(e)}"

        overall_success = me_success and emp_success
        details = f"{me_details} | {emp_details}"
        return self.log_test("Authenticated Endpoints", overall_success, details)

    def test_login_id_format_validation(self):
        """Test Login ID format validation"""
        try:
            # Test with different names to verify format
            test_cases = [
                {'first_name': 'John', 'last_name': 'Doe', 'year': 2022, 'expected_start': 'ODJODO2022'},
                {'first_name': 'Jane', 'last_name': 'Smith', 'year': 2022, 'expected_start': 'ODJASM2022'},
                {'first_name': 'Bob', 'last_name': 'Wilson', 'year': 2025, 'expected_start': 'ODBOWI2025'}
            ]
            
            all_valid = True
            details_list = []
            
            for case in test_cases:
                params = {
                    'first_name': case['first_name'],
                    'last_name': case['last_name'],
                    'year_of_joining': case['year']
                }
                response = requests.post(f"{self.api_url}/auth/preview-login-id", params=params, timeout=10)
                if response.status_code == 200:
                    login_id = response.json().get('login_id', '')
                    valid = login_id.startswith(case['expected_start'])
                    details_list.append(f"{case['first_name']} {case['last_name']}: {login_id} ({'✓' if valid else '✗'})")
                    if not valid:
                        all_valid = False
                else:
                    all_valid = False
                    details_list.append(f"{case['first_name']} {case['last_name']}: API Error")
            
            details = " | ".join(details_list)
            return self.log_test("Login ID Format Validation", all_valid, details)
        except Exception as e:
            return self.log_test("Login ID Format Validation", False, f"Error: {str(e)}")

    def test_duplicate_email_prevention(self):
        """Test duplicate email prevention"""
        try:
            # First signup
            timestamp = datetime.now().strftime("%H%M%S")
            email = f'duplicate.test.{timestamp}@example.com'
            signup_data = {
                'first_name': 'Duplicate',
                'last_name': 'Test',
                'email': email,
                'password': 'DuplicateTest123!',
                'year_of_joining': 2025
            }
            
            response1 = requests.post(f"{self.api_url}/auth/signup", json=signup_data, timeout=10)
            first_success = response1.status_code == 200
            
            # Second signup with same email
            response2 = requests.post(f"{self.api_url}/auth/signup", json=signup_data, timeout=10)
            second_blocked = response2.status_code == 400
            
            success = first_success and second_blocked
            details = f"First signup: {response1.status_code}, Second signup: {response2.status_code} (should be 400)"
            return self.log_test("Duplicate Email Prevention", success, details)
        except Exception as e:
            return self.log_test("Duplicate Email Prevention", False, f"Error: {str(e)}")

    def run_all_tests(self):
        """Run all tests"""
        print("🚀 Starting HRMS API Testing...")
        print("=" * 60)
        
        # Basic connectivity
        self.test_api_health()
        
        # Company setup
        self.test_company_settings()
        
        # Login ID functionality
        self.test_login_id_preview()
        self.test_login_id_format_validation()
        
        # Authentication flow
        self.test_employee_signup()
        self.test_employee_login()
        self.test_authenticated_endpoints()
        
        # Security
        self.test_duplicate_email_prevention()
        
        # Summary
        print("=" * 60)
        print(f"📊 Test Summary: {self.tests_passed}/{self.tests_run} tests passed")
        
        if self.tests_passed == self.tests_run:
            print("🎉 All tests passed!")
            return 0
        else:
            print("⚠️  Some tests failed!")
            return 1

def main():
    tester = HRMSAPITester()
    return tester.run_all_tests()

if __name__ == "__main__":
    sys.exit(main())
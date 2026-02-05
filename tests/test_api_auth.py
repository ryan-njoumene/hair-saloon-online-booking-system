import unittest
import requests

class TestJWTAPI(unittest.TestCase):
    """
    Test case for the JWT-protected API endpoints.

    This class tests the endpoints of the API that require JWT authentication.
    It performs the following tests:
    - Access to protected endpoints with a valid JWT token.
    - Access to protected endpoints with an invalid token.
    - Access to protected endpoints with no token.
    """
    BASE_URL = "http://127.0.0.1:5008/api"  # Base URL for the API

    @classmethod
    def setUpClass(cls):
        """
        Set up the test environment by logging in and obtaining the JWT token.

        This method runs once before all tests to authenticate and store the
        JWT token, which is used in the Authorization header for subsequent tests.
        """
        # Send a POST request to the login endpoint with valid credentials
        response = requests.post(f"{cls.BASE_URL}/login", json={
            "user_name": "andrew",
            "password": "password"
        })
        
        # Raise an exception if login fails
        response.raise_for_status()
        
        # Retrieve and store the access token from the response
        cls.token = response.json().get("access_token")
        cls.headers = {"Authorization": f"Bearer {cls.token}"}  # Set up headers for authorization

    def test_protected_secret_access(self):
        """
        Test accessing the protected 'secret' endpoint with a valid JWT token.

        This test verifies that the request is successful and the correct message is returned.
        """
        # Send a GET request to the protected 'secret' endpoint with the valid JWT token
        response = requests.get(f"{self.BASE_URL}/secret", headers=self.headers)
        
        # Assert that the status code is 200 (OK)
        self.assertEqual(response.status_code, 200)
        
        # Assert that the response contains the expected 'Welcome' message
        self.assertIn("Welcome", response.json().get("message", ""))

    def test_invalid_token_access(self):
        """
        Test accessing the protected 'secret' endpoint with an invalid JWT token.

        This test verifies that the API correctly responds with a 422 error for a malformed token.
        """
        # Set up headers with an invalid token
        bad_headers = {"Authorization": "Bearer invalid.token.value"}
        
        # Send a GET request to the protected 'secret' endpoint
        response = requests.get(f"{self.BASE_URL}/secret", headers=bad_headers)
        
        # Assert that the status code is 422 (Unprocessable Entity) for invalid token
        self.assertEqual(response.status_code, 422)

    def test_missing_token_access(self):
        """
        Test accessing the protected 'secret' endpoint with no token.

        This test verifies that the API responds with a 401 error when no token is provided.
        """
        # Send a GET request to the protected 'secret' endpoint without any authorization headers
        response = requests.get(f"{self.BASE_URL}/secret")
        
        # Assert that the status code is 401 (Unauthorized) when no token is provided
        self.assertEqual(response.status_code, 401)


if __name__ == '__main__':
    unittest.main()

import unittest
from unittest.mock import patch, MagicMock
from app import app, bcrypt  # Importing from your main Flask app module

class FlaskAppTestCase(unittest.TestCase):

    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

    @patch('app.mysql.connector.connect')
    def test_successful_signup(self, mock_connect):
        # Mock database connection and cursor
        mock_cursor = MagicMock()
        mock_connect.return_value.cursor.return_value = mock_cursor
        mock_cursor.execute.return_value = None
        mock_cursor.fetchone.return_value = None
        mock_connect.return_value.commit.return_value = True

        response = self.app.post('/signup', data={
            'username': 'newuser',
            'password': 'test123',
            'email': 'newuser@example.com'
        })

        self.assertEqual(response.status_code, 200)
        mock_cursor.execute.assert_called()
        mock_connect.return_value.commit.assert_called()

    @patch('app.mysql.connector.connect')
    def test_signup_existing_user(self, mock_connect):
        mock_cursor = MagicMock()
        mock_connect.return_value.cursor.return_value = mock_cursor
        mock_cursor.execute.return_value = None
        mock_cursor.fetchone.return_value = {'username': 'existinguser', 'password': 'existingpass', 'email': 'existing@example.com'}
        
        response = self.app.post('/signup', data={
            'username': 'existinguser',
            'password': 'existingpass',
            'email': 'existing@example.com'
        })

        self.assertEqual(response.status_code, 409)
        mock_cursor.execute.assert_called()
        mock_connect.return_value.commit.assert_not_called()

    @patch('app.mysql.connector.connect')
    def test_successful_login(self, mock_connect):
        mock_cursor = MagicMock()
        mock_connect.return_value.cursor.return_value = mock_cursor
        hashed_pw = bcrypt.generate_password_hash('test123').decode('utf-8')
        mock_cursor.execute.return_value = None
        mock_cursor.fetchone.return_value = {'username': 'testuser', 'password': hashed_pw}
        
        response = self.app.post('/login', data={
            'username': 'testuser',
            'password': 'test123'
        })

        self.assertEqual(response.status_code, 200)
        mock_cursor.execute.assert_called()

    @patch('app.mysql.connector.connect')
    def test_failed_login(self, mock_connect):
        mock_cursor = MagicMock()
        mock_connect.return_value.cursor.return_value = mock_cursor
        mock_cursor.execute.return_value = None
        mock_cursor.fetchone.return_value = None
        
        response = self.app.post('/login', data={
            'username': 'nonexistentuser',
            'password': 'wrongpass'
        })

        self.assertEqual(response.status_code, 401)
        mock_cursor.execute.assert_called()

if __name__ == '__main__':
    unittest.main()

import unittest
from unittest.mock import patch, MagicMock
from busy_agent import app

class TestApp(unittest.TestCase):
    def setUp(self):
        app.testing = True
        self.client = app.test_client()

    def test_index_route(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'<title>Busy Agent - Chat</title>', response.data)

    @patch('busy_agent.assistant')
    def test_chat_route_success(self, mock_assistant):
        mock_assistant.chat.return_value = "Hello! I am your agent."
        
        response = self.client.post('/chat', 
                                   json={'message': 'Hi'},
                                   content_type='application/json')
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['response'], "Hello! I am your agent.")
        mock_assistant.chat.assert_called_once_with('Hi', system_message=None)

    @patch('busy_agent.assistant')
    def test_chat_route_with_system_message(self, mock_assistant):
        mock_assistant.chat.return_value = "Hello! I am your agent."
        
        response = self.client.post('/chat', 
                                   json={'message': 'Hi', 'system_message': 'Be helpful'},
                                   content_type='application/json')
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['response'], "Hello! I am your agent.")
        mock_assistant.chat.assert_called_once_with('Hi', system_message='Be helpful')

    def test_chat_route_no_message(self):
        response = self.client.post('/chat', 
                                   json={},
                                   content_type='application/json')
        
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertEqual(data['error'], "No message provided")

    @patch('busy_agent.assistant')
    def test_chat_route_error(self, mock_assistant):
        mock_assistant.chat.side_effect = Exception("API Error")
        
        response = self.client.post('/chat', 
                                   json={'message': 'Hi'},
                                   content_type='application/json')
        
        self.assertEqual(response.status_code, 500)
        data = response.get_json()
        self.assertEqual(data['error'], "API Error")

if __name__ == '__main__':
    unittest.main()

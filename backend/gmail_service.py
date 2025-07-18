"""
Email service using SendGrid API (much easier than Gmail)
Just need a SendGrid API key - get free one at https://sendgrid.com
"""
import os
import logging
from typing import Dict, Any
import requests

# Load environment variables from .env file
def load_env_file():
    try:
        with open('.env', 'r') as f:
            for line in f:
                if '=' in line and not line.strip().startswith('#'):
                    key, value = line.strip().split('=', 1)
                    os.environ[key] = value
    except Exception:
        pass  # If .env doesn't exist, that's okay

load_env_file()

logger = logging.getLogger(__name__)

class EmailService:
    def __init__(self):
        self.sendgrid_api_key = os.getenv('SENDGRID_API_KEY')
        self.from_email = os.getenv('FROM_EMAIL', 'noreply@yourapp.com')
        self.sendgrid_url = "https://api.sendgrid.com/v3/mail/send"
        
    async def send_email(self, to_email: str, subject: str, content: str) -> Dict[str, Any]:
        """Send email using SendGrid API"""
        try:
            if not self.sendgrid_api_key:
                return {
                    "success": False,
                    "error": "SendGrid API key not configured. Get free key at https://sendgrid.com and set SENDGRID_API_KEY environment variable."
                }
            
            # SendGrid API payload
            payload = {
                "personalizations": [
                    {
                        "to": [{"email": to_email}],
                        "subject": subject
                    }
                ],
                "from": {"email": self.from_email},
                "content": [
                    {
                        "type": "text/plain",
                        "value": content
                    }
                ]
            }
            
            headers = {
                "Authorization": f"Bearer {self.sendgrid_api_key}",
                "Content-Type": "application/json"
            }
            
            # Send the email
            response = requests.post(self.sendgrid_url, json=payload, headers=headers)
            
            if response.status_code == 202:  # SendGrid success code
                logger.info(f"Email sent successfully to {to_email}")
                return {
                    "success": True,
                    "message": f"Email sent successfully to {to_email}",
                    "to_email": to_email,
                    "subject": subject,
                    "message_id": response.headers.get('X-Message-Id', 'unknown')
                }
            else:
                logger.error(f"SendGrid API error: {response.status_code} - {response.text}")
                return {
                    "success": False,
                    "error": f"SendGrid API error: {response.status_code} - {response.text}"
                }
            
        except Exception as e:
            logger.error(f"Error sending email: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to send email: {str(e)}"
            }
    
# Global instance
email_service = EmailService()
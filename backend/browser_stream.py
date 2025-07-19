"""
Browser Automation Streaming Service
Implements Phase 1 of day3.md: Screenshot streaming with Docker containers
"""

import asyncio
import base64
import json
import logging
import subprocess
import time
import uuid
from typing import Dict, Any, Optional, List
from playwright.async_api import async_playwright, Browser, Page, BrowserContext
import docker
from docker.models.containers import Container

logger = logging.getLogger(__name__)

class BrowserStreamSession:
    """Manages a single browser automation session with streaming"""
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.container: Optional[Container] = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.playwright_instance = None
        self.is_active = False
        self.created_at = time.time()
        self.last_screenshot = None
        self.websocket_handlers: List[Any] = []
        
    async def start_container(self) -> bool:
        """Start a Docker container with Playwright"""
        try:
            client = docker.from_env()
            
            # Check if Playwright image exists, pull if not
            try:
                client.images.get("mcr.microsoft.com/playwright:latest")
            except docker.errors.ImageNotFound:
                logger.info("Pulling Playwright Docker image...")
                client.images.pull("mcr.microsoft.com/playwright:latest")
            
            # Start container with CDP port exposed
            self.container = client.containers.run(
                "mcr.microsoft.com/playwright:latest",
                name=f"browser-session-{self.session_id}",
                ports={'9222/tcp': None},  # Random host port
                environment={
                    'PLAYWRIGHT_BROWSERS_PATH': '/ms-playwright',
                },
                command="sleep infinity",  # Keep container running
                detach=True,
                remove=True,  # Auto-remove when stopped
                mem_limit="1g",
                cpu_quota=50000,  # 50% CPU limit
            )
            
            # Wait for container to be ready
            await asyncio.sleep(2)
            
            logger.info(f"Started container {self.container.id} for session {self.session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start container for session {self.session_id}: {str(e)}")
            return False
    
    async def start_browser(self) -> bool:
        """Start Playwright browser in the container"""
        try:
            # For simplicity in Phase 1, use local Playwright
            # In production, this would connect to the containerized browser
            self.playwright_instance = await async_playwright().start()
            
            self.browser = await self.playwright_instance.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-gpu',
                    '--remote-debugging-port=9222'
                ]
            )
            
            self.context = await self.browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            )
            
            self.page = await self.context.new_page()
            self.is_active = True
            
            logger.info(f"Browser started for session {self.session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start browser for session {self.session_id}: {str(e)}")
            return False
    
    async def navigate_to(self, url: str) -> Dict[str, Any]:
        """Navigate to a URL and capture screenshot"""
        try:
            if not self.page:
                return {"success": False, "error": "Browser not initialized"}
            
            await self.page.goto(url, wait_until='networkidle', timeout=30000)
            
            # Capture screenshot
            screenshot_data = await self.capture_screenshot()
            
            return {
                "success": True,
                "url": url,
                "title": await self.page.title(),
                "screenshot": screenshot_data
            }
            
        except Exception as e:
            logger.error(f"Navigation error for session {self.session_id}: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def execute_script(self, script: str) -> Dict[str, Any]:
        """Execute JavaScript and capture result + screenshot"""
        try:
            if not self.page:
                return {"success": False, "error": "Browser not initialized"}
            
            # Execute the script
            result = await self.page.evaluate(script)
            
            # Capture screenshot after script execution
            screenshot_data = await self.capture_screenshot()
            
            # Broadcast screenshot to connected websockets
            await self.broadcast_screenshot(screenshot_data)
            
            return {
                "success": True,
                "result": result,
                "screenshot": screenshot_data
            }
            
        except Exception as e:
            logger.error(f"Script execution error for session {self.session_id}: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def capture_screenshot(self) -> str:
        """Capture and return base64 encoded screenshot"""
        try:
            if not self.page:
                return ""
            
            screenshot_bytes = await self.page.screenshot(
                type='png',
                full_page=False
            )
            
            screenshot_b64 = base64.b64encode(screenshot_bytes).decode('utf-8')
            self.last_screenshot = screenshot_b64
            
            return screenshot_b64
            
        except Exception as e:
            logger.error(f"Screenshot capture error for session {self.session_id}: {str(e)}")
            return ""
    
    async def broadcast_screenshot(self, screenshot_data: str):
        """Broadcast screenshot to all connected websockets"""
        if not screenshot_data:
            return
            
        message = {
            "type": "screenshot",
            "session_id": self.session_id,
            "data": screenshot_data,
            "timestamp": time.time()
        }
        
        # Send to all connected websocket handlers
        for handler in self.websocket_handlers:
            try:
                await handler.send_text(json.dumps(message))
            except Exception as e:
                logger.warning(f"Failed to send screenshot to websocket: {str(e)}")
    
    def add_websocket_handler(self, handler):
        """Add a websocket handler for this session"""
        self.websocket_handlers.append(handler)
    
    def remove_websocket_handler(self, handler):
        """Remove a websocket handler"""
        if handler in self.websocket_handlers:
            self.websocket_handlers.remove(handler)
    
    async def cleanup(self):
        """Clean up browser and container resources"""
        try:
            self.is_active = False
            
            # Close browser
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if self.playwright_instance:
                await self.playwright_instance.stop()
            
            # Stop and remove container
            if self.container:
                try:
                    self.container.stop(timeout=5)
                    self.container.remove()
                except Exception as e:
                    logger.warning(f"Error stopping container: {str(e)}")
            
            logger.info(f"Cleaned up session {self.session_id}")
            
        except Exception as e:
            logger.error(f"Cleanup error for session {self.session_id}: {str(e)}")


class BrowserStreamManager:
    """Manages multiple browser automation sessions"""
    
    def __init__(self):
        self.sessions: Dict[str, BrowserStreamSession] = {}
        self.cleanup_task = None
        
    async def start(self):
        """Start the browser stream manager"""
        # Start cleanup task for expired sessions
        self.cleanup_task = asyncio.create_task(self._cleanup_expired_sessions())
        logger.info("Browser stream manager started")
    
    async def stop(self):
        """Stop the browser stream manager"""
        if self.cleanup_task:
            self.cleanup_task.cancel()
        
        # Cleanup all active sessions
        for session in list(self.sessions.values()):
            await session.cleanup()
        
        self.sessions.clear()
        logger.info("Browser stream manager stopped")
    
    async def create_session(self) -> str:
        """Create a new browser automation session"""
        session_id = str(uuid.uuid4())
        session = BrowserStreamSession(session_id)
        
        # Start container and browser
        # container_started = await session.start_container()
        # if not container_started:
        #     raise Exception("Failed to start Docker container")
        
        browser_started = await session.start_browser()
        if not browser_started:
            await session.cleanup()
            raise Exception("Failed to start browser")
        
        self.sessions[session_id] = session
        logger.info(f"Created browser session {session_id}")
        
        return session_id
    
    def get_session(self, session_id: str) -> Optional[BrowserStreamSession]:
        """Get an existing session by ID"""
        return self.sessions.get(session_id)
    
    async def close_session(self, session_id: str):
        """Close and cleanup a specific session"""
        session = self.sessions.get(session_id)
        if session:
            await session.cleanup()
            del self.sessions[session_id]
            logger.info(f"Closed session {session_id}")
    
    async def _cleanup_expired_sessions(self):
        """Background task to cleanup expired sessions"""
        while True:
            try:
                current_time = time.time()
                expired_sessions = []
                
                for session_id, session in self.sessions.items():
                    # Sessions expire after 30 minutes
                    if current_time - session.created_at > 1800:
                        expired_sessions.append(session_id)
                
                for session_id in expired_sessions:
                    await self.close_session(session_id)
                
                await asyncio.sleep(60)  # Check every minute
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup task: {str(e)}")
                await asyncio.sleep(60)

# Global manager instance
browser_manager = BrowserStreamManager()
"""
Browser-Use Integration Service
Generates and executes browser automation scripts using browser-use library
"""

import asyncio
import base64
import json
import logging
import os
import tempfile
import time
import uuid
from typing import Dict, Any, Optional, List
import subprocess
import docker
from pathlib import Path
from marketing_reports import marketing_reports

logger = logging.getLogger(__name__)

class BrowserUseAutomation:
    """Manages browser-use automation scripts and execution"""
    
    def __init__(self):
        try:
            self.docker_client = docker.from_env()
            self.use_docker = True
            logger.info("Docker client initialized successfully")
        except Exception as e:
            logger.warning(f"Docker not available: {str(e)}. Running in local mode.")
            self.docker_client = None
            self.use_docker = False
        
        self.automation_templates = {
            "competitor_pricing": {
                "description": "Monitor competitor pricing and features",
                "template": r"""
import asyncio
import json
import base64
import time
from datetime import datetime

async def main():
    # Simple browser automation using Playwright directly
    try:
        from playwright.async_api import async_playwright
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=False,  # Run with GUI for VNC viewing
                args=[
                    "--no-sandbox", 
                    "--disable-dev-shm-usage", 
                    "--disable-gpu",
                    "--disable-web-security",
                    "--disable-features=VizDisplayCompositor",
                    "--disable-background-timer-throttling",
                    "--disable-backgrounding-occluded-windows",
                    "--disable-renderer-backgrounding",
                    "--window-size=1280,720"
                ]
            )
            page = await browser.new_page()
            
            # Configure page for better performance
            await page.set_viewport_size({"width": 1280, "height": 720})
            await page.set_extra_http_headers({"Accept-Language": "en-US,en;q=0.9"})
            
            # Extract URL from task if possible
            task = "{task}"
            url = "https://stripe.com/pricing"  # Default fallback
            
            # Simple URL extraction
            if "stripe.com" in task.lower():
                url = "https://stripe.com/pricing"
            elif "http" in task.lower():
                import re
                urls = re.findall(r'https?://[^\s]+', task)
                if urls:
                    url = urls[0]
            
            await page.goto(url, wait_until="networkidle")
            await page.wait_for_timeout(3000)  # Wait 3 seconds for page to load
            
            # Take screenshot with 5 minute timeout
            screenshot = await page.screenshot(full_page=True, timeout=300000)  # 5 minute timeout
            screenshot_b64 = base64.b64encode(screenshot).decode('utf-8')
            
            # Get page info
            title = await page.title()
            current_url = page.url
            
            # Simple content extraction
            content = await page.evaluate('''
                () => {
                    const text = document.body.innerText;
                    return text.substring(0, 1000);
                }
            ''')
            
            await browser.close()
            
            result = f"Successfully navigated to {current_url}. Page title: {title}. Content preview: {content[:200]}..."
            
            print(json.dumps({
                "success": True,
                "result": result,
                "screenshot": screenshot_b64,
                "url": current_url,
                "title": title,
                "timestamp": time.time(),
                "date": datetime.now().isoformat(),
                "automation_type": "competitor_pricing"
            }))
            
    except Exception as e:
        print(json.dumps({
            "success": False,
            "error": str(e),
            "timestamp": time.time(),
            "automation_type": "competitor_pricing"
        }))

if __name__ == "__main__":
    asyncio.run(main())
""",
                "example_task": "Go to competitor.com/pricing and extract all pricing plans with features and costs"
            },
            
            "competitor_features": {
                "description": "Extract competitor product features and capabilities", 
                "template": """
import asyncio
from browser_use import Agent
import json
import base64
import time

async def main():
    agent = Agent(
        task="{task}",
        llm=None,
        use_vision=True,
        browser_headless=False,
        browser_executable="/usr/bin/google-chrome",
        browser_args=["--no-sandbox", "--disable-dev-shm-usage"]
    )
    
    try:
        result = await agent.run()
        
        page = agent.browser.get_current_page()
        screenshot = await page.screenshot(full_page=True)
        screenshot_b64 = base64.b64encode(screenshot).decode('utf-8')
        
        print(json.dumps({
            "success": True,
            "result": str(result),
            "screenshot": screenshot_b64,
            "url": page.url,
            "title": await page.title(),
            "timestamp": time.time(),
            "automation_type": "competitor_features"
        }))
        
    except Exception as e:
        print(json.dumps({
            "success": False,
            "error": str(e),
            "timestamp": time.time(),
            "automation_type": "competitor_features"
        }))
    
    finally:
        await agent.close()

if __name__ == "__main__":
    asyncio.run(main())
""",
                "example_task": "Navigate to competitor.com/features and extract all product features, benefits, and capabilities into a structured list"
            },
            
            "competitor_content": {
                "description": "Research competitor content strategy and social media",
                "template": """
import asyncio
from browser_use import Agent
import json
import base64
import time

async def main():
    agent = Agent(
        task="{task}",
        llm=None,
        use_vision=True,
        browser_headless=False,
        browser_executable="/usr/bin/google-chrome",
        browser_args=["--no-sandbox", "--disable-dev-shm-usage"]
    )
    
    try:
        result = await agent.run()
        
        page = agent.browser.get_current_page()
        screenshot = await page.screenshot()
        screenshot_b64 = base64.b64encode(screenshot).decode('utf-8')
        
        print(json.dumps({
            "success": True,
            "result": str(result),
            "screenshot": screenshot_b64,
            "url": page.url,
            "title": await page.title(),
            "timestamp": time.time(),
            "automation_type": "competitor_content"
        }))
        
    except Exception as e:
        print(json.dumps({
            "success": False,
            "error": str(e),
            "timestamp": time.time(),
            "automation_type": "competitor_content"
        }))
    
    finally:
        await agent.close()

if __name__ == "__main__":
    asyncio.run(main())
""",
                "example_task": "Go to competitor's LinkedIn/blog and analyze their recent content strategy, posting frequency, and engagement levels"
            },
            
            "lead_research": {
                "description": "Research potential leads and contact information",
                "template": """
import asyncio
from browser_use import Agent
import json
import base64
import time

async def main():
    agent = Agent(
        task="{task}",
        llm=None,
        use_vision=True,
        browser_headless=False,
        browser_executable="/usr/bin/google-chrome",
        browser_args=["--no-sandbox", "--disable-dev-shm-usage"]
    )
    
    try:
        result = await agent.run()
        
        page = agent.browser.get_current_page()
        screenshot = await page.screenshot()
        screenshot_b64 = base64.b64encode(screenshot).decode('utf-8')
        
        print(json.dumps({
            "success": True,
            "result": str(result),
            "screenshot": screenshot_b64,
            "url": page.url,
            "title": await page.title(),
            "timestamp": time.time(),
            "automation_type": "lead_research"
        }))
        
    except Exception as e:
        print(json.dumps({
            "success": False,
            "error": str(e),
            "timestamp": time.time(),
            "automation_type": "lead_research"
        }))
    
    finally:
        await agent.close()

if __name__ == "__main__":
    asyncio.run(main())
""",
                "example_task": "Search LinkedIn for marketing managers at SaaS companies with 50-200 employees and extract their contact information"
            },
            
            "web_search": {
                "description": "Search for information on Google",
                "template": """
import asyncio
from browser_use import Agent
import json
import base64
import time

async def main():
    agent = Agent(
        task="{task}",
        llm=None,  # Will use environment variables
        use_vision=True,
        browser_headless=False,
        browser_executable="/usr/bin/google-chrome",
        browser_args=["--no-sandbox", "--disable-dev-shm-usage"]
    )
    
    try:
        # Run the automation
        result = await agent.run()
        
        # Take final screenshot
        page = agent.browser.get_current_page()
        screenshot = await page.screenshot()
        screenshot_b64 = base64.b64encode(screenshot).decode('utf-8')
        
        print(json.dumps({
            "success": True,
            "result": str(result),
            "screenshot": screenshot_b64,
            "timestamp": time.time()
        }))
        
    except Exception as e:
        print(json.dumps({
            "success": False,
            "error": str(e),
            "timestamp": time.time()
        }))
    
    finally:
        await agent.close()

if __name__ == "__main__":
    asyncio.run(main())
""",
                "example_task": "Search for 'latest AI news' on Google and summarize the top 3 results"
            },
            
            "form_filling": {
                "description": "Fill out forms on websites",
                "template": """
import asyncio
from browser_use import Agent
import json
import base64
import time

async def main():
    agent = Agent(
        task="{task}",
        llm=None,
        use_vision=True,
        browser_headless=False,
        browser_executable="/usr/bin/google-chrome",
        browser_args=["--no-sandbox", "--disable-dev-shm-usage"]
    )
    
    try:
        result = await agent.run()
        
        page = agent.browser.get_current_page()
        screenshot = await page.screenshot()
        screenshot_b64 = base64.b64encode(screenshot).decode('utf-8')
        
        print(json.dumps({
            "success": True,
            "result": str(result),
            "screenshot": screenshot_b64,
            "timestamp": time.time()
        }))
        
    except Exception as e:
        print(json.dumps({
            "success": False,
            "error": str(e),
            "timestamp": time.time()
        }))
    
    finally:
        await agent.close()

if __name__ == "__main__":
    asyncio.run(main())
""",
                "example_task": "Go to https://httpbin.org/forms/post and fill out the form with test data"
            },
            
            "data_extraction": {
                "description": "Extract data from websites",
                "template": """
import asyncio
from browser_use import Agent
import json
import base64
import time

async def main():
    agent = Agent(
        task="{task}",
        llm=None,
        use_vision=True,
        browser_headless=False,
        browser_executable="/usr/bin/google-chrome",
        browser_args=["--no-sandbox", "--disable-dev-shm-usage"]
    )
    
    try:
        result = await agent.run()
        
        page = agent.browser.get_current_page()
        screenshot = await page.screenshot()
        screenshot_b64 = base64.b64encode(screenshot).decode('utf-8')
        
        print(json.dumps({
            "success": True,
            "result": str(result),
            "screenshot": screenshot_b64,
            "timestamp": time.time()
        }))
        
    except Exception as e:
        print(json.dumps({
            "success": False,
            "error": str(e),
            "timestamp": time.time()
        }))
    
    finally:
        await agent.close()

if __name__ == "__main__":
    asyncio.run(main())
""",
                "example_task": "Go to https://news.ycombinator.com and extract the titles and URLs of the top 5 stories"
            },
            
            "navigation": {
                "description": "Navigate websites and interact with elements",
                "template": """
import asyncio
from browser_use import Agent
import json
import base64
import time

async def main():
    agent = Agent(
        task="{task}",
        llm=None,
        use_vision=True,
        browser_headless=False,
        browser_executable="/usr/bin/google-chrome",
        browser_args=["--no-sandbox", "--disable-dev-shm-usage"]
    )
    
    try:
        result = await agent.run()
        
        page = agent.browser.get_current_page()
        screenshot = await page.screenshot()
        screenshot_b64 = base64.b64encode(screenshot).decode('utf-8')
        
        print(json.dumps({
            "success": True,
            "result": str(result),
            "screenshot": screenshot_b64,
            "timestamp": time.time()
        }))
        
    except Exception as e:
        print(json.dumps({
            "success": False,
            "error": str(e),
            "timestamp": time.time()
        }))
    
    finally:
        await agent.close()

if __name__ == "__main__":
    asyncio.run(main())
""",
                "example_task": "Navigate to Wikipedia, search for 'Artificial Intelligence', and click on the first result"
            }
        }
    
    def detect_automation_type(self, user_request: str) -> str:
        """Detect the type of automation based on user request"""
        request_lower = user_request.lower()
        
        # Marketing-specific automation types
        if any(keyword in request_lower for keyword in ['competitor', 'pricing', 'price', 'competitor pricing', 'monitor pricing']):
            return "competitor_pricing"
        elif any(keyword in request_lower for keyword in ['features', 'competitor features', 'product features', 'capabilities']):
            return "competitor_features"
        elif any(keyword in request_lower for keyword in ['content', 'social media', 'linkedin', 'blog', 'posts', 'competitor content']):
            return "competitor_content"
        elif any(keyword in request_lower for keyword in ['leads', 'prospect', 'contact', 'marketing manager', 'lead research']):
            return "lead_research"
        # General automation types
        elif any(keyword in request_lower for keyword in ['search', 'find', 'look up', 'google']):
            return "web_search"
        elif any(keyword in request_lower for keyword in ['form', 'fill', 'submit', 'input']):
            return "form_filling"
        elif any(keyword in request_lower for keyword in ['extract', 'scrape', 'get data', 'collect']):
            return "data_extraction"
        elif any(keyword in request_lower for keyword in ['navigate', 'go to', 'click', 'visit']):
            return "navigation"
        else:
            return "competitor_pricing"  # Default to useful marketing automation
    
    def generate_task_description(self, user_request: str, automation_type: str) -> str:
        """Generate a specific task description for browser-use"""
        # Clean up the user request
        task = user_request.strip()
        
        # Add context based on automation type
        if automation_type == "competitor_pricing":
            if "pricing" not in task.lower():
                task = f"Go to {task} and extract all pricing plans, features, and costs. Take screenshots of pricing pages and organize the pricing information into a structured format."
            else:
                task = f"{task}. Extract all pricing tiers, features included in each plan, and costs. Take full-page screenshots for comparison."
                
        elif automation_type == "competitor_features":
            if "features" not in task.lower():
                task = f"Navigate to {task} and extract all product features, capabilities, and benefits. Create a comprehensive list of what they offer."
            else:
                task = f"{task}. Extract all features, capabilities, integrations, and product benefits into a structured format."
                
        elif automation_type == "competitor_content":
            if "content" not in task.lower() and "social" not in task.lower():
                task = f"Research {task}'s content strategy by visiting their LinkedIn, blog, or social media. Analyze posting frequency, content types, and engagement."
            else:
                task = f"{task}. Analyze content strategy, posting patterns, engagement levels, and content themes."
                
        elif automation_type == "lead_research":
            if "lead" not in task.lower() and "prospect" not in task.lower():
                task = f"Research potential leads for {task}. Find contact information, company details, and decision makers."
            else:
                task = f"{task}. Extract contact information, job titles, company size, and relevant details for lead qualification."
                
        elif automation_type == "web_search":
            if not any(search_term in task.lower() for search_term in ['search', 'google', 'find']):
                task = f"Search for '{task}' on Google"
        elif automation_type == "form_filling":
            if not any(form_term in task.lower() for form_term in ['form', 'fill']):
                task = f"Fill out the form with the following information: {task}"
        elif automation_type == "data_extraction":
            if not any(extract_term in task.lower() for extract_term in ['extract', 'get']):
                task = f"Extract information about: {task}"
        elif automation_type == "navigation":
            if not any(nav_term in task.lower() for nav_term in ['go to', 'navigate', 'visit']):
                task = f"Navigate to and interact with: {task}"
        
        return task
    
    def generate_script(self, user_request: str) -> Dict[str, Any]:
        """Generate a browser-use automation script based on user request"""
        try:
            automation_type = self.detect_automation_type(user_request)
            logger.info(f"Detected automation type: {automation_type}")
            
            task_description = self.generate_task_description(user_request, automation_type)
            logger.info(f"Generated task description: {task_description}")
            
            if automation_type not in self.automation_templates:
                raise KeyError(f"Automation type '{automation_type}' not found in templates")
            
            template = self.automation_templates[automation_type]
            
            # Use repr() to properly escape the task for Python code
            escaped_task = repr(task_description)
            logger.info(f"Escaped task: {escaped_task}")
            
            # Replace the {task} placeholder with the properly escaped string
            script_content = template["template"].replace('"{task}"', escaped_task)
            
            script_id = str(uuid.uuid4())
            
            return {
                "success": True,
                "script_id": script_id,
                "automation_type": automation_type,
                "task_description": task_description,
                "script_content": script_content,
                "description": template["description"]
            }
            
        except Exception as e:
            logger.error(f"Script generation error: {str(e)}")
            logger.error(f"Error type: {type(e)}")
            logger.error(f"User request: {user_request}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def execute_script_locally(self, script_content: str, script_id: str) -> Dict[str, Any]:
        """Execute the browser-use script locally (fallback when Docker unavailable)"""
        try:
            # Create temporary directory for script
            with tempfile.TemporaryDirectory() as temp_dir:
                script_path = os.path.join(temp_dir, f"automation_{script_id}.py")
                
                # Write script to file
                with open(script_path, 'w') as f:
                    f.write(script_content)
                
                logger.info(f"Executing automation script locally: {script_id}")
                
                # Run the script using subprocess
                result = subprocess.run([
                    'python', script_path
                ], capture_output=True, text=True, timeout=300)
                
                if result.returncode == 0:
                    # Try to parse JSON output
                    try:
                        output_lines = result.stdout.strip().split('\n')
                        json_output = None
                        
                        for line in reversed(output_lines):
                            try:
                                json_output = json.loads(line)
                                break
                            except:
                                continue
                        
                        if json_output:
                            return {
                                "success": json_output.get("success", False),
                                "result": json_output.get("result"),
                                "screenshot": json_output.get("screenshot"),
                                "error": json_output.get("error"),
                                "script_id": script_id,
                                "logs": result.stdout,
                                "execution_mode": "local"
                            }
                        else:
                            return {
                                "success": False,
                                "error": "No valid JSON output from automation script",
                                "script_id": script_id,
                                "logs": result.stdout,
                                "execution_mode": "local"
                            }
                    except Exception as parse_error:
                        return {
                            "success": False,
                            "error": f"Failed to parse automation output: {str(parse_error)}",
                            "script_id": script_id,
                            "logs": result.stdout,
                            "execution_mode": "local"
                        }
                else:
                    return {
                        "success": False,
                        "error": f"Script execution failed with return code {result.returncode}",
                        "script_id": script_id,
                        "logs": result.stderr,
                        "execution_mode": "local"
                    }
                    
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "Script execution timed out after 5 minutes",
                "script_id": script_id,
                "execution_mode": "local"
            }
        except Exception as e:
            logger.error(f"Local script execution error: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "script_id": script_id,
                "execution_mode": "local"
            }

    async def execute_script_in_docker(self, script_content: str, script_id: str) -> Dict[str, Any]:
        """Execute the browser-use script in a Docker container with live streaming"""
        try:
            # Create temporary directory for script
            with tempfile.TemporaryDirectory() as temp_dir:
                # Use consistent filename for Docker
                script_path = os.path.join(temp_dir, "automation_script.py")
                
                # Write script to file
                with open(script_path, 'w') as f:
                    f.write(script_content)
                
                # Create Dockerfile for browser-use environment with VNC
                dockerfile_content = """
FROM python:3.11-slim

# Install system dependencies including VNC
RUN apt-get update && apt-get install -y \\
    wget \\
    gnupg \\
    unzip \\
    curl \\
    xvfb \\
    x11vnc \\
    fluxbox \\
    websockify \\
    novnc \\
    libxss1 \\
    libgconf-2-4 \\
    libxtst6 \\
    libxrandr2 \\
    libasound2 \\
    libpangocairo-1.0-0 \\
    libatk1.0-0 \\
    libcairo-gobject2 \\
    libgtk-3-0 \\
    libgdk-pixbuf2.0-0 \\
    && rm -rf /var/lib/apt/lists/*

# Install Chrome
RUN wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | apt-key add - \\
    && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list \\
    && apt-get update \\
    && apt-get install -y google-chrome-stable \\
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip install --no-cache-dir browser-use playwright

# Install Playwright browsers
RUN playwright install chromium
RUN playwright install-deps

WORKDIR /app
COPY automation_script.py /app/

# Set environment variables
ENV DISPLAY=:99
ENV PYTHONUNBUFFERED=1

# Expose VNC and noVNC ports
EXPOSE 5900 6080

# Start VNC server and run automation inline
CMD ["sh", "-c", "Xvfb :99 -screen 0 1280x720x24 & export DISPLAY=:99 && sleep 2 && fluxbox & x11vnc -display :99 -nopw -listen localhost -xkb -forever -shared & websockify --web=/usr/share/novnc/ 6080 localhost:5900 & sleep 3 && python /app/automation_script.py && tail -f /dev/null"]
"""
                
                dockerfile_path = os.path.join(temp_dir, "Dockerfile")
                with open(dockerfile_path, 'w') as f:
                    f.write(dockerfile_content)
                
                # Build Docker image
                logger.info(f"Building Docker image for automation {script_id}")
                logger.info(f"Temp directory contents: {os.listdir(temp_dir)}")
                image = self.docker_client.images.build(
                    path=temp_dir,
                    dockerfile="Dockerfile",
                    tag=f"browser-automation-{script_id}",
                    rm=True
                )[0]
                
                # Run container with VNC ports exposed
                logger.info(f"Running automation container {script_id}")
                container = self.docker_client.containers.run(
                    image.id,
                    name=f"automation-{script_id}",
                    detach=True,
                    remove=False,  # Don't auto-remove so we can get logs
                    mem_limit="2g",
                    cpu_quota=100000,  # 100% CPU limit
                    ports={
                        '5900/tcp': None,  # VNC server port
                        '6080/tcp': None   # noVNC web port
                    },
                    environment={
                        "DISPLAY": ":99"
                    },
                    # Configure logging driver to support reading
                    log_config={"type": "json-file", "config": {"max-size": "10m"}}
                )
                
                # Get VNC port information
                container.reload()
                vnc_port = None
                novnc_port = None
                
                logger.info(f"Container ports: {container.ports}")
                
                if container.ports:
                    vnc_mapping = container.ports.get('5900/tcp')
                    novnc_mapping = container.ports.get('6080/tcp')
                    
                    logger.info(f"VNC mapping: {vnc_mapping}, noVNC mapping: {novnc_mapping}")
                    
                    if vnc_mapping and len(vnc_mapping) > 0:
                        vnc_port = vnc_mapping[0]['HostPort']
                    if novnc_mapping and len(novnc_mapping) > 0:
                        novnc_port = novnc_mapping[0]['HostPort']
                
                logger.info(f"VNC available at port {vnc_port}, noVNC at port {novnc_port}")
                
                # Monitor container execution
                result = await self._monitor_container_execution(container, script_id, vnc_port, novnc_port)
                
                # Clean up container after getting logs
                try:
                    container.remove(force=True)
                except Exception as cleanup_error:
                    logger.warning(f"Failed to cleanup container {script_id}: {cleanup_error}")
                
                return result
                
        except Exception as e:
            logger.error(f"Script execution error: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "script_id": script_id
            }
    
    async def _monitor_container_execution(self, container, script_id: str, vnc_port: str = None, novnc_port: str = None) -> Dict[str, Any]:
        """Monitor container execution and capture output"""
        logs = ""
        try:
            # Wait for container to complete (with timeout)
            logger.info(f"Waiting for container {script_id} to complete...")
            result = container.wait(timeout=300)  # 5 minute timeout
            exit_code = result['StatusCode']
            logger.info(f"Container {script_id} completed with exit code {exit_code}")
            
            # Try multiple methods to get container logs
            try:
                # Method 1: Standard logs API
                logs = container.logs(stdout=True, stderr=True, timestamps=False).decode('utf-8')
                logger.info(f"Retrieved logs via standard API: {len(logs)} characters")
            except Exception as log_error:
                logger.warning(f"Standard logs failed: {log_error}")
                try:
                    # Method 2: Attach to get output
                    output = container.attach(stdout=True, stderr=True, stream=False, logs=True)
                    if isinstance(output, bytes):
                        logs = output.decode('utf-8')
                    else:
                        logs = str(output)
                    logger.info(f"Retrieved logs via attach: {len(logs)} characters")
                except Exception as attach_error:
                    logger.warning(f"Attach logs failed: {attach_error}")
                    logs = f"Failed to retrieve logs: {log_error}, {attach_error}"
            
            # Log the first few lines for debugging
            if logs:
                log_lines = logs.split('\n')[:10]
                logger.info(f"First 10 lines of container output: {log_lines}")
            
            # If container failed, return error immediately
            if exit_code != 0:
                return {
                    "success": False,
                    "error": f"Container exited with code {exit_code}. This usually means the browser automation script failed to run properly.",
                    "script_id": script_id,
                    "logs": logs,
                    "execution_mode": "docker"
                }
            
            # Try to parse JSON output from the script
            try:
                # Look for JSON output in logs
                lines = logs.strip().split('\n') if logs else []
                json_output = None
                
                for line in reversed(lines):  # Check from end
                    line = line.strip()
                    if line and (line.startswith('{') or line.startswith('[')):
                        try:
                            json_output = json.loads(line)
                            logger.info(f"Found JSON output: {json_output.get('success', 'unknown')}")
                            break
                        except json.JSONDecodeError:
                            continue
                
                if json_output:
                    return {
                        "success": json_output.get("success", False),
                        "result": json_output.get("result"),
                        "screenshot": json_output.get("screenshot"),
                        "error": json_output.get("error"),
                        "script_id": script_id,
                        "logs": logs,
                        "execution_mode": "docker",
                        "vnc_port": vnc_port,
                        "novnc_port": novnc_port,
                        "vnc_url": f"http://localhost:{novnc_port}/vnc.html?host=localhost&port={vnc_port}" if novnc_port and vnc_port else None
                    }
                else:
                    return {
                        "success": False,
                        "error": "No valid JSON output found in container logs. The automation script may have failed to run or produce output.",
                        "script_id": script_id,
                        "logs": logs,
                        "execution_mode": "docker",
                        "vnc_port": vnc_port,
                        "novnc_port": novnc_port,
                        "vnc_url": f"http://localhost:{novnc_port}/vnc.html?host=localhost&port={vnc_port}" if novnc_port and vnc_port else None
                    }
                    
            except Exception as parse_error:
                return {
                    "success": False,
                    "error": f"Failed to parse automation output: {str(parse_error)}",
                    "script_id": script_id,
                    "logs": logs,
                    "execution_mode": "docker"
                }
                
        except Exception as e:
            logger.error(f"Container monitoring error: {str(e)}")
            return {
                "success": False,
                "error": f"Container monitoring failed: {str(e)}",
                "script_id": script_id,
                "logs": logs,
                "execution_mode": "docker"
            }
    
    async def run_automation(self, user_request: str) -> Dict[str, Any]:
        """Complete automation pipeline: generate script and execute"""
        try:
            # Generate script
            script_result = self.generate_script(user_request)
            
            if not script_result["success"]:
                return script_result
            
            # Execute script (choose based on Docker availability)
            if self.use_docker:
                execution_result = await self.execute_script_in_docker(
                    script_result["script_content"],
                    script_result["script_id"]
                )
            else:
                execution_result = await self.execute_script_locally(
                    script_result["script_content"],
                    script_result["script_id"]
                )
            
            # Combine results
            combined_result = {
                **execution_result,
                "automation_type": script_result["automation_type"],
                "task_description": script_result["task_description"],
                "description": script_result["description"]
            }
            
            # Auto-save marketing reports for successful automations
            if combined_result.get("success") and script_result["automation_type"] in [
                "competitor_pricing", "competitor_features", "competitor_content", "lead_research"
            ]:
                try:
                    report_path = marketing_reports.save_automation_report(combined_result)
                    if report_path:
                        combined_result["report_saved"] = True
                        combined_result["report_path"] = report_path
                        logger.info(f"Marketing report auto-saved: {report_path}")
                except Exception as report_error:
                    logger.warning(f"Failed to save marketing report: {str(report_error)}")
                    combined_result["report_saved"] = False
            
            return combined_result
            
        except Exception as e:
            logger.error(f"Automation pipeline error: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def cleanup_automation(self, script_id: str):
        """Clean up Docker resources for an automation"""
        try:
            # Remove container if still running
            try:
                container = self.docker_client.containers.get(f"automation-{script_id}")
                container.stop(timeout=5)
                container.remove()
            except:
                pass
            
            # Remove image
            try:
                image = self.docker_client.images.get(f"browser-automation-{script_id}")
                self.docker_client.images.remove(image.id, force=True)
            except:
                pass
                
            logger.info(f"Cleaned up automation {script_id}")
            
        except Exception as e:
            logger.warning(f"Cleanup error for {script_id}: {str(e)}")

# Global automation manager
browser_automation = BrowserUseAutomation()
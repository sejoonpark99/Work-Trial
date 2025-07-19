# Work Trial - AI Research Agent

A full-stack AI research agent application with automated case study generation, email composition, and browser automation capabilities.

## Project Structure

### Backend (`/backend`)
- **FastAPI-based API** with research agent capabilities
- **Agent Mode**: Multi-turn automated research and task execution
- **Chat Mode**: Single-turn interactions with tool availability
- **Search Tools**: Web search integration with Brave Search API
- **Browser Automation**: AI-powered browser automation using browser-use
- **Apollo Integration**: Lead generation and prospect research automation
- **Email Service**: Gmail integration for automated email composition
- **File System Tools**: Document generation, editing, and management
- **LLM Provider Support**: OpenAI and Anthropic integration with streaming

### Frontend (`/frontend/my-app`)
- **Next.js 15** React application with TypeScript
- **Assistant UI**: Interactive chat interface with real-time streaming
- **Thought Cards**: Visual representation of AI agent reasoning steps
- **Browser Automation Viewer**: Live browser automation monitoring
- **File Preview**: Document and CSV file preview capabilities
- **Apollo Workflow**: Lead generation interface and results display
- **Responsive Design**: Modern UI with Tailwind CSS and shadcn/ui components

## Getting Started

### Prerequisites
- Node.js 18+ and npm
- Python 3.8+
- Gmail API credentials (for email features)
- OpenAI/Anthropic API keys

### Backend Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Set up environment variables (see Environment Variables section)
cp .env.example .env
# Edit .env with your API keys

python main.py
```

### Frontend Setup
```bash
cd frontend/my-app
npm install
npm run dev
```

## Features

### Core AI Capabilities
- **Intelligent Agent Mode**: Multi-turn automated research and task execution with reasoning steps
- **Interactive Chat Mode**: Single-turn conversations with tool access
- **Real-time Streaming**: Live updates and thought process visualization

### Research & Analysis
- **Automated Research**: AI-powered company research and competitive analysis
- **Case Study Generation**: Automated creation of relevant case studies with metrics
- **Web Search Integration**: Brave Search API for up-to-date information
- **Document Management**: Organized output for case studies, emails, and reports

### Browser Automation
- **AI-Powered Automation**: Natural language browser task automation
- **Live Monitoring**: Real-time browser session viewing and control
- **Screenshot Streaming**: WebSocket-based live browser screenshots
- **VNC Integration**: Remote browser access for complex tasks

### Lead Generation
- **Apollo.io Integration**: Automated lead research and data extraction
- **CSV Processing**: Bulk domain processing and prospect identification
- **Job Title Extraction**: Automated role identification and targeting

### Communication
- **Email Composition**: Intelligent email drafting with personalization
- **Gmail Integration**: Automated email sending capabilities
- **Content Generation**: Context-aware marketing content creation

## API Endpoints

### Core Chat & Agent
- `POST /chat` - Main chat interface with streaming AI agent responses
- `GET /health` - Health check endpoint with provider status

### Search & Research
- `POST /search` - Web search functionality (web, news, images)
- `POST /case-study` - Company case study lookup and generation
- `GET /search/test` - Test search functionality status

### File System Operations
- `POST /fs/list` - List files and directories
- `POST /fs/read` - Read file contents
- `POST /fs/write` - Write content to files
- `POST /fs/edit` - Edit files using text replacement
- `POST /fs/delete` - Delete files or directories
- `POST /fs/search` - Search for files by name or content
- `POST /fs/info` - Get file information and metadata
- `POST /fs/mkdir` - Create directories

### Browser Automation
- `POST /browser/session` - Create new browser automation session
- `POST /browser/navigate` - Navigate browser to URL
- `POST /browser/script` - Execute JavaScript in browser
- `DELETE /browser/session/{session_id}` - Close browser session
- `WebSocket /browser/stream/{session_id}` - Live browser screenshot streaming
- `GET /browser/vnc/{script_id}` - Get VNC connection info
- `POST /browser/automate` - Run AI-powered browser automation

### Lead Generation
- `POST /apollo/process` - Process domains through Apollo.io workflow

### Communication
- `POST /send-email` - Send emails via SendGrid/Gmail integration

## Environment Variables

Create a `.env` file in the backend directory with the following variables:

```bash
# LLM Provider API Keys
OPENAI_API_KEY=your_openai_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Search API Keys
BRAVE_SEARCH_API_KEY=your_brave_search_api_key_here

# Email Configuration
GMAIL_CREDENTIALS_FILE=path/to/gmail/credentials.json
SENDGRID_API_KEY=your_sendgrid_api_key_here
FROM_EMAIL=your_email@domain.com

# Apollo.io Configuration
APOLLO_EMAIL=your_apollo_email
APOLLO_PASSWORD=your_apollo_password

# Application Settings
DATA_ROOT=./data
LOGS_ENABLED=true
AGENT_MAX_STEPS=10

# Browser Automation
BROWSER_HEADLESS=true
VNC_DISPLAY=:99
```

## Running the Application

### Using Virtual Environment (Recommended)
```bash
# Backend
cd backend
venv/Scripts/activate  # Windows
# or: source venv/bin/activate  # Linux/Mac
python main.py

# Frontend (in another terminal)
cd frontend/my-app
npm run dev
```

### Using Scripts
- `start_backend.sh/.bat` - Start the backend server
- `start_frontend.sh/.bat` - Start the frontend development server
- `run_day2.py` - Execute day 2 automation tasks

## Ports
- **Backend**: http://localhost:8000
- **Frontend**: http://localhost:3000
- **VNC Browser Viewer**: http://localhost:6080 (when browser automation is active)

## Notices

Please note that the VNC will take up alot of memory; it is better to use it if you already have an initialized container. VNC can stream a lot of data. Please be aware that there needs to be further testing for edge cases.

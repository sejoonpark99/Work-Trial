# Work Trial - AI Research Agent

A full-stack AI research agent application with automated case study generation and email composition capabilities.

## Project Structure

### Backend (`/backend`)
- **FastAPI-based API** with research agent capabilities
- **Agent Mode**: Automated research and case study generation
- **Search Tools**: Web search integration for company research
- **Email Service**: Gmail integration for automated email composition
- **File System Tools**: Document generation and management
- **LLM Provider Support**: OpenAI and Anthropic integration

### Frontend (`/frontend/my-app`)
- **Next.js 15** React application
- **Assistant UI**: Interactive chat interface with AI agent
- **Case Study Analysis**: Real-time case study generation and review
- **Email Preview**: Generated email content preview
- **Responsive Design**: Modern UI with Tailwind CSS

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
python main.py
```

### Frontend Setup
```bash
cd frontend/my-app
npm install
npm run dev
```

## Features

- **Automated Research**: AI-powered company research and analysis
- **Case Study Generation**: Automated creation of relevant case studies
- **Email Composition**: Intelligent email drafting with personalization
- **Real-time Chat**: Interactive assistant interface
- **Document Management**: Organized output for case studies and emails
- **Search Integration**: Web search capabilities for up-to-date information

## API Endpoints

- `POST /chat` - Main chat interface with the AI agent
- `GET /health` - Health check endpoint
- `POST /search` - Web search functionality

## Scripts

- `start_backend.sh/.bat` - Start the backend server
- `start_frontend.sh/.bat` - Start the frontend development server
- `run_day2.py` - Execute day 2 automation tasks
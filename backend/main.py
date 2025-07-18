from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.responses import Response
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import os
from dotenv import load_dotenv
import json
import logging
from datetime import datetime
from providers import ProviderManager, ProviderError
from logger import event_logger
from search_tools import WebSearchManager, SearchError
from agent_mode import AgentMode
from file_tools import FileSystemTools
from gmail_service import email_service

load_dotenv()

app = FastAPI(title="Research Agent API", version="1.0.0")

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize provider manager
provider_manager = ProviderManager()

# Initialize web search manager
web_search_manager = WebSearchManager()

# Initialize file system tools
file_system = FileSystemTools()

# Initialize agent mode
max_agent_steps = int(os.getenv("AGENT_MAX_STEPS", 10))
agent_mode = AgentMode(web_search_manager, file_system, max_steps=max_agent_steps)


# Request/Response models
class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: List[Message]
    provider: str = "openai"
    model: str = "gpt-4o-mini"
    agent_mode: str = "auto"  # "auto" = intelligent, "chat" = force chat, "agent" = force agent
    settings: Optional[Dict[str, Any]] = {}


class ChatResponse(BaseModel):
    ok: bool
    message: Optional[Dict[str, Any]] = None
    parts: Optional[List[Dict[str, Any]]] = None
    usage: Optional[Dict[str, Any]] = None
    tool_suggestions: Optional[List[Dict[str, Any]]] = None
    error: Optional[Dict[str, Any]] = None

class SearchRequest(BaseModel):
    query: str
    count: int = 10
    search_type: str = "web"  # web, news, images
    scrape_top_results: int = 3

class SearchResponse(BaseModel):
    ok: bool
    query: Optional[str] = None
    results: Optional[List[Dict[str, Any]]] = None
    total: Optional[int] = None
    scraped_count: Optional[int] = None
    error: Optional[Dict[str, Any]] = None

class CaseStudyRequest(BaseModel):
    company_domain: str
    context: str = ""

class CaseStudyResponse(BaseModel):
    ok: bool
    company_domain: Optional[str] = None
    summary: Optional[Dict[str, Any]] = None
    all_results: Optional[List[Dict[str, Any]]] = None
    total_found: Optional[int] = None
    saved_path: Optional[str] = None
    error: Optional[Dict[str, Any]] = None

class FileListRequest(BaseModel):
    path: str = ""
    include_hidden: bool = False

class FileReadRequest(BaseModel):
    path: str
    encoding: str = "utf-8"

class FileWriteRequest(BaseModel):
    path: str
    content: str
    encoding: str = "utf-8"
    append: bool = False

class FileEditRequest(BaseModel):
    path: str
    old_text: str
    new_text: str
    encoding: str = "utf-8"

class FileDeleteRequest(BaseModel):
    path: str

class FileSearchRequest(BaseModel):
    query: str
    path: str = ""
    file_extensions: Optional[List[str]] = None

class FileInfoRequest(BaseModel):
    path: str

class FileSystemResponse(BaseModel):
    ok: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

class EmailSendRequest(BaseModel):
    to_email: str
    subject: str
    content: str

class EmailSendResponse(BaseModel):
    success: bool
    message: str
    error: Optional[str] = None


@app.get("/health")
async def health_check():
    """Health check endpoint with provider connectivity test"""
    logger.info("Health check endpoint called")
    await event_logger.log_event("health", {"status": "ok", "phase": 1})

    # Test provider connectivity
    providers_status = {}

    # Test OpenAI
    try:
        openai_provider = provider_manager.providers["openai"]
        test_result = await openai_provider.chat_completion(
            messages=[{"role": "user", "content": "Hello"}],
            model="gpt-3.5-turbo",  # Use cheaper model for health check
        )
        providers_status["openai"] = {"status": "connected", "model": "gpt-3.5-turbo"}
    except Exception as e:
        providers_status["openai"] = {"status": "error", "error": str(e)}

    # Test Anthropic
    try:
        anthropic_provider = provider_manager.providers["anthropic"]
        test_result = await anthropic_provider.chat_completion(
            messages=[{"role": "user", "content": "Hello"}],
            model="claude-3-haiku-20240307",
        )
        providers_status["anthropic"] = {
            "status": "connected",
            "model": "claude-3-haiku-20240307",
        }
    except Exception as e:
        providers_status["anthropic"] = {"status": "error", "error": str(e)}

    # Overall status
    overall_status = (
        "ok"
        if any(p["status"] == "connected" for p in providers_status.values())
        else "error"
    )

    return {
        "status": overall_status,
        "timestamp": datetime.now().isoformat(),
        "providers": providers_status,
        "data_root": os.getenv("DATA_ROOT", "./data"),
        "logs_enabled": os.getenv("LOGS_ENABLED", "false").lower() == "true",
    }


@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """Main chat endpoint"""
    try:
        logger.info(f"Chat endpoint called with provider: {request.provider}, mode: {request.agent_mode}, messages: {len(request.messages)}")
        
        # Log incoming request
        await event_logger.log_event(
            "user_msg",
            {
                "provider": request.provider,
                "agent_mode": request.agent_mode,
                "message_count": len(request.messages),
            },
        )

        # Convert messages to dict format for providers
        messages = [
            {"role": msg.role, "content": msg.content} for msg in request.messages
        ]

        # Determine if we should use agent mode
        if request.agent_mode == "agent":
            use_agent = True
            logger.info("Using Agent Mode (explicitly requested) - Multi-turn with tool chaining")
        elif request.agent_mode == "chat":
            use_agent = False
            logger.info("Using Chat Mode (explicitly requested) - Single-turn with tools")
        else:  # auto mode
            use_agent = await should_use_agent_mode(messages[-1]["content"])
            logger.info(f"Using {'Agent' if use_agent else 'Chat'} Mode (auto-detected) - {'Multi-turn with tool chaining' if use_agent else 'Single-turn with tools'}")
        
        if use_agent:
            await event_logger.log_event("agent_start", {"max_steps": max_agent_steps})
            
            # Use streaming for real-time thought card updates
            async def stream_agent_response():
                thought_card_count = 0
                final_usage = None
                
                async for chunk in agent_mode.run_agent_loop_streaming(messages, provider_manager):
                    # Parse the streaming chunk
                    if chunk.startswith("data: "):
                        try:
                            data = json.loads(chunk[6:])
                            
                            if data.get("type") == "thought_card":
                                # Send each thought card as individual tool call
                                tool_call_data = {
                                    "toolCallId": f"thought_{thought_card_count}",
                                    "toolName": "thought_card",
                                    "args": json.dumps({
                                        "card_type": data["card_type"],
                                        "step": data["step"],
                                        "content": data["content"],
                                        "icon": data["icon"],
                                        "title": data["title"],
                                        "tool_name": data.get("tool_name"),
                                        "tool_args": data.get("tool_args"),
                                        "result": data.get("result")
                                    })
                                }
                                chunk = f"9:{json.dumps(tool_call_data)}\n"
                                logger.info(f"Sending thought card chunk: {chunk}")
                                yield chunk
                                thought_card_count += 1
                                
                            elif data.get("type") == "final_message":
                                # Send final text message
                                final_message = data["content"]
                                chunk = f"0:{json.dumps(final_message)}\n"
                                logger.info(f"Sending final message chunk: {chunk}")
                                yield chunk
                                
                            elif data.get("type") == "final_usage":
                                final_usage = data["usage"]
                                
                        except json.JSONDecodeError:
                            logger.error(f"Failed to parse streaming chunk: {chunk}")
                            continue
                
                # Send completion signal
                completion_chunk = f"d:\n"
                logger.info(f"Sending completion chunk: {completion_chunk}")
                yield completion_chunk
                
                # Log completion
                await event_logger.log_event("agent_complete", {
                    "steps_used": thought_card_count,
                    "usage": final_usage or {"tokens_in": 0, "tokens_out": 0, "cost_usd": 0.0}
                })
            
            return StreamingResponse(
                stream_agent_response(),
                media_type="text/plain",
                headers={
                    "Content-Type": "text/plain; charset=utf-8",
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive"
                }
            )
        
        else:
            logger.info("Using Chat Mode - Single-turn with tools available")
            await event_logger.log_event("chat_start", {"provider": request.provider})
            
            # Single-turn chat with tools available
            result = await run_single_turn_chat(messages, provider_manager, request.provider, request.model)
            
            await event_logger.log_event("chat_complete", {
                "usage": result["usage"]
            })
            
            # Build response (no agent_steps for chat mode)
            response_message = result["message"]
            parts = [{"type": "text", "text": response_message["content"]}]
            
            return ChatResponse(
                ok=True, message=response_message, parts=parts, usage=result["usage"]
            )

    except ProviderError as e:
        logger.error(f"Provider error: {str(e)}")
        await event_logger.log_event(
            "error",
            {"type": "provider_error", "provider": request.provider, "message": str(e)},
        )
        return ChatResponse(
            ok=False, error={"type": "provider_error", "message": str(e)}
        )
    except Exception as e:
        logger.error(f"Chat endpoint error: {str(e)}")
        logger.error(f"Request data: {request}")
        await event_logger.log_event(
            "error", {"type": "internal_error", "message": str(e)}
        )
        return ChatResponse(
            ok=False, error={"type": "internal_error", "message": str(e)}
        )

@app.post("/search", response_model=SearchResponse)
async def search_endpoint(request: SearchRequest):
    """Web search endpoint"""
    try:
        logger.info(f"Search endpoint called with query: '{request.query}', type: {request.search_type}")
        
        # Log search request
        await event_logger.log_event("search_request", {
            "query": request.query,
            "search_type": request.search_type,
            "count": request.count
        })
        
        # Perform search based on type
        if request.search_type == "web":
            if request.scrape_top_results > 0:
                results = await web_search_manager.search_and_scrape(
                    request.query, 
                    count=request.count,
                    scrape_top_results=request.scrape_top_results
                )
            else:
                results = await web_search_manager.brave_search.search(
                    request.query, 
                    count=request.count
                )
                results["scraped_count"] = 0
        elif request.search_type == "news":
            results = await web_search_manager.search_news(
                request.query, 
                count=request.count
            )
            results["scraped_count"] = 0
        elif request.search_type == "images":
            results = await web_search_manager.search_images(
                request.query, 
                count=request.count
            )
            results["scraped_count"] = 0
        else:
            raise SearchError(f"Unsupported search type: {request.search_type}")
        
        # Log search response
        await event_logger.log_event("search_response", {
            "query": request.query,
            "results_count": len(results["results"]),
            "scraped_count": results.get("scraped_count", 0)
        })
        
        return SearchResponse(
            ok=True,
            query=results["query"],
            results=results["results"],
            total=results["total"],
            scraped_count=results.get("scraped_count", 0)
        )
        
    except SearchError as e:
        logger.error(f"Search error: {str(e)}")
        await event_logger.log_event("error", {
            "type": "search_error",
            "query": request.query,
            "message": str(e)
        })
        return SearchResponse(
            ok=False,
            error={"type": "search_error", "message": str(e)}
        )
    except Exception as e:
        logger.error(f"Search endpoint error: {str(e)}")
        await event_logger.log_event("error", {
            "type": "internal_error",
            "message": str(e)
        })
        return SearchResponse(
            ok=False,
            error={"type": "internal_error", "message": str(e)}
        )

@app.post("/case-study", response_model=CaseStudyResponse)
async def case_study_endpoint(request: CaseStudyRequest):
    """Case study lookup endpoint"""
    try:
        logger.info(f"Case study lookup for: {request.company_domain}")
        
        # Log case study request
        await event_logger.log_event("case_study_request", {
            "company_domain": request.company_domain,
            "context": request.context
        })
        
        # Perform case study lookup
        result = await web_search_manager.case_study_tool.lookup_case_study(
            request.company_domain,
            request.context
        )
        
        if result["ok"]:
            # Auto-save the top case study summary
            saved_path = await save_case_study_summary(request.company_domain, result["summary"])
            
            # Log case study response
            await event_logger.log_event("case_study_response", {
                "company_domain": request.company_domain,
                "total_found": result["total_found"],
                "saved_path": saved_path
            })
            
            return CaseStudyResponse(
                ok=True,
                company_domain=result["company_domain"],
                summary=result["summary"],
                all_results=result["all_results"],
                total_found=result["total_found"],
                saved_path=saved_path
            )
        else:
            return CaseStudyResponse(
                ok=False,
                company_domain=request.company_domain,
                error={"type": "case_study_error", "message": result["error"]}
            )
            
    except Exception as e:
        logger.error(f"Case study endpoint error: {str(e)}")
        await event_logger.log_event("error", {
            "type": "case_study_error",
            "company_domain": request.company_domain,
            "message": str(e)
        })
        return CaseStudyResponse(
            ok=False,
            company_domain=request.company_domain,
            error={"type": "internal_error", "message": str(e)}
        )

async def run_single_turn_chat(messages: List[Dict[str, Any]], provider_manager, provider: str, model: str) -> Dict[str, Any]:
    """
    Run single-turn chat with tools available but no looping
    LLM can decide to use tools, but everything must be completed in one cycle
    """
    try:
        # Get file context for the system prompt
        file_context = await agent_mode._get_file_context()
        
        # Create system prompt for single-turn chat with tools
        system_prompt = f"""You are an intelligent assistant with access to tools. You can use tools to help answer questions, but you must complete everything in a single response cycle.

Available Tools:
- web_search: Search the web for current information. Args: {{"query": "search term"}}
- case_study_lookup: Find case studies for specific companies. Args: {{"company_domain": "company name"}}
- file_read: Read contents of a file. Args: {{"path": "file/path"}}
- file_write: Write content to a file. Args: {{"path": "file/path", "content": "content to write"}}
- file_edit: Edit file by replacing text. Args: {{"path": "file/path", "old_text": "text to replace", "new_text": "replacement text"}}
- file_list: List files in a directory. Args: {{"path": "directory/path"}}
- file_search: Search for files by name or content. Args: {{"query": "search term", "path": "directory/path"}}
- workspace_overview: Get complete overview of all files in workspace. Args: {{}}

{file_context}

IMPORTANT: 
- You can decide to use tools if needed to answer the question
- You must complete everything in ONE response cycle (no looping)
- You can use MULTIPLE tools in a single response if needed
- Use the format: <tool>{{...}}</tool> for each tool OR provide direct answer

For simple questions that don't need tools, answer directly.
For questions that need tools, use the appropriate tools then provide your answer.

Examples:
- "What is Python?" → Direct answer (no tools needed)
- "Show me my files" → <tool>{{"name": "workspace_overview", "args": {{}}}}</tool>
- "Read the guidelines" → <tool>{{"name": "file_read", "args": {{"path": "knowledge_base/research_guidelines.md"}}}}</tool>
- "Research HubSpot" → <tool>{{"name": "file_search", "args": {{"query": "hubspot", "path": ""}}}}</tool> (check existing first)
- "Research HubSpot and save it" → <tool>{{"name": "file_search", "args": {{"query": "hubspot", "path": ""}}}}</tool><tool>{{"name": "case_study_lookup", "args": {{"company_domain": "HubSpot"}}}}</tool><tool>{{"name": "file_write", "args": {{"path": "output/case_studies/hubspot.md", "content": "# HubSpot Research..."}}}}</tool>

IMPORTANT: When asked to "research" a company, ALWAYS check existing files first using file_search before doing web searches!
You can use multiple tools in a single response to complete complex tasks!
"""

        # Add system prompt to messages
        chat_messages = [{"role": "system", "content": system_prompt}] + messages
        
        # Get LLM response
        result = await provider_manager.get_completion(
            provider=provider,
            messages=chat_messages,
            model=model
        )
        
        response_content = result["message"]["content"]
        
        # Parse and execute any tool calls in the response
        tool_calls = extract_tool_calls_from_response(response_content)
        
        if tool_calls:
            # In chat mode, execute ALL tool calls in sequence (single turn)
            tool_results = []
            for i, tool_call in enumerate(tool_calls):
                tool_result = await agent_mode.execute_tool(tool_call)
                tool_results.append(f"Tool {i+1}: {tool_call.get('name', 'unknown')}\nResult: {tool_result}")
            
            # Create a combined response with all tool results
            all_tool_results = "\n\n".join(tool_results)
            combined_response = f"{response_content}\n\nTool Results:\n{all_tool_results}"
            
            return {
                "message": {
                    "role": "assistant", 
                    "content": combined_response
                },
                "usage": result["usage"]
            }
        else:
            # No tools used, return original response
            return result
            
    except Exception as e:
        logger.error(f"Single-turn chat error: {str(e)}")
        return {
            "message": {
                "role": "assistant",
                "content": f"I encountered an error: {str(e)}"
            },
            "usage": {"tokens_in": 0, "tokens_out": 0, "cost_usd": 0.0}
        }

def extract_tool_calls_from_response(content: str) -> List[Dict[str, Any]]:
    """Extract tool calls from LLM response"""
    import re
    import json
    
    tool_calls = []
    
    # Look for tool call patterns in the response
    tool_pattern = r'<tool>(.*?)</tool>'
    matches = re.findall(tool_pattern, content, re.DOTALL)
    
    for match in matches:
        try:
            tool_call = json.loads(match.strip())
            tool_calls.append(tool_call)
        except json.JSONDecodeError:
            continue
    
    return tool_calls

async def should_use_agent_mode(user_message: str) -> bool:
    """
    Intelligently detect if the user request needs agent mode (tools)
    Returns True if tools are likely needed, False for simple chat
    """
    message_lower = user_message.lower()
    
    # Keywords that indicate need for tools
    tool_keywords = [
        # File operations
        "list", "show", "read", "write", "save", "create", "edit", "delete", "file", "files",
        # Research operations
        "research", "find", "search", "look up", "case study", "case studies",
        # Workspace operations
        "workspace", "directory", "folder", "output", "knowledge base",
        # Action words that typically need tools
        "generate", "create", "build", "make", "produce", "analyze",
        # Company-specific research
        "shopify", "hubspot", "salesforce", "klaviyo", "stripe", "zendesk",
        # Specific file references
        "guidelines", "target companies", "bloomreach", "summary"
    ]
    
    # Chat-only keywords (things that don't need tools)
    chat_keywords = [
        "what is", "how does", "explain", "tell me about", "define", "difference between",
        "help me understand", "can you explain", "what are", "how to", "why does",
        "concept", "theory", "principle", "example", "tutorial", "guide"
    ]
    
    # Check for tool keywords
    for keyword in tool_keywords:
        if keyword in message_lower:
            return True
    
    # Check for chat-only patterns
    for keyword in chat_keywords:
        if keyword in message_lower:
            return False
    
    # Default to chat mode for ambiguous cases
    return False

async def save_case_study_summary(company_domain: str, summary: Dict[str, Any]) -> str:
    """Save case study summary to file"""
    try:
        import os
        from datetime import datetime
        
        # Ensure output directory exists
        data_root = os.getenv("DATA_ROOT", "./data")
        case_studies_dir = os.path.join(data_root, "output", "case_studies")
        os.makedirs(case_studies_dir, exist_ok=True)
        
        # Create filename
        safe_domain = "".join(c for c in company_domain if c.isalnum() or c in ('-', '_')).lower()
        filename = f"{safe_domain}.md"
        filepath = os.path.join(case_studies_dir, filename)
        
        # Create markdown content
        content = f"""# Case Study: {company_domain}

## Summary
**Title:** {summary.get('title', 'N/A')}
**URL:** {summary.get('url', 'N/A')}
**Relevance Score:** {summary.get('relevance_score', 0)}

## Description
{summary.get('description', 'No description available')}

## Key Metrics
{chr(10).join(f"- {metric}" for metric in summary.get('key_metrics', []))}

## Content Preview
{summary.get('content_preview', 'No content preview available')}

---
*Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
*Source: {summary.get('url', 'N/A')}*
"""
        
        # Write to file
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info(f"Case study saved to: {filepath}")
        return filepath
        
    except Exception as e:
        logger.error(f"Error saving case study: {str(e)}")
        return ""

# File System Endpoints
@app.post("/fs/list", response_model=FileSystemResponse)
async def list_files_endpoint(request: FileListRequest):
    """List files and directories"""
    try:
        await event_logger.log_event("fs_list", {
            "path": request.path,
            "include_hidden": request.include_hidden
        })
        
        result = await file_system.list_files(request.path, request.include_hidden)
        
        if result["ok"]:
            await event_logger.log_event("fs_list_success", {
                "path": request.path,
                "total_files": result["total_files"],
                "total_directories": result["total_directories"]
            })
            return FileSystemResponse(ok=True, data=result)
        else:
            await event_logger.log_event("fs_list_error", {
                "path": request.path,
                "error": result["error"]
            })
            return FileSystemResponse(ok=False, error=result["error"])
            
    except Exception as e:
        logger.error(f"List files endpoint error: {str(e)}")
        await event_logger.log_event("error", {
            "type": "fs_list_error",
            "path": request.path,
            "message": str(e)
        })
        return FileSystemResponse(ok=False, error=str(e))

@app.post("/fs/read", response_model=FileSystemResponse)
async def read_file_endpoint(request: FileReadRequest):
    """Read file contents"""
    try:
        await event_logger.log_event("fs_read", {
            "path": request.path,
            "encoding": request.encoding
        })
        
        result = await file_system.read_file(request.path, request.encoding)
        
        if result["ok"]:
            await event_logger.log_event("fs_read_success", {
                "path": request.path,
                "size": result["size"],
                "is_binary": result.get("is_binary", False)
            })
            return FileSystemResponse(ok=True, data=result)
        else:
            await event_logger.log_event("fs_read_error", {
                "path": request.path,
                "error": result["error"]
            })
            return FileSystemResponse(ok=False, error=result["error"])
            
    except Exception as e:
        logger.error(f"Read file endpoint error: {str(e)}")
        await event_logger.log_event("error", {
            "type": "fs_read_error",
            "path": request.path,
            "message": str(e)
        })
        return FileSystemResponse(ok=False, error=str(e))

@app.post("/fs/write", response_model=FileSystemResponse)
async def write_file_endpoint(request: FileWriteRequest):
    """Write file contents"""
    try:
        await event_logger.log_event("fs_write", {
            "path": request.path,
            "size": len(request.content),
            "append": request.append
        })
        
        result = await file_system.write_file(
            request.path, 
            request.content, 
            request.encoding, 
            request.append
        )
        
        if result["ok"]:
            await event_logger.log_event("fs_write_success", {
                "path": request.path,
                "size": result["size"],
                "mode": result["mode"]
            })
            return FileSystemResponse(ok=True, data=result)
        else:
            await event_logger.log_event("fs_write_error", {
                "path": request.path,
                "error": result["error"]
            })
            return FileSystemResponse(ok=False, error=result["error"])
            
    except Exception as e:
        logger.error(f"Write file endpoint error: {str(e)}")
        await event_logger.log_event("error", {
            "type": "fs_write_error",
            "path": request.path,
            "message": str(e)
        })
        return FileSystemResponse(ok=False, error=str(e))

@app.post("/fs/edit", response_model=FileSystemResponse)
async def edit_file_endpoint(request: FileEditRequest):
    """Edit file contents using text replacement"""
    try:
        await event_logger.log_event("fs_edit", {
            "path": request.path,
            "old_text_length": len(request.old_text),
            "new_text_length": len(request.new_text)
        })
        
        result = await file_system.edit_file(
            request.path, 
            request.old_text, 
            request.new_text, 
            request.encoding
        )
        
        if result["ok"]:
            await event_logger.log_event("fs_edit_success", {
                "path": request.path,
                "replacements": result["replacements"],
                "size": result["size"]
            })
            return FileSystemResponse(ok=True, data=result)
        else:
            await event_logger.log_event("fs_edit_error", {
                "path": request.path,
                "error": result["error"]
            })
            return FileSystemResponse(ok=False, error=result["error"])
            
    except Exception as e:
        logger.error(f"Edit file endpoint error: {str(e)}")
        await event_logger.log_event("error", {
            "type": "fs_edit_error",
            "path": request.path,
            "message": str(e)
        })
        return FileSystemResponse(ok=False, error=str(e))

@app.post("/fs/delete", response_model=FileSystemResponse)
async def delete_file_endpoint(request: FileDeleteRequest):
    """Delete file or directory"""
    try:
        await event_logger.log_event("fs_delete", {
            "path": request.path
        })
        
        result = await file_system.delete_file(request.path)
        
        if result["ok"]:
            await event_logger.log_event("fs_delete_success", {
                "path": request.path,
                "type": result["type"]
            })
            return FileSystemResponse(ok=True, data=result)
        else:
            await event_logger.log_event("fs_delete_error", {
                "path": request.path,
                "error": result["error"]
            })
            return FileSystemResponse(ok=False, error=result["error"])
            
    except Exception as e:
        logger.error(f"Delete file endpoint error: {str(e)}")
        await event_logger.log_event("error", {
            "type": "fs_delete_error",
            "path": request.path,
            "message": str(e)
        })
        return FileSystemResponse(ok=False, error=str(e))

@app.post("/fs/search", response_model=FileSystemResponse)
async def search_files_endpoint(request: FileSearchRequest):
    """Search for files"""
    try:
        await event_logger.log_event("fs_search", {
            "query": request.query,
            "path": request.path,
            "file_extensions": request.file_extensions
        })
        
        result = await file_system.search_files(
            request.query, 
            request.path, 
            request.file_extensions
        )
        
        if result["ok"]:
            await event_logger.log_event("fs_search_success", {
                "query": request.query,
                "total_matches": result["total_matches"]
            })
            return FileSystemResponse(ok=True, data=result)
        else:
            await event_logger.log_event("fs_search_error", {
                "query": request.query,
                "error": result["error"]
            })
            return FileSystemResponse(ok=False, error=result["error"])
            
    except Exception as e:
        logger.error(f"Search files endpoint error: {str(e)}")
        await event_logger.log_event("error", {
            "type": "fs_search_error",
            "query": request.query,
            "message": str(e)
        })
        return FileSystemResponse(ok=False, error=str(e))

@app.post("/fs/info", response_model=FileSystemResponse)
async def file_info_endpoint(request: FileInfoRequest):
    """Get file information"""
    try:
        await event_logger.log_event("fs_info", {
            "path": request.path
        })
        
        result = await file_system.get_file_info(request.path)
        
        if result["ok"]:
            await event_logger.log_event("fs_info_success", {
                "path": request.path,
                "is_file": result["info"]["is_file"],
                "size": result["info"]["size"]
            })
            return FileSystemResponse(ok=True, data=result)
        else:
            await event_logger.log_event("fs_info_error", {
                "path": request.path,
                "error": result["error"]
            })
            return FileSystemResponse(ok=False, error=result["error"])
            
    except Exception as e:
        logger.error(f"File info endpoint error: {str(e)}")
        await event_logger.log_event("error", {
            "type": "fs_info_error",
            "path": request.path,
            "message": str(e)
        })
        return FileSystemResponse(ok=False, error=str(e))

@app.post("/fs/mkdir", response_model=FileSystemResponse)
async def create_directory_endpoint(request: FileInfoRequest):
    """Create directory"""
    try:
        await event_logger.log_event("fs_mkdir", {
            "path": request.path
        })
        
        result = await file_system.create_directory(request.path)
        
        if result["ok"]:
            await event_logger.log_event("fs_mkdir_success", {
                "path": request.path
            })
            return FileSystemResponse(ok=True, data=result)
        else:
            await event_logger.log_event("fs_mkdir_error", {
                "path": request.path,
                "error": result["error"]
            })
            return FileSystemResponse(ok=False, error=result["error"])
            
    except Exception as e:
        logger.error(f"Create directory endpoint error: {str(e)}")
        await event_logger.log_event("error", {
            "type": "fs_mkdir_error",
            "path": request.path,
            "message": str(e)
        })
        return FileSystemResponse(ok=False, error=str(e))

@app.get("/search/test")
async def test_search():
    """Test endpoint to verify search functionality"""
    try:
        # Test Brave Search
        brave_status = "available" if web_search_manager.brave_search else "not available"
        scraperjs_status = "available" if web_search_manager.scraperjs else "not available"
        
        return {
            "brave_search": brave_status,
            "scraperjs": scraperjs_status,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Search test error: {str(e)}")
        return {
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@app.post("/send-email", response_model=EmailSendResponse)
async def send_email(request: EmailSendRequest):
    """Send email via SendGrid"""
    try:
        logger.info(f"Sending email to {request.to_email} with subject: {request.subject}")
        
        result = await email_service.send_email(
            to_email=request.to_email,
            subject=request.subject,
            content=request.content
        )
        
        if result["success"]:
            return EmailSendResponse(
                success=True,
                message=result["message"]
            )
        else:
            return EmailSendResponse(
                success=False,
                message="Failed to send email",
                error=result["error"]
            )
            
    except Exception as e:
        logger.error(f"Error in send_email endpoint: {str(e)}")
        return EmailSendResponse(
            success=False,
            message="Internal server error",
            error=str(e)
        )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)

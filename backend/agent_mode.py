import os
import json
import re
import logging
import time
from typing import Dict, Any, List, Optional, Tuple, AsyncGenerator
from search_tools import WebSearchManager, SearchError

logger = logging.getLogger(__name__)

class AgentMode:
    """
    Agent Mode implementation with step-bounded tool loops
    Based on research-agent-lesson patterns
    """
    
    def __init__(self, web_search_manager: WebSearchManager, file_system_tools=None, max_steps: int = 3):
        self.web_search_manager = web_search_manager
        self.file_system_tools = file_system_tools
        self.max_steps = max_steps
        self.tools = {
            "web_search": self.web_search_tool,
            "case_study_lookup": self.case_study_lookup_tool,
            "file_read": self.file_read_tool,
            "file_write": self.file_write_tool,
            "file_edit": self.file_edit_tool,
            "file_list": self.file_list_tool,
            "file_search": self.file_search_tool,
            "workspace_overview": self.workspace_overview_tool,
            "email_write": self.email_write_tool,
            "save_as_markdown": self.save_as_markdown_tool,
        }
        
    async def get_system_prompt(self) -> str:
        """Get the system prompt for Agent Mode with current file listings"""
        # Get current file listings for intelligent file references
        file_context = await self._get_file_context()
        
        return """You are an intelligent assistant that can use web search and file system tools when needed. You can chain multiple tools together and loop through multiple steps to complete complex tasks.

Available Tools:
- web_search: Search the web for current information. Args: {{"query": "search term"}}
- case_study_lookup: Find case studies for specific companies. Args: {{"company_domain": "company name", "rep_domain": "your-company.com"}}
- file_read: Read contents of a file. Args: {{"path": "file/path"}}
- file_write: Write content to a file. Args: {{"path": "file/path", "content": "content to write"}}
- file_edit: Edit file by replacing text. Args: {{"path": "file/path", "old_text": "text to replace", "new_text": "replacement text"}}
- file_list: List files in a directory. Args: {{"path": "directory/path"}}
- file_search: Search for files by name or content. Args: {{"query": "search term", "path": "directory/path"}}
- workspace_overview: Get complete overview of all files in workspace. Args: {{}}
- save_as_markdown: Save case study analysis as structured markdown. Args: {{"company_domain": "company name", "rep_domain": "your-company.com", "output_path": "optional/path"}}

AGENT MODE CAPABILITIES:
- You can use multiple tools in sequence (tool chaining)
- You can loop through multiple steps to complete complex tasks
- You can research, analyze, save, and create multiple files
- You can perform multi-step workflows like: research → summarize → save → create emails

TOOL SELECTION GUIDE:
- Use case_study_lookup if user asks for case studies about a specific company
- Use web_search for current events, recent information, or specific research queries
- Use file_read to read existing files from the workspace
- Use file_write to save content to files (case studies, summaries, etc.)
- Use file_edit to modify existing files by replacing specific text
- Use file_list to see what files are available in a directory
- Use file_search to find specific files by name or content
- Use workspace_overview to see ALL files in the workspace at once (most efficient for "show me everything")
- Use email_write to create email drafts with typewriter effect preview and optional sending
- Use save_as_markdown to save case study analysis as structured markdown files (combines lookup + formatting + saving)
- For general conversations, coding help, explanations, or questions you can answer directly, provide an answer WITHOUT using tools
- For follow-up questions about content just created (like "read it", "show me", "what's in there"), use file_read to show the specific file
- Do NOT re-run research tools for simple follow-up questions about existing content

DETAILED RESEARCH WORKFLOW:
When conducting comprehensive research (NOT simple lookups), follow this systematic approach:
1. SEARCH STRATEGY: Use multiple targeted searches focusing on:
   - Industry statistics and market data
   - Financial metrics and performance data
   - Growth rates, revenue figures, user numbers
   - Competitive analysis and benchmarks
   - Recent trends and forecasts
2. DATA COLLECTION: Look for:
   - Annual reports and SEC filings
   - Industry research from credible sources (McKinsey, Deloitte, etc.)
   - Government data and statistics
   - Academic studies and white papers
   - Third-party market research reports
3. DOCUMENTATION: Create structured documents with:
   - Executive summary with key findings
   - Quantitative data tables and metrics
   - Source citations with clickable links
   - Data quality assessment
   - Actionable insights and recommendations
   - Reference links section with all source URLs
4. VALIDATION: Cross-reference data from multiple sources for accuracy

EMAIL WORKFLOW:
When users ask to "send email", "write email", "draft email", or "create email":
1. Use the email_write tool with these EXACT parameters:
   - subject: The email subject line
   - content: The email body/message
   - to_email: Recipient email address (optional)
   - path: File path to save draft (optional)
2. The frontend will show a typewriter preview of the email being written
3. Users can then enter a recipient email address and send via SendGrid
4. Always include professional, clear subject lines and well-formatted content
5. CRITICAL: If referencing case studies or research, include clickable links in email content
6. Use format: "You can view the detailed case study [here](URL)" or "Read the full analysis [in this link](URL)"
7. NEVER include raw URLs in email content - always use clean hyperlinked text like "here" or "this link"
8. Structure emails professionally with proper formatting, bullet points, and clear value propositions

EXAMPLE EMAIL TOOL USAGE:
<tool>
{
  "name": "email_write",
  "args": {
    "subject": "Bloomreach Case Study: 50% Faster Customer Onboarding",
    "content": "Hi [Name],\n\nI hope this message finds you well.\n\nI wanted to share an insightful case study that demonstrates how Bloomreach transformed their customer onboarding process:\n\n**Key Results:**\n• 50% reduction in onboarding time\n• Enhanced value delivery efficiency\n• Higher customer satisfaction (NPS)\n• Increased market expansion opportunities\n\nThis transformation was achieved through strategic data integration improvements that streamlined complex processes.\n\nYou can read the full case study [here](URL) to see the detailed implementation and results.\n\nI'd love to discuss how we can implement similar strategies to drive comparable value for your organization.\n\nBest regards,\nJulius\nSales Representative",
    "to_email": "recipient@example.com"
  }
}
</tool>

RESEARCH WORKFLOW:
When users ask to "research" a company or topic, ALWAYS follow this pattern:
1. FIRST: Check existing knowledge base files using file_search or file_read for that company/topic
2. If existing files found: Read and present the existing information
3. If no existing files OR user specifically asks for "new research": 
   - For COMPREHENSIVE research: Follow the DETAILED RESEARCH WORKFLOW above
   - For simple lookups: Use web_search or case_study_lookup
4. ALWAYS save detailed findings to structured documents in output directory
5. Include quantitative data, metrics, and clickable source links in all research documents
6. Create executive summaries and data tables for easy reference
7. CRITICAL: Always include source URLs as clickable markdown links [Source Title](URL)
8. For case studies, include "This link" references to actual case study URLs

READING WORKFLOW:
When reading existing files (file_read), simply:
1. Read the requested file
2. Show the content to the user
3. Do NOT save anything (you're just reading existing content)

FOLLOW-UP QUESTIONS:
When users ask follow-up questions about content you just created or referenced (like "read the summary", "show me the findings", "what did you save"):
1. Look at the conversation history to see what files you recently created or mentioned
2. If you just saved a file (like "goldman_sachs_case_study_summary.md"), use file_read to show that specific file
3. Provide a direct answer WITHOUT re-running the original research tools
4. Do NOT repeat the entire research process for simple "read" or "show" requests
5. Context matters: if you just said "saved to file X", then "read the summary" means "read file X"

IMPORTANT: Always check existing files BEFORE doing web searches. Our knowledge base contains valuable case studies that should be presented first!

CRITICAL: You must respond in this format:

<think>
Your reasoning about what to do next. If you just received tool results, analyze them and decide if you need more information or if you can provide a final answer.
</think>

<tool>
{{
  "name": "web_search",
  "args": {{
    "query": "your search query here"
  }}
}}
</tool>

OR (if you have enough information):

<answer>
Your final answer to the user based on the search results. ALWAYS include the actual URLs as clickable markdown links [title](url).
</answer>

IMPORTANT: If you have all the information needed to answer the user's question, you MUST provide an <answer> tag. If you received file content or search results that answer the question, don't just think about it - provide the answer!

""" + file_context + """

IMPORTANT RULES:
1. ALWAYS start with <think> tags
2. After receiving tool results, you can chain multiple tools or provide a final answer
3. Maximum """ + str(self.max_steps) + """ steps total
4. ALWAYS include actual source URLs as clickable markdown links [title](url) in your final answer
5. You can reference existing files by name (e.g., "read the bloomreach study") - I'll find the right file path
6. When users mention file names, use file_search or file_read tools to access them
7. You can chain tools together - search → read files → write summaries → etc.
8. CRITICAL: Do NOT repeat the same tool call - if you get results, either use a different tool or provide your final answer
9. CRITICAL: When creating emails about research/case studies, ALWAYS include "You can view [this link](URL)" references
10. Extract and preserve source URLs from all research results and include them in documents and emails
11. IMPORTANT: When mentioning saved files, only use the filename (e.g. "bloomreach_case_study.md") NOT the full path (e.g. "output/case_studies/bloomreach_case_study.md")
12. After getting search results, you should typically provide an answer rather than searching again
13. If you have information from tools, provide a final answer - don't just keep thinking
14. Maximum 5 tool calls per conversation - after that, you MUST provide your final answer
15. Be efficient - if you need to list files, start with the root directory (path: "") to see everything at once

Example flows:
Workspace overview: <think>User wants to see all files</think> <tool>{{"name": "workspace_overview", "args": {{}}}}</tool> → <answer>Here's your complete workspace: [detailed file listing]</answer>

Reading existing file: <think>User wants to see existing content</think> <tool>{{"name": "file_read", "args": {{"path": "output/case_studies/hubspot.md"}}}}</tool> → <answer>Here's the content of the HubSpot summary: [content]</answer>

COMPREHENSIVE research workflow: <think>I need to conduct detailed research on HubSpot with quantitative data</think> <tool>{{"name": "web_search", "args": {{"query": "HubSpot annual revenue 2023 financial metrics"}}}}</tool> → <think>Found some financial data, need more market data</think> <tool>{{"name": "web_search", "args": {{"query": "HubSpot market share CRM software statistics"}}}}</tool> → <think>Good data collected, now I'll create a comprehensive research document with source links</think> <tool>{{"name": "file_write", "args": {{"path": "output/research/hubspot_comprehensive_analysis.md", "content": "# HubSpot Comprehensive Analysis\\n\\n## Executive Summary\\n- Revenue: $1.7B (2023)\\n- Market Cap: $28B\\n- CRM Market Share: 8.5%\\n\\n## Financial Metrics\\n[detailed tables with sources]\\n\\n## Market Analysis\\n[quantitative data with citations]\\n\\n## Sources\\n- [HubSpot Investor Relations](https://investors.hubspot.com)\\n- [CRM Market Report](https://example.com/crm-report)"}}}}</tool> → <think>Now I'll send a professional email with the research and clean links</think> <tool>{{"name": "email_write", "args": {{"subject": "HubSpot Market Analysis: $1.7B Revenue & 8.5% Market Share", "content": "Hi,\\n\\nI hope this message finds you well.\\n\\nI've completed comprehensive research on HubSpot that reveals impressive growth metrics:\\n\\n**Key Findings:**\\n• Revenue: $1.7B (2023)\\n• Market Cap: $28B\\n• CRM Market Share: 8.5%\\n\\nThe analysis includes detailed financial metrics, competitive positioning, and market trends that could inform our strategic approach.\\n\\nYou can view the complete analysis [here](hubspot_comprehensive_analysis.md).\\n\\nI'd be happy to discuss these insights and their implications for our business strategy.\\n\\nBest regards,\\nJulius", "to_email": "user@example.com"}}}}</tool> → <answer>I've completed comprehensive research on HubSpot and created a detailed analysis document with quantitative data, financial metrics, and clickable source links. I've also sent a professionally formatted email with key findings and a clean link to the full document.</answer>"""

    async def run_agent_loop(self, messages: List[Dict[str, Any]], provider_manager) -> Dict[str, Any]:
        """
        Run the agent loop with step-bounded tool execution
        """
        agent_messages = messages.copy()
        step = 0
        total_usage = {"tokens_in": 0, "tokens_out": 0, "cost_usd": 0.0}
        previous_tool_calls = []  # Track previous tool calls to prevent loops
        tool_call_count = 0  # Track total tool calls
        thought_process = []  # Track thinking steps for frontend display
        
        # Add system prompt with current file context
        system_prompt = await self.get_system_prompt()
        agent_messages.insert(0, {
            "role": "system",
            "content": system_prompt
        })
        
        while step < self.max_steps:
            step += 1
            logger.info(f"Agent step {step}/{self.max_steps}")
            
            try:
                # Emit thought card for thinking
                thought_process.append({
                    "step": step,
                    "type": "thought_card",
                    "card_type": "thinking",
                    "content": f"Processing step {step}...",
                    "meta": f"Analyzing request and determining next actions",
                    "timestamp": time.time()
                })
                
                # Get response from LLM
                result = await provider_manager.get_completion(
                    provider="openai",
                    messages=agent_messages,
                    model="gpt-4o-mini"
                )
                
                # Accumulate usage
                usage = result.get("usage", {})
                total_usage["tokens_in"] += usage.get("tokens_in", 0)
                total_usage["tokens_out"] += usage.get("tokens_out", 0)
                total_usage["cost_usd"] += usage.get("cost_usd", 0.0)
                
                response_content = result["message"]["content"]
                
                # Parse the response
                thinking = self.parse_thinking(response_content)
                tool_call = self.parse_tool_call(response_content)
                final_answer = self.parse_answer(response_content)
                
                logger.info(f"Step {step} - Thinking: {thinking[:100] if thinking else 'None'}")
                logger.info(f"Step {step} - Tool call: {tool_call}")
                if final_answer:
                    logger.info(f"Step {step} - Final answer found (length: {len(final_answer)})")
                else:
                    logger.info(f"Step {step} - Final answer: None")
                
                # Capture thinking step for frontend display
                if thinking:
                    thought_process.append({
                        "step": step,
                        "type": "thinking",
                        "content": thinking.strip(),
                        "timestamp": time.time()
                    })
                
                # Add assistant response to conversation
                agent_messages.append({
                    "role": "assistant",
                    "content": response_content
                })
                
                # Execute tool call if present
                if tool_call:
                    tool_call_count += 1
                    
                    # Emit thought card for executing
                    thought_process.append({
                        "step": step,
                        "type": "thought_card",
                        "card_type": "executing",
                        "content": f"Executing {tool_call.get('name', 'unknown')} tool...",
                        "meta": f"Tool: {tool_call.get('name', 'unknown')}",
                        "timestamp": time.time()
                    })
                    
                    # Check for tool call limit (5 max)
                    if tool_call_count > 5:
                        logger.warning(f"Tool call limit reached ({tool_call_count}), forcing final answer")
                        return {
                            "message": {
                                "role": "assistant",
                                "content": "I've reached the maximum number of tool calls. Based on my research, I can provide you with the information I've gathered so far."
                            },
                            "usage": total_usage,
                            "agent_steps": step,
                            "thought_process": thought_process
                        }
                    
                    # Check for duplicate tool calls to prevent loops
                    tool_args = tool_call.get('args', {})
                    if not tool_args:
                        tool_args = {k: v for k, v in tool_call.items() if k not in ["name", "args"]}
                    tool_signature = f"{tool_call.get('name', '')}:{json.dumps(tool_args, sort_keys=True)}"
                    if tool_signature in previous_tool_calls:
                        logger.warning(f"Duplicate tool call detected: {tool_signature}")
                        # Force a final answer to break the loop
                        return {
                            "message": {
                                "role": "assistant",
                                "content": "I found the information but encountered a processing loop. Based on my search results, I can provide you with the available information about case studies."
                            },
                            "usage": total_usage,
                            "agent_steps": step,
                            "thought_process": thought_process
                        }
                    
                    previous_tool_calls.append(tool_signature)
                    
                    # Capture tool execution step for frontend display
                    thought_process.append({
                        "step": step,
                        "type": "tool_execution",
                        "tool_name": tool_call.get('name', 'unknown'),
                        "tool_args": tool_call.get('args', {}),
                        "timestamp": time.time()
                    })
                    
                    tool_result = await self.execute_tool(tool_call)
                    
                    # Capture tool result for frontend display
                    thought_process.append({
                        "step": step,
                        "type": "tool_result",
                        "tool_name": tool_call.get('name', 'unknown'),
                        "result": tool_result[:500] + "..." if len(str(tool_result)) > 500 else str(tool_result),
                        "timestamp": time.time()
                    })
                    
                    # Add tool result to conversation as user message
                    agent_messages.append({
                        "role": "user", 
                        "content": f"Tool result from {tool_call.get('name', 'unknown')}: {tool_result}"
                    })
                
                # Check if we have a final answer
                if final_answer:
                    logger.info(f"Agent completed in {step} steps")
                    
                    # Add final answer to thought process
                    thought_process.append({
                        "step": step,
                        "type": "final_answer",
                        "content": final_answer.strip(),
                        "timestamp": time.time()
                    })
                    
                    return {
                        "message": {
                            "role": "assistant",
                            "content": final_answer
                        },
                        "usage": total_usage,
                        "agent_steps": step,
                        "thought_process": thought_process
                    }
                
                # If we have a tool call but no final answer, continue the loop for chaining
                if tool_call:
                    logger.info(f"Step {step}: Tool executed, continuing for potential chaining")
                    continue
                
                # If no thinking, tool call, or final answer, but we have content, treat it as an answer
                if not thinking and not tool_call and not final_answer:
                    # Check if the response contains useful content that should be treated as an answer
                    content_length = len(response_content.strip())
                    if content_length > 50:  # Has substantial content
                        logger.info(f"LLM provided direct answer without format tags ({content_length} chars), treating as final answer")
                        return {
                            "message": {
                                "role": "assistant",
                                "content": response_content.strip()
                            },
                            "usage": total_usage,
                            "agent_steps": step,
                            "thought_process": thought_process
                        }
                    else:
                        logger.error(f"LLM response doesn't follow required format: {response_content[:200]}")
                        return {
                            "message": {
                                "role": "assistant",
                                "content": f"I encountered a formatting error in my response. Here's what I found so far based on the search results, but I may not have the complete information you requested."
                            },
                            "usage": total_usage,
                            "agent_steps": step,
                            "thought_process": thought_process
                        }
                
                # If we have thinking but no tool call or final answer, force an answer based on context
                if thinking and not tool_call and not final_answer:
                    # Force answer if we're past step 3 OR if we just completed an email task
                    should_force_answer = step > 3
                    
                    # Check if we just completed an email-related task
                    for msg in reversed(agent_messages[-2:]):  # Check last 2 messages
                        if msg.get("role") == "user" and "email_write" in msg.get("content", ""):
                            should_force_answer = True
                            break
                        if msg.get("role") == "user" and "file_write" in msg.get("content", "") and "email" in msg.get("content", "").lower():
                            should_force_answer = True
                            break
                    
                    if should_force_answer:
                        logger.warning(f"Agent thinking but not acting after step {step}, forcing final answer")
                        # Look for the last tool result to provide context
                        last_tool_result = None
                        for msg in reversed(agent_messages):
                            if msg.get("role") == "user" and msg.get("content", "").startswith("Tool result:"):
                                last_tool_result = msg["content"]
                                break
                        
                        # If the last tool was email-related, provide appropriate completion message
                        if last_tool_result and ("email" in last_tool_result.lower() or "status\": \"sent" in last_tool_result):
                            content = "Task completed successfully. The email has been sent as requested."
                        elif last_tool_result:
                            content = f"Based on my research and actions, I have completed the requested task. {last_tool_result}"
                        else:
                            content = "I have completed the requested task based on the available information."
                    
                    return {
                        "message": {
                            "role": "assistant",
                            "content": content
                        },
                        "usage": total_usage,
                        "agent_steps": step,
                        "thought_process": thought_process
                    }
                
            except Exception as e:
                logger.error(f"Agent step {step} error: {str(e)}")
                return {
                    "message": {
                        "role": "assistant",
                        "content": f"I encountered an error during my research: {str(e)}"
                    },
                    "usage": total_usage,
                    "agent_steps": step,
                    "thought_process": thought_process
                }
        
        # Max steps reached
        logger.warning(f"Agent reached max steps ({self.max_steps})")
        return {
            "message": {
                "role": "assistant",
                "content": "I've reached my maximum number of research steps. Based on what I found, I can provide you with the information I gathered so far."
            },
            "usage": total_usage,
            "agent_steps": step,
            "thought_process": thought_process
        }
    
    async def run_agent_loop_streaming(self, messages: List[Dict[str, Any]], provider_manager) -> AsyncGenerator[str, None]:
        """
        Run the agent loop with streaming thought process updates
        """
        agent_messages = messages.copy()
        step = 0
        total_usage = {"tokens_in": 0, "tokens_out": 0, "cost_usd": 0.0}
        previous_tool_calls = []
        tool_call_count = 0
        
        # Add system prompt
        system_prompt = await self.get_system_prompt()
        agent_messages.insert(0, {
            "role": "system",
            "content": system_prompt
        })
        
        # Send initial status
        yield f"data: {json.dumps({'type': 'status', 'message': 'Agent started', 'step': 0})}\n\n"
        
        while step < self.max_steps:
            step += 1
            logger.info(f"Agent step {step}/{self.max_steps}")
            
            # Send step start
            yield f"data: {json.dumps({'type': 'step_start', 'step': step})}\n\n"
            
            try:
                # Send thinking card IMMEDIATELY when step starts
                yield f"data: {json.dumps({'type': 'thought_card', 'card_type': 'thinking', 'step': step, 'content': f'Processing step {step}...', 'icon': '💭', 'title': 'Thinking'})}\n\n"
                
                # Longer delay to slow down card display
                import asyncio
                await asyncio.sleep(1.0)  # 1 second delay
                
                # Get response from LLM
                result = await provider_manager.get_completion(
                    provider="openai",
                    messages=agent_messages,
                    model="gpt-4o-mini"
                )
                
                # Accumulate usage
                usage = result.get("usage", {})
                total_usage["tokens_in"] += usage.get("tokens_in", 0)
                total_usage["tokens_out"] += usage.get("tokens_out", 0)
                total_usage["cost_usd"] += usage.get("cost_usd", 0.0)
                
                response_content = result["message"]["content"]
                
                # Parse the response
                thinking = self.parse_thinking(response_content)
                tool_call = self.parse_tool_call(response_content)
                final_answer = self.parse_answer(response_content)
                
                # Update thinking card with actual content
                if thinking:
                    yield f"data: {json.dumps({'type': 'thought_card', 'card_type': 'thinking', 'step': step, 'content': thinking.strip(), 'icon': '💭', 'title': 'Thinking'})}\n\n"
                    # Longer delay to slow down card display
                    import asyncio
                    await asyncio.sleep(1.5)  # 1.5 second delay
                
                # Add assistant response to conversation
                agent_messages.append({
                    "role": "assistant",
                    "content": response_content
                })
                
                # Execute tool call if present
                if tool_call:
                    tool_call_count += 1
                    
                    # Check for tool call limit
                    if tool_call_count > 5:
                        yield f"data: {json.dumps({'type': 'error', 'message': 'Tool call limit reached'})}\n\n"
                        break
                    
                    # Check for duplicate tool calls
                    tool_signature = f"{tool_call.get('name', '')}:{json.dumps(tool_call.get('args', {}), sort_keys=True)}"
                    if tool_signature in previous_tool_calls:
                        yield f"data: {json.dumps({'type': 'error', 'message': 'Duplicate tool call detected'})}\n\n"
                        break
                    
                    previous_tool_calls.append(tool_signature)
                    
                    # Stream tool execution as thought_card IMMEDIATELY
                    tool_name = tool_call.get('name', 'unknown')
                    tool_args = tool_call.get('args', {})
                    execution_content = f'Executing: {tool_name}'
                    yield f"data: {json.dumps({'type': 'thought_card', 'card_type': 'tool_execution', 'step': step, 'content': execution_content, 'tool_name': tool_name, 'tool_args': tool_args, 'icon': '🔧', 'title': 'Tool Execution'})}\n\n"
                    
                    # Delay before executing tool
                    import asyncio
                    await asyncio.sleep(1.0)  # 1 second delay before tool execution
                    
                    tool_result = await self.execute_tool(tool_call)
                    
                    # Stream tool result as thought_card IMMEDIATELY after execution
                    result_preview = tool_result[:200] + "..." if len(str(tool_result)) > 200 else str(tool_result)
                    tool_name = tool_call.get('name', 'unknown')
                    result_content = f'Result from {tool_name}: {result_preview}'
                    yield f"data: {json.dumps({'type': 'thought_card', 'card_type': 'tool_result', 'step': step, 'content': result_content, 'tool_name': tool_name, 'result': str(tool_result), 'icon': '✅', 'title': 'Tool Result'})}\n\n"
                    
                    # Longer delay to slow down card display
                    await asyncio.sleep(2.0)  # 2 second delay after tool result
                    
                    # Add tool result to conversation as user message
                    agent_messages.append({
                        "role": "user", 
                        "content": f"Tool result from {tool_call.get('name', 'unknown')}: {tool_result}"
                    })
                
                # Check if we have a final answer
                if final_answer:
                    yield f"data: {json.dumps({'type': 'thought_card', 'card_type': 'final_answer', 'step': step, 'content': final_answer.strip(), 'icon': '🎯', 'title': 'Final Answer'})}\n\n"
                    yield f"data: {json.dumps({'type': 'final_message', 'content': final_answer.strip()})}\n\n"
                    yield f"data: {json.dumps({'type': 'final_usage', 'usage': total_usage, 'agent_steps': step})}\n\n"
                    break
                
                # If we have a tool call but no final answer, continue
                if tool_call:
                    continue
                
                # Handle other cases similar to regular run_agent_loop
                if not thinking and not tool_call and not final_answer:
                    content_length = len(response_content.strip())
                    if content_length > 50:
                        yield f"data: {json.dumps({'type': 'thought_card', 'card_type': 'final_answer', 'step': step, 'content': response_content.strip(), 'icon': '🎯', 'title': 'Final Answer'})}\n\n"
                        yield f"data: {json.dumps({'type': 'final_message', 'content': response_content.strip()})}\n\n"
                        yield f"data: {json.dumps({'type': 'final_usage', 'usage': total_usage, 'agent_steps': step})}\n\n"
                        break
                
                # Force answer if thinking but not acting
                if thinking and not tool_call and not final_answer:
                    # Force answer if we're past step 3 OR if we just completed an email task
                    should_force_answer = step > 3
                    
                    # Check if we just completed an email-related task
                    for msg in reversed(agent_messages[-2:]):  # Check last 2 messages
                        if msg.get("role") == "user" and "email_write" in msg.get("content", ""):
                            should_force_answer = True
                            break
                        if msg.get("role") == "user" and "file_write" in msg.get("content", "") and "email" in msg.get("content", "").lower():
                            should_force_answer = True
                            break
                    
                    if should_force_answer:
                        # Look for the last tool result to provide context
                        last_tool_result = None
                        for msg in reversed(agent_messages):
                            if msg.get("role") == "user" and msg.get("content", "").startswith("Tool result:"):
                                last_tool_result = msg["content"]
                                break
                        
                        # If the last tool was email-related, provide appropriate completion message
                        if last_tool_result and ("email" in last_tool_result.lower() or "status\": \"sent" in last_tool_result):
                            final_content = "Task completed successfully. The email has been sent as requested."
                        elif last_tool_result:
                            final_content = f"Based on my research and actions, I have completed the requested task."
                        else:
                            final_content = "I have completed the requested task based on the available information."
                        
                        yield f"data: {json.dumps({'type': 'thought_card', 'card_type': 'final_answer', 'step': step, 'content': final_content, 'icon': '🎯', 'title': 'Final Answer'})}\n\n"
                        yield f"data: {json.dumps({'type': 'final_message', 'content': final_content})}\n\n"
                        yield f"data: {json.dumps({'type': 'final_usage', 'usage': total_usage, 'agent_steps': step})}\n\n"
                        break
                
            except Exception as e:
                logger.error(f"Agent step {step} error: {str(e)}")
                yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
                break
        
        # Max steps reached
        if step >= self.max_steps:
            yield f"data: {json.dumps({'type': 'thought_card', 'card_type': 'final_answer', 'step': step, 'content': 'I reached my maximum number of research steps. Here is what I found so far.', 'icon': '🎯', 'title': 'Final Answer'})}\n\n"
            yield f"data: {json.dumps({'type': 'final_message', 'content': 'I reached my maximum number of research steps. Here is what I found so far.'})}\n\n"
            yield f"data: {json.dumps({'type': 'final_usage', 'usage': total_usage, 'agent_steps': step})}\n\n"
    
    def parse_thinking(self, content: str) -> Optional[str]:
        """Parse thinking content from response"""
        match = re.search(r'<think>(.*?)</think>', content, re.DOTALL)
        return match.group(1).strip() if match else None
    
    def parse_tool_call(self, content: str) -> Optional[Dict[str, Any]]:
        """Parse tool call from response"""
        match = re.search(r'<tool>(.*?)</tool>', content, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1).strip())
            except json.JSONDecodeError as e:
                logger.error(f"Invalid tool JSON: {str(e)}")
                return None
        return None
    
    def parse_answer(self, content: str) -> Optional[str]:
        """Parse final answer from response"""
        # Try to find <answer> tags first
        match = re.search(r'<answer>(.*?)</answer>', content, re.DOTALL)
        if match:
            answer_content = match.group(1).strip()
            logger.info(f"Found answer in tags, extracted: {answer_content[:100]}...")
            return answer_content
        
        # If no <answer> tags but we have substantial content after tool results, treat it as answer
        if "Tool result:" in content:
            # Look for content after the last tool result
            parts = content.split("Tool result:")
            if len(parts) > 1:
                last_part = parts[-1].strip()
                # If there's substantial content after the tool result, it might be an answer
                if len(last_part) > 100 and not last_part.startswith("{"):
                    logger.info(f"Using fallback answer parsing: {last_part[:100]}...")
                    return last_part
        
        logger.info(f"No answer found in content: {content[:200]}...")
        return None
    
    async def execute_tool(self, tool_call: Dict[str, Any]) -> str:
        """Execute a tool call and return the result"""
        tool_name = tool_call.get("name")
        tool_args = tool_call.get("args", {})
        
        # Handle the case where args are at the top level (backward compatibility)
        if not tool_args:
            tool_args = {k: v for k, v in tool_call.items() if k not in ["name", "args"]}
        
        if tool_name not in self.tools:
            return f"Error: Unknown tool '{tool_name}'"
        
        try:
            logger.info(f"Executing tool '{tool_name}' with args: {tool_args}")
            result = await self.tools[tool_name](**tool_args)
            return json.dumps(result, indent=2)
        except Exception as e:
            logger.error(f"Tool execution error: {str(e)}")
            logger.error(f"Tool: {tool_name}, Args: {tool_args}")
            return f"Error executing {tool_name}: {str(e)}"
    
    async def web_search_tool(self, query: str) -> Dict[str, Any]:
        """Web search tool implementation"""
        try:
            if not self.web_search_manager.brave_search:
                return {
                    "tool": "web_search",
                    "query": query,
                    "error": "Brave Search is not available. Please configure BRAVE_API_KEY environment variable."
                }
            
            results = await self.web_search_manager.brave_search.search(query, count=5)
            return {
                "tool": "web_search",
                "query": query,
                "results": results["results"][:3],  # Return top 3 results
                "total_found": results["total"]
            }
        except Exception as e:
            return {
                "tool": "web_search",
                "query": query,
                "error": str(e)
            }
    
    async def case_study_lookup_tool(self, company_domain: str, context: str = "", rep_domain: str = "") -> Dict[str, Any]:
        """Case study lookup tool implementation"""
        try:
            result = await self.web_search_manager.case_study_tool.lookup_case_study(
                company_domain, context, rep_domain
            )
            return {
                "tool": "case_study_lookup",
                "company_domain": company_domain,
                "success": result.get("ok", False),
                "summary": result.get("summary", {}),
                "all_results": result.get("all_results", [])[:3],  # Include top 3 results with URLs
                "total_found": result.get("total_found", 0)
            }
        except Exception as e:
            return {
                "tool": "case_study_lookup",
                "company_domain": company_domain,
                "error": str(e)
            }
    
    async def file_read_tool(self, path: str) -> Dict[str, Any]:
        """File read tool implementation"""
        try:
            if not self.file_system_tools:
                return {"tool": "file_read", "path": path, "error": "File system tools not available"}
            
            result = await self.file_system_tools.read_file(path)
            return {
                "tool": "file_read",
                "path": path,
                "success": result.get("ok", False),
                "content": result.get("content", ""),
                "size": result.get("size", 0),
                "is_binary": result.get("is_binary", False),
                "error": result.get("error", None)
            }
        except Exception as e:
            return {
                "tool": "file_read",
                "path": path,
                "error": str(e)
            }
    
    async def file_write_tool(self, path: str, content: str, append: bool = False) -> Dict[str, Any]:
        """File write tool implementation"""
        try:
            if not self.file_system_tools:
                return {"tool": "file_write", "path": path, "error": "File system tools not available"}
            
            result = await self.file_system_tools.write_file(path, content, append=append)
            return {
                "tool": "file_write",
                "path": path,
                "success": result.get("ok", False),
                "size": result.get("size", 0),
                "mode": result.get("mode", "write"),
                "error": result.get("error", None)
            }
        except Exception as e:
            return {
                "tool": "file_write",
                "path": path,
                "error": str(e)
            }
    
    async def file_edit_tool(self, path: str, old_text: str, new_text: str) -> Dict[str, Any]:
        """File edit tool implementation (Ampcode pattern)"""
        try:
            if not self.file_system_tools:
                return {"tool": "file_edit", "path": path, "error": "File system tools not available"}
            
            result = await self.file_system_tools.edit_file(path, old_text, new_text)
            return {
                "tool": "file_edit",
                "path": path,
                "success": result.get("ok", False),
                "old_text": old_text,
                "new_text": new_text,
                "replacements": result.get("replacements", 0),
                "size": result.get("size", 0),
                "error": result.get("error", None)
            }
        except Exception as e:
            return {
                "tool": "file_edit",
                "path": path,
                "error": str(e)
            }
    
    async def file_list_tool(self, path: str = "") -> Dict[str, Any]:
        """File list tool implementation"""
        try:
            if not self.file_system_tools:
                return {"tool": "file_list", "path": path, "error": "File system tools not available"}
            
            result = await self.file_system_tools.list_files(path)
            return {
                "tool": "file_list",
                "path": path,
                "success": result.get("ok", False),
                "files": result.get("files", []),
                "directories": result.get("directories", []),
                "total_files": result.get("total_files", 0),
                "total_directories": result.get("total_directories", 0),
                "error": result.get("error", None)
            }
        except Exception as e:
            return {
                "tool": "file_list",
                "path": path,
                "error": str(e)
            }
    
    async def file_search_tool(self, query: str, path: str = "") -> Dict[str, Any]:
        """File search tool implementation"""
        try:
            if not self.file_system_tools:
                return {"tool": "file_search", "query": query, "error": "File system tools not available"}
            
            result = await self.file_system_tools.search_files(query, path)
            return {
                "tool": "file_search",
                "query": query,
                "path": path,
                "success": result.get("ok", False),
                "matches": result.get("matches", []),
                "total_matches": result.get("total_matches", 0),
                "error": result.get("error", None)
            }
        except Exception as e:
            return {
                "tool": "file_search",
                "query": query,
                "error": str(e)
            }
    
    async def workspace_overview_tool(self) -> Dict[str, Any]:
        """Get complete overview of all files in workspace"""
        try:
            if not self.file_system_tools:
                return {"tool": "workspace_overview", "error": "File system tools not available"}
            
            overview = {
                "tool": "workspace_overview",
                "directories": {}
            }
            
            # Key directories to check
            directories_to_check = [
                ("", "Root"),
                ("knowledge_base", "Knowledge Base"),
                ("output", "Output"),
                ("output/case_studies", "Case Studies"),
                ("output/emails", "Email Drafts"),
                ("output/slides", "Slides"),
                ("output/context", "Context Files"),
                ("logs", "Logs")
            ]
            
            for dir_path, dir_name in directories_to_check:
                try:
                    result = await self.file_system_tools.list_files(dir_path)
                    if result.get("ok", False):
                        overview["directories"][dir_name] = {
                            "path": dir_path,
                            "files": result.get("files", []),
                            "subdirectories": result.get("directories", []),
                            "total_files": result.get("total_files", 0)
                        }
                except Exception as e:
                    logger.debug(f"Error listing {dir_path}: {str(e)}")
                    overview["directories"][dir_name] = {
                        "path": dir_path,
                        "error": str(e)
                    }
            
            return overview
            
        except Exception as e:
            return {
                "tool": "workspace_overview",
                "error": str(e)
            }
    
    async def _get_file_context(self) -> str:
        """Get current file listings for the system prompt"""
        try:
            if not self.file_system_tools:
                return "\nCURRENT WORKSPACE: File system tools not available."
            
            # Get listings for key directories
            directories_to_check = [
                ("", "Root"),
                ("knowledge_base", "Knowledge Base"),
                ("output", "Output"),
                ("output/case_studies", "Case Studies"),
                ("output/emails", "Email Drafts"),
                ("output/slides", "Slides"),
                ("output/context", "Context Files"),
                ("logs", "Logs")
            ]
            
            file_context = "\nCURRENT WORKSPACE FILES:\n"
            
            for dir_path, dir_name in directories_to_check:
                try:
                    result = await self.file_system_tools.list_files(dir_path)
                    if result.get("success"):
                        files = result.get("files", [])
                        if files:
                            file_context += f"\n📁 {dir_name}:\n"
                            # Show up to 10 files per directory
                            for f in files[:10]:
                                if f.get('type') == 'file':
                                    size_kb = f.get('size', 0) / 1024
                                    file_context += f"  📄 {f['name']} ({size_kb:.1f}KB)\n"
                            
                            if len(files) > 10:
                                file_context += f"  ... and {len(files) - 10} more files\n"
                except Exception as e:
                    logger.debug(f"Error listing {dir_path}: {str(e)}")
                    continue
            
            file_context += "\nTo access files, use:\n"
            file_context += "- file_read: Read specific files by path\n"
            file_context += "- file_search: Find files by name (e.g., 'bloomreach', 'case study')\n"
            file_context += "- file_write: Save new content to files\n"
            file_context += "- file_list: List contents of specific directories (use path='' for root overview)\n"
            file_context += "\nTIP: Start with file_list path='' to see the full workspace structure efficiently!\n"
            
            return file_context
            
        except Exception as e:
            logger.error(f"Error getting file context: {str(e)}")
            return "\nCURRENT WORKSPACE: Error loading file context."
    
    async def email_write_tool(self, subject: str, content: str, to_email: str = "", path: str = "") -> Dict[str, Any]:
        """Email writing tool with typewriter preview and optional sending"""
        try:
            # Generate a path if not provided
            if not path:
                import time
                timestamp = int(time.time())
                safe_subject = "".join(c for c in subject if c.isalnum() or c in (' ', '-', '_')).rstrip()
                safe_subject = safe_subject.replace(' ', '_').lower()[:50]
                path = f"output/emails/email_{safe_subject}_{timestamp}.md"
            
            # Create email content with headers
            email_content = f"""# Email Draft

**To:** {to_email if to_email else '[Recipient Email]'}
**Subject:** {subject}

---

{content}

---
*Draft created: {time.strftime('%Y-%m-%d %H:%M:%S')}*
"""
            
            # Save the email draft
            if self.file_system_tools:
                result = await self.file_system_tools.write_file(path, email_content)
                
                # If to_email is provided, also send the email
                if to_email and to_email.strip():
                    try:
                        from gmail_service import email_service
                        send_result = await email_service.send_email(to_email, subject, content)
                        
                        if send_result["success"]:
                            return {
                                "tool": "email_write",
                                "path": path,
                                "subject": subject,
                                "to_email": to_email,
                                "content": content,
                                "preview_content": email_content,
                                "file_result": result,
                                "send_result": send_result,
                                "status": "sent",
                                "message": f"Email sent successfully to {to_email} and draft saved at {path}."
                            }
                        else:
                            return {
                                "tool": "email_write",
                                "path": path,
                                "subject": subject,
                                "to_email": to_email,
                                "content": content,
                                "preview_content": email_content,
                                "file_result": result,
                                "send_result": send_result,
                                "status": "draft_created_send_failed",
                                "message": f"Email draft created at {path} but sending failed: {send_result.get('error', 'Unknown error')}"
                            }
                    except Exception as send_error:
                        return {
                            "tool": "email_write",
                            "path": path,
                            "subject": subject,
                            "to_email": to_email,
                            "content": content,
                            "preview_content": email_content,
                            "file_result": result,
                            "status": "draft_created_send_failed",
                            "message": f"Email draft created at {path} but sending failed: {str(send_error)}"
                        }
                
                return {
                    "tool": "email_write",
                    "path": path,
                    "subject": subject,
                    "to_email": to_email,
                    "content": content,
                    "preview_content": email_content,
                    "file_result": result,
                    "status": "draft_created",
                    "message": f"Email draft created at {path}. Ready for preview and sending."
                }
            else:
                return {
                    "tool": "email_write",
                    "error": "File system tools not available for saving email draft",
                    "subject": subject,
                    "content": content,
                    "preview_content": email_content
                }
                
        except Exception as e:
            logger.error(f"Error in email_write_tool: {str(e)}")
            return {
                "tool": "email_write",
                "error": f"Error creating email draft: {str(e)}",
                "subject": subject,
                "content": content
            }
    
    async def save_as_markdown_tool(self, company_domain: str, context: str = "", rep_domain: str = "", output_path: str = None) -> Dict[str, Any]:
        """Save case study analysis as a structured markdown file"""
        try:
            # First, get the case study data
            case_study_data = await self.web_search_manager.case_study_tool.lookup_case_study(
                company_domain, context, rep_domain
            )
            
            if not case_study_data.get("ok", False):
                return {
                    "tool": "save_as_markdown",
                    "company_domain": company_domain,
                    "error": f"Failed to get case study data: {case_study_data.get('error', 'Unknown error')}",
                    "success": False
                }
            
            # Save as markdown using the case study tool's save method
            save_result = self.web_search_manager.case_study_tool.save_as_markdown(
                case_study_data, output_path
            )
            
            if save_result.get("success", False):
                return {
                    "tool": "save_as_markdown",
                    "company_domain": company_domain,
                    "success": True,
                    "filepath": save_result.get("filepath", ""),
                    "filename": save_result.get("filename", ""),
                    "size": save_result.get("size", 0),
                    "message": f"Case study analysis for {company_domain} saved as markdown at {save_result.get('filepath', '')}",
                    "analysis_summary": {
                        "total_results": case_study_data.get("total_found", 0),
                        "top_result_score": case_study_data.get("summary", {}).get("relevance_score", 0),
                        "key_metrics": case_study_data.get("summary", {}).get("key_metrics", [])
                    }
                }
            else:
                return {
                    "tool": "save_as_markdown",
                    "company_domain": company_domain,
                    "error": save_result.get("error", "Failed to save markdown"),
                    "success": False
                }
                
        except Exception as e:
            logger.error(f"Error in save_as_markdown_tool: {str(e)}")
            return {
                "tool": "save_as_markdown",
                "company_domain": company_domain,
                "error": f"Error saving case study as markdown: {str(e)}",
                "success": False
            }

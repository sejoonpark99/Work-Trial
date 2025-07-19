import os
import json
import re
import logging
import time
from typing import Dict, Any, List, Optional, Tuple, AsyncGenerator
from search_tools import WebSearchManager, SearchError
from browser_use_integration import browser_automation

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
            "apollo_process": self.apollo_process_tool,
            "browser_automate": self.browser_automate_tool,
            "file_read": self.file_read_tool,
            "file_write": self.file_write_tool,
            "file_edit": self.file_edit_tool,
            "file_list": self.file_list_tool,
            "file_search": self.file_search_tool,
            "workspace_overview": self.workspace_overview_tool,
            "email_write": self.email_write_tool,
        }
        
    async def get_system_prompt(self) -> str:
        """Get the system prompt for Agent Mode with current file listings"""
        # Get current file listings for intelligent file references
        file_context = await self._get_file_context()
        
        return """You are an intelligent assistant that can use web search and file system tools when needed. You can chain multiple tools together and loop through multiple steps to complete complex tasks.

Available Tools:
- web_search: Search the web for current information. Args: {"query": "search term"}
- case_study_lookup: Search for case studies using your own query. Args: {"query": "your search query with site: filtering"}
- apollo_process: Process domains through Apollo.io workflow. Args: {"csv_content": "CSV content as string", "headless": true, "run_apify": false}
- browser_automate: Launch browser automation with AI agent. Args: {"user_request": "describe what you want to automate"}
- file_read: Read contents of a file. Args: {"path": "file/path"}
- file_write: Write content to a file. Args: {"path": "file/path", "content": "content to write"}
- file_edit: Edit file by replacing text. Args: {"path": "file/path", "old_text": "text to replace", "new_text": "replacement text"}
- file_list: List files in a directory. Args: {"path": "directory/path"}
- file_search: Search for files by name or content. Args: {"query": "search term", "path": "directory/path"}
- workspace_overview: Get complete overview of all files in workspace. Args: {}

AGENT MODE CAPABILITIES:
- You can use multiple tools in sequence (tool chaining)
- You can loop through multiple steps to complete complex tasks
- You can research, analyze, save, and create multiple files
- You can perform multi-step workflows like: research → summarize → save → create emails

TOOL SELECTION GUIDE:
- Use case_study_lookup when searching for case studies - you generate the search query with site: filtering (e.g., "Nike case study ecommerce site:bloomreach.com")
- Use web_search for current events, recent information, or general research queries
- Use browser_automate for interactive web tasks like scraping, form filling, taking screenshots, or when user mentions "browser automate"
- Use file_read to read existing files from the workspace
- Use file_write to save content to files (case studies, summaries, etc.)
- Use file_edit to modify existing files by replacing specific text
- Use file_list to see what files are available in a directory
- Use file_search to find specific files by name or content
- Use workspace_overview to see ALL files in the workspace at once (most efficient for "show me everything")
- For general conversations, coding help, explanations, or questions you can answer directly, provide an answer WITHOUT using tools
- For follow-up questions about content just created (like "read it", "show me", "what's in there"), use file_read to show the specific file
- Do NOT re-run research tools for simple follow-up questions about existing content

CRITICAL DECISION-MAKING RULES:
1. AVOID INFINITE LOOPS: 
   - If you've already found case studies (even incomplete ones), STOP searching and work with what you have
   - Maximum 2-3 case_study_lookup calls per task - don't keep searching for "better" results
   - If content extraction fails (404, errors), accept the limited data and proceed

2. WORK WITH AVAILABLE DATA:
   - If case studies lack perfect structure, extract what's available and note limitations
   - Don't reject case studies just because they're missing some sections
   - Use partial data and clearly indicate what information is available vs. unavailable

3. EFFICIENT COMPLETION:
   - Once you have ANY usable case study data, proceed to summarization and file writing
   - Don't attempt to read non-existent files - if a file doesn't exist, create it
   - Complete tasks with available information rather than endlessly searching for perfect data

4. ERROR HANDLING:
   - When tools return errors (404, access denied, etc.), acknowledge the limitation and move forward
   - Document what went wrong but don't let errors block task completion
   - Use search result snippets and descriptions when full content isn't available

CASE STUDY SEARCH REQUIREMENTS:
IMPORTANT: When searching for case studies, you must find ACTUAL case studies with proper structure, not just any page mentioning the company.

WHAT MAKES A PROPER CASE STUDY:
- Has clear "Challenge" or "Problem" section
- Has "Solution" or "Implementation" section  
- Has "Results" or "Outcomes" section with metrics/data
- Often includes "Demo" or "Key Takeaways" section
- Contains quantifiable results (ROI, percentage improvements, cost savings, etc.)
- Is typically found in /case-studies/, /customer-stories/, /success-stories/ URL paths

CASE STUDY SEARCH EXAMPLES:
- For "I'm a sales rep at Bloomreach selling to Nike. Research case studies about ecommerce personalization": 
  → Search for case studies FROM Bloomreach's website about ecommerce personalization
  → Use: case_study_lookup with query "ecommerce personalization case study site:bloomreach.com"
  → NOT about Nike (Nike is the prospect you're selling TO)

- For "I'm at Anthropic, find case studies about AI implementation":
  → Search: "AI implementation case study site:anthropic.com"
  → Focus on YOUR company's case studies, not the prospect's

- Generate natural search queries based on:
  → The TOPIC/CONTEXT requested (e.g., "ecommerce personalization", "AI implementation")  
  → The REP'S company domain (e.g., site:bloomreach.com, site:anthropic.com)
  → Natural language that would find structured case studies

CASE STUDY QUALITY EVALUATION:
After finding case studies, evaluate them for quality:
- ✓ GOOD: URLs like /case-studies/nike-ecommerce-transformation/ with clear challenge/solution/results structure
- ✓ GOOD: Contains specific metrics (30% increase, $2M savings, 50% faster onboarding)
- ✗ BAD: Generic blog posts or news articles just mentioning the company
- ✗ BAD: Product pages or marketing materials without structured case study format
- ✗ BAD: Pages without clear problem/solution/results sections

If search results don't contain proper case studies, try different search terms or look for /customer-stories/ or /success-stories/ paths.

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

Your final answer to the user based on the search results. ALWAYS include the actual URLs as clickable markdown links [title](url).

MANDATORY RESPONSE FORMAT RULES:
1. You MUST ALWAYS provide a final answer when responding to user questions
2. Even if you need to say "I need more information", provide it as your response
3. After receiving tool results, analyze them and provide your findings immediately
4. If you have tool results, analyze them and provide your findings as your response
5. If you're unsure, provide your best answer and ask for clarification
6. EXAMPLE: I found several case studies but need more specific criteria. Which industry interests you most?

CRITICAL: After receiving tool results with case study information, you MUST immediately provide your response with the results. Do not continue searching - provide what you found.

IMPORTANT: If you have all the information needed to answer the user's question, you MUST provide your answer. If you received file content or search results that answer the question, don't just think about it - provide the answer!

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
Workspace overview: <think>User wants to see all files</think> <tool>{"name": "workspace_overview", "args": {}}</tool> → <answer>Here's your complete workspace: [detailed file listing]</answer>

Reading existing file: <think>User wants to see existing content</think> <tool>{"name": "file_read", "args": {"path": "output/case_studies/hubspot.md"}}</tool> → <answer>Here's the content of the HubSpot summary: [content]</answer>

COMPREHENSIVE research workflow: <think>I need to conduct detailed research on HubSpot with quantitative data</think> <tool>{"name": "web_search", "args": {"query": "HubSpot annual revenue 2023 financial metrics"}}</tool> → <think>Found some financial data, need more market data</think> <tool>{"name": "web_search", "args": {"query": "HubSpot market share CRM software statistics"}}</tool> → <think>Good data collected, now I'll create a comprehensive research document with source links</think> <tool>{"name": "file_write", "args": {"path": "output/research/hubspot_comprehensive_analysis.md", "content": "# HubSpot Comprehensive Analysis\\n\\n## Executive Summary\\n- Revenue: $1.7B (2023)\\n- Market Cap: $28B\\n- CRM Market Share: 8.5%\\n\\n## Financial Metrics\\n[detailed tables with sources]\\n\\n## Market Analysis\\n[quantitative data with citations]\\n\\n## Sources\\n- [HubSpot Investor Relations](https://investors.hubspot.com)\\n- [CRM Market Report](https://example.com/crm-report)"}}</tool> → <think>Now I'll send a professional email with the research and clean links</think> <tool>{"name": "email_write", "args": {"subject": "HubSpot Market Analysis: $1.7B Revenue & 8.5% Market Share", "content": "Hi,\\n\\nI hope this message finds you well.\\n\\nI've completed comprehensive research on HubSpot that reveals impressive growth metrics:\\n\\n**Key Findings:**\\n• Revenue: $1.7B (2023)\\n• Market Cap: $28B\\n• CRM Market Share: 8.5%\\n\\nThe analysis includes detailed financial metrics, competitive positioning, and market trends that could inform our strategic approach.\\n\\nYou can view the complete analysis [here](hubspot_comprehensive_analysis.md).\\n\\nI'd be happy to discuss these insights and their implications for our business strategy.\\n\\nBest regards,\\nJulius", "to_email": "user@example.com"}}</tool> → <answer>I've completed comprehensive research on HubSpot and created a detailed analysis document with quantitative data, financial metrics, and clickable source links. I've also sent a professionally formatted email with key findings and a clean link to the full document.</answer>"""

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
                        yield f"data: {json.dumps({'type': 'final_message', 'content': 'I have reached the maximum number of tool calls. Based on my research, I can provide you with the information I have gathered so far.'})}\n\n"
                        yield f"data: {json.dumps({'type': 'final_usage', 'usage': total_usage, 'agent_steps': step})}\n\n"
                        return
                    
                    # Check for duplicate tool calls to prevent loops
                    tool_args = tool_call.get('args', {})
                    if not tool_args:
                        tool_args = {k: v for k, v in tool_call.items() if k not in ["name", "args"]}
                    tool_signature = f"{tool_call.get('name', '')}:{json.dumps(tool_args, sort_keys=True)}"
                    if tool_signature in previous_tool_calls:
                        logger.warning(f"Duplicate tool call detected: {tool_signature}")
                        # Force a final answer to break the loop
                        yield f"data: {json.dumps({'type': 'final_message', 'content': 'I found the information but encountered a processing loop. Based on my search results, I can provide you with the available information about case studies.'})}\n\n"
                        yield f"data: {json.dumps({'type': 'final_usage', 'usage': total_usage, 'agent_steps': step})}\n\n"
                        return
                    
                    previous_tool_calls.append(tool_signature)
                    
                    # Capture tool execution step for frontend display
                    thought_process.append({
                        "step": step,
                        "type": "tool_execution",
                        "tool_name": tool_call.get('name', 'unknown'),
                        "tool_args": tool_call.get('args', {}),
                        "timestamp": time.time()
                    })
                    
                    # Create a streaming function that we can pass to execute_tool
                    streaming_buffer = []
                    def stream_to_buffer(data):
                        streaming_buffer.append(data)
                    
                    tool_result = await self.execute_tool(tool_call, step, stream_to_buffer)
                    
                    # Yield any buffered streaming data
                    for data in streaming_buffer:
                        yield data
                    
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
                    
                    yield f"data: {json.dumps({'type': 'final_message', 'content': final_answer.strip()})}\n\n"
                    yield f"data: {json.dumps({'type': 'final_usage', 'usage': total_usage, 'agent_steps': step})}\n\n"
                    return
                
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
                        yield f"data: {json.dumps({'type': 'final_message', 'content': response_content.strip()})}\n\n"
                        yield f"data: {json.dumps({'type': 'final_usage', 'usage': total_usage, 'agent_steps': step})}\n\n"
                        return
                    else:
                        logger.error(f"LLM response doesn't follow required format: {response_content[:200]}")
                        yield f"data: {json.dumps({'type': 'final_message', 'content': 'I encountered a formatting error in my response. Here is what I found so far based on the search results, but I may not have the complete information you requested.'})}\n\n"
                        yield f"data: {json.dumps({'type': 'final_usage', 'usage': total_usage, 'agent_steps': step})}\n\n"
                        return
                
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
                    
                    yield f"data: {json.dumps({'type': 'final_message', 'content': content})}\n\n"
                    yield f"data: {json.dumps({'type': 'final_usage', 'usage': total_usage, 'agent_steps': step})}\n\n"
                    return
                
            except Exception as e:
                logger.error(f"Agent step {step} error: {str(e)}")
                yield f"data: {json.dumps({'type': 'final_message', 'content': f'I encountered an error during my research: {str(e)}'})}\n\n"
                yield f"data: {json.dumps({'type': 'final_usage', 'usage': total_usage, 'agent_steps': step})}\n\n"
                return
        
        # Max steps reached
        logger.warning(f"Agent reached max steps ({self.max_steps})")
        yield f"data: {json.dumps({'type': 'thought_card', 'card_type': 'final_answer', 'step': step, 'content': 'I have reached my maximum number of research steps. Here is what I found so far.', 'icon': '🎯', 'title': 'Final Answer'})}\n\n"
        yield f"data: {json.dumps({'type': 'final_message', 'content': 'I have reached my maximum number of research steps. Here is what I found so far.'})}\n\n"
        yield f"data: {json.dumps({'type': 'final_usage', 'usage': total_usage, 'agent_steps': step})}\n\n"
        return
    
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
                    
                    # Special handling for case_study_lookup to surface the search query
                    if tool_name == 'case_study_lookup' and 'query' in tool_args:
                        execution_content = f'🔍 Running search: `{tool_args["query"]}`'
                    else:
                        execution_content = f'Executing: {tool_name}'
                    
                    yield f"data: {json.dumps({'type': 'thought_card', 'card_type': 'tool_execution', 'step': step, 'content': execution_content, 'tool_name': tool_name, 'tool_args': tool_args, 'icon': '🔧', 'title': 'Tool Execution'})}\n\n"
                    
                    # Delay before executing tool
                    import asyncio
                    await asyncio.sleep(1.0)  # 1 second delay before tool execution
                    
                    # Create a streaming function that we can pass to execute_tool
                    streaming_buffer = []
                    def stream_to_buffer(data):
                        streaming_buffer.append(data)
                    
                    tool_result = await self.execute_tool(tool_call, step, stream_to_buffer)
                    
                    # Yield any buffered streaming data
                    for data in streaming_buffer:
                        yield data
                    
                    # Stream tool result as thought_card IMMEDIATELY after execution
                    tool_name = tool_call.get('name', 'unknown')
                    
                    # Special handling for case_study_lookup to surface the search queries used
                    if tool_name == 'case_study_lookup':
                        try:
                            import json as json_module
                            result_dict = json_module.loads(tool_result) if isinstance(tool_result, str) else tool_result
                            
                            if isinstance(result_dict, dict) and 'search_queries_used' in result_dict:
                                queries_used = result_dict['search_queries_used']
                                total_found = result_dict.get('total_found', 0)
                                
                                if queries_used:
                                    result_content = f'🔍 Search completed: {total_found} results found using {len(queries_used)} queries:\n' + '\n'.join(f'• {q}' for q in queries_used)
                                else:
                                    result_content = f'🔍 Search completed: {total_found} results found'
                            else:
                                result_content = f'Result from {tool_name}: {str(tool_result)[:200]}...'
                        except:
                            result_content = f'Result from {tool_name}: {str(tool_result)[:200]}...'
                    else:
                        result_preview = tool_result[:200] + "..." if len(str(tool_result)) > 200 else str(tool_result)
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
            yield f"data: {json.dumps({'type': 'thought_card', 'card_type': 'final_answer', 'step': step, 'content': 'I have reached my maximum number of research steps. Here is what I found so far.', 'icon': '🎯', 'title': 'Final Answer'})}\n\n"
            yield f"data: {json.dumps({'type': 'final_message', 'content': 'I have reached my maximum number of research steps. Here is what I found so far.'})}\n\n"
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
                tool_json = match.group(1).strip()
                
                # Fix double curly braces issue - handle both outer and nested braces
                if tool_json.startswith('{{') and tool_json.endswith('}}'):
                    tool_json = tool_json[1:-1]  # Remove outer braces
                
                # Fix nested double braces in args field
                tool_json = re.sub(r'"args":\s*\{\{', '"args": {', tool_json)
                tool_json = re.sub(r'\}\}\s*\}', '} }', tool_json)
                
                return json.loads(tool_json)
            except json.JSONDecodeError as e:
                logger.error(f"Invalid tool JSON: {str(e)}")
                logger.error(f"Tool JSON content: {match.group(1).strip()}")
                return None
        return None
    
    def strip_internal_tags(self, content: str) -> str:
        """Strip internal tags like <think> and <tool> from content"""
        
        # Remove <think>...</think> tags and their content
        content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL)
        
        # Remove <tool>...</tool> tags and their content
        content = re.sub(r'<tool>.*?</tool>', '', content, flags=re.DOTALL)
        
        # Clean up extra whitespace and newlines
        content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)  # Multiple newlines to double
        content = content.strip()
        
        return content

    def parse_answer(self, content: str) -> Optional[str]:
        """Parse final answer from response"""
        # Try to find <answer> tags first and extract content WITHOUT the tags
        match = re.search(r'<answer>(.*?)</answer>', content, re.DOTALL)
        if match:
            answer_content = match.group(1).strip()  # This extracts only the content inside the tags
            logger.info(f"Found answer in tags, extracted content without tags: {answer_content[:100]}...")
            # Strip internal tags from the answer content
            return self.strip_internal_tags(answer_content)
        
        # If no <answer> tags but we have substantial content after tool results, treat it as answer
        if "Tool result:" in content:
            # Look for content after the last tool result
            parts = content.split("Tool result:")
            if len(parts) > 1:
                last_part = parts[-1].strip()
                # If there's substantial content after the tool result, it might be an answer
                if len(last_part) > 100 and not last_part.startswith("{"):
                    logger.info(f"Using fallback answer parsing: {last_part[:100]}...")
                    return self.strip_internal_tags(last_part)
        
        # If we have substantial content that looks like an answer, use it
        # Look for content that starts with common answer patterns
        answer_patterns = [
            r'Here are the summaries.*?:',
            r'Based on.*?research.*?:',
            r'I found.*?case studies.*?:',
            r'The following.*?results.*?:',
            r'\d+\.\s*\*\*.*?\*\*'  # Numbered lists with bold titles
        ]
        
        for pattern in answer_patterns:
            if re.search(pattern, content, re.IGNORECASE | re.DOTALL):
                # If we find answer-like content, return the full content
                logger.info(f"Found answer-like content, using full response: {content[:100]}...")
                return self.strip_internal_tags(content)
        
        logger.info(f"No answer found in content: {content[:200]}...")
        return None
    
    async def execute_tool(self, tool_call: Dict[str, Any], step: int = 0, yield_func=None) -> str:
        """Execute a tool call and return the result"""
        tool_name = tool_call.get("name")
        tool_args = tool_call.get("args", {})
        
        # Handle the case where args are at the top level (backward compatibility)
        if not tool_args:
            tool_args = {k: v for k, v in tool_call.items() if k not in ["name", "args"]}
        
        if tool_name not in self.tools:
            return f"Error: Unknown tool '{tool_name}'"
        
        try:
            logger.info(f"DEBUG: Executing tool '{tool_name}' with args: {tool_args}")
            
            # Special handling for file_write to enable live streaming
            if tool_name == "file_write" and yield_func:
                tool_args["step"] = step
                tool_args["yield_func"] = yield_func
            
            result = await self.tools[tool_name](**tool_args)
            logger.info(f"DEBUG: Tool '{tool_name}' returned result type: {type(result)}")
            logger.info(f"DEBUG: Tool '{tool_name}' result keys: {list(result.keys()) if isinstance(result, dict) else 'Not a dict'}")
            
            json_result = json.dumps(result, indent=2)
            logger.info(f"DEBUG: Tool '{tool_name}' JSON result length: {len(json_result)}")
            return json_result
        except Exception as e:
            logger.error(f"DEBUG: Tool execution error: {str(e)}")
            logger.error(f"DEBUG: Tool: {tool_name}, Args: {tool_args}")
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
    
    async def browser_automate_tool(self, user_request: str) -> Dict[str, Any]:
        """Browser automation tool using browser-use"""
        try:
            logger.info(f"Starting browser automation: {user_request}")
            
            # Run the automation
            result = await browser_automation.run_automation(user_request)
            
            if result["success"]:
                return {
                    "tool": "browser_automate",
                    "user_request": user_request,
                    "automation_type": result.get("automation_type"),
                    "task_description": result.get("task_description"), 
                    "result": result.get("result"),
                    "screenshot_available": bool(result.get("screenshot")),
                    "execution_mode": result.get("execution_mode", "docker"),
                    "script_id": result.get("script_id")
                }
            else:
                return {
                    "tool": "browser_automate",
                    "user_request": user_request,
                    "error": result.get("error", "Browser automation failed"),
                    "script_id": result.get("script_id")
                }
                
        except Exception as e:
            logger.error(f"Browser automation tool error: {str(e)}")
            return {
                "tool": "browser_automate", 
                "user_request": user_request,
                "error": str(e)
            }
    
    async def case_study_lookup_tool(self, query: str) -> Dict[str, Any]:
        """Case study lookup using web search WITH scraping - let LLM generate the query with site: filtering"""
        try:
            logger.info(f"DEBUG: Starting case_study_lookup_tool with query: '{query}'")
            
            # Parse the query to extract structured components for better search
            # Try to extract site: filter and context from the query
            import re
            site_match = re.search(r'site:([^\s]+)', query)
            rep_domain = site_match.group(1) if site_match else ""
            
            # Extract company name from quotes OR derive from rep_domain
            company_match = re.search(r'"([^"]+)"', query)
            if company_match:
                company_name = company_match.group(1)
            elif rep_domain:
                # Use the domain's root as the company name
                company_name = rep_domain.split('.')[0]  # "bloomreach" from "bloomreach.com"
            else:
                company_name = ""
            
            # Extract context (everything except site: and company name)
            context_query = query
            if site_match:
                context_query = context_query.replace(site_match.group(0), "").strip()
            if company_match:
                context_query = context_query.replace(company_match.group(0), "").strip()
            context_query = context_query.replace("case study", "").strip()
            
            logger.info(f"DEBUG: Parsed query - Company: '{company_name}', Context: '{context_query}', Rep domain: '{rep_domain}'")
            
            # Always force case-studies path filtering for better results
            search_queries = [
                f"{context_query} case study inurl:case-studies site:{rep_domain}",
                f"{context_query} success story inurl:customer-stories site:{rep_domain}",
                f"{context_query} customer story inurl:success-stories site:{rep_domain}",
                f"{context_query} case study site:{rep_domain}/en/case-studies",
                # Fallback to original query
                query
            ]
            
            logger.info(f"DEBUG: Generated {len(search_queries)} targeted search queries with inurl filters")
            
            all_results = []
            successful_queries = []
            
            # Try all search queries until we find case studies
            max_queries_to_try = len(search_queries)  # Try all queries
            
            for i, search_query in enumerate(search_queries[:max_queries_to_try]):
                try:
                    logger.info(f"DEBUG: Trying search query {i+1}/{max_queries_to_try}: '{search_query}'")
                    
                    # Use Brave Search only (no scraping) for speed and reliability
                    result = await self.web_search_manager.brave_search.search(search_query, count=8)
                    
                    if result.get("results"):
                        # Strict filtering: MUST have case-studies in URL AND must NOT have blog
                        filtered_results = []
                        for r in result.get("results", []):
                            url = r.get("url", "").lower()
                            
                            # MUST have case-studies related paths
                            has_case_studies = any(path in url for path in ["/case-studies/", "/customer-stories/", "/success-stories/", "case-study", "customer-story"])
                            
                            # MUST NOT have blog, news, or press paths
                            has_excluded_paths = any(path in url for path in ["/blog/", "/news/", "/press/", "/articles/", "blog."])
                            
                            if has_case_studies and not has_excluded_paths:
                                filtered_results.append(r)
                                logger.info(f"DEBUG: [ACCEPTED] case study URL: {url}")
                            else:
                                logger.info(f"DEBUG: [REJECTED] URL: {url} (case_studies={has_case_studies}, excluded={has_excluded_paths})")
                        
                        if filtered_results:
                            # Found actual case studies, use these
                            all_results.extend(filtered_results)
                            successful_queries.append(search_query)
                            logger.info(f"DEBUG: Query {i+1} returned {len(filtered_results)} valid case study URLs")
                            logger.info(f"DEBUG: Found actual case studies, stopping search")
                            break
                        else:
                            logger.info(f"DEBUG: Query {i+1} returned {len(result.get('results', []))} results but no valid case study URLs, continuing search")
                    else:
                        logger.info(f"DEBUG: Query {i+1} returned no results")
                        
                except Exception as query_error:
                    logger.error(f"DEBUG: Error with query {i+1}: {str(query_error)}")
                    continue
            
            # Remove duplicates based on URL
            seen_urls = set()
            unique_results = []
            for result in all_results:
                url = result.get('url', '')
                if url not in seen_urls:
                    seen_urls.add(url)
                    unique_results.append(result)
            
            logger.info(f"DEBUG: Final results: {len(unique_results)} unique results from {len(successful_queries)} successful queries")
            
            # Log detailed information about each result
            for i, res in enumerate(unique_results):
                logger.info(f"DEBUG: Result {i+1}:")
                logger.info(f"  Title: {res.get('title', 'N/A')}")
                logger.info(f"  URL: {res.get('url', 'N/A')}")
                logger.info(f"  Description: {res.get('description', 'N/A')[:200]}...")
                logger.info(f"  Type: {res.get('type', 'N/A')}")
            
            # Fetch actual case study content from the URLs
            detailed_results = []
            for result in unique_results[:3]:  # Limit to top 3 for performance
                try:
                    url = result.get("url", "")
                    logger.info(f"DEBUG: Fetching content from {url}")
                    
                    # Fetch the actual page content
                    import aiohttp
                    import asyncio
                    from bs4 import BeautifulSoup
                    
                    timeout = aiohttp.ClientTimeout(total=10)
                    async with aiohttp.ClientSession(timeout=timeout) as session:
                        async with session.get(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}) as response:
                            if response.status == 200:
                                html_content = await response.text()
                                soup = BeautifulSoup(html_content, 'html.parser')
                                
                                # Extract case study content
                                case_study_content = self.extract_case_study_content(soup, url)
                                
                                if case_study_content:
                                    detailed_results.append({
                                        "title": result.get("title", ""),
                                        "url": url,
                                        "description": result.get("description", ""),
                                        "content": case_study_content,
                                        "type": "case_study"
                                    })
                                else:
                                    # Create fallback content structure if extraction fails
                                    fallback_content = {
                                        "title": result.get("title", ""),
                                        "company": None,
                                        "challenge": "Content extraction failed - challenge details not available",
                                        "solution": "Content extraction failed - solution details not available", 
                                        "results": "Content extraction failed - results not available",
                                        "full_content": result.get("description", "Limited description available"),
                                        "key_metrics": []
                                    }
                                    detailed_results.append({
                                        "title": result.get("title", ""),
                                        "url": url,
                                        "description": result.get("description", ""),
                                        "content": fallback_content,
                                        "type": "case_study_partial"
                                    })
                            else:
                                logger.warning(f"Failed to fetch {url}: HTTP {response.status}")
                                # Create fallback for HTTP errors with clear error indication
                                error_content = {
                                    "title": result.get("title", ""),
                                    "company": None,
                                    "challenge": f"Unable to access case study - HTTP {response.status} error",
                                    "solution": "Content unavailable due to access error",
                                    "results": "Results unavailable due to access error", 
                                    "full_content": result.get("description", "Limited description from search results"),
                                    "key_metrics": [],
                                    "access_error": f"HTTP {response.status}"
                                }
                                detailed_results.append({
                                    "title": result.get("title", ""),
                                    "url": url,
                                    "description": result.get("description", ""),
                                    "content": error_content,
                                    "type": "case_study_error"
                                })
                                
                except Exception as e:
                    logger.error(f"Error fetching content from {url}: {str(e)}")
                    # Create fallback for exceptions with clear error indication
                    exception_content = {
                        "title": result.get("title", ""),
                        "company": None,
                        "challenge": f"Unable to access case study - Network/parsing error: {str(e)[:100]}",
                        "solution": "Content unavailable due to technical error",
                        "results": "Results unavailable due to technical error", 
                        "full_content": result.get("description", "Limited description from search results"),
                        "key_metrics": [],
                        "fetch_error": str(e)
                    }
                    detailed_results.append({
                        "title": result.get("title", ""),
                        "url": result.get("url", ""),
                        "description": result.get("description", ""),
                        "content": exception_content,
                        "type": "case_study_error"
                    })
                    
                # Add delay between requests to be respectful
                await asyncio.sleep(0.5)

            response = {
                "tool": "case_study_lookup",
                "original_query": query,
                "search_queries_used": successful_queries,
                "total_queries_tried": len(search_queries),
                "success": True,
                "results": detailed_results,
                "total_found": len(detailed_results),
                "method": "brave_search_with_content_extraction",
                "filtering": "strict_case_studies_only"
            }
            
            logger.info(f"DEBUG: case_study_lookup_tool returning response with {response['total_found']} detailed results")
            return response
                
        except Exception as e:
            logger.error(f"DEBUG: case_study_lookup_tool error: {str(e)}")
            return {
                "tool": "case_study_lookup",
                "query": query,
                "error": str(e)
            }

    def extract_case_study_content(self, soup, url):
        """Extract structured case study content from HTML"""
        try:
            content = {}
            
            # Extract title
            title = None
            for selector in ['h1', '.hero-title', '.page-title', '.case-study-title']:
                elem = soup.select_one(selector)
                if elem:
                    title = elem.get_text(strip=True)
                    break
            content['title'] = title or "Case Study"
            
            # Extract company name from title or content
            company = None
            if title:
                # Try to extract company name from title patterns
                company_patterns = [
                    r'^([^:]+):', # "Company Name: Title"
                    r'([^-]+)-', # "Company Name - Title"  
                    r'(\w+(?:\s+\w+){0,2})\s+(?:Case Study|Success Story|Customer Story)', # "Company Name Case Study"
                ]
                for pattern in company_patterns:
                    match = re.search(pattern, title, re.IGNORECASE)
                    if match:
                        company = match.group(1).strip()
                        break
            content['company'] = company
            
            # Extract main content sections
            main_content = ""
            
            # Look for case study specific sections  
            sections = soup.find_all(['div', 'section'], class_=re.compile(r'case-study|content|main|story'))
            if not sections:
                # Fallback to main content areas
                sections = soup.find_all(['main', 'article', '.content', '.body'])
                
            for section in sections:
                if section:
                    # Remove navigation, header, footer elements
                    for unwanted in section.find_all(['nav', 'header', 'footer', '.navigation', '.sidebar']):
                        unwanted.decompose()
                    
                    text = section.get_text(separator=' ', strip=True)
                    if len(text) > 200:  # Only include substantial content
                        main_content += text + " "
            
            # Extract specific challenge/solution/results if available
            challenge = self.extract_section(soup, ['challenge', 'problem', 'situation'])
            solution = self.extract_section(soup, ['solution', 'approach', 'implementation'])
            results = self.extract_section(soup, ['results', 'outcome', 'benefits', 'impact'])
            
            content['challenge'] = challenge
            content['solution'] = solution  
            content['results'] = results
            content['full_content'] = main_content[:2000]  # Limit content length
            
            # Extract key metrics if available
            metrics = []
            metric_patterns = [
                r'(\d+%)\s+(?:increase|improvement|growth|boost)',
                r'(\d+x)\s+(?:increase|improvement|growth|boost)', 
                r'(\$[\d,]+(?:\.\d+)?[kKmMbB]?)\s+(?:revenue|sales|savings)',
                r'(\d+(?:,\d+)*)\s+(?:customers|users|leads|conversions)'
            ]
            
            for pattern in metric_patterns:
                matches = re.findall(pattern, main_content, re.IGNORECASE)
                metrics.extend(matches)
            
            content['key_metrics'] = metrics[:5]  # Limit to top 5 metrics
            
            # Only return content if we extracted meaningful information
            if main_content and len(main_content) > 300:
                return content
            else:
                return None
                
        except Exception as e:
            logger.error(f"Error extracting content from {url}: {str(e)}")
            return None
    
    def extract_section(self, soup, keywords):
        """Extract specific sections based on keywords"""
        try:
            for keyword in keywords:
                # Look for headings with keyword
                for heading in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
                    if keyword.lower() in heading.get_text().lower():
                        # Get the next sibling content
                        content = ""
                        for sibling in heading.next_siblings:
                            if hasattr(sibling, 'name'):
                                if sibling.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                                    break  # Stop at next heading
                                text = sibling.get_text(strip=True)
                                if text:
                                    content += text + " "
                        if len(content) > 50:
                            return content.strip()[:500]  # Limit section length
                            
                # Look for divs/sections with keyword in class or id
                for element in soup.find_all(['div', 'section'], attrs={'class': re.compile(keyword, re.I)}):
                    text = element.get_text(strip=True)
                    if len(text) > 50:
                        return text[:500]
                        
            return None
        except:
            return None
    
    async def apollo_process_tool(self, csv_content: str, headless: bool = True, run_apify: bool = False) -> Dict[str, Any]:
        """Apollo processing tool implementation"""
        try:
            logger.info(f"DEBUG: Starting apollo_process_tool with CSV content length: {len(csv_content)}")
            
            # Use the Apollo processing tool from web_search_manager
            result = await self.web_search_manager.apollo_tool.process_domains_csv(csv_content, headless, run_apify)
            
            logger.info(f"DEBUG: Apollo processing result: {result}")
            
            return {
                "tool": "apollo_process",
                "success": result.get("success", False),
                "search_id": result.get("search_id"),
                "search_url": result.get("search_url"),
                "bulk_url": result.get("bulk_url"),
                "job_titles": result.get("job_titles", []),
                "domains_processed": result.get("domains_processed", 0),
                "domains_list": result.get("domains_list", []),
                "message": result.get("message", ""),
                "error": result.get("error", None)
            }
            
        except Exception as e:
            logger.error(f"DEBUG: apollo_process_tool error: {str(e)}")
            return {
                "tool": "apollo_process",
                "success": False,
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
    
    async def file_write_tool(self, path: str, content: str, append: bool = False, step: int = 0, yield_func=None) -> Dict[str, Any]:
        """File write tool implementation with live streaming"""
        try:
            if not self.file_system_tools:
                return {"tool": "file_write", "path": path, "error": "File system tools not available"}
            
            # Extract filename and file type for frontend preview
            filename = os.path.basename(path)
            file_extension = filename.split('.')[-1].lower() if '.' in filename else 'txt'
            
            # Send initial file creation thought card
            if yield_func:
                yield_func(f"data: {json.dumps({'type': 'thought_card', 'card_type': 'file_writing', 'step': step, 'content': f'Creating {filename}...', 'file_path': path, 'file_type': file_extension, 'icon': '📝', 'title': 'File Creation'})}\n\n")
                
                # Send live writing content in chunks with typewriter effect
                import asyncio
                chunk_size = 100  # Characters per chunk
                for i in range(0, len(content), chunk_size):
                    chunk = content[:i + chunk_size]
                    progress = min(100, int((i + chunk_size) / len(content) * 100))
                    
                    yield_func(f"data: {json.dumps({'type': 'thought_card', 'card_type': 'file_writing', 'step': step, 'content': chunk, 'file_path': path, 'filename': filename, 'file_type': file_extension, 'progress': progress, 'writing': True, 'icon': '📝', 'title': 'Writing File'})}\n\n")
                    
                    # Small delay for typewriter effect
                    await asyncio.sleep(0.05)
            
            # Actually write the file
            result = await self.file_system_tools.write_file(path, content, append=append)
            
            # Send completion thought card
            if yield_func:
                yield_func(f"data: {json.dumps({'type': 'thought_card', 'card_type': 'file_complete', 'step': step, 'content': content, 'file_path': path, 'filename': filename, 'file_type': file_extension, 'size': result.get('size', 0), 'writing': False, 'icon': '✅', 'title': 'File Complete'})}\n\n")
            
            return {
                "tool": "file_write",
                "path": path,
                "content": content,  # Include content for live preview
                "filename": filename,
                "file_type": file_extension,
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

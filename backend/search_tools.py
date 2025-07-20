import os
import requests
import json
from typing import Dict, Any, List, Optional
import logging
from urllib.parse import quote
import time
import asyncio
import subprocess

logger = logging.getLogger(__name__)

class SearchError(Exception):
    pass

class OpenAIWebSearchTool:
    """
    Web search tool using Brave Search API + OpenAI for content reading and analysis
    """
    def __init__(self):
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.brave_api_key = os.getenv("BRAVE_API_KEY")
        
        if not self.openai_api_key:
            logger.warning("OPENAI_API_KEY not found in environment variables")
        if not self.brave_api_key:
            logger.warning("BRAVE_API_KEY not found in environment variables")
            
        self.brave_base_url = "https://api.search.brave.com/res/v1"
        self.brave_headers = {
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "X-Subscription-Token": self.brave_api_key
        } if self.brave_api_key else {}
        
        logger.info("OpenAIWebSearchTool: Initialized with Brave Search + OpenAI")
    
    async def search(self, query: str, count: int = 10, read_content: bool = True) -> Dict[str, Any]:
        """
        Perform web search using search engines and read content with OpenAI
        
        Args:
            query: Search query string
            count: Number of results to return
            read_content: Whether to read the actual content of pages
            
        Returns:
            Dictionary containing search results with optional content
        """
        try:
            # Input validation
            if not query or not isinstance(query, str) or len(query.strip()) == 0:
                raise SearchError("Query must be a non-empty string")
            
            if not isinstance(count, int) or count < 1 or count > 20:
                raise SearchError("Count must be an integer between 1 and 20")
            
            logger.info(f"OpenAIWebSearch: Searching for '{query}' with read_content={read_content}")
            
            # Use Brave Search API to get URLs
            search_urls = await self._search_brave(query, count)
            
            results = []
            for i, url_data in enumerate(search_urls[:count]):
                result = {
                    "title": url_data.get("title", ""),
                    "url": url_data.get("url", ""),
                    "description": url_data.get("description", ""),
                    "rank": i + 1
                }
                
                # Read content if requested and OpenAI API key is available
                if read_content and self.openai_api_key:
                    try:
                        content = await self._read_url_content(url_data.get("url", ""))
                        result["content"] = content
                        result["content_read"] = True
                    except Exception as e:
                        logger.warning(f"Failed to read content from {url_data.get('url', '')}: {str(e)}")
                        result["content_read"] = False
                        result["content_error"] = str(e)
                else:
                    result["content_read"] = False
                    if not self.openai_api_key:
                        result["content_error"] = "OpenAI API key not available"
                
                results.append(result)
            
            search_result = {
                "query": query,
                "results": results,
                "total": len(results),
                "tool_type": "openai_websearch",
                "read_content_enabled": read_content,
                "brave_api_available": bool(self.brave_api_key),
                "openai_api_available": bool(self.openai_api_key),
                "validation": {
                    "query_valid": True,
                    "count_valid": True,
                    "parameters_validated": True
                }
            }
            
            logger.info(f"OpenAIWebSearch: Found {len(results)} results for '{query}'")
            return search_result
            
        except SearchError:
            raise
        except Exception as e:
            logger.error(f"OpenAIWebSearch error: {str(e)}")
            raise SearchError(f"OpenAIWebSearch error: {str(e)}")
    
    async def _search_brave(self, query: str, count: int) -> List[Dict[str, str]]:
        """Search using Brave Search API"""
        try:
            if not self.brave_api_key:
                logger.error("BRAVE_API_KEY not available")
                return []
            
            params = {
                "q": query,
                "count": min(count, 20),  # Brave API limit
                "offset": 0,
                "search_lang": "en",
                "country": "US",
                "safesearch": "moderate"
            }
            
            response = requests.get(
                f"{self.brave_base_url}/web/search",
                headers=self.brave_headers,
                params=params,
                timeout=30
            )
            
            response.raise_for_status()
            data = response.json()
            
            results = []
            if "web" in data and "results" in data["web"]:
                for result in data["web"]["results"]:
                    results.append({
                        "title": result.get("title", ""),
                        "url": result.get("url", ""),
                        "description": result.get("description", "")
                    })
            
            logger.info(f"Brave Search: Found {len(results)} results for '{query}'")
            return results
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Brave Search API error: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"Brave Search error: {str(e)}")
            return []
    
    async def _read_url_content(self, url: str) -> str:
        """Read and summarize URL content using OpenAI"""
        try:
            # Fetch the URL content
            response = requests.get(url, timeout=10, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            response.raise_for_status()
            
            # Parse HTML content
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style", "nav", "footer", "header", "aside"]):
                script.decompose()
            
            # Extract text content
            text = soup.get_text()
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            clean_text = ' '.join(chunk for chunk in chunks if chunk)
            
            # Limit content length for API processing
            if len(clean_text) > 4000:
                clean_text = clean_text[:4000] + "..."
            
            # Use OpenAI to summarize/extract key information
            if self.openai_api_key:
                summary = await self._summarize_with_openai(clean_text)
                return summary
            else:
                return clean_text[:1000] + "..." if len(clean_text) > 1000 else clean_text
            
        except Exception as e:
            logger.error(f"Error reading URL content: {str(e)}")
            return f"Error reading content: {str(e)}"
    
    async def _summarize_with_openai(self, content: str) -> str:
        """Summarize content using OpenAI API"""
        try:
            import openai
            
            openai.api_key = self.openai_api_key
            
            response = await openai.ChatCompletion.acreate(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "Summarize the following web page content, extracting key information and main points. Keep it concise but informative."},
                    {"role": "user", "content": content}
                ],
                max_tokens=300,
                temperature=0.3
            )
            
            return response.choices[0].message.content.strip()
            
        except ImportError:
            logger.error("openai library not installed. Install with: pip install openai")
            return content[:500] + "..." if len(content) > 500 else content
        except Exception as e:
            logger.error(f"OpenAI summarization error: {str(e)}")
            return content[:500] + "..." if len(content) > 500 else content
    
    async def search_with_content_extraction(self, query: str, count: int = 5) -> Dict[str, Any]:
        """
        Search and extract content from top results with OpenAI processing
        
        Args:
            query: Search query
            count: Number of results to process
            
        Returns:
            Dictionary containing search results with extracted content
        """
        try:
            # Input validation
            if not query or not isinstance(query, str) or len(query.strip()) == 0:
                raise SearchError("Query must be a non-empty string")
            
            if not isinstance(count, int) or count < 1 or count > 10:
                raise SearchError("Count must be an integer between 1 and 10 for content extraction")
            
            logger.info(f"OpenAIWebSearch: Content extraction for '{query}' (count={count})")
            
            # Perform search with content reading enabled
            search_results = await self.search(query, count, read_content=True)
            
            # Enhanced processing with OpenAI
            enhanced_results = search_results.copy()
            enhanced_results["tool_type"] = "openai_websearch_with_content"
            enhanced_results["content_extraction_enabled"] = True
            enhanced_results["features"] = {
                "web_search": "Brave Search API",
                "content_reading": "Direct HTTP requests with BeautifulSoup", 
                "ai_processing": "OpenAI GPT content summarization"
            }
            
            return enhanced_results
            
        except SearchError:
            raise
        except Exception as e:
            logger.error(f"OpenAIWebSearch content extraction error: {str(e)}")
            raise SearchError(f"OpenAIWebSearch content extraction error: {str(e)}")
    
    def validate_search_query(self, query: str) -> Dict[str, Any]:
        """Validate search query format and content"""
        validation = {
            "valid": False,
            "errors": [],
            "warnings": []
        }
        
        if not query:
            validation["errors"].append("Query is empty")
            return validation
        
        if not isinstance(query, str):
            validation["errors"].append("Query must be a string")
            return validation
        
        query = query.strip()
        if len(query) == 0:
            validation["errors"].append("Query is empty after trimming")
            return validation
        
        if len(query) > 1000:
            validation["warnings"].append("Query is very long (>1000 chars)")
        
        if len(query) < 3:
            validation["warnings"].append("Query is very short (<3 chars)")
        
        # Check for potentially unsafe content
        unsafe_patterns = ['javascript:', 'data:', 'vbscript:', 'file:']
        for pattern in unsafe_patterns:
            if pattern in query.lower():
                validation["errors"].append(f"Query contains potentially unsafe pattern: {pattern}")
        
        if not validation["errors"]:
            validation["valid"] = True
        
        return validation
    
    def get_tool_info(self) -> Dict[str, Any]:
        """Get information about this tool's capabilities"""
        return {
            "name": "OpenAIWebSearchTool", 
            "description": "Web search tool using Brave Search API + OpenAI for content reading and analysis",
            "features": [
                "Web search with Brave Search API",
                "Content extraction with HTTP requests + BeautifulSoup",
                "AI-powered content summarization with OpenAI GPT",
                "Input validation and error handling", 
                "Structured search result processing"
            ],
            "advantages": [
                "High-quality search results via Brave API",
                "OpenAI integration for smart content processing",
                "Professional search API reliability",
                "Robust content extraction",
                "Comprehensive validation",
                "Better error handling"
            ],
            "validation": [
                "Query format validation",
                "Parameter range checking", 
                "Safety pattern detection",
                "Content length validation"
            ],
            "requirements": [
                "pip install openai",
                "pip install beautifulsoup4", 
                "pip install requests",
                "BRAVE_API_KEY environment variable",
                "OPENAI_API_KEY environment variable"
            ],
            "status": "Ready to use"
        }

class BraveSearchTool:
    """
    Brave Search API integration for web search functionality
    """
    def __init__(self):
        self.api_key = os.getenv("BRAVE_API_KEY")
        if not self.api_key:
            raise SearchError("BRAVE_API_KEY environment variable not set")
        
        self.base_url = "https://api.search.brave.com/res/v1"
        self.headers = {
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "X-Subscription-Token": self.api_key
        }
    
    async def search(self, query: str, count: int = 10, offset: int = 0, search_type: str = "web") -> Dict[str, Any]:
        """
        Perform a web search using Brave Search API
        
        Args:
            query: Search query string
            count: Number of results to return (max 20)
            offset: Number of results to skip
            search_type: Type of search (web, news, images)
        
        Returns:
            Dictionary containing search results
        """
        try:
            # Prepare search parameters
            params = {
                "q": query,
                "count": min(count, 20),  # Brave API limit
                "offset": offset,
                "search_lang": "en",
                "country": "US",
                "safesearch": "moderate"
            }
            
            # Different endpoints for different search types
            if search_type == "news":
                endpoint = f"{self.base_url}/news/search"
            elif search_type == "images":
                endpoint = f"{self.base_url}/images/search"
            else:
                endpoint = f"{self.base_url}/web/search"
            
            logger.info(f"Brave Search: Searching for '{query}' (type: {search_type})")
            
            response = requests.get(
                endpoint,
                headers=self.headers,
                params=params,
                timeout=30
            )
            
            response.raise_for_status()
            data = response.json()
            
            # Process results based on search type
            if search_type == "web":
                results = self._process_web_results(data)
            elif search_type == "news":
                results = self._process_news_results(data)
            elif search_type == "images":
                results = self._process_image_results(data)
            else:
                results = {"results": [], "total": 0}
            
            logger.info(f"Brave Search: Found {len(results['results'])} results for '{query}'")
            return results
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Brave Search API error: {str(e)}")
            raise SearchError(f"Brave Search API error: {str(e)}")
        except Exception as e:
            logger.error(f"Brave Search error: {str(e)}")
            raise SearchError(f"Brave Search error: {str(e)}")
    
    def _process_web_results(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process web search results"""
        results = []
        
        # Process main web results
        if "web" in data and "results" in data["web"]:
            for result in data["web"]["results"]:
                results.append({
                    "title": result.get("title", ""),
                    "url": result.get("url", ""),
                    "description": result.get("description", ""),
                    "snippet": result.get("description", ""),
                    "type": "web"
                })
        
        # Process featured snippets if available
        if "infobox" in data and data["infobox"]:
            infobox = data["infobox"]
            results.insert(0, {
                "title": infobox.get("title", ""),
                "url": infobox.get("url", ""),
                "description": infobox.get("description", ""),
                "snippet": infobox.get("description", ""),
                "type": "featured"
            })
        
        return {
            "results": results,
            "total": len(results),
            "query": data.get("query", {}).get("original", "")
        }
    
    def _process_news_results(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process news search results"""
        results = []
        
        if "results" in data:
            for result in data["results"]:
                results.append({
                    "title": result.get("title", ""),
                    "url": result.get("url", ""),
                    "description": result.get("description", ""),
                    "snippet": result.get("description", ""),
                    "published_date": result.get("age", ""),
                    "source": result.get("meta_url", {}).get("hostname", ""),
                    "type": "news"
                })
        
        return {
            "results": results,
            "total": len(results),
            "query": data.get("query", {}).get("original", "")
        }
    
    def _process_image_results(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process image search results"""
        results = []
        
        if "results" in data:
            for result in data["results"]:
                results.append({
                    "title": result.get("title", ""),
                    "url": result.get("url", ""),
                    "thumbnail": result.get("thumbnail", {}).get("src", ""),
                    "source": result.get("source", ""),
                    "type": "image"
                })
        
        return {
            "results": results,
            "total": len(results),
            "query": data.get("query", {}).get("original", "")
        }

# ScraperAPI tool removed - not actively used and replaced with ClaudeWebSearchTool

class CaseStudyTool:
    """
    Simplified case study lookup tool using site: filtering and content analysis
    """
    def __init__(self, web_search_manager):
        self.web_search_manager = web_search_manager
        
    async def lookup_case_study(self, company_domain: str, context: str = "", rep_domain: str = "") -> Dict[str, Any]:
        """
        Look up case studies for a specific company using simple site: filtering and content analysis
        
        Args:
            company_domain: Domain or company name to search for (prospect)
            context: Additional context for the search
            rep_domain: Sales rep's domain to filter for own company's case studies
            
        Returns:
            Dictionary containing case study results
        """
        try:
            # Input validation
            if not company_domain:
                return {"ok": False, "error": "Company domain is required"}
            
            if not rep_domain:
                return {"ok": False, "error": "Rep domain is required for site: filtering"}
            
            # Extract company name from domain
            company_name = company_domain.replace('.com', '').replace('.org', '').replace('.net', '')
            
            # Generate smart search query using LLM
            search_query = await self._generate_smart_search_query(company_name, rep_domain, context)
            
            logger.info(f"Searching for case studies: {search_query}")
            
            # Use OpenAI WebSearch tool to search and read content
            search_results = await self.web_search_manager.openai_websearch.search(
                search_query, 
                count=5,  # Fewer, higher quality results
                read_content=True
            )
            
            if not search_results.get("results"):
                return {
                    "ok": False,
                    "company_domain": company_domain,
                    "error": "No search results found"
                }
            
            # Analyze results using OpenAI content analysis
            analyzed_results = await self._analyze_case_studies_with_ai(
                search_results["results"], 
                company_name,
                context
            )
            
            if analyzed_results:
                return {
                    "ok": True,
                    "company_domain": company_domain,
                    "search_query": search_query,
                    "method": "simplified_site_filtering",
                    "top_result": analyzed_results[0],
                    "all_results": analyzed_results,
                    "total_found": len(analyzed_results)
                }
            else:
                return {
                    "ok": False,
                    "company_domain": company_domain,
                    "error": "No relevant case studies found after content analysis"
                }
                
        except Exception as e:
            logger.error(f"Case study lookup error: {str(e)}")
            return {
                "ok": False,
                "company_domain": company_domain,
                "error": str(e)
            }
    
    async def _analyze_case_studies_with_ai(self, search_results: List[Dict], company_name: str, context: str = "") -> List[Dict]:
        """
        Use OpenAI to analyze search results and identify real case studies
        
        Args:
            search_results: List of search results with content
            company_name: Name of the company to look for
            context: Additional context for analysis
            
        Returns:
            List of verified case studies ranked by relevance
        """
        try:
            verified_case_studies = []
            
            for result in search_results:
                # Skip if no content was read
                if not result.get("content_read") or not result.get("content"):
                    continue
                
                # Use OpenAI to analyze if this is a real case study about the company
                is_case_study = await self._verify_case_study_with_ai(
                    result.get("content", ""),
                    result.get("title", ""),
                    company_name,
                    context
                )
                
                if is_case_study["is_case_study"]:
                    result.update({
                        "ai_analysis": is_case_study,
                        "relevance_score": is_case_study.get("relevance_score", 0),
                        "case_study_type": is_case_study.get("case_study_type", "unknown"),
                        "key_insights": is_case_study.get("key_insights", [])
                    })
                    verified_case_studies.append(result)
            
            # Sort by relevance score (highest first)
            verified_case_studies.sort(
                key=lambda x: x.get("relevance_score", 0), 
                reverse=True
            )
            
            return verified_case_studies
            
        except Exception as e:
            logger.error(f"Error analyzing case studies with AI: {str(e)}")
            return []
    
    async def _verify_case_study_with_ai(self, content: str, title: str, company_name: str, context: str = "") -> Dict:
        """
        Use OpenAI to verify if content is actually a case study about the specified company
        """
        try:
            # Use the OpenAI API from the web search tool
            openai_tool = self.web_search_manager.openai_websearch
            if not openai_tool.openai_api_key:
                return {"is_case_study": False, "error": "OpenAI API key not available"}
            
            import openai
            openai.api_key = openai_tool.openai_api_key
            
            prompt = f"""
            Analyze this content to determine if it's a case study about "{company_name}".
            
            Title: {title}
            Content: {content[:2000]}...
            Context: {context}
            
            Please respond with a JSON object containing:
            {{
                "is_case_study": true/false,
                "relevance_score": 0-100,
                "case_study_type": "customer_success" | "implementation" | "testimonial" | "other",
                "key_insights": ["insight1", "insight2", ...],
                "reasoning": "brief explanation"
            }}
            
            A case study should:
            1. Feature {company_name} as a customer/client (not as the vendor)
            2. Describe challenges, solutions, and results
            3. Include specific outcomes or metrics
            4. Tell a story of implementation or success
            """
            
            response = await openai.ChatCompletion.acreate(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are an expert at analyzing business content to identify case studies. Always respond with valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,
                temperature=0.1
            )
            
            # Parse JSON response
            import json
            analysis = json.loads(response.choices[0].message.content.strip())
            return analysis
            
        except Exception as e:
            logger.error(f"Error verifying case study with AI: {str(e)}")
            return {"is_case_study": False, "error": str(e)}
    
    async def _generate_smart_search_query(self, company_name: str, rep_domain: str, context: str = "") -> str:
        """
        Use OpenAI to generate a smart search query based on the company and context
        
        Args:
            company_name: Name of the prospect company (e.g., "Nike")
            rep_domain: Sales rep's company domain (e.g., "bloomreach.com")
            context: Additional context about the industry or use case
            
        Returns:
            Optimized search query string
        """
        try:
            # Use the OpenAI API from the web search tool
            openai_tool = self.web_search_manager.openai_websearch
            if not openai_tool.openai_api_key:
                # Fallback to simple query if no OpenAI API key
                return f'"{company_name}" case study site:{rep_domain}'
            
            import openai
            openai.api_key = openai_tool.openai_api_key
            
            prompt = f"""
            Generate an optimized search query to find case studies about {company_name} on the {rep_domain} website.
            
            Company: {company_name}
            Rep Domain: {rep_domain}
            Context: {context if context else "No specific context provided"}
            
            Based on the company name, infer what industry they're in and what business challenges they might face.
            Generate a search query that would find relevant case studies using these guidelines:
            
            1. Include relevant industry keywords (e.g., "ecommerce", "retail", "healthcare", "fintech")
            2. Include relevant use case keywords (e.g., "personalization", "automation", "analytics")
            3. Must end with "case study site:{rep_domain}"
            4. Keep it concise (under 10 words total)
            5. Don't include the company name in quotes
            
            Examples:
            - For Nike: "ecommerce personalization case study site:bloomreach.com"
            - For Tesla: "automotive customer experience case study site:salesforce.com"
            - For Airbnb: "marketplace optimization case study site:segment.com"
            
            Return only the search query, nothing else.
            """
            
            response = await openai.ChatCompletion.acreate(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are an expert at generating effective search queries for finding business case studies. Always respond with just the search query, no additional text."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=50,
                temperature=0.3
            )
            
            generated_query = response.choices[0].message.content.strip()
            
            # Validate the generated query has the required site: filter
            if f"site:{rep_domain}" not in generated_query:
                generated_query += f" site:{rep_domain}"
            
            logger.info(f"Generated smart search query: {generated_query}")
            return generated_query
            
        except Exception as e:
            logger.error(f"Error generating smart search query: {str(e)}")
            # Fallback to simple query
            return f'"{company_name}" case study site:{rep_domain}'
    
    async def generate_client_report(self, case_study_data: Dict[str, Any], format_type: str = "pdf") -> Dict[str, Any]:
        """
        Generate an AI-designed professional client-ready report with intelligent layout and visualizations
        
        Args:
            case_study_data: The case study data from lookup_case_study
            format_type: "pdf", "html", or "both"
            
        Returns:
            Dictionary with generated report file paths and metadata
        """
        try:
            from datetime import datetime
            import os
            
            # Create output directory
            output_dir = os.path.join(os.getcwd(), "output", "client_reports")
            os.makedirs(output_dir, exist_ok=True)
            
            # Generate base filename
            company_domain = case_study_data.get('company_domain', 'unknown')
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            base_filename = f"case_study_report_{company_domain}_{timestamp}"
            
            results = {
                "success": True,
                "company": company_domain,
                "generated_files": [],
                "timestamp": timestamp
            }
            
            # STEP 1: Let AI analyze data and design the report
            logger.info("🤖 AI analyzing case study data and designing report layout...")
            report_design = await self._ai_design_report(case_study_data)
            
            # STEP 2: Prepare data based on AI recommendations  
            enhanced_data = await self._prepare_ai_designed_data(case_study_data, report_design)
            
            # STEP 3: Generate HTML report using AI design
            html_path = await self._generate_ai_designed_html_report(enhanced_data, report_design, output_dir, base_filename)
            results["generated_files"].append({"type": "html", "path": html_path})
            results["ai_design"] = report_design
            
            # STEP 4: Generate PDF if requested
            if format_type in ["pdf", "both"]:
                pdf_path = await self._generate_pdf_report(enhanced_data, output_dir, base_filename, html_path)
                results["generated_files"].append({"type": "pdf", "path": pdf_path})
            
            logger.info(f"✅ Generated AI-designed client report(s) for {company_domain}")
            return results
            
        except Exception as e:
            logger.error(f"Error generating client report: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _ai_design_report(self, case_study_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Use AI to analyze the case study data and design an optimal report layout
        
        Args:
            case_study_data: Raw case study data to analyze
            
        Returns:
            Dictionary containing AI-designed report structure and recommendations
        """
        try:
            # Use the OpenAI API from the web search tool
            openai_tool = self.web_search_manager.openai_websearch
            if not openai_tool.openai_api_key:
                # Fallback to default design
                return self._get_default_report_design()
            
            import openai
            openai.api_key = openai_tool.openai_api_key
            
            # Analyze the data structure
            all_results = case_study_data.get('all_results', [])
            company = case_study_data.get('company_domain', 'Unknown')
            
            # Prepare data summary for AI analysis
            data_summary = {
                "company": company,
                "total_results": len(all_results),
                "has_verified_case_studies": any(r.get('ai_analysis', {}).get('is_case_study', False) for r in all_results),
                "relevance_scores": [r.get('relevance_score', 0) for r in all_results],
                "case_study_types": [r.get('ai_analysis', {}).get('case_study_type', 'unknown') for r in all_results if r.get('ai_analysis', {}).get('is_case_study', False)],
                "key_insights": [insight for r in all_results for insight in r.get('ai_analysis', {}).get('key_insights', [])],
                "has_metrics": any('metric' in str(r.get('ai_analysis', {}).get('key_insights', [])).lower() for r in all_results)
            }
            
            prompt = f"""
            You are a professional report designer. Analyze this case study data and design an optimal client presentation report.
            
            Data Analysis:
            {json.dumps(data_summary, indent=2)}
            
            Design a professional report with the following considerations:
            1. What's the most compelling story this data tells?
            2. What charts/visualizations would best represent this data?
            3. What sections should be included for maximum client impact?
            4. What color scheme and design style would be most professional?
            5. What executive summary would be most persuasive?
            
            Respond with a JSON object containing:
            {{
                "report_title": "Compelling title for the report",
                "executive_summary": "2-3 sentence executive summary highlighting key findings",
                "recommended_sections": [
                    {{
                        "title": "Section name",
                        "content_type": "text|chart|stats|highlight",
                        "description": "What this section should contain",
                        "priority": 1-5
                    }}
                ],
                "recommended_charts": [
                    {{
                        "type": "bar|line|pie|doughnut|scatter|radar",
                        "title": "Chart title",
                        "data_source": "What data to visualize",
                        "reasoning": "Why this chart is recommended"
                    }}
                ],
                "color_scheme": {{
                    "primary": "#hex_color",
                    "secondary": "#hex_color", 
                    "accent": "#hex_color",
                    "style": "professional|modern|corporate|creative"
                }},
                "key_messages": [
                    "Key message 1",
                    "Key message 2", 
                    "Key message 3"
                ],
                "design_rationale": "Why this design approach was chosen"
            }}
            
            Focus on creating a report that tells a compelling business story and demonstrates clear value to the client.
            """
            
            response = await openai.ChatCompletion.acreate(
                model="gpt-4",  # Use GPT-4 for better design thinking
                messages=[
                    {"role": "system", "content": "You are an expert business intelligence report designer who creates compelling, data-driven presentations for executive audiences. Always respond with valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1500,
                temperature=0.7  # Allow some creativity in design
            )
            
            # Parse AI design response
            import json
            design = json.loads(response.choices[0].message.content.strip())
            
            logger.info(f"🎨 AI designed report: {design.get('report_title', 'Custom Report')}")
            return design
            
        except Exception as e:
            logger.error(f"Error in AI report design: {str(e)}")
            return self._get_default_report_design()
    
    def _get_default_report_design(self) -> Dict[str, Any]:
        """Fallback report design if AI is not available"""
        return {
            "report_title": "Case Study Analysis Report",
            "executive_summary": "Comprehensive analysis of relevant case studies and business intelligence insights.",
            "recommended_sections": [
                {"title": "Executive Summary", "content_type": "text", "description": "Key findings overview", "priority": 1},
                {"title": "Performance Metrics", "content_type": "stats", "description": "Statistical overview", "priority": 2},
                {"title": "Data Visualization", "content_type": "chart", "description": "Charts and graphs", "priority": 3},
                {"title": "Top Results", "content_type": "highlight", "description": "Best case studies found", "priority": 4}
            ],
            "recommended_charts": [
                {"type": "bar", "title": "Relevance Scores", "data_source": "relevance_scores", "reasoning": "Shows quality ranking"},
                {"type": "doughnut", "title": "Case Study Types", "data_source": "case_study_types", "reasoning": "Shows distribution"}
            ],
            "color_scheme": {
                "primary": "#2c3e50",
                "secondary": "#3498db", 
                "accent": "#e74c3c",
                "style": "professional"
            },
            "key_messages": [
                "Comprehensive case study analysis completed",
                "Data-driven insights identified",
                "Actionable intelligence provided"
            ],
            "design_rationale": "Clean, professional design optimized for executive presentation"
        }
    
    async def _prepare_ai_designed_data(self, case_study_data: Dict[str, Any], report_design: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare data according to AI design recommendations"""
        try:
            enhanced_data = case_study_data.copy()
            enhanced_data['ai_design'] = report_design
            
            # Prepare data based on recommended charts
            all_results = case_study_data.get('all_results', [])
            charts_data = {}
            
            for chart in report_design.get('recommended_charts', []):
                data_source = chart.get('data_source', '')
                chart_type = chart.get('type', 'bar')
                
                if data_source == 'relevance_scores':
                    charts_data['relevance_scores'] = {
                        'data': [r.get('relevance_score', 0) for r in all_results[:5]],
                        'labels': [r.get('title', 'Unknown')[:30] + '...' for r in all_results[:5]],
                        'type': chart_type
                    }
                elif data_source == 'case_study_types':
                    types = self._analyze_case_study_types(all_results)
                    charts_data['case_study_types'] = {
                        'data': list(types.values()),
                        'labels': list(types.keys()),
                        'type': chart_type
                    }
                elif data_source == 'insights_timeline':
                    # Create timeline if recommended
                    charts_data['insights_timeline'] = {
                        'data': [len(r.get('ai_analysis', {}).get('key_insights', [])) for r in all_results[:5]],
                        'labels': [f"Result {i+1}" for i in range(min(5, len(all_results)))],
                        'type': chart_type
                    }
            
            enhanced_data['ai_charts'] = charts_data
            
            # Prepare statistics based on design
            enhanced_data['ai_statistics'] = {
                'total_results': len(all_results),
                'avg_relevance_score': sum(r.get('relevance_score', 0) for r in all_results) / max(len(all_results), 1),
                'content_read_count': sum(1 for r in all_results if r.get('content_read', False)),
                'verified_case_studies': sum(1 for r in all_results if r.get('ai_analysis', {}).get('is_case_study', False)),
                'key_insights_total': sum(len(r.get('ai_analysis', {}).get('key_insights', [])) for r in all_results)
            }
            
            return enhanced_data
            
        except Exception as e:
            logger.error(f"Error preparing AI-designed data: {str(e)}")
            return await self._prepare_report_data(case_study_data)
    
    async def _prepare_report_data(self, case_study_data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare and enhance data for report generation"""
        try:
            enhanced_data = case_study_data.copy()
            
            # Extract metrics and insights
            all_results = case_study_data.get('all_results', [])
            
            # Prepare chart data
            enhanced_data['charts'] = {
                'relevance_scores': [r.get('relevance_score', 0) for r in all_results[:5]],
                'result_titles': [r.get('title', 'Unknown')[:30] + '...' for r in all_results[:5]],
                'case_study_types': self._analyze_case_study_types(all_results),
                'key_metrics': self._extract_all_metrics(all_results)
            }
            
            # Prepare summary statistics
            enhanced_data['statistics'] = {
                'total_results': len(all_results),
                'avg_relevance_score': sum(r.get('relevance_score', 0) for r in all_results) / max(len(all_results), 1),
                'content_read_count': sum(1 for r in all_results if r.get('content_read', False)),
                'verified_case_studies': sum(1 for r in all_results if r.get('ai_analysis', {}).get('is_case_study', False))
            }
            
            return enhanced_data
            
        except Exception as e:
            logger.error(f"Error preparing report data: {str(e)}")
            return case_study_data
    
    def _analyze_case_study_types(self, results: List[Dict]) -> Dict[str, int]:
        """Analyze and categorize case study types"""
        types = {}
        for result in results:
            case_type = result.get('ai_analysis', {}).get('case_study_type', 'other')
            types[case_type] = types.get(case_type, 0) + 1
        return types
    
    def _extract_all_metrics(self, results: List[Dict]) -> List[str]:
        """Extract all metrics from case study results"""
        all_metrics = []
        for result in results:
            metrics = result.get('ai_analysis', {}).get('key_insights', [])
            all_metrics.extend(metrics)
        return list(set(all_metrics))[:10]  # Top 10 unique metrics
    
    async def _generate_ai_designed_html_report(self, data: Dict[str, Any], report_design: Dict[str, Any], output_dir: str, base_filename: str) -> str:
        """Generate HTML report using AI-designed layout and styling"""
        try:
            html_content = self._build_ai_designed_html_template(data, report_design)
            
            html_path = os.path.join(output_dir, f"{base_filename}.html")
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            logger.info(f"Generated AI-designed HTML report: {html_path}")
            return html_path
            
        except Exception as e:
            logger.error(f"Error generating AI-designed HTML report: {str(e)}")
            # Fallback to standard report
            return await self._generate_html_report(data, output_dir, base_filename)
    
    def _build_ai_designed_html_template(self, data: Dict[str, Any], report_design: Dict[str, Any]) -> str:
        """Build HTML template based on AI design recommendations"""
        from datetime import datetime
        
        company = data.get('company_domain', 'Unknown Company')
        design = report_design
        ai_charts = data.get('ai_charts', {})
        ai_stats = data.get('ai_statistics', {})
        top_result = data.get('top_result', {})
        
        # Get AI-designed styling
        colors = design.get('color_scheme', {})
        primary_color = colors.get('primary', '#2c3e50')
        secondary_color = colors.get('secondary', '#3498db')
        accent_color = colors.get('accent', '#e74c3c')
        
        # Build sections based on AI recommendations
        sections_html = self._build_ai_sections(data, design)
        
        # Build charts based on AI recommendations
        charts_html, charts_js = self._build_ai_charts(ai_charts, design)
        
        html_template = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{design.get('report_title', 'AI-Designed Case Study Report')} - {company}</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background: linear-gradient(135deg, {primary_color} 0%, {secondary_color} 100%);
            color: #333;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            overflow: hidden;
        }}
        .header {{
            background: linear-gradient(135deg, {primary_color} 0%, {secondary_color} 100%);
            color: white;
            padding: 40px;
            text-align: center;
        }}
        .header h1 {{
            margin: 0;
            font-size: 2.8em;
            font-weight: 300;
            text-shadow: 0 2px 4px rgba(0,0,0,0.3);
        }}
        .header p {{
            margin: 15px 0 0 0;
            opacity: 0.9;
            font-size: 1.2em;
        }}
        .executive-summary {{
            background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
            padding: 30px;
            margin: 0;
            border-left: 5px solid {accent_color};
        }}
        .executive-summary h2 {{
            color: {primary_color};
            margin-top: 0;
        }}
        .content {{
            padding: 30px;
        }}
        .ai-section {{
            margin: 30px 0;
            padding: 25px;
            border-radius: 12px;
            border-left: 4px solid {secondary_color};
        }}
        .ai-section.stats {{
            background: linear-gradient(135deg, #e8f5e8 0%, #d4edda 100%);
        }}
        .ai-section.chart {{
            background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%);
        }}
        .ai-section.highlight {{
            background: linear-gradient(135deg, #fff3e0 0%, #ffe0b2 100%);
        }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }}
        .stat-card {{
            background: white;
            padding: 25px;
            border-radius: 12px;
            text-align: center;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            border-left: 4px solid {accent_color};
        }}
        .stat-number {{
            font-size: 2.5em;
            font-weight: bold;
            color: {accent_color};
            margin-bottom: 8px;
        }}
        .stat-label {{
            color: #666;
            font-size: 0.95em;
            font-weight: 500;
        }}
        .charts-container {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 30px;
            margin: 30px 0;
        }}
        .chart-wrapper {{
            background: white;
            padding: 25px;
            border-radius: 12px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            height: 400px;
        }}
        .top-result {{
            background: linear-gradient(135deg, #e8f5e8 0%, #c8e6c9 100%);
            border: 2px solid #4caf50;
            border-radius: 15px;
            padding: 30px;
            margin: 30px 0;
            box-shadow: 0 4px 12px rgba(76, 175, 80, 0.2);
        }}
        .top-result h3 {{
            color: #2e7d32;
            margin-top: 0;
            font-size: 1.5em;
        }}
        .key-messages {{
            background: linear-gradient(135deg, #f3e5f5 0%, #e1bee7 100%);
            padding: 25px;
            border-radius: 12px;
            margin: 25px 0;
        }}
        .key-messages ul {{
            list-style: none;
            padding: 0;
        }}
        .key-messages li {{
            background: white;
            margin: 10px 0;
            padding: 15px;
            border-radius: 8px;
            border-left: 4px solid #9c27b0;
            box-shadow: 0 2px 6px rgba(0,0,0,0.1);
        }}
        .design-note {{
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            font-style: italic;
            color: #666;
            margin: 20px 0;
            border-left: 3px solid {secondary_color};
        }}
        .footer {{
            background: {primary_color};
            color: white;
            padding: 25px;
            text-align: center;
        }}
        @media print {{
            body {{ background: white; }}
            .container {{ box-shadow: none; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{design.get('report_title', 'AI-Designed Case Study Report')}</h1>
            <p>{company} • Generated by AI on {datetime.now().strftime('%B %d, %Y')}</p>
        </div>
        
        <div class="executive-summary">
            <h2>🎯 Executive Summary</h2>
            <p>{design.get('executive_summary', 'AI-powered analysis of case study data with intelligent insights.')}</p>
        </div>
        
        <div class="content">
            {sections_html}
            
            <div class="key-messages">
                <h3>🔑 Key Messages</h3>
                <ul>
                    {''.join([f'<li>{msg}</li>' for msg in design.get('key_messages', [])])}
                </ul>
            </div>
            
            <div class="design-note">
                <strong>AI Design Rationale:</strong> {design.get('design_rationale', 'Report designed using artificial intelligence to optimize presentation and impact.')}
            </div>
        </div>
        
        <div class="footer">
            <p>🤖 AI-Designed Report • Generated by Intelligent Case Study Analysis Tool</p>
        </div>
    </div>

    <script>
        {charts_js}
    </script>
</body>
</html>
"""
        return html_template
    
    def _build_ai_sections(self, data: Dict[str, Any], design: Dict[str, Any]) -> str:
        """Build HTML sections based on AI recommendations"""
        sections_html = ""
        ai_stats = data.get('ai_statistics', {})
        top_result = data.get('top_result', {})
        
        # Sort sections by priority
        sections = sorted(design.get('recommended_sections', []), key=lambda x: x.get('priority', 5))
        
        for section in sections:
            title = section.get('title', 'Section')
            content_type = section.get('content_type', 'text')
            description = section.get('description', '')
            
            if content_type == 'stats':
                sections_html += f"""
                <div class="ai-section stats">
                    <h3>📊 {title}</h3>
                    <p>{description}</p>
                    <div class="stats-grid">
                        <div class="stat-card">
                            <div class="stat-number">{ai_stats.get('total_results', 0)}</div>
                            <div class="stat-label">Total Results</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-number">{ai_stats.get('verified_case_studies', 0)}</div>
                            <div class="stat-label">Verified Studies</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-number">{ai_stats.get('avg_relevance_score', 0):.1f}</div>
                            <div class="stat-label">Avg Score</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-number">{ai_stats.get('key_insights_total', 0)}</div>
                            <div class="stat-label">Key Insights</div>
                        </div>
                    </div>
                </div>
                """
            elif content_type == 'chart':
                sections_html += f"""
                <div class="ai-section chart">
                    <h3>📈 {title}</h3>
                    <p>{description}</p>
                    <div class="charts-container" id="ai-charts-container">
                        <!-- Charts will be inserted here by JavaScript -->
                    </div>
                </div>
                """
            elif content_type == 'highlight':
                sections_html += f"""
                <div class="ai-section highlight">
                    <h3>🏆 {title}</h3>
                    <p>{description}</p>
                    <div class="top-result">
                        <h4>{top_result.get('title', 'No title available')}</h4>
                        <p><strong>URL:</strong> <a href="{top_result.get('url', '#')}" target="_blank">{top_result.get('url', 'No URL')}</a></p>
                        <p><strong>Relevance Score:</strong> {top_result.get('relevance_score', 0)}/100</p>
                        <p><strong>AI Analysis:</strong> {top_result.get('ai_analysis', {}).get('reasoning', 'Comprehensive case study analysis completed.')}</p>
                    </div>
                </div>
                """
            else:  # text
                sections_html += f"""
                <div class="ai-section">
                    <h3>📝 {title}</h3>
                    <p>{description}</p>
                </div>
                """
        
        return sections_html
    
    def _build_ai_charts(self, charts_data: Dict[str, Any], design: Dict[str, Any]) -> tuple:
        """Build chart HTML and JavaScript based on AI recommendations"""
        charts_html = ""
        charts_js = ""
        
        chart_id = 0
        for chart_rec in design.get('recommended_charts', []):
            chart_id += 1
            chart_type = chart_rec.get('type', 'bar')
            chart_title = chart_rec.get('title', 'Chart')
            data_source = chart_rec.get('data_source', '')
            
            if data_source in charts_data:
                chart_data = charts_data[data_source]
                
                charts_html += f"""
                <div class="chart-wrapper">
                    <canvas id="aiChart{chart_id}"></canvas>
                </div>
                """
                
                # Build JavaScript for this chart
                colors = ['rgba(52, 152, 219, 0.8)', 'rgba(231, 76, 60, 0.8)', 'rgba(46, 204, 113, 0.8)', 
                         'rgba(155, 89, 182, 0.8)', 'rgba(241, 196, 15, 0.8)']
                
                if chart_type == 'doughnut' or chart_type == 'pie':
                    charts_js += f"""
                    const ctx{chart_id} = document.getElementById('aiChart{chart_id}').getContext('2d');
                    new Chart(ctx{chart_id}, {{
                        type: '{chart_type}',
                        data: {{
                            labels: {chart_data.get('labels', [])},
                            datasets: [{{
                                data: {chart_data.get('data', [])},
                                backgroundColor: {colors}
                            }}]
                        }},
                        options: {{
                            responsive: true,
                            maintainAspectRatio: false,
                            plugins: {{
                                title: {{
                                    display: true,
                                    text: '{chart_title}'
                                }}
                            }}
                        }}
                    }});
                    """
                else:  # bar, line, etc.
                    charts_js += f"""
                    const ctx{chart_id} = document.getElementById('aiChart{chart_id}').getContext('2d');
                    new Chart(ctx{chart_id}, {{
                        type: '{chart_type}',
                        data: {{
                            labels: {chart_data.get('labels', [])},
                            datasets: [{{
                                label: '{chart_title}',
                                data: {chart_data.get('data', [])},
                                backgroundColor: '{colors[0]}',
                                borderColor: '{colors[0].replace("0.8", "1")}',
                                borderWidth: 2
                            }}]
                        }},
                        options: {{
                            responsive: true,
                            maintainAspectRatio: false,
                            plugins: {{
                                title: {{
                                    display: true,
                                    text: '{chart_title}'
                                }}
                            }},
                            scales: {{
                                y: {{
                                    beginAtZero: true
                                }}
                            }}
                        }}
                    }});
                    """
        
        # Insert charts into container
        if charts_html:
            charts_js = f"""
            document.addEventListener('DOMContentLoaded', function() {{
                const container = document.getElementById('ai-charts-container');
                if (container) {{
                    container.innerHTML = `{charts_html}`;
                    setTimeout(() => {{
                        {charts_js}
                    }}, 100);
                }}
            }});
            """
        
        return charts_html, charts_js
    
    async def _generate_html_report(self, data: Dict[str, Any], output_dir: str, base_filename: str) -> str:
        """Generate professional HTML report with charts"""
        try:
            html_content = self._build_html_template(data)
            
            html_path = os.path.join(output_dir, f"{base_filename}.html")
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            logger.info(f"Generated HTML report: {html_path}")
            return html_path
            
        except Exception as e:
            logger.error(f"Error generating HTML report: {str(e)}")
            raise
    
    def _build_html_template(self, data: Dict[str, Any]) -> str:
        """Build professional HTML template with charts"""
        from datetime import datetime
        
        company = data.get('company_domain', 'Unknown Company')
        top_result = data.get('top_result', {})
        charts = data.get('charts', {})
        stats = data.get('statistics', {})
        
        # Prepare chart data for JavaScript
        relevance_scores = charts.get('relevance_scores', [])
        result_titles = charts.get('result_titles', [])
        case_types = charts.get('case_study_types', {})
        
        html_template = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Case Study Analysis Report - {company}</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #333;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            overflow: hidden;
        }}
        .header {{
            background: linear-gradient(135deg, #2c3e50 0%, #34495e 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }}
        .header h1 {{
            margin: 0;
            font-size: 2.5em;
            font-weight: 300;
        }}
        .header p {{
            margin: 10px 0 0 0;
            opacity: 0.9;
            font-size: 1.1em;
        }}
        .content {{
            padding: 30px;
        }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .stat-card {{
            background: #f8f9fa;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
            border-left: 4px solid #3498db;
        }}
        .stat-number {{
            font-size: 2em;
            font-weight: bold;
            color: #3498db;
            margin-bottom: 5px;
        }}
        .stat-label {{
            color: #666;
            font-size: 0.9em;
        }}
        .charts-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 30px;
            margin: 30px 0;
        }}
        .chart-container {{
            background: #f8f9fa;
            padding: 20px;
            border-radius: 10px;
            height: 400px;
        }}
        .top-result {{
            background: #e8f5e8;
            border: 1px solid #28a745;
            border-radius: 10px;
            padding: 20px;
            margin: 20px 0;
        }}
        .top-result h3 {{
            color: #28a745;
            margin-top: 0;
        }}
        .url-link {{
            color: #007bff;
            text-decoration: none;
            word-break: break-all;
        }}
        .url-link:hover {{
            text-decoration: underline;
        }}
        .insights-list {{
            list-style: none;
            padding: 0;
        }}
        .insights-list li {{
            background: #fff3cd;
            margin: 5px 0;
            padding: 10px;
            border-radius: 5px;
            border-left: 3px solid #ffc107;
        }}
        .footer {{
            background: #f8f9fa;
            padding: 20px;
            text-align: center;
            color: #666;
            border-top: 1px solid #dee2e6;
        }}
        @media print {{
            body {{ background: white; }}
            .container {{ box-shadow: none; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Case Study Analysis Report</h1>
            <p>{company} • Generated on {datetime.now().strftime('%B %d, %Y')}</p>
        </div>
        
        <div class="content">
            <!-- Statistics Overview -->
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-number">{stats.get('total_results', 0)}</div>
                    <div class="stat-label">Total Results Found</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{stats.get('verified_case_studies', 0)}</div>
                    <div class="stat-label">Verified Case Studies</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{stats.get('avg_relevance_score', 0):.1f}</div>
                    <div class="stat-label">Avg Relevance Score</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{stats.get('content_read_count', 0)}</div>
                    <div class="stat-label">Pages Analyzed</div>
                </div>
            </div>
            
            <!-- Charts -->
            <div class="charts-grid">
                <div class="chart-container">
                    <canvas id="relevanceChart"></canvas>
                </div>
                <div class="chart-container">
                    <canvas id="typeChart"></canvas>
                </div>
            </div>
            
            <!-- Top Result -->
            <div class="top-result">
                <h3>🏆 Top Case Study Result</h3>
                <h4>{top_result.get('title', 'No title available')}</h4>
                <p><strong>URL:</strong> <a href="{top_result.get('url', '#')}" class="url-link" target="_blank">{top_result.get('url', 'No URL')}</a></p>
                <p><strong>Relevance Score:</strong> {top_result.get('relevance_score', 0)}/100</p>
                <p><strong>Description:</strong> {top_result.get('description', 'No description available')[:300]}...</p>
                
                <h5>Key Insights:</h5>
                <ul class="insights-list">
                    {' '.join([f'<li>{insight}</li>' for insight in top_result.get('ai_analysis', {}).get('key_insights', ['No insights available'])[:5]])}
                </ul>
            </div>
        </div>
        
        <div class="footer">
            <p>Generated by AI-Powered Case Study Analysis Tool • Confidential Business Intelligence</p>
        </div>
    </div>

    <script>
        // Relevance Scores Chart
        const ctx1 = document.getElementById('relevanceChart').getContext('2d');
        new Chart(ctx1, {{
            type: 'bar',
            data: {{
                labels: {result_titles},
                datasets: [{{
                    label: 'Relevance Score',
                    data: {relevance_scores},
                    backgroundColor: 'rgba(52, 152, 219, 0.8)',
                    borderColor: 'rgba(52, 152, 219, 1)',
                    borderWidth: 1
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    title: {{
                        display: true,
                        text: 'Case Study Relevance Scores'
                    }}
                }},
                scales: {{
                    y: {{
                        beginAtZero: true,
                        max: 100
                    }}
                }}
            }}
        }});

        // Case Study Types Chart
        const ctx2 = document.getElementById('typeChart').getContext('2d');
        new Chart(ctx2, {{
            type: 'doughnut',
            data: {{
                labels: {list(case_types.keys())},
                datasets: [{{
                    data: {list(case_types.values())},
                    backgroundColor: [
                        'rgba(255, 99, 132, 0.8)',
                        'rgba(54, 162, 235, 0.8)',
                        'rgba(255, 205, 86, 0.8)',
                        'rgba(75, 192, 192, 0.8)',
                        'rgba(153, 102, 255, 0.8)'
                    ]
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    title: {{
                        display: true,
                        text: 'Case Study Types Distribution'
                    }}
                }}
            }}
        }});
    </script>
</body>
</html>
"""
        return html_template
    
    async def _generate_pdf_report(self, data: Dict[str, Any], output_dir: str, base_filename: str, html_path: str) -> str:
        """Generate PDF report from HTML using pdfkit"""
        try:
            pdf_path = os.path.join(output_dir, f"{base_filename}.pdf")
            
            # First try pdfkit (since you installed it)
            try:
                import pdfkit
                
                # PDF options for better rendering
                options = {
                    'page-size': 'A4',
                    'orientation': 'Portrait',
                    'margin-top': '0.75in',
                    'margin-right': '0.75in',
                    'margin-bottom': '0.75in',
                    'margin-left': '0.75in',
                    'encoding': 'UTF-8',
                    'no-outline': None,
                    'enable-local-file-access': None,
                    'javascript-delay': 1000,  # Wait for charts to load
                    'disable-smart-shrinking': None,
                    'print-media-type': None
                }
                
                logger.info(f"🔄 Generating PDF with pdfkit: {pdf_path}")
                pdfkit.from_file(html_path, pdf_path, options=options)
                
                # Verify PDF was created and has content
                if os.path.exists(pdf_path) and os.path.getsize(pdf_path) > 1000:  # At least 1KB
                    logger.info(f"✅ PDF generated successfully: {pdf_path}")
                    logger.info(f"📄 PDF size: {os.path.getsize(pdf_path)} bytes")
                    return pdf_path
                else:
                    logger.error("❌ PDF file was not created or is too small")
                    
            except ImportError:
                logger.error("❌ pdfkit not installed. Run: pip install pdfkit")
            except Exception as e:
                logger.error(f"❌ pdfkit error: {str(e)}")
                # Check if wkhtmltopdf is available
                if "wkhtmltopdf" in str(e).lower():
                    logger.error("💡 wkhtmltopdf is required. Install from: https://wkhtmltopdf.org/downloads.html")
            
            # Try direct wkhtmltopdf command if pdfkit fails
            try:
                import subprocess
                logger.info("🔄 Trying direct wkhtmltopdf command...")
                
                result = subprocess.run([
                    'wkhtmltopdf', 
                    '--page-size', 'A4',
                    '--orientation', 'Portrait',
                    '--margin-top', '0.75in',
                    '--margin-right', '0.75in',
                    '--margin-bottom', '0.75in',
                    '--margin-left', '0.75in',
                    '--encoding', 'UTF-8',
                    '--enable-local-file-access',
                    '--javascript-delay', '1000',
                    html_path,
                    pdf_path
                ], capture_output=True, text=True, timeout=30)
                
                if result.returncode == 0 and os.path.exists(pdf_path):
                    logger.info(f"✅ PDF generated with wkhtmltopdf: {pdf_path}")
                    return pdf_path
                else:
                    logger.error(f"❌ wkhtmltopdf failed: {result.stderr}")
                    
            except FileNotFoundError:
                logger.error("❌ wkhtmltopdf not found in PATH")
            except subprocess.TimeoutExpired:
                logger.error("❌ wkhtmltopdf timed out")
            except Exception as e:
                logger.error(f"❌ wkhtmltopdf error: {str(e)}")
            
            # Final fallback: Create instructions file
            logger.warning("⚠️ PDF generation failed, creating instructions file")
            instructions_path = os.path.join(output_dir, f"{base_filename}_pdf_instructions.txt")
            with open(instructions_path, 'w') as f:
                f.write("PDF Generation Instructions\n")
                f.write("="*50 + "\n\n")
                f.write(f"HTML report available at: {html_path}\n\n")
                f.write("To generate PDF, install wkhtmltopdf:\n")
                f.write("1. Download from: https://wkhtmltopdf.org/downloads.html\n")
                f.write("2. Install and add to your PATH\n")
                f.write("3. Re-run the report generation\n\n")
                f.write("Alternative: Open the HTML file in a browser and print to PDF\n")
            
            return instructions_path
            
        except Exception as e:
            logger.error(f"💥 Critical error in PDF generation: {str(e)}")
            raise

class ApolloProcessingTool:
    """
    Tool for processing Apollo.io domain workflows
    """
    def __init__(self):
        import sys
        import os
        
        # Add project root to path for imports
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        sys.path.append(project_root)
        
        self.output_dir = os.path.join(os.getcwd(), "data", "output")
        os.makedirs(self.output_dir, exist_ok=True)
        
    async def process_domains_csv(self, csv_content: str, headless: bool = True, run_apify: bool = False) -> Dict[str, Any]:
        """
        Process a CSV file containing domains through the Apollo workflow
        
        Args:
            csv_content: CSV content as string
            headless: Whether to run browser in headless mode
            run_apify: Whether to run Apify scraping after URL generation
            
        Returns:
            Dictionary containing workflow results
        """
        try:
            import tempfile
            import csv
            import io
            import json
            from datetime import datetime
            
            # Parse CSV content
            csv_reader = csv.DictReader(io.StringIO(csv_content))
            domains = []
            
            for row in csv_reader:
                # Look for domain column (try various common column names)
                domain_columns = ['domain', 'Domain', 'company_domain', 'website', 'url']
                domain = None
                
                for col in domain_columns:
                    if col in row and row[col]:
                        domain = row[col].strip()
                        # Clean up domain (remove http/https, www)
                        domain = domain.replace('http://', '').replace('https://', '').replace('www.', '')
                        if domain.endswith('/'):
                            domain = domain[:-1]
                        domains.append(domain)
                        break
                
                if not domain:
                    # If no standard column found, use the first non-empty value
                    for value in row.values():
                        if value and value.strip():
                            domain = value.strip()
                            domain = domain.replace('http://', '').replace('https://', '').replace('www.', '')
                            if domain.endswith('/'):
                                domain = domain[:-1]
                            domains.append(domain)
                            break
            
            if not domains:
                return {
                    "success": False,
                    "error": "No domains found in CSV file",
                    "domains_processed": 0
                }
            
            # Create temporary CSV file for the workflow
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            temp_csv_path = os.path.join(self.output_dir, f"domains_{timestamp}.csv")
            
            with open(temp_csv_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['domain'])
                for domain in domains:
                    writer.writerow([domain])
            
            # Run the Apollo workflow
            result = await self._run_apollo_workflow(temp_csv_path, headless)
            
            # Add domain info to result
            result["domains_processed"] = len(domains)
            result["domains_list"] = domains
            result["csv_path"] = temp_csv_path
            
            # Optional: Run Apify scraping if requested and workflow succeeded
            if run_apify and result.get("success") and result.get("bulk_url"):
                logger.info("🔄 Step 8: Running Apify scraper (optional)")
                try:
                    from automation.run_apify import create_apify_scraper
                    
                    apify_token = os.getenv("APIFY_TOKEN")
                    if apify_token:
                        scraper = create_apify_scraper(token=apify_token)
                        
                        # Use the actor ID specified in guidelines: "jljBwyyQakqrL1wae"
                        scraper_result = scraper.run_scraper(
                            url=result["bulk_url"],
                            total_records=200,
                            filename="Apollo Prospects",
                            wait_for_completion=True
                        )
                        
                        if scraper_result.get("success"):
                            logger.info("✅ Apify scraping completed successfully")
                            result["apify_result"] = scraper_result
                            result["contacts_scraped"] = scraper_result.get("results_count", 0)
                            
                            # Save results to output/contacts.json as per guidelines
                            output_path = os.path.join(self.output_dir, "contacts.json")
                            with open(output_path, 'w', encoding='utf-8') as f:
                                json.dump(scraper_result.get("results", []), f, indent=2)
                            
                            result["output_file"] = output_path
                            logger.info(f"✅ Contact records saved to {output_path}")
                        else:
                            logger.warning(f"⚠️ Apify scraping failed: {scraper_result.get('error')}")
                            result["apify_error"] = scraper_result.get("error")
                    else:
                        logger.warning("⚠️ APIFY_TOKEN not found, skipping Apify scraping")
                        result["apify_error"] = "APIFY_TOKEN not configured"
                        
                except Exception as e:
                    logger.error(f"❌ Error running Apify scraper: {str(e)}")
                    result["apify_error"] = str(e)
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing domains CSV: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "domains_processed": 0
            }
    
    async def _run_apollo_workflow(self, csv_path: str, headless: bool = True) -> Dict[str, Any]:
        """
        Run the Apollo workflow with the given CSV file following claude_day_2_guidelines.md
        
        Args:
            csv_path: Path to the CSV file
            headless: Whether to run browser in headless mode
            
        Returns:
            Dictionary containing workflow results
        """
        try:
            logger.info("🔄 Starting Apollo workflow - Step 1: Load domains")
            
            # Step 1: Load domains using pandas (as per guidelines)
            from data.load_domains import load_domains
            from config.job_titles import get_priority_titles
            from automation.browser_setup import create_apollo_controller
            from utils.url_utils import extract_search_id, build_bulk_url
            
            # Load domains - must return newline-separated string (per guidelines)
            domains_str = load_domains(csv_path)
            domains_list = domains_str.split('\n')
            logger.info(f"✅ Loaded {len(domains_list)} domains from CSV")
            
            # Step 2: Browser automation setup using browser_use Controller
            logger.info("🔄 Step 2: Initialize browser automation controller")
            controller = create_apollo_controller(
                cookies_file="cookies/apollo.json",
                headless=headless
            )
            
            await controller.initialize()
            logger.info("✅ Browser controller initialized")
            
            # Step 3: Navigate to Apollo.io
            logger.info("🔄 Step 3: Navigate to Apollo.io")
            nav_result = await controller.navigate_to_apollo()
            if not nav_result["success"]:
                return {
                    "success": False,
                    "error": f"Failed to navigate to Apollo: {nav_result['error']}"
                }
            logger.info("✅ Successfully navigated to Apollo.io")
            
            # Step 4: Load and paste domains (using @controller.action pattern)
            logger.info("🔄 Step 4: Load and paste domains into Apollo")
            domains_result = await controller.load_and_paste_domains(domains_str)
            if not domains_result["success"]:
                return {
                    "success": False,
                    "error": f"Failed to load domains: {domains_result['error']}"
                }
            logger.info("✅ Successfully pasted domains into Apollo")
            
            # Step 5: Save search (must double-click and wait 15 seconds per guidelines)
            logger.info("🔄 Step 5: Save search and extract URL (waiting 15 seconds)")
            save_result = await controller.save_and_extract_url()
            if not save_result["success"]:
                return {
                    "success": False,
                    "error": f"Failed to save search: {save_result['error']}"
                }
            logger.info("✅ Successfully saved search and extracted URL")
            
            # Step 6: Extract search ID from fragment (not query string per guidelines)
            logger.info("🔄 Step 6: Extract qOrganizationSearchListId from URL fragment")
            search_url = save_result["url"]
            search_id = extract_search_id(search_url)
            
            if not search_id:
                return {
                    "success": False,
                    "error": "Failed to extract qOrganizationSearchListId from URL fragment"
                }
            logger.info(f"✅ Successfully extracted search ID: {search_id}")
            
            # Step 7: Build bulk URL with URL-encoded job titles
            logger.info("🔄 Step 7: Construct final URL for scraping with job titles")
            job_titles = get_priority_titles()[:5]  # Use top 5 titles
            bulk_url = build_bulk_url(search_id, job_titles)
            logger.info(f"✅ Successfully built bulk URL with {len(job_titles)} job titles")
            
            # Step 8: Cleanup
            await controller.close()
            logger.info("✅ Browser controller closed")
            
            # Final status
            logger.info("🎯 Apollo workflow completed successfully!")
            
            return {
                "success": True,
                "search_id": search_id,
                "search_url": search_url,
                "bulk_url": bulk_url,
                "job_titles": job_titles,
                "domains_count": len(domains_list),
                "message": f"Successfully processed {len(domains_list)} domains and created Apollo search with ID: {search_id}"
            }
            
        except Exception as e:
            logger.error(f"❌ Error running Apollo workflow: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

class WebSearchManager:
    """
    Manager class that combines Brave Search and Claude's WebSearch for comprehensive web search with content reading
    """
    def __init__(self):
        try:
            self.brave_search = BraveSearchTool()
        except SearchError as e:
            logger.warning(f"Brave Search not available: {str(e)}")
            self.brave_search = None
        
        # Initialize OpenAI WebSearch tool for content reading
        self.openai_websearch = OpenAIWebSearchTool()
        
        # Initialize case study tool
        self.case_study_tool = CaseStudyTool(self)
        
        # Initialize Apollo processing tool
        self.apollo_tool = ApolloProcessingTool()
    
    async def search_and_read_content(self, query: str, count: int = 5, read_top_results: int = 3) -> Dict[str, Any]:
        """
        Perform a web search and read the top results for detailed content using Claude's WebSearch
        
        Args:
            query: Search query
            count: Number of search results to return
            read_top_results: Number of top results to read for detailed content
        
        Returns:
            Dictionary containing search results and read content
        """
        # Input validation
        if not query or not isinstance(query, str):
            raise SearchError("Query must be a non-empty string")
        
        if count < 1 or count > 20:
            raise SearchError("Count must be between 1 and 20")
        
        if read_top_results < 0 or read_top_results > count:
            raise SearchError("read_top_results must be between 0 and count")
        
        logger.info(f"search_and_read_content called with query='{query}', count={count}, read_top_results={read_top_results}")
        
        # Use OpenAI WebSearch tool which can read content directly
        try:
            # First try OpenAI WebSearch for comprehensive search with content
            if self.openai_websearch:
                logger.info("Using OpenAI WebSearch tool for search with content reading")
                search_results = await self.openai_websearch.search_with_content_extraction(query, count)
                
                # Validate search results
                if not isinstance(search_results, dict):
                    raise SearchError("Invalid search results format")
                
                search_results["method"] = "openai_websearch"
                search_results["content_read"] = True
                return search_results
            
            # Fallback to Brave Search only if Claude WebSearch is not available
            elif self.brave_search:
                logger.info("Fallback to Brave Search (no content reading)")
                search_results = await self.brave_search.search(query, count=count)
                
                # Validate search results
                if not isinstance(search_results, dict) or "results" not in search_results:
                    raise SearchError("Invalid search results from Brave Search")
                
                search_results["method"] = "brave_search_only" 
                search_results["content_read"] = False
                search_results["warning"] = "Content reading not available with Brave Search only"
                return search_results
            
            else:
                raise SearchError("No search tools available")
                
        except Exception as e:
            logger.error(f"Search error: {str(e)}")
            raise SearchError(f"Search failed: {str(e)}")
    
    # Keep old method for backward compatibility
    async def search_and_scrape(self, query: str, count: int = 5, scrape_top_results: int = 3) -> Dict[str, Any]:
        """
        Legacy method - redirects to search_and_read_content
        """
        logger.warning("search_and_scrape is deprecated, use search_and_read_content instead")
        return await self.search_and_read_content(query, count, scrape_top_results)
    
    async def search_news(self, query: str, count: int = 10) -> Dict[str, Any]:
        """Search for news articles"""
        if not self.brave_search:
            raise SearchError("Brave Search is not available")
        
        return await self.brave_search.search(query, count=count, search_type="news")
    
    async def search_images(self, query: str, count: int = 10) -> Dict[str, Any]:
        """Search for images"""
        if not self.brave_search:
            raise SearchError("Brave Search is not available")
        
        return await self.brave_search.search(query, count=count, search_type="images")
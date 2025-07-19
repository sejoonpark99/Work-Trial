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
    Case study lookup tool that builds on web search for domain-scoped case studies
    """
    def __init__(self, web_search_manager):
        self.web_search_manager = web_search_manager
        self.case_study_keywords = [
            "case study", "customer story", "success story", "implementation",
            "results", "ROI", "transformation", "deployment", "metrics",
            "performance", "growth", "improvement", "testimonial", "customer success",
            "client story", "business case", "use case", "implementation story"
        ]
        
        # Common company domains for faster case study reference
        self.common_company_domains = {
            'perplexity': 'perplexity.ai',
            'zerotier': 'zerotier.com', 
            'deepgram': 'deepgram.com',
            'scale': 'scale.com',
            'anthropic': 'anthropic.com',
            'openai': 'openai.com',
            'deepl': 'deepl.com',
            'mistral': 'mistral.ai',
            'cradlewise': 'cradlewise.com',
            'photoroom': 'photoroom.com'
        }
        
    async def lookup_case_study(self, company_domain: str, context: str = "", rep_domain: str = "") -> Dict[str, Any]:
        """
        Look up case studies for a specific company domain
        
        Args:
            company_domain: Domain or company name to search for (prospect)
            context: Additional context for the search
            rep_domain: Sales rep's domain to filter for own company's case studies
            
        Returns:
            Dictionary containing case study results
        """
        try:
            # Extract company name from domain for better search
            company_name = company_domain.replace('.com', '').replace('.org', '').replace('.net', '')
            
            # Build targeted search query based on context and guidelines
            search_terms = self._generate_targeted_search_queries(company_name, context, rep_domain)
            
            logger.info(f"Generated search queries for {company_name}: {search_terms}")
            
            all_results = []
            
            # Search with just the first term to avoid rate limits
            search_term = search_terms[0]  # Only use the first, most relevant term
            try:
                # Add delay to avoid rate limiting
                await asyncio.sleep(1)
                
                # Use basic search without scraping to avoid rate limits
                results = await self.web_search_manager.brave_search.search(
                    search_term, 
                    count=8  # Get more results in a single request
                )
                all_results.extend(results['results'])
                logger.info(f"Successfully searched for '{search_term}', found {len(results['results'])} results")
            except Exception as e:
                logger.error(f"Error searching for '{search_term}': {str(e)}")
                # Return error info for debugging
                return {
                    "ok": False,
                    "company_domain": company_domain,
                    "error": f"Search failed: {str(e)}"
                }
            
            # Rank and filter results with new scoring system
            ranked_results = self._rank_case_study_results(all_results, company_domain, rep_domain)
            
            # Get top result for detailed analysis
            top_result = ranked_results[0] if ranked_results else None
            
            if top_result:
                # Extract key information from the top result
                summary = self._extract_case_study_summary(top_result)
                
                return {
                    "ok": True,
                    "company_domain": company_domain,
                    "top_result": top_result,
                    "summary": summary,
                    "all_results": ranked_results[:5],  # Return top 5
                    "total_found": len(ranked_results)
                }
            else:
                return {
                    "ok": False,
                    "company_domain": company_domain,
                    "error": "No case studies found for this domain"
                }
                
        except Exception as e:
            logger.error(f"Case study lookup error: {str(e)}")
            return {
                "ok": False,
                "company_domain": company_domain,
                "error": str(e)
            }
    
    def _generate_targeted_search_queries(self, company_name: str, context: str = "", rep_domain: str = "") -> List[str]:
        """
        Generate intelligent, targeted search queries based on context and knowledge base guidelines.
        
        Args:
            company_name: The company name (e.g., "nike")
            context: Additional context (e.g., "automation", "marketing")
            rep_domain: The rep's company domain (e.g., "bloomreach.com")
            
        Returns:
            List of targeted search queries
        """
        # Build site filter to ensure we get case studies from the rep's company
        site_filter = ""
        if rep_domain:
            # Check if rep_domain is in our common domains mapping
            if rep_domain.lower() in self.common_company_domains:
                site_filter = f'site:{self.common_company_domains[rep_domain.lower()]}'
            else:
                site_filter = f'site:{rep_domain}'
        
        # Determine search focus based on context
        if context:
            context_lower = context.lower()
            
            # Map context to specific search terms
            context_mappings = {
                'automation': ['automation', 'workflow', 'process optimization', 'efficiency'],
                'marketing': ['marketing', 'personalization', 'campaign', 'customer engagement'],
                'ecommerce': ['ecommerce', 'online retail', 'digital commerce', 'conversion'],
                'analytics': ['analytics', 'data insights', 'reporting', 'business intelligence'],
                'personalization': ['personalization', 'customer experience', 'segmentation', 'targeting'],
                'growth': ['growth', 'revenue', 'expansion', 'scaling'],
                'conversion': ['conversion', 'optimization', 'A/B testing', 'performance'],
                'customer': ['customer success', 'retention', 'satisfaction', 'loyalty']
            }
            
            # Find relevant keywords
            relevant_keywords = []
            for key, keywords in context_mappings.items():
                if key in context_lower:
                    relevant_keywords.extend(keywords)
            
            if not relevant_keywords:
                relevant_keywords = [context]
        else:
            relevant_keywords = ['customer success', 'implementation', 'results']
        
        # Generate targeted search queries with emphasis on case study structure
        queries = []
        
        # Primary query: Target actual case study URLs with path filtering
        primary_context = relevant_keywords[0] if relevant_keywords else 'customer success'
        queries.append(f'"{company_name}" "case study" {primary_context} {site_filter} -inurl:blog -inurl:news')
        
        # Secondary query: Look specifically in case study directories
        queries.append(f'"{company_name}" {primary_context} {site_filter} inurl:case-studies OR inurl:customer-stories OR inurl:success-stories')
        
        # Tertiary query: PDF case studies with structure
        queries.append(f'"{company_name}" "case study" filetype:pdf {primary_context} {site_filter}')
        
        # Quaternary query: Customer testimonials with results
        queries.append(f'"{company_name}" customer testimonial results metrics {primary_context} {site_filter} -inurl:blog')
        
        return queries
    
    def parse_case_study_request(self, user_message: str) -> Dict[str, str]:
        """
        Parse natural language case study requests to extract company and context.
        
        Args:
            user_message: User's natural language request
            
        Returns:
            Dictionary with parsed company, context, and rep_domain
        """
        import re
        
        # Extract company mentions (looking for company names)
        company_patterns = [
            r'selling to (\w+)',
            r'prospect (\w+)',
            r'client (\w+)',
            r'customer (\w+)',
            r'company (\w+)',
            r'at (\w+)'
        ]
        
        company = None
        for pattern in company_patterns:
            match = re.search(pattern, user_message.lower())
            if match:
                company = match.group(1)
                break
        
        # Extract rep company (where the sales rep works)
        rep_patterns = [
            r'sales rep at (\w+)',
            r'work at (\w+)',
            r'from (\w+)',
            r'rep at (\w+)'
        ]
        
        rep_company = None
        for pattern in rep_patterns:
            match = re.search(pattern, user_message.lower())
            if match:
                rep_company = match.group(1)
                break
        
        # Extract context from common keywords
        context_keywords = ['automation', 'marketing', 'ecommerce', 'analytics', 
                          'personalization', 'growth', 'conversion', 'customer']
        
        context = None
        for keyword in context_keywords:
            if keyword in user_message.lower():
                context = keyword
                break
        
        return {
            'company': company,
            'rep_company': rep_company,
            'context': context or 'customer success'
        }
    
    def _validate_case_study_structure(self, content: str) -> Dict[str, Any]:
        """
        Validate that content has proper case study structure with challenge and solution sections.
        
        Args:
            content: The page content to validate
            
        Returns:
            Dictionary with validation results and scoring
        """
        content_lower = content.lower()
        validation_result = {
            'has_challenge': False,
            'has_solution': False,
            'has_results': False,
            'structure_score': 0,
            'sections_found': []
        }
        
        # Check for Challenge/Problem section
        challenge_keywords = ['challenge', 'problem', 'issue', 'obstacle', 'difficulty', 'pain point', 'before']
        for keyword in challenge_keywords:
            if keyword in content_lower:
                validation_result['has_challenge'] = True
                validation_result['sections_found'].append(keyword)
                break
        
        # Check for Solution/Implementation section
        solution_keywords = ['solution', 'implementation', 'approach', 'methodology', 'strategy', 'how we', 'our approach']
        for keyword in solution_keywords:
            if keyword in content_lower:
                validation_result['has_solution'] = True
                validation_result['sections_found'].append(keyword)
                break
        
        # Check for Results/Outcomes section
        results_keywords = ['results', 'outcomes', 'impact', 'achieved', 'improvement', 'success', 'roi', 'metrics', 'after']
        for keyword in results_keywords:
            if keyword in content_lower:
                validation_result['has_results'] = True
                validation_result['sections_found'].append(keyword)
                break
        
        # Calculate structure score
        if validation_result['has_challenge'] and validation_result['has_solution']:
            validation_result['structure_score'] = 20  # Base score for having both challenge and solution
            if validation_result['has_results']:
                validation_result['structure_score'] += 10  # Bonus for having results
        elif validation_result['has_challenge'] or validation_result['has_solution']:
            validation_result['structure_score'] = 5  # Partial score for having one section
        
        return validation_result
    
    def _rank_case_study_results(self, results: List[Dict[str, Any]], company_domain: str, rep_domain: str = "") -> List[Dict[str, Any]]:
        """Rank case study results by relevance with new scoring system"""
        scored_results = []
        
        for result in results:
            score = 0
            title = result.get('title', '').lower()
            description = result.get('description', '').lower()
            content = result.get('scraped_content', '').lower()
            url = result.get('url', '').lower()
            
            # CASE STUDY STRUCTURE VALIDATION - NEW PRIORITY
            full_text = f"{title} {description} {content}"
            structure_validation = self._validate_case_study_structure(full_text)
            score += structure_validation['structure_score']
            
            # Add structure validation to result for later reference
            result['structure_validation'] = structure_validation
            
            # NEW SCORING SYSTEM based on case_study_tool_changes.md
            
            # +2 points for same domain (rep's domain)
            if rep_domain and rep_domain.lower() in url:
                score += 2
            
            # +1 point for PDF or resources subdomain
            if 'filetype:pdf' in url or 'resources.' in url or '.pdf' in url:
                score += 1
            
            # +10 points for actual case study URLs
            if any(path in url for path in ['/case-studies/', '/customer-stories/', '/success-stories/', '/customers/']):
                score += 10
            
            # +5 points for case study in URL path
            if 'case-study' in url or 'customer-story' in url or 'success-story' in url:
                score += 5
            
            # -3 points for "How [prospect] helped..." patterns (wrong ownership)
            if f'how {company_domain.lower()}' in title or f'how {company_domain.lower()}' in description:
                score -= 3
            
            # -2 points for listicles
            if any(word in title for word in ['top 10', 'best practices', 'tips', 'guide to', 'how to']):
                score -= 2
            
            # -5 points for blog posts and news articles (NOT case studies)
            if any(path in url for path in ['/blog/', '/news/', '/press/', '/articles/']):
                score -= 5
            
            # -3 points for generic pages
            if any(word in title.lower() for word in ['what is', 'why', 'introduction to', 'overview of']):
                score -= 3
            
            # EXISTING SCORING (keep existing logic but with adjusted weights)
            
            # Domain relevance - prospect name as mandatory
            if company_domain.lower() in title:
                score += 10
            if company_domain.lower() in description:
                score += 5
            if company_domain.lower() in content:
                score += 3
            
            # Case study keywords
            for keyword in self.case_study_keywords:
                if keyword in title:
                    score += 8
                if keyword in description:
                    score += 4
                if keyword in content:
                    score += 2
            
            # Boost actual implementation and specific company results
            implementation_keywords = ['implementation', 'deployed', 'launched', 'achieved', 'increased', 'improved', 'reduced', 'saved']
            for keyword in implementation_keywords:
                if keyword in title:
                    score += 8
                if keyword in description:
                    score += 5
            
            # Metrics and results keywords
            metrics_keywords = ['roi', 'results', 'metrics', 'performance', 'growth', 'increase', 'improvement', '%', 'percent', 'x increase']
            for keyword in metrics_keywords:
                if keyword in title:
                    score += 6
                if keyword in description:
                    score += 3
                if keyword in content:
                    score += 1
            
            # Boost specific company mentions (not generic)
            company_indicators = ['customer', 'client', 'company', 'business', 'organization']
            for indicator in company_indicators:
                if f'{indicator} story' in title.lower() or f'{indicator} case' in title.lower():
                    score += 10
            
            # Recency boost (if we can detect dates)
            if '2024' in title or '2023' in title:
                score += 3
            
            scored_results.append({
                **result,
                'relevance_score': score
            })
        
        # Filter out results that don't have proper case study structure
        # Only keep results that have either challenge+solution OR high relevance score AND are not blog posts
        filtered_results = []
        for result in scored_results:
            structure_val = result.get('structure_validation', {})
            url = result.get('url', '').lower()
            
            # Skip blog posts, news articles, and generic pages entirely
            if any(path in url for path in ['/blog/', '/news/', '/press/', '/articles/']):
                continue
            
            # Keep results that have proper case study structure OR high relevance score
            if (structure_val.get('has_challenge') and structure_val.get('has_solution')) or result['relevance_score'] > 15:
                filtered_results.append(result)
        
        # Sort by score (descending) and remove duplicates
        filtered_results.sort(key=lambda x: x['relevance_score'], reverse=True)
        
        # Remove duplicates based on URL
        seen_urls = set()
        unique_results = []
        for result in filtered_results:
            url = result.get('url', '')
            if url not in seen_urls:
                seen_urls.add(url)
                unique_results.append(result)
        
        return unique_results
    
    def _extract_case_study_summary(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Extract key information from a case study result"""
        title = result.get('title', '')
        description = result.get('description', '')
        content = result.get('scraped_content', '')
        url = result.get('url', '')
        structure_validation = result.get('structure_validation', {})
        
        # Extract potential metrics
        metrics = []
        metric_patterns = [
            r'(\d+%?\s*(?:increase|improvement|growth|boost|rise))',
            r'(\d+%?\s*(?:decrease|reduction|drop|decline))',
            r'(\d+x\s*(?:faster|quicker|more|better))',
            r'(\$\d+[kmb]?\s*(?:saved|revenue|profit|cost))',
            r'(\d+%?\s*ROI)',
        ]
        
        full_text = f"{title} {description} {content}".lower()
        for pattern in metric_patterns:
            import re
            matches = re.findall(pattern, full_text, re.IGNORECASE)
            metrics.extend(matches)
        
        return {
            "title": title,
            "url": url,
            "description": description[:500],  # Truncate for summary
            "key_metrics": metrics[:5],  # Top 5 metrics
            "content_preview": content[:1000] if content else description[:1000],
            "relevance_score": result.get('relevance_score', 0),
            "structure_validation": {
                "has_challenge": structure_validation.get('has_challenge', False),
                "has_solution": structure_validation.get('has_solution', False),
                "has_results": structure_validation.get('has_results', False),
                "structure_score": structure_validation.get('structure_score', 0),
                "sections_found": structure_validation.get('sections_found', [])
            }
        }
    
    def save_as_markdown(self, case_study_data: Dict[str, Any], output_path: str = None) -> Dict[str, Any]:
        """
        Save case study analysis as a structured markdown file
        
        Args:
            case_study_data: The case study data from lookup_case_study
            output_path: Optional custom output path
            
        Returns:
            Dictionary with save result and file path
        """
        try:
            from datetime import datetime
            import os
            
            # Create output directory if it doesn't exist
            output_dir = output_path or os.path.join(os.getcwd(), "output", "case_studies")
            os.makedirs(output_dir, exist_ok=True)
            
            # Generate filename
            company_domain = case_study_data.get('company_domain', 'unknown')
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"case_study_{company_domain}_{timestamp}.md"
            filepath = os.path.join(output_dir, filename)
            
            # Build markdown content
            markdown_content = self._build_markdown_content(case_study_data)
            
            # Write to file
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(markdown_content)
            
            logger.info(f"Case study saved as markdown: {filepath}")
            
            return {
                "success": True,
                "filepath": filepath,
                "filename": filename,
                "size": len(markdown_content)
            }
            
        except Exception as e:
            logger.error(f"Error saving case study as markdown: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _build_markdown_content(self, case_study_data: Dict[str, Any]) -> str:
        """Build structured markdown content from case study data"""
        from datetime import datetime
        
        company_domain = case_study_data.get('company_domain', 'Unknown Company')
        top_result = case_study_data.get('top_result', {})
        summary = case_study_data.get('summary', {})
        all_results = case_study_data.get('all_results', [])
        
        # Build markdown content
        markdown = f"""# Case Study Analysis: {company_domain}

*Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*

## Summary

**Company:** {company_domain}  
**Total Results Found:** {case_study_data.get('total_found', 0)}  
**Analysis Status:** {'✅ Success' if case_study_data.get('ok') else '❌ Failed'}

## Top Case Study

"""
        
        if top_result:
            markdown += f"""### {summary.get('title', 'No title')}

**URL:** [{summary.get('url', 'No URL')}]({summary.get('url', '#')})  
**Relevance Score:** {summary.get('relevance_score', 0)}

#### Description
{summary.get('description', 'No description available')}

#### Key Metrics
"""
            
            key_metrics = summary.get('key_metrics', [])
            if key_metrics:
                for metric in key_metrics:
                    markdown += f"- {metric}\n"
            else:
                markdown += "- No specific metrics found\n"
            
            markdown += f"""
#### Content Preview
{summary.get('content_preview', 'No content preview available')}

"""
        
        # Add all results section
        markdown += """## All Results

| Rank | Title | URL | Score |
|------|-------|-----|-------|
"""
        
        for i, result in enumerate(all_results[:10], 1):  # Top 10 results
            title = result.get('title', 'No title')[:50] + ('...' if len(result.get('title', '')) > 50 else '')
            url = result.get('url', 'No URL')
            score = result.get('relevance_score', 0)
            markdown += f"| {i} | {title} | [{url}]({url}) | {score} |\n"
        
        # Add current behavior analysis
        markdown += """
## Current Behavior Analysis

### What the tool does today
1. **Domain scoping rule** - Takes the prospect company name and prepends a site: filter
2. **Search query example:** `{company_domain} case study site:{company_domain}.com`
3. **Results ranking** - Ranks by recency and numeric KPI keywords

### Why this misidentifies stories
- Current approach finds stories where the prospect is the **vendor**, not the **customer**
- This returns "How [Company] helped..." stories instead of "[Company] as customer" stories
- Domain scoping should be flipped to rep company domain

### Needed Changes
1. **Domain flip** - Filter by rep company domain instead of prospect domain
2. **Negative filters** - Exclude "How [prospect] helped..." patterns
3. **Schema tweak** - Better identification of customer vs vendor stories
4. **Ranking weights** - Updated scoring for customer success stories
5. **Better metrics** - Focus on customer outcome metrics
6. **Updated tests** - Test cases for improved accuracy

---

*This analysis was generated by the Case Study Tool and saved as markdown for easy sharing and reference.*
"""
        
        return markdown

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
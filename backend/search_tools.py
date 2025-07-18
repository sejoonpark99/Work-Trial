import os
import requests
import json
from typing import Dict, Any, List, Optional
import logging
from urllib.parse import quote
import time
import asyncio

logger = logging.getLogger(__name__)

class SearchError(Exception):
    pass

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

class ScraperJSTool:
    """
    ScraperJS API integration for enhanced data fetching
    """
    def __init__(self):
        self.api_key = os.getenv("SCRAPERJS_API_KEY")
        if not self.api_key:
            raise SearchError("SCRAPERJS_API_KEY environment variable not set")
        
        self.base_url = "https://api.scraperjs.com/v1"
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
    
    async def scrape_url(self, url: str, extract_text: bool = True, extract_links: bool = False) -> Dict[str, Any]:
        """
        Scrape content from a URL using ScraperJS API
        
        Args:
            url: URL to scrape
            extract_text: Whether to extract text content
            extract_links: Whether to extract links
        
        Returns:
            Dictionary containing scraped content
        """
        try:
            payload = {
                "url": url,
                "extract_text": extract_text,
                "extract_links": extract_links,
                "timeout": 30000,
                "wait_for": 3000
            }
            
            logger.info(f"ScraperJS: Scraping URL '{url}'")
            
            response = requests.post(
                f"{self.base_url}/scrape",
                headers=self.headers,
                json=payload,
                timeout=60
            )
            
            response.raise_for_status()
            data = response.json()
            
            # Process the scraped content
            result = {
                "url": url,
                "title": data.get("title", ""),
                "text": data.get("text", ""),
                "links": data.get("links", []) if extract_links else [],
                "success": data.get("success", False),
                "status_code": data.get("status_code", 0)
            }
            
            logger.info(f"ScraperJS: Successfully scraped {len(result['text'])} characters from '{url}'")
            return result
            
        except requests.exceptions.RequestException as e:
            logger.error(f"ScraperJS API error: {str(e)}")
            raise SearchError(f"ScraperJS API error: {str(e)}")
        except Exception as e:
            logger.error(f"ScraperJS error: {str(e)}")
            raise SearchError(f"ScraperJS error: {str(e)}")
    
    async def batch_scrape(self, urls: List[str], extract_text: bool = True) -> List[Dict[str, Any]]:
        """
        Scrape multiple URLs in batch
        
        Args:
            urls: List of URLs to scrape
            extract_text: Whether to extract text content
        
        Returns:
            List of dictionaries containing scraped content
        """
        results = []
        
        for url in urls:
            try:
                result = await self.scrape_url(url, extract_text=extract_text)
                results.append(result)
                # Add delay to respect rate limits
                time.sleep(1)
            except Exception as e:
                logger.error(f"Failed to scrape {url}: {str(e)}")
                results.append({
                    "url": url,
                    "success": False,
                    "error": str(e)
                })
        
        return results

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
            # Build search query filtering by rep domain to ensure we get our own case studies
            site_filter = ""
            if rep_domain:
                # Filter to rep's domain and resources subdomain
                site_filter = f'site:{rep_domain} OR site:resources.{rep_domain}'
            
            # Build search terms with prospect name as mandatory keyword
            base_query = f'"{company_domain}"'
            if context:
                base_query += f' {context}'
            
            search_terms = [
                f'{base_query} customer case study implementation results metrics {site_filter}',
                f'{base_query} customer success story ROI revenue lift {site_filter}',
                f'{base_query} client case study performance metrics results {site_filter}',
                f'{base_query} implementation success testimonial {site_filter} filetype:pdf'
            ]
            
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
    
    def _rank_case_study_results(self, results: List[Dict[str, Any]], company_domain: str, rep_domain: str = "") -> List[Dict[str, Any]]:
        """Rank case study results by relevance with new scoring system"""
        scored_results = []
        
        for result in results:
            score = 0
            title = result.get('title', '').lower()
            description = result.get('description', '').lower()
            content = result.get('scraped_content', '').lower()
            url = result.get('url', '').lower()
            
            # NEW SCORING SYSTEM based on case_study_tool_changes.md
            
            # +2 points for same domain (rep's domain)
            if rep_domain and rep_domain.lower() in url:
                score += 2
            
            # +1 point for PDF or resources subdomain
            if 'filetype:pdf' in url or 'resources.' in url or '.pdf' in url:
                score += 1
            
            # -3 points for "How [prospect] helped..." patterns (wrong ownership)
            if f'how {company_domain.lower()}' in title or f'how {company_domain.lower()}' in description:
                score -= 3
            
            # -2 points for listicles
            if any(word in title for word in ['top 10', 'best practices', 'tips', 'guide to', 'how to']):
                score -= 2
            
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
        
        # Filter out very low scoring results (likely generic articles)
        filtered_results = [r for r in scored_results if r['relevance_score'] > 0]
        
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
            "relevance_score": result.get('relevance_score', 0)
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

class WebSearchManager:
    """
    Manager class that combines Brave Search and ScraperJS for comprehensive web search
    """
    def __init__(self):
        try:
            self.brave_search = BraveSearchTool()
        except SearchError as e:
            logger.warning(f"Brave Search not available: {str(e)}")
            self.brave_search = None
        
        try:
            self.scraperjs = ScraperJSTool()
        except SearchError as e:
            logger.warning(f"ScraperJS not available: {str(e)}")
            self.scraperjs = None
        
        # Initialize case study tool
        self.case_study_tool = CaseStudyTool(self)
    
    async def search_and_scrape(self, query: str, count: int = 5, scrape_top_results: int = 3) -> Dict[str, Any]:
        """
        Perform a web search and scrape the top results for detailed content
        
        Args:
            query: Search query
            count: Number of search results to return
            scrape_top_results: Number of top results to scrape for detailed content
        
        Returns:
            Dictionary containing search results and scraped content
        """
        if not self.brave_search:
            raise SearchError("Brave Search is not available")
        
        # Perform the search
        search_results = await self.brave_search.search(query, count=count)
        
        # Scrape top results if ScraperJS is available
        scraped_content = []
        if self.scraperjs and scrape_top_results > 0:
            top_urls = [result["url"] for result in search_results["results"][:scrape_top_results]]
            scraped_content = await self.scraperjs.batch_scrape(top_urls)
        
        # Combine search results with scraped content
        enhanced_results = []
        for i, result in enumerate(search_results["results"]):
            enhanced_result = result.copy()
            
            # Add scraped content if available
            if i < len(scraped_content) and scraped_content[i]["success"]:
                enhanced_result["scraped_content"] = scraped_content[i]["text"][:2000]  # Limit content
                enhanced_result["full_title"] = scraped_content[i]["title"]
            
            enhanced_results.append(enhanced_result)
        
        return {
            "query": query,
            "results": enhanced_results,
            "total": search_results["total"],
            "scraped_count": len([c for c in scraped_content if c.get("success", False)])
        }
    
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
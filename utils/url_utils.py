"""
URL Utilities for Apollo.io Automation
Handles URL parsing, search ID extraction, and bulk URL construction
"""
import re
import logging
from urllib.parse import urlparse, parse_qs, quote, urlencode
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

# Apollo.io base URL for people search
APOLLO_PEOPLE_BASE_URL = "https://app.apollo.io/#/people"

def extract_search_id(url: str) -> Optional[str]:
    """
    Extract search ID from Apollo.io URL
    
    The search ID is typically in the URL fragment as qOrganizationSearchListId
    Example: https://app.apollo.io/#/companies?qOrganizationSearchListId=12345
    
    Args:
        url: Apollo.io URL containing search ID
        
    Returns:
        Search ID string or None if not found
    """
    try:
        parsed = urlparse(url)
        fragment = parsed.fragment or ""
        
        # Handle both fragment and query parameters
        if fragment:
            # Check if fragment contains query parameters
            if '?' in fragment:
                # Split fragment into path and query
                frag_parts = fragment.split('?', 1)
                if len(frag_parts) > 1:
                    query_string = frag_parts[1]
                    params = parse_qs(query_string)
                    
                    # Look for search ID in various parameter names
                    search_id_params = [
                        'qOrganizationSearchListId',
                        'organizationSearchListId', 
                        'searchListId',
                        'listId'
                    ]
                    
                    for param in search_id_params:
                        if param in params and params[param]:
                            search_id = params[param][0]
                            logger.info(f"Extracted search ID: {search_id}")
                            return search_id
        
        # Also check main query parameters
        if parsed.query:
            params = parse_qs(parsed.query)
            search_id_params = [
                'qOrganizationSearchListId',
                'organizationSearchListId',
                'searchListId',
                'listId'
            ]
            
            for param in search_id_params:
                if param in params and params[param]:
                    search_id = params[param][0]
                    logger.info(f"Extracted search ID from query: {search_id}")
                    return search_id
        
        logger.warning(f"No search ID found in URL: {url}")
        return None
        
    except Exception as e:
        logger.error(f"Error extracting search ID from URL {url}: {str(e)}")
        return None

def build_bulk_url(search_id: str, job_titles: List[str], page: int = 1) -> str:
    """
    Build bulk URL for Apollo.io people search with job titles
    
    Args:
        search_id: Organization search list ID
        job_titles: List of job titles to filter by
        page: Page number (default: 1)
        
    Returns:
        Complete Apollo.io people search URL
    """
    try:
        # Base parameters
        params = {
            'page': str(page),
            'sortAscending': 'false',
            'sortByField': '[none]',
            'qOrganizationSearchListId': search_id
        }
        
        # Build query string manually to handle multiple personTitles[] parameters
        query_parts = []
        
        # Add base parameters
        for key, value in params.items():
            query_parts.append(f"{key}={quote(str(value))}")
        
        # Add job titles as personTitles[] parameters
        for title in job_titles:
            encoded_title = quote(title)
            query_parts.append(f"personTitles[]={encoded_title}")
        
        # Construct final URL
        query_string = "&".join(query_parts)
        full_url = f"{APOLLO_PEOPLE_BASE_URL}?{query_string}"
        
        logger.info(f"Built bulk URL with {len(job_titles)} job titles for search ID {search_id}")
        
        return full_url
        
    except Exception as e:
        logger.error(f"Error building bulk URL: {str(e)}")
        raise

def parse_apollo_url(url: str) -> Dict[str, Any]:
    """
    Parse Apollo.io URL and extract all parameters
    
    Args:
        url: Apollo.io URL to parse
        
    Returns:
        Dictionary containing parsed URL components
    """
    try:
        parsed = urlparse(url)
        
        result = {
            'base_url': f"{parsed.scheme}://{parsed.netloc}",
            'path': parsed.path,
            'fragment': parsed.fragment,
            'query_params': {},
            'fragment_params': {},
            'search_id': None,
            'job_titles': [],
            'page': 1
        }
        
        # Parse query parameters
        if parsed.query:
            result['query_params'] = parse_qs(parsed.query)
        
        # Parse fragment parameters  
        if parsed.fragment and '?' in parsed.fragment:
            frag_parts = parsed.fragment.split('?', 1)
            if len(frag_parts) > 1:
                result['fragment_params'] = parse_qs(frag_parts[1])
        
        # Extract search ID
        result['search_id'] = extract_search_id(url)
        
        # Extract job titles from personTitles[] parameters
        all_params = {**result['query_params'], **result['fragment_params']}
        
        if 'personTitles[]' in all_params:
            result['job_titles'] = all_params['personTitles[]']
        
        # Extract page number
        if 'page' in all_params:
            try:
                result['page'] = int(all_params['page'][0])
            except (ValueError, IndexError):
                result['page'] = 1
        
        return result
        
    except Exception as e:
        logger.error(f"Error parsing Apollo URL {url}: {str(e)}")
        raise

def validate_apollo_url(url: str) -> bool:
    """
    Validate if URL is a valid Apollo.io URL
    
    Args:
        url: URL to validate
        
    Returns:
        True if valid Apollo.io URL
    """
    try:
        parsed = urlparse(url)
        
        # Check if it's an Apollo.io domain
        if 'apollo.io' not in parsed.netloc:
            return False
        
        # Check if it's HTTPS
        if parsed.scheme != 'https':
            return False
        
        return True
        
    except Exception:
        return False

def build_company_search_url(domains: List[str]) -> str:
    """
    Build URL for Apollo.io company search
    
    Args:
        domains: List of company domains
        
    Returns:
        Apollo.io company search URL
    """
    try:
        base_url = "https://app.apollo.io/#/companies"
        
        # For now, return base URL - domain filtering is handled in browser automation
        return base_url
        
    except Exception as e:
        logger.error(f"Error building company search URL: {str(e)}")
        raise

# Test and validation functions
def test_url_extraction():
    """Test URL extraction functionality"""
    test_urls = [
        "https://app.apollo.io/#/companies?qOrganizationSearchListId=12345",
        "https://app.apollo.io/#/people?page=1&qOrganizationSearchListId=67890&personTitles[]=CEO",
        "https://app.apollo.io/companies?organizationSearchListId=11111"
    ]
    
    print("Testing URL extraction:")
    for url in test_urls:
        search_id = extract_search_id(url)
        print(f"URL: {url}")
        print(f"Search ID: {search_id}")
        print(f"Valid: {validate_apollo_url(url)}")
        print("-" * 50)

if __name__ == "__main__":
    # Test URL utilities
    test_url_extraction()
    
    # Test bulk URL building
    print("\nTesting bulk URL building:")
    test_search_id = "12345"
    test_job_titles = ["CEO", "CTO", "VP Sales"]
    
    bulk_url = build_bulk_url(test_search_id, test_job_titles)
    print(f"Bulk URL: {bulk_url}")
    
    # Parse the built URL
    parsed = parse_apollo_url(bulk_url)
    print(f"Parsed URL: {parsed}")
    
    print("\nURL utilities test complete.")
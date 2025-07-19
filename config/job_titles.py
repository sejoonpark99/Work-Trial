"""
Job Titles Configuration for Apollo.io Contact Extraction
Defines job titles to filter contacts by role
"""
from urllib.parse import quote
from typing import List, Dict

# Primary job titles for contact extraction
JOB_TITLES = [
    "CEO",
    "CTO", 
    "CFO",
    "VP Sales",
    "VP Marketing",
    "VP Engineering",
    "VP Product",
    "Chief Revenue Officer",
    "Chief Marketing Officer",
    "Chief Technology Officer",
    "Chief Financial Officer",
    "President",
    "Co-Founder",
    "Founder",
    "Head of Sales",
    "Head of Marketing",
    "Head of Engineering",
    "Head of Product",
    "Director of Sales",
    "Director of Marketing",
    "Director of Engineering",
    "Director of Product",
    "Sales Director",
    "Marketing Director",
    "Engineering Director",
    "Product Director",
    "General Manager",
    "Managing Director",
    "Executive Vice President",
    "Senior Vice President"
]

# Categorized job titles for targeted searches
JOB_TITLE_CATEGORIES = {
    "c_suite": [
        "CEO",
        "CTO",
        "CFO", 
        "COO",
        "Chief Executive Officer",
        "Chief Technology Officer",
        "Chief Financial Officer",
        "Chief Operating Officer",
        "Chief Revenue Officer",
        "Chief Marketing Officer",
        "Chief Product Officer",
        "Chief Data Officer"
    ],
    "vp_level": [
        "VP Sales",
        "VP Marketing", 
        "VP Engineering",
        "VP Product",
        "VP Operations",
        "VP Business Development",
        "Vice President Sales",
        "Vice President Marketing",
        "Vice President Engineering",
        "Vice President Product",
        "Executive Vice President",
        "Senior Vice President"
    ],
    "director_level": [
        "Director of Sales",
        "Director of Marketing",
        "Director of Engineering", 
        "Director of Product",
        "Director of Operations",
        "Director of Business Development",
        "Sales Director",
        "Marketing Director",
        "Engineering Director",
        "Product Director",
        "Managing Director"
    ],
    "head_level": [
        "Head of Sales",
        "Head of Marketing",
        "Head of Engineering",
        "Head of Product", 
        "Head of Operations",
        "Head of Business Development",
        "Head of Growth",
        "Head of Customer Success"
    ],
    "founders": [
        "Founder",
        "Co-Founder",
        "Founding Partner",
        "Founding Member"
    ]
}

def get_job_titles_by_category(category: str) -> List[str]:
    """
    Get job titles for a specific category
    
    Args:
        category: Category key (c_suite, vp_level, director_level, head_level, founders)
        
    Returns:
        List of job titles in that category
    """
    return JOB_TITLE_CATEGORIES.get(category, [])

def get_all_job_titles() -> List[str]:
    """
    Get all job titles from all categories
    
    Returns:
        Complete list of all job titles
    """
    all_titles = []
    for titles in JOB_TITLE_CATEGORIES.values():
        all_titles.extend(titles)
    return list(set(all_titles))  # Remove duplicates

def url_encode_job_titles(titles: List[str]) -> List[str]:
    """
    URL encode job titles for use in Apollo.io URLs
    
    Args:
        titles: List of job titles to encode
        
    Returns:
        List of URL-encoded job titles
    """
    return [quote(title) for title in titles]

def get_priority_titles() -> List[str]:
    """
    Get high-priority job titles for initial searches
    
    Returns:
        List of most important job titles
    """
    return JOB_TITLES[:15]  # Top 15 most important titles

def validate_job_title(title: str) -> bool:
    """
    Validate if a job title is in our approved list
    
    Args:
        title: Job title to validate
        
    Returns:
        True if title is in approved list
    """
    all_titles = get_all_job_titles()
    return title in all_titles

# Default export
__all__ = [
    "JOB_TITLES",
    "JOB_TITLE_CATEGORIES", 
    "get_job_titles_by_category",
    "get_all_job_titles",
    "url_encode_job_titles",
    "get_priority_titles",
    "validate_job_title"
]

if __name__ == "__main__":
    # Test URL encoding
    print("Testing URL encoding:")
    test_titles = ["VP Sales", "Head of Marketing", "C-Suite Executive"]
    encoded = url_encode_job_titles(test_titles)
    
    for original, encoded_title in zip(test_titles, encoded):
        print(f"'{original}' -> '{encoded_title}'")
    
    # Show categories
    print(f"\nJob title categories:")
    for category, titles in JOB_TITLE_CATEGORIES.items():
        print(f"{category}: {len(titles)} titles")
        
    print(f"\nTotal unique job titles: {len(get_all_job_titles())}")
    print(f"Priority titles: {len(get_priority_titles())}")
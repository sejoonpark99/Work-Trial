const API_BASE_URL = process.env.API_BASE_URL || 'http://127.0.0.1:8000';

export async function POST(req: Request) {
  try {
    const { query, count = 10, search_type = "web", scrape_top_results = 3 } = await req.json();
    
    console.log(`Search API: Searching for "${query}" (type: ${search_type})`);
    
    const payload = {
      query,
      count,
      search_type,
      scrape_top_results
    };
    
    const response = await fetch(`${API_BASE_URL}/search`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    });
    
    if (!response.ok) {
      throw new Error(`Backend error: ${response.status}`);
    }
    
    const data = await response.json();
    
    if (!data.ok) {
      throw new Error(data.error?.message || 'Search failed');
    }
    
    console.log(`Search API: Found ${data.total} results for "${query}"`);
    
    return new Response(JSON.stringify(data), {
      headers: {
        'Content-Type': 'application/json',
      },
    });
    
  } catch (error) {
    console.error('Search API error:', error);
    return new Response(
      JSON.stringify({
        ok: false,
        error: error instanceof Error ? error.message : 'Unknown error'
      }),
      {
        status: 500,
        headers: {
          'Content-Type': 'application/json',
        },
      }
    );
  }
}

export async function GET() {
  try {
    console.log('Testing search functionality');
    
    const response = await fetch(`${API_BASE_URL}/search/test`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });
    
    if (!response.ok) {
      throw new Error(`Backend error: ${response.status}`);
    }
    
    const data = await response.json();
    
    return new Response(JSON.stringify(data), {
      headers: {
        'Content-Type': 'application/json',
      },
    });
    
  } catch (error) {
    console.error('Search test error:', error);
    return new Response(
      JSON.stringify({
        error: error instanceof Error ? error.message : 'Unknown error'
      }),
      {
        status: 500,
        headers: {
          'Content-Type': 'application/json',
        },
      }
    );
  }
}
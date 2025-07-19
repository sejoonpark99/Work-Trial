import { NextRequest, NextResponse } from 'next/server';

interface LinkPreviewData {
  title?: string;
  description?: string;
  image?: string;
  url: string;
}

export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams;
  const url = searchParams.get('url');

  if (!url) {
    return NextResponse.json({ error: 'URL parameter is required' }, { status: 400 });
  }

  try {
    // Validate URL
    const validUrl = new URL(url);
    
    // Fetch the page
    const response = await fetch(validUrl.toString(), {
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
      },
      signal: AbortSignal.timeout(10000), // 10 second timeout
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const html = await response.text();
    
    // Extract metadata using regex patterns
    const preview: LinkPreviewData = {
      url: validUrl.toString(),
    };

    // Extract title
    const titleMatch = html.match(/<title[^>]*>([^<]+)<\/title>/i) ||
                      html.match(/<meta[^>]*property="og:title"[^>]*content="([^"]*)"[^>]*>/i) ||
                      html.match(/<meta[^>]*name="twitter:title"[^>]*content="([^"]*)"[^>]*>/i);
    if (titleMatch) {
      preview.title = titleMatch[1].trim();
    }

    // Extract description
    const descriptionMatch = html.match(/<meta[^>]*property="og:description"[^>]*content="([^"]*)"[^>]*>/i) ||
                            html.match(/<meta[^>]*name="description"[^>]*content="([^"]*)"[^>]*>/i) ||
                            html.match(/<meta[^>]*name="twitter:description"[^>]*content="([^"]*)"[^>]*>/i);
    if (descriptionMatch) {
      preview.description = descriptionMatch[1].trim();
    }

    // Extract image
    const imageMatch = html.match(/<meta[^>]*property="og:image"[^>]*content="([^"]*)"[^>]*>/i) ||
                      html.match(/<meta[^>]*name="twitter:image"[^>]*content="([^"]*)"[^>]*>/i);
    if (imageMatch) {
      let imageUrl = imageMatch[1].trim();
      // Convert relative URLs to absolute
      if (imageUrl.startsWith('/')) {
        imageUrl = `${validUrl.origin}${imageUrl}`;
      } else if (!imageUrl.startsWith('http')) {
        imageUrl = `${validUrl.origin}/${imageUrl}`;
      }
      preview.image = imageUrl;
    }

    return NextResponse.json(preview);
  } catch (error) {
    console.error('Link preview error:', error);
    return NextResponse.json(
      { 
        error: 'Failed to fetch link preview',
        url: url 
      }, 
      { status: 500 }
    );
  }
}
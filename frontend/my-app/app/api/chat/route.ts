const API_BASE_URL = process.env.API_BASE_URL || 'http://localhost:8000';

export async function GET() {
  return Response.json({ 
    status: 'ok', 
    message: 'Chat API endpoint is working',
    timestamp: new Date().toISOString()
  });
}

export async function POST(req: Request) {
  try {
    // Debug the incoming request
    console.log('Request method:', req.method);
    console.log('Request headers:', Object.fromEntries(req.headers.entries()));
    
    // Check if request has body
    const body = await req.text();
    console.log('Request body:', body);
    
    if (!body || body.trim() === '') {
      throw new Error('Request body is empty');
    }
    
    // Try to parse the JSON
    let requestData;
    try {
      requestData = JSON.parse(body);
    } catch (parseError) {
      console.error('JSON parse error:', parseError);
      throw new Error('Invalid JSON in request body');
    }
    
    const { messages, system, tools, agent_mode } = requestData;
    
    // Convert messages to our backend format
    const backendMessages = messages.map((msg: any) => ({
      role: msg.role,
      content: Array.isArray(msg.content) 
        ? msg.content.map((c: any) => c.text || c.content).join('')
        : msg.content
    }));
    
    // Create payload for backend
    const payload = {
      messages: backendMessages,
      provider: 'openai',
      model: 'gpt-4o-mini',
      agent_mode: 'agent', // Always use agent mode with intelligent tool selection
      settings: {
        showCost: true,
        contextCompression: false
      }
    };
    
    // Add system message if present
    if (system) {
      payload.messages.unshift({
        role: 'system',
        content: system
      });
    }
    
    console.log(`Connecting to: ${API_BASE_URL}/chat`);
    console.log('Sending payload:', JSON.stringify(payload, null, 2));
    const response = await fetch(`${API_BASE_URL}/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    });
    
    if (!response.ok) {
      throw new Error(`Backend error: ${response.status}`);
    }
    
    // Check if response is streaming (agent mode)
    const contentType = response.headers.get('content-type');
    if (contentType?.includes('text/plain')) {
      // Backend sends AI SDK format chunks, pass through with manual streaming
      console.log('Received streaming response from backend, manual streaming');
      
      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error('No reader available');
      }
      
      const stream = new ReadableStream({
        start(controller) {
          let buffer = '';
          let isClosed = false;
          
          const safeEnqueue = (data: Uint8Array) => {
            if (!isClosed) {
              try {
                controller.enqueue(data);
              } catch (error) {
                console.error('Enqueue error:', error);
                isClosed = true;
              }
            }
          };
          
          const safeClose = () => {
            if (!isClosed) {
              try {
                controller.close();
                isClosed = true;
              } catch (error) {
                console.error('Close error:', error);
              }
            }
          };
          
          const pump = async () => {
            try {
              while (true) {
                const { done, value } = await reader.read();
                if (done) {
                  // Send any remaining buffer
                  if (buffer.trim()) {
                    safeEnqueue(new TextEncoder().encode(buffer));
                  }
                  break;
                }
                
                const chunk = new TextDecoder().decode(value);
                console.log('Raw chunk received:', chunk);
                
                // Add to buffer
                buffer += chunk;
                
                // Split by lines and process complete lines
                const lines = buffer.split('\n');
                
                // Keep the last potentially incomplete line in buffer
                buffer = lines.pop() || '';
                
                // Process complete lines
                for (const line of lines) {
                  if (line.trim()) {
                    console.log('Streaming line:', line);
                    
                    // Send each complete line immediately
                    safeEnqueue(new TextEncoder().encode(line + '\n'));
                  }
                }
              }
            } catch (error) {
              console.error('Streaming error:', error);
              if (!isClosed) {
                try {
                  controller.error(error);
                  isClosed = true;
                } catch (e) {
                  console.error('Error reporting error:', e);
                }
              }
            } finally {
              safeClose();
            }
          };
          pump();
        }
      });
      
      return new Response(stream, {
        headers: {
          'Content-Type': 'text/plain; charset=utf-8',
          'Cache-Control': 'no-cache, no-store, must-revalidate',
          'Connection': 'keep-alive',
          'X-Accel-Buffering': 'no', // Disable nginx buffering
          'X-Content-Type-Options': 'nosniff',
          'Transfer-Encoding': 'chunked', // Force chunked encoding
        },
      });
    }
    
    // Handle regular JSON response (chat mode)
    const data = await response.json();
    
    if (!data.ok) {
      throw new Error(data.error?.message || 'Backend returned error');
    }
    
    console.log('Backend response data:', JSON.stringify(data, null, 2));
    
    // Return streaming response in AI SDK format with progressive delivery
    const stream = new ReadableStream({
      start(controller) {
        const processPartsSequentially = async () => {
          if (data.parts && data.parts.length > 0) {
            console.log('Found parts:', data.parts.length);
            
            for (let index = 0; index < data.parts.length; index++) {
              const part = data.parts[index];
              console.log(`Processing part ${index}:`, part);
              
              if (part.type === 'thought_card') {
                const toolCallId = `thought_${index}`;
                const toolCall = `9:${JSON.stringify({
                  toolCallId: toolCallId,
                  toolName: "thought_card",
                  args: JSON.stringify(part)
                })}\n`;
                console.log('Sending toolCall:', toolCall);
                controller.enqueue(new TextEncoder().encode(toolCall));
                
                // Add delay between thought cards
                await new Promise(resolve => setTimeout(resolve, 200));
              } else if (part.type === 'text') {
                const textChunk = `0:${JSON.stringify(part.text)}\n`;
                controller.enqueue(new TextEncoder().encode(textChunk));
                await new Promise(resolve => setTimeout(resolve, 100));
              }
            }
          } else {
            console.log('No parts found, using fallback message');
            const textChunk = `0:${JSON.stringify(data.message.content)}\n`;
            controller.enqueue(new TextEncoder().encode(textChunk));
          }
          
          const finishChunk = `d:{"finishReason":"stop","usage":${JSON.stringify(data.usage)}}\n`;
          controller.enqueue(new TextEncoder().encode(finishChunk));
          
          controller.close();
        };
        
        processPartsSequentially().catch(error => {
          console.error('Error in sequential processing:', error);
          controller.error(error);
        });
      }
    });

    return new Response(stream, {
      headers: {
        'Content-Type': 'text/plain; charset=utf-8',
      },
    });
    
  } catch (error) {
    console.error('API route error:', error);
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

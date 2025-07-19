"use client";

import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Play, 
  Square, 
  Globe, 
  Code, 
  Camera,
  Loader2,
  AlertCircle,
  Maximize2,
  Minimize2,
  X,
  CheckCircle,
  Monitor,
  ExternalLink
} from 'lucide-react';

interface BrowserAutomationViewerProps {
  isVisible: boolean;
  onClose?: () => void;
}

interface BrowserSession {
  sessionId: string;
  isActive: boolean;
  currentUrl: string;
  lastScreenshot: string;
  websocket: WebSocket | null;
}

export const BrowserAutomationViewer: React.FC<BrowserAutomationViewerProps> = ({
  isVisible,
  onClose
}) => {
  const [session, setSession] = useState<BrowserSession | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [currentUrl, setCurrentUrl] = useState('https://example.com');
  const [script, setScript] = useState('');
  const [isConnected, setIsConnected] = useState(false);
  const [automationRequest, setAutomationRequest] = useState('');
  const [automationResult, setAutomationResult] = useState<any>(null);
  
  const wsRef = useRef<WebSocket | null>(null);
  const screenshotRef = useRef<HTMLImageElement>(null);

  // Create browser session
  const createSession = async () => {
    setIsLoading(true);
    setError(null);
    
    try {
      const response = await fetch('http://localhost:8000/browser/session', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });
      
      const data = await response.json();
      
      if (data.success) {
        const newSession: BrowserSession = {
          sessionId: data.session_id,
          isActive: true,
          currentUrl: '',
          lastScreenshot: '',
          websocket: null
        };
        
        setSession(newSession);
        connectWebSocket(data.session_id);
      } else {
        setError(data.error || 'Failed to create browser session');
      }
    } catch (err) {
      setError('Failed to connect to browser service');
      console.error('Session creation error:', err);
    } finally {
      setIsLoading(false);
    }
  };

  // Connect to WebSocket for live streaming
  const connectWebSocket = (sessionId: string) => {
    try {
      const ws = new WebSocket(`ws://localhost:8000/browser/stream/${sessionId}`);
      wsRef.current = ws;
      
      ws.onopen = () => {
        console.log('WebSocket connected');
        setIsConnected(true);
        setError(null);
      };
      
      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          
          if (data.type === 'screenshot') {
            setSession(prev => prev ? {
              ...prev,
              lastScreenshot: data.data
            } : null);
          } else if (data.type === 'error') {
            setError(data.message);
          }
        } catch (err) {
          console.error('WebSocket message error:', err);
        }
      };
      
      ws.onclose = () => {
        console.log('WebSocket disconnected');
        setIsConnected(false);
      };
      
      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        setError('WebSocket connection failed');
        setIsConnected(false);
      };
      
      // Update session with websocket
      setSession(prev => prev ? { ...prev, websocket: ws } : null);
      
    } catch (err) {
      console.error('WebSocket connection error:', err);
      setError('Failed to establish live streaming connection');
    }
  };

  // Navigate to URL
  const navigateToUrl = async () => {
    if (!session) return;
    
    setIsLoading(true);
    try {
      const response = await fetch('http://localhost:8000/browser/navigate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          session_id: session.sessionId,
          url: currentUrl
        }),
      });
      
      const data = await response.json();
      
      if (data.success) {
        setSession(prev => prev ? {
          ...prev,
          currentUrl: currentUrl,
          lastScreenshot: data.data.screenshot || prev.lastScreenshot
        } : null);
      } else {
        setError(data.error || 'Navigation failed');
      }
    } catch (err) {
      setError('Navigation request failed');
      console.error('Navigation error:', err);
    } finally {
      setIsLoading(false);
    }
  };

  // Execute JavaScript
  const executeScript = async () => {
    if (!session || !script.trim()) return;
    
    setIsLoading(true);
    try {
      const response = await fetch('http://localhost:8000/browser/script', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          session_id: session.sessionId,
          script: script
        }),
      });
      
      const data = await response.json();
      
      if (data.success) {
        console.log('Script result:', data.data.result);
        // Screenshot will be updated via WebSocket
      } else {
        setError(data.error || 'Script execution failed');
      }
    } catch (err) {
      setError('Script execution request failed');
      console.error('Script execution error:', err);
    } finally {
      setIsLoading(false);
    }
  };

  // Close session
  const closeSession = async () => {
    if (!session) return;
    
    try {
      // Close WebSocket
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
      
      // Close session on server
      await fetch(`http://localhost:8000/browser/session/${session.sessionId}`, {
        method: 'DELETE',
      });
      
      setSession(null);
      setIsConnected(false);
      setError(null);
    } catch (err) {
      console.error('Session close error:', err);
    }
  };

  // Request screenshot manually
  const requestScreenshot = () => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'request_screenshot' }));
    }
  };

  // Run browser-use automation
  const runAutomation = async () => {
    if (!automationRequest.trim()) return;
    
    setIsLoading(true);
    setError(null);
    setAutomationResult(null);
    
    try {
      const response = await fetch('http://localhost:8000/browser/automate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          user_request: automationRequest
        }),
      });
      
      const data = await response.json();
      
      if (data.success) {
        setAutomationResult(data);
        console.log('Automation completed:', data);
      } else {
        setError(data.error || 'Automation failed');
      }
    } catch (err) {
      setError('Automation request failed');
      console.error('Automation error:', err);
    } finally {
      setIsLoading(false);
    }
  };

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  if (!isVisible) return null;

  return (
    <div
      className={`
        ${isFullscreen 
          ? 'fixed inset-0 z-50 bg-white' 
          : 'mt-4 bg-white/40 backdrop-blur-md rounded-xl border border-gray-300/60 shadow-xl ring-1 ring-gray-400/30'
        }
      `}
    >
        {/* Header */}
        <div className="flex items-center gap-2 text-sm font-medium text-black p-4">
          <Globe className="h-4 w-4 text-gray-600" />
          <span>Browser Automation</span>
          
          {session && (
            <div className={`flex items-center gap-1 px-2 py-1 rounded-full text-xs ml-auto ${
              isConnected ? 'bg-gray-100/80 text-gray-700' : 'bg-gray-100/80 text-gray-600'
            }`}>
              <div className={`w-1.5 h-1.5 rounded-full ${
                isConnected ? 'bg-gray-600' : 'bg-gray-500'
              }`} />
              {isConnected ? 'Live' : 'Ready'}
            </div>
          )}
          
          <div className="flex items-center gap-1 ml-2">
            {!isFullscreen && (
              <button
                onClick={() => setIsFullscreen(true)}
                className="p-1 hover:bg-white/20 rounded-md transition-colors"
              >
                <Maximize2 className="h-3 w-3 text-black" />
              </button>
            )}
            {onClose && (
              <button
                onClick={onClose}
                className="p-1 hover:bg-white/20 rounded-md transition-colors"
              >
                <X className="h-3 w-3 text-black" />
              </button>
            )}
          </div>
        </div>

        <div className={`${isFullscreen ? 'h-full flex flex-col' : 'px-4 pb-4'}`}>
          {/* Browser-Use Automation (Primary) */}
          <div className="bg-white/50 backdrop-blur-sm rounded-lg p-3 border border-gray-300/40 shadow-sm mb-3">
            <h4 className="text-sm font-medium text-black mb-3 flex items-center gap-2">
              <Code className="h-4 w-4 text-gray-600" />
              AI Browser Automation
            </h4>
            <div className="flex items-center gap-2">
              <input
                type="text"
                value={automationRequest}
                onChange={(e) => setAutomationRequest(e.target.value)}
                placeholder="e.g., 'competitor pricing for stripe.com' or 'research hubspot features'"
                className="flex-1 px-3 py-2 bg-white/80 border border-gray-300/60 rounded-lg focus:ring-2 focus:ring-gray-500 focus:border-transparent text-sm"
                onKeyDown={(e) => e.key === 'Enter' && !isLoading && runAutomation()}
              />
              <button
                onClick={runAutomation}
                disabled={isLoading || !automationRequest.trim()}
                className="flex items-center gap-2 px-3 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 disabled:opacity-50 text-sm"
              >
                {isLoading ? <Loader2 className="h-3 w-3 animate-spin" /> : <Play className="h-3 w-3" />}
                Run
              </button>
            </div>
            <p className="text-xs text-black/70 mt-2">
              AI agent will automate browser tasks and generate reports
            </p>
          </div>

          {/* Manual Session Management (Secondary) */}
          <details className="group">
            <summary className="cursor-pointer text-xs text-black/60 hover:text-black">
              Advanced Manual Controls
            </summary>
            <div className="mt-2 space-y-2 bg-white/50 backdrop-blur-sm rounded-lg p-3 border border-gray-300/40 shadow-sm">
              <div className="flex items-center gap-3">
                {!session ? (
                  <button
                    onClick={createSession}
                    disabled={isLoading}
                    className="flex items-center gap-2 px-4 py-2 bg-gray-500 text-white rounded-lg hover:bg-gray-600 disabled:opacity-50"
                  >
                    {isLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
                    Start Manual Session
                  </button>
                ) : (
                  <button
                    onClick={closeSession}
                    className="flex items-center gap-2 px-4 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600"
                  >
                    <Square className="h-4 w-4" />
                    Stop Session
                  </button>
                )}
                
                {session && (
                  <button
                    onClick={requestScreenshot}
                    className="flex items-center gap-2 px-3 py-2 bg-gray-500 text-white rounded-lg hover:bg-gray-600"
                  >
                    <Camera className="h-4 w-4" />
                    Capture
                  </button>
                )}
              </div>

              {/* URL Navigation */}
              {session && (
                <div className="flex items-center gap-2">
                  <input
                    type="url"
                    value={currentUrl}
                    onChange={(e) => setCurrentUrl(e.target.value)}
                    placeholder="Enter URL..."
                    className="flex-1 px-3 py-2 bg-white/80 border border-gray-300/60 rounded-lg focus:ring-2 focus:ring-gray-500 focus:border-transparent"
                  />
                  <button
                    onClick={navigateToUrl}
                    disabled={isLoading}
                    className="px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 disabled:opacity-50"
                  >
                    {isLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Go'}
                  </button>
                </div>
              )}

              {/* Script Execution */}
              {session && (
                <div className="flex items-center gap-2">
                  <textarea
                    value={script}
                    onChange={(e) => setScript(e.target.value)}
                    placeholder="Enter JavaScript to execute..."
                    className="flex-1 px-3 py-2 bg-white/80 border border-gray-300/60 rounded-lg focus:ring-2 focus:ring-gray-500 focus:border-transparent resize-none"
                    rows={2}
                  />
                  <button
                    onClick={executeScript}
                    disabled={isLoading || !script.trim()}
                    className="flex items-center gap-2 px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 disabled:opacity-50"
                  >
                    <Code className="h-4 w-4" />
                    Execute
                  </button>
                </div>
              )}
            </div>
          </details>

          {/* Error Display */}
          {error && (
            <div className="mx-4 mt-4 p-3 bg-red-100 border border-red-300 rounded-lg flex items-center gap-2">
              <AlertCircle className="h-4 w-4 text-red-500" />
              <span className="text-red-700 text-sm">{error}</span>
              <button
                onClick={() => setError(null)}
                className="ml-auto text-red-500 hover:text-red-700"
              >
                ×
              </button>
            </div>
          )}

          {/* Automation Results */}
          {automationResult && (
            <div className="mx-4 mt-4 p-4 bg-green-50 border border-green-200 rounded-lg">
              <h4 className="text-sm font-semibold text-green-800 mb-2 flex items-center gap-2">
                <CheckCircle className="h-4 w-4" />
                Marketing Automation Completed
              </h4>
              <div className="space-y-2 text-sm">
                <div><strong>Task:</strong> {automationResult.task_description}</div>
                <div><strong>Type:</strong> {automationResult.automation_type?.replace(/_/g, ' ').toUpperCase()}</div>
                
                {automationResult.url && (
                  <div><strong>URL:</strong> <a href={automationResult.url} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">{automationResult.url}</a></div>
                )}
                
                {automationResult.execution_mode && (
                  <div><strong>Execution:</strong> {automationResult.execution_mode}</div>
                )}
                
                {/* VNC Live View */}
                {automationResult.vnc_url && (
                  <div className="bg-blue-50 p-3 rounded border border-blue-200">
                    <div className="flex items-center justify-between mb-2">
                      <strong className="text-blue-800 flex items-center gap-2">
                        <Monitor className="h-4 w-4" />
                        🔴 Live Browser View Available
                      </strong>
                      <a 
                        href={automationResult.vnc_url} 
                        target="_blank" 
                        rel="noopener noreferrer"
                        className="flex items-center gap-1 px-2 py-1 bg-blue-600 text-white text-xs rounded hover:bg-blue-700 transition-colors"
                      >
                        <ExternalLink className="h-3 w-3" />
                        Open Live View
                      </a>
                    </div>
                    <div className="text-xs text-blue-600">
                      Watch the browser automation in real-time! The automation is running with a visual interface.
                    </div>
                    {automationResult.novnc_port && (
                      <div className="text-xs text-blue-500 mt-1">
                        VNC Port: {automationResult.novnc_port}
                      </div>
                    )}
                  </div>
                )}
                
                {automationResult.report_saved && (
                  <div className="bg-blue-50 p-2 rounded border border-blue-200">
                    <strong className="text-blue-800">📊 Report Auto-Saved:</strong>
                    <div className="text-xs text-blue-600 mt-1">{automationResult.report_path}</div>
                  </div>
                )}
                
                {automationResult.result && (
                  <div className="bg-white p-2 rounded border">
                    <strong>Automation Results:</strong>
                    <pre className="whitespace-pre-wrap text-xs mt-1 max-h-32 overflow-y-auto">{automationResult.result}</pre>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Browser Viewport */}
          <div className={`p-4 ${isFullscreen ? 'flex-1 flex flex-col' : ''}`}>
            {automationResult && automationResult.screenshot ? (
              <div className={`bg-gray-100 rounded-lg overflow-hidden border border-gray-300 ${
                isFullscreen ? 'flex-1 flex items-center justify-center' : 'aspect-video'
              }`}>
                <img
                  ref={screenshotRef}
                  src={`data:image/png;base64,${automationResult.screenshot}`}
                  alt="Automation Screenshot"
                  className={`${isFullscreen ? 'max-w-full max-h-full object-contain' : 'w-full h-full object-cover'}`}
                  style={{ imageRendering: 'crisp-edges' }}
                />
              </div>
            ) : session && session.lastScreenshot ? (
              <div className={`bg-gray-100 rounded-lg overflow-hidden border border-gray-300 ${
                isFullscreen ? 'flex-1 flex items-center justify-center' : 'aspect-video'
              }`}>
                <img
                  ref={screenshotRef}
                  src={`data:image/png;base64,${session.lastScreenshot}`}
                  alt="Browser Screenshot"
                  className={`${isFullscreen ? 'max-w-full max-h-full object-contain' : 'w-full h-full object-cover'}`}
                  style={{ imageRendering: 'crisp-edges' }}
                />
              </div>
            ) : session ? (
              <div className={`bg-gray-50 rounded-lg border-2 border-dashed border-gray-300 flex items-center justify-center ${
                isFullscreen ? 'flex-1' : 'aspect-video'
              }`}>
                <div className="text-center text-gray-500">
                  <Globe className="h-12 w-12 mx-auto mb-2 opacity-50" />
                  <p>Navigate to a URL to see the browser view</p>
                </div>
              </div>
            ) : (
              <div className={`bg-gray-50 rounded-lg border-2 border-dashed border-gray-300 flex items-center justify-center ${
                isFullscreen ? 'flex-1' : 'aspect-video'
              }`}>
                <div className="text-center text-gray-500">
                  <Code className="h-12 w-12 mx-auto mb-2 opacity-50" />
                  <p>Enter a browser automation request above to get started</p>
                </div>
              </div>
            )}
          </div>

          {/* Status Footer */}
          {(session || automationResult) && (
            <div className="px-4 pb-4 text-xs text-gray-500">
              <div className="flex items-center justify-between">
                {session && <span>Session: {session.sessionId.slice(0, 8)}...</span>}
                {automationResult && <span>Automation: {automationResult.script_id?.slice(0, 8)}...</span>}
                <span>
                  {automationResult ? 
                    `Task: ${automationResult.automation_type}` : 
                    session ? `URL: ${session.currentUrl || 'No page loaded'}` : ''
                  }
                </span>
              </div>
            </div>
          )}
        </div>
    </div>
  );
};

export default BrowserAutomationViewer;
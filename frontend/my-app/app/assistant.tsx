"use client";

import { AssistantRuntimeProvider } from "@assistant-ui/react";
import { useChatRuntime } from "@assistant-ui/react-ai-sdk";
import { Thread } from "@/components/assistant-ui/thread";
import { ThoughtCardProvider } from "@/components/assistant-ui/thought-card-context";
import { SidebarInset, SidebarProvider, SidebarTrigger } from "@/components/ui/sidebar";
import { AppSidebar } from "@/components/app-sidebar";
import { Separator } from "@/components/ui/separator";
import { Breadcrumb, BreadcrumbItem, BreadcrumbLink, BreadcrumbList, BreadcrumbPage, BreadcrumbSeparator } from "@/components/ui/breadcrumb";
import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { BrainIcon, ZapIcon, TrendingUpIcon } from "lucide-react";

interface HealthStatus {
  status: string;
  providers?: {
    openai: { status: string; model?: string; error?: string };
    anthropic: { status: string; model?: string; error?: string };
  };
  timestamp: string;
}

export const Assistant = () => {
  const [healthStatus, setHealthStatus] = useState<HealthStatus | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [agentMode, setAgentMode] = useState<boolean>(false);
  
  const runtime = useChatRuntime({
    api: "/api/chat",
    body: {
      agent_mode: agentMode ? 'agent' : 'chat'
    },
    maxTokens: 100, // Force shorter chunks for immediate streaming
    streamMode: "stream-data", // Enable immediate streaming  
    experimental_streamingReactComponents: true, // Force immediate updates
    onToolCall: (toolCall) => {
      console.log("Runtime received tool call IMMEDIATELY:", toolCall);
    }
  });


  useEffect(() => {
    const checkHealth = async () => {
      try {
        const response = await fetch('/api/health');
        const data = await response.json();
        setHealthStatus(data);
        console.log('Health Check Result:', data);
      } catch (error) {
        console.error('Health check failed:', error);
        setHealthStatus({
          status: 'error',
          timestamp: new Date().toISOString()
        });
      } finally {
        setIsLoading(false);
      }
    };
    
    checkHealth();
    // Check health every 30 seconds
    const interval = setInterval(checkHealth, 30000);
    return () => clearInterval(interval);
  }, []);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'ok':
      case 'connected':
        return 'bg-green-500';
      case 'error':
        return 'bg-red-500';
      default:
        return 'bg-yellow-500';
    }
  };

  return (
    <AssistantRuntimeProvider runtime={runtime}>
      <ThoughtCardProvider>
        <SidebarProvider>
          <AppSidebar />
          <SidebarInset>
          <motion.header 
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex h-20 shrink-0 items-center gap-2 border-b bg-gradient-to-r from-slate-50 to-white px-4 shadow-sm"
          >
            <SidebarTrigger />
            <Separator orientation="vertical" className="mr-2 h-4" />
            
            {/* Enhanced Header with Agent Mode Visual Indicator */}
            <div className="flex items-center gap-3">
              {/* <motion.div
                className={`p-2 rounded-lg transition-all duration-300 ${
                  agentMode 
                    ? 'bg-gradient-to-r from-orange-500 to-red-500 text-white shadow-lg' 
                    : 'bg-gray-100 text-gray-600'
                }`}
                animate={{
                  scale: agentMode ? [1, 1.05, 1] : 1,
                  rotate: agentMode ? [0, 5, -5, 0] : 0,
                }}
                transition={{ duration: 0.5 }}
              >
                <BrainIcon className="h-5 w-5" />
              </motion.div> */}
              
              <Breadcrumb>
                <BreadcrumbList>
                  <BreadcrumbItem className="hidden md:block">
                    <BreadcrumbLink href="#" className="flex items-center gap-2 font-semibold text-slate-700">
                      Research Agent
                      <TrendingUpIcon className="h-4 w-4" />
                    </BreadcrumbLink>
                  </BreadcrumbItem>
                  <BreadcrumbSeparator className="hidden md:block" />
                  <BreadcrumbItem>
                    <BreadcrumbPage className="flex items-center gap-2">
                      <motion.span
                        animate={{ opacity: agentMode ? [0.7, 1, 0.7] : 1 }}
                        transition={{ duration: 2, repeat: agentMode ? Infinity : 0 }}
                        className={agentMode ? 'text-orange-600 font-semibold' : 'text-slate-600'}
                      >
                        {agentMode ? 'Agent Mode' : 'Chat Mode'}
                      </motion.span>
                      {agentMode && (
                        <motion.div
                          initial={{ scale: 0 }}
                          animate={{ scale: 1 }}
                          className="flex items-center gap-1"
                        >
                          {/* <ZapIcon className="h-4 w-4 text-yellow-500" /> */}
                          <span className="text-xs bg-gradient-to-r from-orange-500 to-red-500 text-white px-2 py-1 rounded-full">
                            Active
                          </span>
                        </motion.div>
                      )}
                    </BreadcrumbPage>
                  </BreadcrumbItem>
                </BreadcrumbList>
              </Breadcrumb>
            </div>
            
            {/* Enhanced Agent Mode Toggle */}
            <div className="ml-auto flex items-center gap-6">
              <motion.div 
                className="flex items-center gap-3"
                whileHover={{ scale: 1.02 }}
              >
                <span className="text-sm font-medium text-slate-600">Agent Mode:</span>
                <motion.button
                  onClick={() => setAgentMode(!agentMode)}
                  className={`relative px-4 py-2 rounded-lg text-sm font-medium transition-all duration-300 ${
                    agentMode 
                      ? 'bg-gradient-to-r from-orange-500 to-red-500 text-white shadow-lg' 
                      : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                  }`}
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                >
                  {agentMode && (
                    <motion.div
                      className="absolute inset-0 bg-gradient-to-r from-orange-400 to-red-400 rounded-lg opacity-50"
                      animate={{ 
                        scale: [1, 1.1, 1],
                        opacity: [0.5, 0.8, 0.5] 
                      }}
                      transition={{ duration: 2, repeat: Infinity }}
                    />
                  )}
                  <span className="relative z-10">
                    {agentMode ? 'ON' : 'OFF'}
                  </span>
                </motion.button>
              </motion.div>
              
              {/* Enhanced Health Status Indicator */}
              <motion.div 
                className="flex items-center gap-3 px-3 py-2 bg-white rounded-lg border shadow-sm"
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.2 }}
              >
                <div className="text-sm font-medium text-slate-600">Status:</div>
                <motion.div 
                  className={`w-3 h-3 rounded-full ${
                    isLoading ? 'bg-yellow-500' : getStatusColor(healthStatus?.status || 'error')
                  }`}
                  animate={{
                    scale: isLoading ? [1, 1.2, 1] : 1,
                  }}
                  transition={{ duration: 1.5, repeat: isLoading ? Infinity : 0 }}
                />
                
                {healthStatus?.providers && (
                  <div className="flex items-center gap-2 text-xs text-slate-500">
                    <div className="flex items-center gap-1">
                      <span>GPT:</span>
                      <motion.div 
                        className={`w-2 h-2 rounded-full ${
                          getStatusColor(healthStatus.providers.openai.status)
                        }`}
                        animate={{ 
                          opacity: healthStatus.providers.openai.status === 'connected' ? [0.5, 1, 0.5] : 1 
                        }}
                        transition={{ duration: 2, repeat: Infinity }}
                      />
                    </div>
                    <div className="flex items-center gap-1">
                      <span>Claude:</span>
                      <motion.div 
                        className={`w-2 h-2 rounded-full ${
                          getStatusColor(healthStatus.providers.anthropic.status)
                        }`}
                        animate={{ 
                          opacity: healthStatus.providers.anthropic.status === 'connected' ? [0.5, 1, 0.5] : 1 
                        }}
                        transition={{ duration: 2, repeat: Infinity, delay: 0.5 }}
                      />
                    </div>
                  </div>
                )}
              </motion.div>
            </div>
          </motion.header>
          <Thread />
        </SidebarInset>
        </SidebarProvider>
      </ThoughtCardProvider>
    </AssistantRuntimeProvider>
  );
};

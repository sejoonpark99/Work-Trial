"use client";

import React, { createContext, useContext, useCallback, useEffect } from 'react';
import { useAIThoughtCard } from './ai-thought-card';

interface ThoughtCardContextType {
  isVisible: boolean;
  status: 'processing' | 'completed' | 'error';
  progress: number;
  thinkingTime: number;
  steps: Array<{
    id: string;
    text: string;
    meta?: string;
    timestamp: number;
    type: 'step' | 'thinking' | 'executing' | 'complete';
  }>;
  liveText: string;
  isTyping: boolean;
  startThinking: (initialText?: string) => (() => void);
  addStep: (text: string, meta?: string, type?: 'step' | 'thinking' | 'executing' | 'complete') => void;
  updateLiveText: (text: string, typing?: boolean) => void;
  complete: () => void;
  error: () => void;
  hide: () => void;
  reset: () => void;
  setProgress: (progress: number) => void;
}

const ThoughtCardContext = createContext<ThoughtCardContextType | undefined>(undefined);

export const useThoughtCard = () => {
  const context = useContext(ThoughtCardContext);
  if (!context) {
    throw new Error('useThoughtCard must be used within a ThoughtCardProvider');
  }
  return context;
};

interface ThoughtCardProviderProps {
  children: React.ReactNode;
}

export const ThoughtCardProvider: React.FC<ThoughtCardProviderProps> = ({ children }) => {
  const thoughtCard = useAIThoughtCard();

  // Listen for agent mode responses and automatically show thought card
  useEffect(() => {
    const handleBeforeUnload = () => {
      thoughtCard.reset();
    };

    window.addEventListener('beforeunload', handleBeforeUnload);
    return () => window.removeEventListener('beforeunload', handleBeforeUnload);
  }, [thoughtCard]);

  const value: ThoughtCardContextType = {
    ...thoughtCard,
  };

  return (
    <ThoughtCardContext.Provider value={value}>
      {children}
    </ThoughtCardContext.Provider>
  );
};

// Hook to integrate with streaming responses
export const useThoughtCardWithStreaming = () => {
  const thoughtCard = useThoughtCard();

  const handleStreamingData = useCallback((data: any) => {
    if (data.type === 'thought_card') {
      // Handle different thought card types
      switch (data.card_type) {
        case 'thinking':
          if (!thoughtCard.isVisible) {
            thoughtCard.startThinking('Starting analysis...');
          }
          thoughtCard.addStep(data.content, data.meta, 'thinking');
          break;
        
        case 'executing':
          thoughtCard.addStep(data.content, data.meta, 'executing');
          break;
        
        case 'complete':
          thoughtCard.addStep(data.content, data.meta, 'complete');
          thoughtCard.complete();
          break;
        
        case 'progress':
          thoughtCard.setProgress(data.progress || 0);
          break;
        
        case 'live_text':
          thoughtCard.updateLiveText(data.content, data.typing !== false);
          break;
        
        default:
          thoughtCard.addStep(data.content, data.meta, 'step');
      }
    } else if (data.type === 'step_start') {
      // Auto-show thought card when agent starts processing
      if (!thoughtCard.isVisible) {
        thoughtCard.startThinking('Processing your request...');
      }
      thoughtCard.addStep(`Starting step ${data.step}...`, undefined, 'thinking');
    } else if (data.type === 'final_message') {
      // Complete thought card when final message arrives
      thoughtCard.complete();
      
      // Auto-hide after a delay
      setTimeout(() => {
        thoughtCard.hide();
      }, 3000);
    }
  }, [thoughtCard]);

  return {
    ...thoughtCard,
    handleStreamingData
  };
};

export default ThoughtCardProvider;
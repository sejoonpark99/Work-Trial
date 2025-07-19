"use client";

import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Minimize2, Maximize2, Activity } from 'lucide-react';
import { Card, CardContent, CardHeader } from '@/components/ui/card';

interface ThoughtStep {
  id: string;
  text: string;
  meta?: string;
  timestamp: number;
  type: 'step' | 'thinking' | 'executing' | 'complete';
}

interface AIThoughtCardProps {
  isVisible: boolean;
  onClose?: () => void;
  onMinimize?: () => void;
  status: 'processing' | 'completed' | 'error';
  progress?: number;
  thinkingTime?: number;
  steps: ThoughtStep[];
  liveText?: string;
  isTyping?: boolean;
}

export const AIThoughtCard: React.FC<AIThoughtCardProps> = ({
  isVisible,
  onClose,
  onMinimize,
  status = 'processing',
  progress = 0,
  thinkingTime = 0,
  steps = [],
  liveText = '',
  isTyping = false
}) => {
  const [isMinimized, setIsMinimized] = useState(false);
  const [autoScrollEnabled, setAutoScrollEnabled] = useState(true);
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const latestStepRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to latest step when new steps are added
  useEffect(() => {
    if (autoScrollEnabled && latestStepRef.current) {
      latestStepRef.current.scrollIntoView({ 
        behavior: 'smooth', 
        block: 'nearest' 
      });
    }
  }, [steps.length, autoScrollEnabled]);

  // Format thinking time
  const formatThinkingTime = (seconds: number) => {
    if (seconds < 60) return `${seconds}s`;
    return `${Math.floor(seconds / 60)}m ${seconds % 60}s`;
  };

  const handleMinimize = () => {
    setIsMinimized(!isMinimized);
    onMinimize?.();
  };

  const getStatusIcon = () => {
    switch (status) {
      case 'processing':
        return <Activity className="h-4 w-4 animate-spin" />;
      case 'completed':
        return <div className="h-4 w-4 rounded-full bg-green-500" />;
      case 'error':
        return <div className="h-4 w-4 rounded-full bg-red-500" />;
      default:
        return <Activity className="h-4 w-4" />;
    }
  };

  if (!isVisible) return null;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0, y: 100, scale: 0.9 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        exit={{ opacity: 0, y: 100, scale: 0.9 }}
        transition={{ duration: 0.3, ease: "easeOut" }}
        className="fixed bottom-4 right-4 w-96 max-h-[70vh] rounded-2xl bg-zinc-900 shadow-2xl/40 overflow-hidden border border-zinc-800 z-50"
        layoutId="ai-thought-card"
      >
        {/* Header */}
        <CardHeader className="sticky top-0 z-20 bg-zinc-900/90 backdrop-blur-sm p-3 border-b border-zinc-800">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="text-xl">🧠</span>
              <div className="flex flex-col">
                <h3 className="text-base font-semibold text-white">AI Activity</h3>
                {thinkingTime > 0 && (
                  <span className="text-xs text-zinc-400">
                    Thought for {formatThinkingTime(thinkingTime)}
                  </span>
                )}
              </div>
            </div>
            <div className="flex items-center gap-1">
              {getStatusIcon()}
              <motion.button
                whileHover={{ scale: 1.1 }}
                whileTap={{ scale: 0.9 }}
                onClick={handleMinimize}
                className="p-1 rounded-md hover:bg-zinc-800 text-zinc-400 hover:text-white transition-colors"
              >
                {isMinimized ? <Maximize2 className="h-4 w-4" /> : <Minimize2 className="h-4 w-4" />}
              </motion.button>
              {onClose && (
                <motion.button
                  whileHover={{ scale: 1.1 }}
                  whileTap={{ scale: 0.9 }}
                  onClick={onClose}
                  className="p-1 rounded-md hover:bg-zinc-800 text-zinc-400 hover:text-white transition-colors"
                >
                  <X className="h-4 w-4" />
                </motion.button>
              )}
            </div>
          </div>
        </CardHeader>

        {/* Content - hidden when minimized */}
        <AnimatePresence>
          {!isMinimized && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="overflow-hidden"
            >
              {/* Timeline Steps */}
              <CardContent 
                ref={scrollContainerRef}
                className="space-y-2 overflow-y-auto max-h-[50vh] p-4"
              >
                {steps.map((step, index) => (
                  <motion.div
                    key={step.id}
                    ref={index === steps.length - 1 ? latestStepRef : null}
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.3, delay: index * 0.1 }}
                    className={`flex flex-col border-b border-zinc-800 pb-2 ${
                      index === steps.length - 1 ? 'border-none' : ''
                    }`}
                  >
                    <div className="flex items-start gap-2">
                      <div className={`w-2 h-2 rounded-full mt-2 flex-shrink-0 ${
                        step.type === 'complete' ? 'bg-green-500' :
                        step.type === 'executing' ? 'bg-yellow-500' :
                        step.type === 'thinking' ? 'bg-orange-500' :
                        'bg-zinc-600'
                      }`} />
                      <div className="flex-1">
                        <p className="text-sm text-white leading-relaxed">
                          {step.text}
                        </p>
                        {step.meta && (
                          <code className="font-mono text-emerald-400 text-xs mt-1 block">
                            {step.meta}
                          </code>
                        )}
                      </div>
                    </div>
                  </motion.div>
                ))}
              </CardContent>

              {/* Live Typing Area */}
              {liveText && (
                <div className="px-4 pb-4 border-t border-zinc-800">
                  <div className="bg-zinc-800 rounded-lg p-3">
                    <p className="text-sm font-medium font-mono text-white">
                      {liveText}
                      {isTyping && (
                        <motion.span
                          initial={{ opacity: 1 }}
                          animate={{ opacity: [1, 0.2, 1] }}
                          transition={{ duration: 1, repeat: Infinity }}
                          className="inline-block ml-1"
                        >
                          █
                        </motion.span>
                      )}
                    </p>
                  </div>
                </div>
              )}

              {/* Status Footer */}
              <div className="p-3 bg-zinc-800 text-sm text-gray-400 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span>
                    {status === 'processing' && 'Processing...'}
                    {status === 'completed' && 'Completed ✓'}
                    {status === 'error' && 'Error ✗'}
                  </span>
                  {status === 'processing' && progress > 0 && (
                    <span className="text-xs">({Math.round(progress)}%)</span>
                  )}
                </div>
                
                {status === 'processing' && progress > 0 && (
                  <div className="flex-1 mx-3 h-1 bg-zinc-700 rounded-full overflow-hidden">
                    <motion.div
                      initial={{ width: 0 }}
                      animate={{ width: `${progress}%` }}
                      transition={{ duration: 0.5 }}
                      className="h-full bg-emerald-400 rounded-full"
                    />
                  </div>
                )}
                
                {steps.length > 0 && (
                  <span className="text-xs">
                    {steps.length} step{steps.length !== 1 ? 's' : ''}
                  </span>
                )}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>
    </AnimatePresence>
  );
};

// Hook for managing thought card state
export const useAIThoughtCard = () => {
  const [isVisible, setIsVisible] = useState(false);
  const [status, setStatus] = useState<'processing' | 'completed' | 'error'>('processing');
  const [progress, setProgress] = useState(0);
  const [thinkingTime, setThinkingTime] = useState(0);
  const [steps, setSteps] = useState<ThoughtStep[]>([]);
  const [liveText, setLiveText] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [fileWriting, setFileWriting] = useState(null);
  const timerRef = useRef<NodeJS.Timeout | null>(null);

  const startThinking = (initialText?: string) => {
    // Clear any existing timer
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }

    setIsVisible(true);
    setStatus('processing');
    setProgress(0);
    setThinkingTime(0);
    setSteps([]);
    setLiveText(initialText || '');
    setIsTyping(true);

    // Start thinking timer
    const startTime = Date.now();
    timerRef.current = setInterval(() => {
      setThinkingTime(Math.floor((Date.now() - startTime) / 1000));
    }, 1000);

    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
    };
  };

  const addStep = (text: string, meta?: string, type: ThoughtStep['type'] = 'step') => {
    const newStep: ThoughtStep = {
      id: `step-${Date.now()}-${Math.random()}`,
      text,
      meta,
      timestamp: Date.now(),
      type
    };
    setSteps(prev => [...prev, newStep]);
  };

  const updateLiveText = (text: string, typing: boolean = true) => {
    setLiveText(text);
    setIsTyping(typing);
  };

  const updateFileWriting = (fileData: any) => {
    setFileWriting(fileData);
  };

  const complete = () => {
    setStatus('completed');
    setProgress(100);
    setIsTyping(false);
  };

  const error = () => {
    setStatus('error');
    setIsTyping(false);
  };

  const hide = () => {
    setIsVisible(false);
  };

  const reset = () => {
    // Clear any existing timer
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }

    setIsVisible(false);
    setStatus('processing');
    setProgress(0);
    setThinkingTime(0);
    setSteps([]);
    setLiveText('');
    setIsTyping(false);
    setFileWriting(null);
  };

  return {
    isVisible,
    status,
    progress,
    thinkingTime,
    steps,
    liveText,
    isTyping,
    fileWriting,
    startThinking,
    addStep,
    updateLiveText,
    updateFileWriting,
    complete,
    error,
    hide,
    reset,
    setProgress
  };
};

export default AIThoughtCard;
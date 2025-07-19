"use client";

import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Lightbulb, 
  FileText, 
  Search, 
  Download, 
  Mail, 
  X,
  ChevronUp,
  Zap
} from 'lucide-react';

interface QuickAction {
  id: string;
  title: string;
  description: string;
  icon: React.ReactNode;
  action: () => void;
  type: 'search' | 'download' | 'email' | 'file' | 'analyze' | 'custom';
}

interface QuickActionsCardProps {
  actions: QuickAction[];
  isVisible: boolean;
  onClose?: () => void;
}

export const QuickActionsCard: React.FC<QuickActionsCardProps> = ({
  actions,
  isVisible,
  onClose
}) => {
  const [isMinimized, setIsMinimized] = useState(false);

  const getIconForType = (type: string) => {
    switch (type) {
      case 'search': return <Search className="h-4 w-4" />;
      case 'download': return <Download className="h-4 w-4" />;
      case 'email': return <Mail className="h-4 w-4" />;
      case 'file': return <FileText className="h-4 w-4" />;
      case 'analyze': return <Lightbulb className="h-4 w-4" />;
      default: return <Zap className="h-4 w-4" />;
    }
  };

  if (!isVisible || actions.length === 0) return null;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -10 }}
        transition={{ duration: 0.3, ease: "easeOut" }}
        className="w-full bg-white/60 backdrop-blur-sm rounded-lg border border-gray-300/50 shadow-sm mt-4"
      >
        {/* Header */}
        <div className="flex items-center justify-between p-3 border-b border-gray-200/50">
          <div className="flex items-center gap-2">
            {/* <Lightbulb className="h-4 w-4 text-yellow-500" /> */}
            <h3 className="text-sm font-semibold text-gray-800">Quick Actions</h3>
            <span className="text-xs text-gray-500 bg-gray-100 px-1.5 py-0.5 rounded">
              1
            </span>
          </div>
          <div className="flex items-center gap-1">
            <button
              onClick={() => setIsMinimized(!isMinimized)}
              className="p-1 hover:bg-gray-200/50 rounded-md transition-colors"
            >
              <motion.div
                animate={{ rotate: isMinimized ? 180 : 0 }}
                transition={{ duration: 0.2 }}
              >
                <ChevronUp className="h-3 w-3 text-gray-600" />
              </motion.div>
            </button>
            {onClose && (
              <button
                onClick={onClose}
                className="p-1 hover:bg-gray-200/50 rounded-md transition-colors"
              >
                <X className="h-3 w-3 text-gray-600" />
              </button>
            )}
          </div>
        </div>

        {/* Single Action */}
        <AnimatePresence>
          {!isMinimized && actions.length > 0 && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="overflow-hidden"
            >
              <div className="p-3">
                <motion.button
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ duration: 0.2 }}
                  onClick={() => {
                    actions[0].action();
                    if (onClose) onClose();
                  }}
                  className="w-full flex items-start gap-3 p-3 bg-gray-50/50 hover:bg-gray-100/70 rounded-lg border border-transparent hover:border-gray-300/50 transition-all duration-200 text-left group"
                >
                  <div className="flex-shrink-0 mt-0.5 text-gray-600 group-hover:text-gray-800 transition-colors">
                    {actions[0].icon || getIconForType(actions[0].type)}
                  </div>
                  <div className="flex-1 min-w-0">
                    <h4 className="text-sm font-medium text-gray-800 group-hover:text-gray-900 transition-colors">
                      {actions[0].title}
                    </h4>
                    <p className="text-xs text-gray-600 mt-0.5 leading-relaxed">
                      {actions[0].description}
                    </p>
                  </div>
                </motion.button>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Footer */}
        <div className="px-3 py-2 border-t border-gray-200/50 bg-gray-50/30">
          <p className="text-xs text-gray-500 text-center">
            AI-recommended actions based on your conversation
          </p>
        </div>
      </motion.div>
    </AnimatePresence>
  );
};

// Hook for managing quick actions state
export const useQuickActions = () => {
  const [actions, setActions] = useState<QuickAction[]>([]);
  const [isVisible, setIsVisible] = useState(false);

  const addAction = (action: QuickAction) => {
    setActions(prev => [...prev, action]);
    setIsVisible(true);
  };

  const addActions = (newActions: QuickAction[]) => {
    setActions(newActions);
    setIsVisible(newActions.length > 0);
  };

  const clearActions = () => {
    setActions([]);
    setIsVisible(false);
  };

  const hideActions = () => {
    setIsVisible(false);
  };

  const showActions = () => {
    setIsVisible(actions.length > 0);
  };

  return {
    actions,
    isVisible,
    addAction,
    addActions,
    clearActions,
    hideActions,
    showActions
  };
};

export default QuickActionsCard;
"use client";

import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import ThoughtProcess from './thought-process';
import CaseStudyAnalysis from './case-study-analysis';
import { ChevronRightIcon, ExpandIcon, MinimizeIcon } from 'lucide-react';

interface CaseStudyToolChangesProps {
  companyDomain: string;
  caseStudyData?: any;
  onSaveAsMarkdown?: (companyDomain: string, repDomain?: string) => void;
  autoStart?: boolean;
}

const CaseStudyToolChanges: React.FC<CaseStudyToolChangesProps> = ({
  companyDomain,
  caseStudyData,
  onSaveAsMarkdown,
  autoStart = false
}) => {
  const [currentPhase, setCurrentPhase] = useState<'thinking' | 'analysis' | 'complete'>('thinking');
  const [isExpanded, setIsExpanded] = useState(true);
  const [thoughtComplete, setThoughtComplete] = useState(false);

  useEffect(() => {
    if (autoStart) {
      setCurrentPhase('thinking');
    }
  }, [autoStart]);

  const handleThoughtComplete = () => {
    setThoughtComplete(true);
    setTimeout(() => {
      setCurrentPhase('analysis');
    }, 1000);
  };

  const handleAnalysisComplete = () => {
    setCurrentPhase('complete');
  };

  return (
    <div className="w-full max-w-6xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <motion.div
            className="p-2 bg-gradient-to-r from-orange-500 to-red-500 rounded-lg"
            animate={{ scale: currentPhase === 'thinking' ? [1, 1.1, 1] : 1 }}
            transition={{ duration: 2, repeat: currentPhase === 'thinking' ? Infinity : 0 }}
          >
            <ExpandIcon className="h-5 w-5 text-white" />
          </motion.div>
          <div>
            <h1 className="text-2xl font-bold text-white">Case Study Tool — Current vs Needed Changes</h1>
            <p className="text-slate-400">
              Analyzing improvements for {companyDomain} case study tool
            </p>
          </div>
        </div>
        
        <motion.button
          onClick={() => setIsExpanded(!isExpanded)}
          className="p-2 text-slate-400 hover:text-white transition-colors"
          whileHover={{ scale: 1.1 }}
          whileTap={{ scale: 0.9 }}
        >
          {isExpanded ? (
            <MinimizeIcon className="h-5 w-5" />
          ) : (
            <ExpandIcon className="h-5 w-5" />
          )}
        </motion.button>
      </div>

      {/* Content */}
      <AnimatePresence mode="wait">
        {isExpanded && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="space-y-6"
          >
            {/* Phase Indicators */}
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2">
                <div className={`w-3 h-3 rounded-full ${
                  currentPhase === 'thinking' 
                    ? 'bg-orange-500 animate-pulse' 
                    : thoughtComplete 
                    ? 'bg-green-500' 
                    : 'bg-slate-600'
                }`} />
                <span className={`text-sm font-medium ${
                  currentPhase === 'thinking' 
                    ? 'text-orange-400' 
                    : thoughtComplete 
                    ? 'text-green-400' 
                    : 'text-slate-500'
                }`}>
                  Thinking Process
                </span>
              </div>
              
              <ChevronRightIcon className="h-4 w-4 text-slate-500" />
              
              <div className="flex items-center gap-2">
                <div className={`w-3 h-3 rounded-full ${
                  currentPhase === 'analysis' 
                    ? 'bg-orange-500 animate-pulse' 
                    : currentPhase === 'complete' 
                    ? 'bg-green-500' 
                    : 'bg-slate-600'
                }`} />
                <span className={`text-sm font-medium ${
                  currentPhase === 'analysis' 
                    ? 'text-orange-400' 
                    : currentPhase === 'complete' 
                    ? 'text-green-400' 
                    : 'text-slate-500'
                }`}>
                  Analysis Results
                </span>
              </div>
              
              <ChevronRightIcon className="h-4 w-4 text-slate-500" />
              
              <div className="flex items-center gap-2">
                <div className={`w-3 h-3 rounded-full ${
                  currentPhase === 'complete' 
                    ? 'bg-green-500' 
                    : 'bg-slate-600'
                }`} />
                <span className={`text-sm font-medium ${
                  currentPhase === 'complete' 
                    ? 'text-green-400' 
                    : 'text-slate-500'
                }`}>
                  Complete
                </span>
              </div>
            </div>

            {/* Thinking Process Phase */}
            <AnimatePresence mode="wait">
              {currentPhase === 'thinking' && (
                <motion.div
                  key="thinking"
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -20 }}
                >
                  <ThoughtProcess
                    onComplete={handleThoughtComplete}
                    topic="Case Study Tool Changes"
                    duration={15000}
                  />
                </motion.div>
              )}
            </AnimatePresence>

            {/* Analysis Phase */}
            <AnimatePresence mode="wait">
              {(currentPhase === 'analysis' || currentPhase === 'complete') && caseStudyData && (
                <motion.div
                  key="analysis"
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -20 }}
                >
                  <CaseStudyAnalysis
                    companyDomain={companyDomain}
                    topResult={caseStudyData.summary}
                    allResults={caseStudyData.all_results}
                    totalFound={caseStudyData.total_found}
                    onSaveAsMarkdown={onSaveAsMarkdown}
                  />
                </motion.div>
              )}
            </AnimatePresence>

            {/* What the tool does today */}
            <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
              <h2 className="text-xl font-semibold text-white mb-4">What the tool does today</h2>
              
              <div className="space-y-4">
                <div className="flex items-start gap-3">
                  <div className="flex-shrink-0 w-8 h-8 bg-orange-500 rounded-full flex items-center justify-center text-white font-bold text-sm">
                    1
                  </div>
                  <div>
                    <h3 className="font-medium text-white mb-1">Domain scope on the prospect</h3>
                    <p className="text-slate-300 text-sm mb-2">
                      Builds a query like{' '}
                      <code className="bg-slate-700 px-2 py-1 rounded text-orange-400">
                        {companyDomain} case study site:{companyDomain}.com
                      </code>{' '}
                      and ranks hits by recency
                    </p>
                    <p className="text-slate-400 text-xs">+ numeric KPI keywords.</p>
                  </div>
                </div>
              </div>
            </div>

            {/* Answer in chat instead */}
            <div className="text-center">
              <motion.div
                className="inline-flex items-center gap-2 px-4 py-2 bg-slate-700 rounded-lg text-slate-300"
                animate={{ opacity: [0.7, 1, 0.7] }}
                transition={{ duration: 2, repeat: Infinity }}
              >
                <ChevronRightIcon className="h-4 w-4" />
                Answer in chat instead
              </motion.div>
            </div>

            {/* Saved message */}
            {currentPhase === 'complete' && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="bg-green-900 rounded-lg p-4 border border-green-700"
              >
                <p className="text-green-100 text-sm">
                  <strong>Saved!</strong> You'll find "Case Study Tool Changes" in the canvas as a Markdown doc outlining:
                </p>
                <ul className="mt-2 space-y-1 text-green-200 text-xs">
                  <li>• Current behaviour (prospect-scoped search).</li>
                  <li>• Why that misidentifies stories where the prospect is the customer.</li>
                  <li>• Six concrete changes (domain flip to rep company, negative filters, schema tweak, ranking weights, updated tests).</li>
                </ul>
              </motion.div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default CaseStudyToolChanges;
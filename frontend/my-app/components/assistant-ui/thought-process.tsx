"use client";

import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { BrainIcon, ChevronRightIcon, CheckCircleIcon, ArrowRightIcon } from 'lucide-react';

interface ThoughtProcessProps {
  onComplete?: () => void;
  topic?: string;
  duration?: number;
}

const ThoughtProcess: React.FC<ThoughtProcessProps> = ({ 
  onComplete, 
  topic = "Case Study Tool Changes",
  duration = 15000 
}) => {
  const [currentStep, setCurrentStep] = useState(0);
  const [isComplete, setIsComplete] = useState(false);
  const [progress, setProgress] = useState(0);

  const thoughtSteps = [
    {
      title: "Analyzing current tool behavior",
      content: "The current Case Studies tool uses domain scoping rules",
      detail: "It takes the prospect company name (Bloomreach) and simply prepends a site: filter",
      timing: 0
    },
    {
      title: "Identifying the problem",
      content: "This approach misidentifies stories where the prospect is the customer",
      detail: "Current: bloomreach case study site:bloomreach.com → finds vendor stories, not customer stories",
      timing: 3000
    },
    {
      title: "Evaluating needed changes",
      content: "Need to flip domain scope to rep company, not prospect company",
      detail: "Better: bloomreach case study site:yourcompany.com → finds customer success stories",
      timing: 6000
    },
    {
      title: "Planning ranking improvements",
      content: "Update ranking weights for better relevance",
      detail: "Negative filters, schema tweaks, and improved scoring algorithm",
      timing: 9000
    },
    {
      title: "Designing save functionality",
      content: "Add Save as Markdown capability",
      detail: "Allow users to save case study analysis as structured markdown files",
      timing: 12000
    },
    {
      title: "Ready to implement",
      content: "Six concrete changes identified for improved case study tool",
      detail: "Domain flip, negative filters, schema tweak, ranking weights, updated tests",
      timing: 15000
    }
  ];

  useEffect(() => {
    const interval = setInterval(() => {
      setProgress(prev => {
        const newProgress = prev + (100 / (duration / 100));
        if (newProgress >= 100) {
          setIsComplete(true);
          onComplete?.();
          return 100;
        }
        return newProgress;
      });
    }, 100);

    const stepInterval = setInterval(() => {
      setCurrentStep(prev => {
        const nextStep = prev + 1;
        if (nextStep >= thoughtSteps.length) {
          clearInterval(stepInterval);
          return prev;
        }
        return nextStep;
      });
    }, duration / thoughtSteps.length);

    return () => {
      clearInterval(interval);
      clearInterval(stepInterval);
    };
  }, [duration, onComplete]);

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      className="w-full max-w-4xl mx-auto p-6 bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 rounded-xl border border-slate-700 shadow-2xl"
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <motion.div
            animate={{ 
              rotate: isComplete ? 0 : 360,
              scale: isComplete ? 1.1 : 1
            }}
            transition={{ 
              rotate: { duration: 2, repeat: isComplete ? 0 : Infinity, ease: "linear" },
              scale: { duration: 0.3 }
            }}
            className={`p-3 rounded-full ${
              isComplete 
                ? 'bg-gradient-to-r from-green-500 to-emerald-500' 
                : 'bg-gradient-to-r from-orange-500 to-red-500'
            }`}
          >
            {isComplete ? (
              <CheckCircleIcon className="h-6 w-6 text-white" />
            ) : (
              <BrainIcon className="h-6 w-6 text-white" />
            )}
          </motion.div>
          <div>
            <h3 className="text-lg font-semibold text-white">
              {isComplete ? 'Analysis Complete' : `Thought for ${Math.ceil((duration - (progress * duration / 100)) / 1000)} seconds`}
            </h3>
            <p className="text-sm text-slate-300">
              What the <span className="text-orange-400 font-medium">current</span> Case Studies tool does
            </p>
          </div>
        </div>
        <ChevronRightIcon className="h-5 w-5 text-slate-400" />
      </div>

      {/* Progress Bar */}
      <div className="mb-6">
        <div className="flex justify-between items-center mb-2">
          <span className="text-sm text-slate-300">Analysis Progress</span>
          <span className="text-sm text-slate-300">{Math.round(progress)}%</span>
        </div>
        <div className="w-full bg-slate-700 rounded-full h-2">
          <motion.div
            className="h-2 bg-gradient-to-r from-orange-500 to-red-500 rounded-full"
            initial={{ width: 0 }}
            animate={{ width: `${progress}%` }}
            transition={{ duration: 0.1 }}
          />
        </div>
      </div>

      {/* Current Analysis */}
      <div className="space-y-4">
        <div className="bg-slate-800 rounded-lg p-4 border border-slate-700">
          <h4 className="text-white font-semibold mb-3 flex items-center gap-2">
            <span className="text-orange-400">1.</span>
            Domain scoping rule
          </h4>
          <p className="text-slate-300 mb-2">
            It takes the <span className="text-blue-400 font-medium">prospect</span> company name (
            <code className="bg-slate-700 px-2 py-1 rounded text-orange-400 font-mono">Bloomreach</code>
            ) and simply prepends a{' '}
            <code className="bg-slate-700 px-2 py-1 rounded text-orange-400 font-mono">site:</code>
            filter, e.g.
          </p>
          <div className="bg-slate-900 rounded p-3 border border-slate-600">
            <code className="text-green-400 font-mono">
              bloomreach case study site:bloomreach.com
            </code>
          </div>
        </div>

        {/* Thought Steps */}
        <AnimatePresence mode="wait">
          {thoughtSteps.slice(0, currentStep + 1).map((step, index) => (
            <motion.div
              key={index}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: index * 0.1 }}
              className="bg-slate-800 rounded-lg p-4 border border-slate-700"
            >
              <div className="flex items-start gap-3">
                <div className="flex-shrink-0 mt-1">
                  <div className="w-2 h-2 bg-orange-500 rounded-full" />
                </div>
                <div className="flex-1">
                  <h5 className="text-white font-medium mb-1">{step.title}</h5>
                  <p className="text-slate-300 text-sm mb-2">{step.content}</p>
                  <p className="text-slate-400 text-xs">{step.detail}</p>
                </div>
                {index === currentStep && !isComplete && (
                  <motion.div
                    animate={{ opacity: [0.5, 1, 0.5] }}
                    transition={{ duration: 1, repeat: Infinity }}
                    className="text-orange-400"
                  >
                    <ArrowRightIcon className="h-4 w-4" />
                  </motion.div>
                )}
              </div>
            </motion.div>
          ))}
        </AnimatePresence>

        {/* Completion Message */}
        {isComplete && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="bg-gradient-to-r from-green-900 to-emerald-900 rounded-lg p-4 border border-green-700"
          >
            <div className="flex items-center gap-3 mb-2">
              <CheckCircleIcon className="h-5 w-5 text-green-400" />
              <h4 className="text-white font-semibold">Analysis Complete</h4>
            </div>
            <p className="text-green-100 text-sm">
              Ready to implement six concrete changes for improved case study tool functionality.
            </p>
          </motion.div>
        )}
      </div>
    </motion.div>
  );
};

export default ThoughtProcess;
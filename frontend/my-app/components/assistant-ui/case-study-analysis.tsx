"use client";

import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { 
  DownloadIcon, 
  FileTextIcon, 
  CheckCircleIcon, 
  AlertCircleIcon,
  ExternalLinkIcon,
  TrendingUpIcon,
  BuildingIcon,
  ClockIcon
} from 'lucide-react';

interface CaseStudyResult {
  title: string;
  url: string;
  description: string;
  relevance_score: number;
  key_metrics?: string[];
}

interface CaseStudyAnalysisProps {
  companyDomain: string;
  topResult?: CaseStudyResult;
  allResults?: CaseStudyResult[];
  totalFound: number;
  onSaveAsMarkdown?: (companyDomain: string, repDomain?: string) => void;
  isLoading?: boolean;
  savedFilePath?: string;
}

const CaseStudyAnalysis: React.FC<CaseStudyAnalysisProps> = ({
  companyDomain,
  topResult,
  allResults = [],
  totalFound,
  onSaveAsMarkdown,
  isLoading = false,
  savedFilePath
}) => {
  const [isSaving, setIsSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);

  const handleSaveAsMarkdown = async () => {
    if (!onSaveAsMarkdown) return;
    
    setIsSaving(true);
    setSaveSuccess(false);
    
    try {
      await onSaveAsMarkdown(companyDomain);
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 3000);
    } catch (error) {
      console.error('Error saving as markdown:', error);
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="w-full max-w-4xl mx-auto p-6 bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 rounded-xl border border-slate-700 shadow-2xl"
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="p-3 bg-gradient-to-r from-orange-500 to-red-500 rounded-full">
            <BuildingIcon className="h-6 w-6 text-white" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-white">Case Study Analysis</h2>
            <p className="text-slate-300 text-sm">
              {companyDomain} • {totalFound} results found
            </p>
          </div>
        </div>
        
        {/* Save as Markdown Button */}
        <motion.button
          onClick={handleSaveAsMarkdown}
          disabled={isSaving || !topResult}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-all duration-300 ${
            saveSuccess
              ? 'bg-green-600 text-white'
              : isSaving
              ? 'bg-slate-600 text-slate-300 cursor-not-allowed'
              : 'bg-gradient-to-r from-orange-500 to-red-500 text-white hover:from-orange-600 hover:to-red-600'
          }`}
          whileHover={{ scale: isSaving ? 1 : 1.05 }}
          whileTap={{ scale: isSaving ? 1 : 0.95 }}
        >
          {saveSuccess ? (
            <>
              <CheckCircleIcon className="h-4 w-4" />
              Saved!
            </>
          ) : isSaving ? (
            <>
              <motion.div
                animate={{ rotate: 360 }}
                transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
                className="w-4 h-4 border-2 border-slate-300 border-t-transparent rounded-full"
              />
              Saving...
            </>
          ) : (
            <>
              <DownloadIcon className="h-4 w-4" />
              Save as Markdown
            </>
          )}
        </motion.button>
      </div>

      {/* Top Result */}
      {topResult && (
        <div className="mb-6 p-4 bg-slate-800 rounded-lg border border-slate-700">
          <div className="flex items-start justify-between mb-3">
            <h3 className="text-lg font-semibold text-white">Top Result</h3>
            <div className="flex items-center gap-2 text-sm text-slate-400">
              <TrendingUpIcon className="h-4 w-4" />
              Score: {topResult.relevance_score}
            </div>
          </div>
          
          <div className="space-y-3">
            <div className="flex items-start gap-3">
              <FileTextIcon className="h-5 w-5 text-orange-400 mt-0.5 flex-shrink-0" />
              <div className="flex-1">
                <h4 className="font-medium text-white mb-1">{topResult.title}</h4>
                <p className="text-slate-300 text-sm mb-2">{topResult.description}</p>
                <a
                  href={topResult.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 text-orange-400 hover:text-orange-300 text-sm"
                >
                  View Case Study
                  <ExternalLinkIcon className="h-3 w-3" />
                </a>
              </div>
            </div>
            
            {/* Key Metrics */}
            {topResult.key_metrics && topResult.key_metrics.length > 0 && (
              <div className="mt-3 p-3 bg-slate-900 rounded border border-slate-600">
                <h5 className="text-sm font-medium text-slate-300 mb-2">Key Metrics:</h5>
                <div className="space-y-1">
                  {topResult.key_metrics.map((metric, index) => (
                    <div key={index} className="text-sm text-green-400">
                      • {metric}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* All Results */}
      {allResults.length > 0 && (
        <div className="space-y-3">
          <h3 className="text-lg font-semibold text-white flex items-center gap-2">
            <ClockIcon className="h-5 w-5" />
            All Results ({allResults.length})
          </h3>
          
          <div className="space-y-2">
            {allResults.map((result, index) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: index * 0.1 }}
                className="p-3 bg-slate-800 rounded border border-slate-700 hover:border-slate-600 transition-colors"
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <h4 className="font-medium text-white text-sm mb-1">
                      {result.title}
                    </h4>
                    <p className="text-slate-400 text-xs mb-2 line-clamp-2">
                      {result.description}
                    </p>
                    <div className="flex items-center gap-4">
                      <a
                        href={result.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1 text-orange-400 hover:text-orange-300 text-xs"
                      >
                        View
                        <ExternalLinkIcon className="h-3 w-3" />
                      </a>
                      <span className="text-xs text-slate-500">
                        Score: {result.relevance_score}
                      </span>
                    </div>
                  </div>
                  <div className="ml-3 text-right">
                    <span className="text-xs text-slate-400">#{index + 1}</span>
                  </div>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      )}

      {/* Current Behavior Analysis */}
      <div className="mt-6 p-4 bg-slate-800 rounded-lg border border-slate-700">
        <h3 className="text-lg font-semibold text-white mb-3 flex items-center gap-2">
          <AlertCircleIcon className="h-5 w-5 text-orange-400" />
          Current Tool Behavior
        </h3>
        <div className="space-y-2 text-sm text-slate-300">
          <p>
            <strong>Domain scoping rule:</strong> Takes the prospect company name and prepends a site: filter
          </p>
          <p>
            <strong>Query example:</strong> <code className="bg-slate-700 px-2 py-1 rounded text-orange-400">
              {companyDomain} case study site:{companyDomain}.com
            </code>
          </p>
          <p className="text-slate-400">
            This approach finds stories where the prospect is the <strong>vendor</strong>, not the <strong>customer</strong>.
          </p>
        </div>
      </div>

      {/* Save Status */}
      {savedFilePath && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="mt-4 p-3 bg-green-900 rounded border border-green-700"
        >
          <div className="flex items-center gap-2 text-green-100">
            <CheckCircleIcon className="h-4 w-4" />
            <span className="text-sm">
              Analysis saved to: <code className="bg-green-800 px-2 py-1 rounded">{savedFilePath}</code>
            </span>
          </div>
        </motion.div>
      )}
    </motion.div>
  );
};

export default CaseStudyAnalysis;
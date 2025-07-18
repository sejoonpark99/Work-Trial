import { FC, useState, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { CheckIcon, LoaderIcon, FileTextIcon, ClipboardListIcon } from "lucide-react";

interface CaseStudyChange {
  id: string;
  action: string;
  rationale: string;
  status: 'pending' | 'in_progress' | 'completed';
}

interface CaseStudyContainerProps {
  isVisible: boolean;
  changes: CaseStudyChange[];
  typedSummary: string;
  isTyping: boolean;
  onClose: () => void;
}

export const CaseStudyContainer: FC<CaseStudyContainerProps> = ({
  isVisible,
  changes,
  typedSummary,
  isTyping,
  onClose,
}) => {
  const bottomRef = useRef<HTMLDivElement>(null);
  const [isMinimized, setIsMinimized] = useState(false);

  // Auto-scroll to newest content
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [changes, typedSummary]);

  if (!isVisible) return null;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0, x: 400 }}
        animate={{ opacity: 1, x: 0 }}
        exit={{ opacity: 0, x: 400 }}
        className="fixed top-4 right-4 max-h-[80vh] w-96 z-40"
        layoutId="case-study-card"
      >
        <Card className="bg-gradient-to-br from-slate-900 to-slate-800 text-white overflow-hidden shadow-2xl border border-slate-700">
          <CardHeader className="sticky top-0 bg-slate-900/95 backdrop-blur border-b border-slate-700">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <ClipboardListIcon className="h-5 w-5 text-blue-400" />
                <h3 className="text-base font-semibold">Case Study Tool Changes</h3>
              </div>
              <div className="flex items-center gap-1">
                <button
                  onClick={() => setIsMinimized(!isMinimized)}
                  className="p-1 hover:bg-slate-800 rounded transition-colors"
                >
                  <FileTextIcon className="h-4 w-4" />
                </button>
                <button
                  onClick={onClose}
                  className="p-1 hover:bg-slate-800 rounded transition-colors text-slate-400 hover:text-white"
                >
                  ×
                </button>
              </div>
            </div>
          </CardHeader>

          {!isMinimized && (
            <CardContent className="p-4 space-y-4 overflow-y-auto max-h-[60vh]">
              {/* Scrollable Change Summary */}
              <div className="space-y-3">
                <h4 className="text-sm font-medium text-slate-300 flex items-center gap-2">
                  <span className="w-2 h-2 bg-blue-400 rounded-full"></span>
                  Rule-based Validations
                </h4>
                
                {changes.map((change, index) => (
                  <motion.div
                    key={change.id}
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: index * 0.1 }}
                    className={cn(
                      "p-3 rounded-lg border-l-2 bg-slate-800/50",
                      change.status === 'completed' && "border-l-green-500",
                      change.status === 'in_progress' && "border-l-yellow-500",
                      change.status === 'pending' && "border-l-slate-500"
                    )}
                  >
                    <div className="flex items-center gap-2 mb-1">
                      {change.status === 'completed' && (
                        <CheckIcon className="h-4 w-4 text-green-500" />
                      )}
                      {change.status === 'in_progress' && (
                        <LoaderIcon className="h-4 w-4 text-yellow-500 animate-spin" />
                      )}
                      {change.status === 'pending' && (
                        <div className="h-4 w-4 border-2 border-slate-500 rounded-full" />
                      )}
                      <span className="text-sm font-medium text-white">
                        {change.action}
                      </span>
                    </div>
                    <p className="text-xs text-slate-300 ml-6">
                      {change.rationale}
                    </p>
                  </motion.div>
                ))}
              </div>

              {/* Real-Time AI Typing Animation */}
              {(typedSummary || isTyping) && (
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="space-y-2"
                >
                  <h4 className="text-sm font-medium text-slate-300 flex items-center gap-2">
                    <span className="w-2 h-2 bg-emerald-400 rounded-full"></span>
                    Generated Summary
                  </h4>
                  
                  <div className="p-3 bg-slate-800/50 rounded-lg border border-slate-700">
                    <div className="text-sm text-slate-200 leading-relaxed">
                      {typedSummary}
                      {isTyping && (
                        <motion.span
                          className="inline-block w-2 h-4 bg-emerald-400 ml-1"
                          animate={{ opacity: [1, 0] }}
                          transition={{ duration: 0.8, repeat: Infinity }}
                        >
                          |
                        </motion.span>
                      )}
                    </div>
                  </div>
                </motion.div>
              )}

              <div ref={bottomRef} />
            </CardContent>
          )}

          {/* Status Footer */}
          <div className="px-4 py-2 bg-slate-900/50 border-t border-slate-700">
            <div className="flex items-center justify-between text-xs">
              <span className="text-slate-400">
                {changes.filter(c => c.status === 'completed').length} of {changes.length} completed
              </span>
              {isTyping ? (
                <span className="text-emerald-400 flex items-center gap-1">
                  <LoaderIcon className="h-3 w-3 animate-spin" />
                  Processing...
                </span>
              ) : (
                <span className="text-green-400 flex items-center gap-1">
                  <CheckIcon className="h-3 w-3" />
                  Saved ✓
                </span>
              )}
            </div>
          </div>
        </Card>
      </motion.div>
    </AnimatePresence>
  );
};
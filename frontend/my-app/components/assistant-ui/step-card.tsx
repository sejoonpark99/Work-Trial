import { FC, useState, useEffect } from "react";
import { cn } from "@/lib/utils";
import { ChevronDownIcon, ChevronUpIcon, CheckIcon } from "lucide-react";
import { motion } from "framer-motion";

interface StepData {
  thinking?: string;
  toolExecution?: {
    tool_name: string;
    tool_args: any;
    content: string;
  };
  toolResult?: {
    tool_name: string;
    result: string;
    content: string;
  };
}

interface StepCardProps {
  step: number;
  data: StepData;
  isComplete: boolean;
}

export const StepCard: FC<StepCardProps> = ({
  step,
  data,
  isComplete
}) => {
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [currentPhase, setCurrentPhase] = useState<'thinking' | 'executing' | 'complete'>('thinking');

  useEffect(() => {
    if (data.thinking && !data.toolExecution) {
      setCurrentPhase('thinking');
    } else if (data.toolExecution && !data.toolResult) {
      setCurrentPhase('executing');
    } else if (data.toolResult || isComplete) {
      setCurrentPhase('complete');
    }
  }, [data, isComplete]);

  const getStatusIcon = () => {
    switch (currentPhase) {
      case 'thinking':
        return (
          <motion.div 
            className="rounded-full h-4 w-4 border-2 border-orange-300 border-t-orange-600"
            animate={{ rotate: 360 }}
            transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
          />
        );
      case 'executing':
        return (
          <motion.div 
            className="rounded-full h-4 w-4 border-2 border-yellow-300 border-t-yellow-600"
            animate={{ rotate: 360 }}
            transition={{ duration: 0.8, repeat: Infinity, ease: "linear" }}
          />
        );
      case 'complete':
        return (
          <motion.div
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ type: "spring", stiffness: 200 }}
          >
            <CheckIcon className="h-4 w-4 text-green-600" />
          </motion.div>
        );
    }
  };

  const getPhaseTitle = () => {
    switch (currentPhase) {
      case 'thinking':
        return 'Thinking...';
      case 'executing':
        return `Executing: ${data.toolExecution?.tool_name || 'Tool'}`;
      case 'complete':
        return 'Complete';
    }
  };

  const getCardStyle = () => {
    switch (currentPhase) {
      case 'thinking':
        return "border-l-orange-500 bg-gradient-to-r from-orange-50 to-white";
      case 'executing':
        return "border-l-yellow-500 bg-gradient-to-r from-yellow-50 to-white";
      case 'complete':
        return "border-l-green-500 bg-gradient-to-r from-green-50 to-white";
      default:
        return "border-l-zinc-600 bg-white";
    }
  };

  return (
    <motion.div 
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className={cn(
        "my-2 border-l-4 p-4 shadow-lg text-black rounded-lg",
        getCardStyle()
      )}>
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className="font-semibold text-sm">{getPhaseTitle()}</span>
          <div className="ml-2">
            {getStatusIcon()}
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className="bg-zinc-100 text-zinc-700 text-xs px-2 py-1 rounded-full">
            Step {step}
          </span>
          <button
            onClick={() => setIsCollapsed(!isCollapsed)}
            className="p-1 hover:bg-zinc-100 transition-colors"
          >
            {isCollapsed ? (
              <ChevronDownIcon className="h-4 w-4 text-zinc-600" />
            ) : (
              <ChevronUpIcon className="h-4 w-4 text-zinc-600" />
            )}
          </button>
        </div>
      </div>
      
      {!isCollapsed && (
        <div className="space-y-3">
          {/* Thinking Section */}
          {data.thinking && (
            <div className="border-l-2 border-blue-200 pl-3">
              <div className="text-xs text-zinc-600 font-semibold mb-1">💭 THINKING</div>
              <div className="text-sm text-black leading-relaxed">
                {data.thinking}
              </div>
            </div>
          )}
          
          {/* Tool Execution Section */}
          {data.toolExecution && (
            <div className="border-l-2 border-yellow-200 pl-3">
              <div className="text-xs text-zinc-600 font-semibold mb-1">🔧 TOOL EXECUTION</div>
              <div className="text-sm text-black leading-relaxed mb-2">
                {data.toolExecution.content}
              </div>
              {data.toolExecution.tool_args && (
                <div className="p-2 bg-zinc-50 text-xs font-mono text-zinc-600">
                  <strong className="text-zinc-800">Args:</strong> {JSON.stringify(data.toolExecution.tool_args, null, 2)}
                </div>
              )}
            </div>
          )}
          
          {/* Tool Result Section */}
          {data.toolResult && (
            <div className="border-l-2 border-green-200 pl-3">
              <div className="text-xs text-zinc-600 font-semibold mb-1">✅ RESULT</div>
              <div className="text-sm text-black leading-relaxed">
                {data.toolResult.content}
              </div>
              {data.toolResult.result && data.toolResult.result.length > 200 && (
                <div className="mt-2 text-xs text-zinc-500">
                  Full result: {data.toolResult.result.substring(0, 200)}...
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </motion.div>
  );
};
import { FC, useState, useEffect } from "react";
import { StepCard } from "./step-card";
import { ChevronDownIcon, ChevronUpIcon } from "lucide-react";

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

interface StepManagerProps {
  // This will be populated by the ToolFallback component
}

// Global state to manage steps
const stepData: Map<number, StepData> = new Map();
const stepListeners: Set<() => void> = new Set();
let finalAnswer: string | null = null;

export const clearAllSteps = () => {
  stepData.clear();
  finalAnswer = null;
  // Notify all listeners
  stepListeners.forEach(listener => listener());
};

export const addStepData = (step: number, cardType: string, data: any) => {
  if (cardType === 'final_answer') {
    finalAnswer = data.content;
    // Notify all listeners
    stepListeners.forEach(listener => listener());
    return;
  }

  const existing = stepData.get(step) || {};
  
  switch (cardType) {
    case 'thinking':
      existing.thinking = data.content;
      break;
    case 'tool_execution':
      existing.toolExecution = {
        tool_name: data.tool_name,
        tool_args: data.tool_args,
        content: data.content
      };
      break;
    case 'tool_result':
      existing.toolResult = {
        tool_name: data.tool_name,
        result: data.result,
        content: data.content
      };
      break;
  }
  
  stepData.set(step, existing);
  
  // Notify all listeners
  stepListeners.forEach(listener => listener());
};

export const StepManager: FC<StepManagerProps> = () => {
  const [steps, setSteps] = useState<Map<number, StepData>>(new Map());
  const [currentFinalAnswer, setCurrentFinalAnswer] = useState<string | null>(null);
  const [isFinalAnswerCollapsed, setIsFinalAnswerCollapsed] = useState(false);
  const [isProcessCollapsed, setIsProcessCollapsed] = useState(false);
  const [isProcessComplete, setIsProcessComplete] = useState(false);

  useEffect(() => {
    const updateSteps = () => {
      setSteps(new Map(stepData));
      setCurrentFinalAnswer(finalAnswer);
      
      // Mark process as complete when final answer is received
      if (finalAnswer && !isProcessComplete) {
        setIsProcessComplete(true);
        setIsProcessCollapsed(true); // Auto-collapse when complete
      }
      
      // Reset completion state when steps are cleared (new conversation)
      if (stepData.size === 0 && !finalAnswer) {
        setIsProcessComplete(false);
        setIsProcessCollapsed(false);
      }
    };

    stepListeners.add(updateSteps);
    
    return () => {
      stepListeners.delete(updateSteps);
    };
  }, []);

  const sortedSteps = Array.from(steps.entries()).sort(([a], [b]) => a - b);

  return (
    <div>
      {/* Step Cards or Summary */}
      {isProcessComplete && isProcessCollapsed ? (
        // Summary Card when collapsed
        <div className="my-2 border-l-4 border-l-green-600 p-4 shadow-lg bg-white text-black">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <span className="font-semibold text-sm">Process Complete</span>
              <div className="text-green-600">✅</div>
            </div>
            <div className="flex items-center gap-2">
              <span className="bg-green-100 text-green-700 text-xs px-2 py-1 rounded-full">
                {sortedSteps.length} Steps
              </span>
              <button
                onClick={() => setIsProcessCollapsed(!isProcessCollapsed)}
                className="p-1 hover:bg-green-100 transition-colors"
              >
                <ChevronDownIcon className="h-4 w-4 text-green-600" />
              </button>
            </div>
          </div>
          <div className="text-sm text-gray-600">
            Agent completed research in {sortedSteps.length} steps. Click to expand details.
          </div>
        </div>
      ) : (
        // Individual Step Cards
        sortedSteps.map(([stepNumber, data]) => (
          <StepCard
            key={stepNumber}
            step={stepNumber}
            data={data}
            isComplete={!!(data.toolResult || (data.thinking && !data.toolExecution))}
          />
        ))
      )}
      
      {/* Expand/Collapse button when process is complete */}
      {isProcessComplete && !isProcessCollapsed && (
        <div className="my-2 flex justify-center">
          <button
            onClick={() => setIsProcessCollapsed(true)}
            className="px-3 py-1 text-xs bg-green-100 text-green-700 rounded-full hover:bg-green-200 transition-colors"
          >
            Collapse Process ({sortedSteps.length} steps)
          </button>
        </div>
      )}
      
      {/* Final Answer Section - Hidden as requested */}
      {false && currentFinalAnswer && (
        <div className="my-4 border-l-4 border-l-black p-4 bg-white text-black">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <span className="font-semibold text-sm">Final Answer</span>
              <div className="text-green-600">🎯</div>
            </div>
            <button
              onClick={() => setIsFinalAnswerCollapsed(!isFinalAnswerCollapsed)}
              className="p-1 hover:bg-green-100 transition-colors"
            >
              {isFinalAnswerCollapsed ? (
                <ChevronDownIcon className="h-4 w-4 text-black" />
              ) : (
                <ChevronUpIcon className="h-4 w-4 text-black" />
              )}
            </button>
          </div>
          {!isFinalAnswerCollapsed && (
            <div className="text-sm leading-relaxed">
              {currentFinalAnswer}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
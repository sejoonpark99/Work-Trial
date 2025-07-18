import { FC, useEffect, useState, useRef } from "react";
import { cn } from "@/lib/utils";
import { ChevronDownIcon, ChevronUpIcon, CheckIcon, MinimizeIcon, XIcon } from "lucide-react";
import { motion } from "framer-motion";
import { Card, CardContent, CardHeader } from "@/components/ui/card";

interface ThoughtStep {
  id: string;
  text: string;
  meta?: string;
  card_type: string;
  step: number;
  icon: string;
  title: string;
  tool_name?: string;
  tool_args?: any;
  result?: string;
}

interface ThoughtCardProps {
  card_type: string;
  step: number;
  content: string;
  icon: string;
  title: string;
  tool_name?: string;
  tool_args?: any;
  result?: string;
}

interface AIThoughtCardProps {
  steps: ThoughtStep[];
  isVisible: boolean;
  onMinimize: () => void;
  onClose: () => void;
}

// New AI Thought Card based on ai_thought_card_ui_spec.md
export const AIThoughtCard: FC<AIThoughtCardProps> = ({
  steps,
  isVisible,
  onMinimize,
  onClose,
}) => {
  const [isMinimized, setIsMinimized] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to newest item
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [steps]);

  if (!isVisible) return null;

  return (
    <motion.div
      initial={{ opacity: 0, y: 64 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: 64 }}
      className="fixed bottom-4 right-4 max-h-[70vh] w-96 z-50"
      layoutId="ai-card"
    >
      <Card className="bg-zinc-900 text-white overflow-hidden shadow-2xl">
        <CardHeader className="sticky top-0 bg-zinc-900/90 backdrop-blur border-b border-zinc-800">
          <div className="flex items-center justify-between">
            <h3 className="text-base font-semibold flex items-center gap-2">
              🧠 AI Activity
            </h3>
            <div className="flex items-center gap-1">
              <button
                onClick={() => setIsMinimized(!isMinimized)}
                className="p-1 hover:bg-zinc-800 rounded transition-colors"
              >
                <MinimizeIcon className="h-4 w-4" />
              </button>
              <button
                onClick={onClose}
                className="p-1 hover:bg-zinc-800 rounded transition-colors"
              >
                <XIcon className="h-4 w-4" />
              </button>
            </div>
          </div>
        </CardHeader>

        {!isMinimized && (
          <CardContent className="space-y-2 overflow-y-auto max-h-[60vh] pr-2 p-4">
            {steps.map((step, index) => (
              <motion.div
                key={step.id}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.1 }}
                className={cn(
                  "border-b border-zinc-800 pb-2 last:border-none",
                  "p-2 rounded-lg"
                )}
              >
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-sm">{step.icon}</span>
                  <span className="text-sm font-medium">{step.title}</span>
                  <span className="bg-zinc-800 text-zinc-300 text-xs px-2 py-1 rounded-full ml-auto">
                    Step {step.step}
                  </span>
                </div>
                <p className="text-sm text-zinc-300">{step.text}</p>
                {step.meta && (
                  <code className="font-mono text-emerald-400 text-xs block mt-1">
                    {step.meta}
                  </code>
                )}
                {step.tool_args && (
                  <div className="mt-2 p-2 bg-zinc-800 rounded text-xs font-mono text-zinc-400">
                    <strong className="text-zinc-200">Args:</strong> {JSON.stringify(step.tool_args, null, 2)}
                  </div>
                )}
              </motion.div>
            ))}
            <div ref={bottomRef} />
          </CardContent>
        )}
      </Card>
    </motion.div>
  );
};

// Original ThoughtCard component (keeping for backward compatibility)
export const ThoughtCard: FC<ThoughtCardProps> = ({
  card_type,
  step,
  content,
  icon,
  title,
  tool_name,
  tool_args,
  result,
}) => {
  console.log("🎯 ThoughtCard MOUNTED:", {
    card_type,
    step,
    content: content.substring(0, 50) + "...",
    timestamp: new Date().toISOString()
  });

  const [isCollapsed, setIsCollapsed] = useState(false);
  const [isComplete, setIsComplete] = useState(false);

  // Mark thinking cards as complete after a delay (simulating thinking completion)
  useEffect(() => {
    if (card_type === 'thinking') {
      const timer = setTimeout(() => setIsComplete(true), 3000); // 3 seconds
      return () => clearTimeout(timer);
    } else {
      setIsComplete(true); // Other card types are immediately complete
    }
  }, [card_type]);

  const cardStyles = {
    thinking: "border-l-zinc-700 bg-white text-zinc-850 shadow-zinc-200",
    tool_execution: "border-l-zinc-600 bg-white text-zinc-850 shadow-zinc-200", 
    tool_result: "border-l-zinc-500 bg-white text-zinc-850 shadow-zinc-200",
    final_answer: "border-l-zinc-400 bg-white text-zinc-850 shadow-zinc-200",
  };

  const cardTypeStyle = cardStyles[card_type as keyof typeof cardStyles] || "border-l-zinc-500 bg-white text-zinc-850";

  return (
    <motion.div 
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className={cn(
        "my-2 rounded-lg border-l-4 p-4 shadow-lg",
        cardTypeStyle
      )}
    >
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className="text-lg">{icon}</span>
          <span className="font-semibold text-sm">{title}</span>
          {card_type === 'thinking' && (
            <div className="ml-2">
              {isComplete ? (
                <CheckIcon className="h-4 w-4 text-green-600" />
              ) : (
                <div className="animate-spin rounded-full h-4 w-4 border-2 border-zinc-300 border-t-zinc-700"></div>
              )}
            </div>
          )}
        </div>
        <div className="flex items-center gap-2">
          <span className="bg-zinc-100 text-zinc-700 text-xs px-2 py-1 rounded-full">
            Step {step}
          </span>
          <button
            onClick={() => setIsCollapsed(!isCollapsed)}
            className="p-1 hover:bg-zinc-100 rounded transition-colors"
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
        <>
          <div className="text-sm text-black leading-relaxed">
            {content}
          </div>
          
          {tool_args && (
            <div className="mt-3 p-2 bg-zinc-50 rounded text-xs font-mono text-zinc-600">
              <strong className="text-zinc-800">Args:</strong> {JSON.stringify(tool_args, null, 2)}
            </div>
          )}
          
          {result && result.length > 200 && (
            <div className="mt-2 text-xs text-zinc-500">
              Full result: {result.substring(0, 200)}...
            </div>
          )}
        </>
      )}
    </motion.div>
  );
};
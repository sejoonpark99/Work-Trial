import {
  ActionBarPrimitive,
  BranchPickerPrimitive,
  ComposerPrimitive,
  MessagePrimitive,
  ThreadPrimitive,
} from "@assistant-ui/react";
import type { FC } from "react";
import { useState, useRef, useEffect, useMemo } from "react";
import {
  ArrowDownIcon,
  CheckIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
  ChevronDownIcon,
  CopyIcon,
  PencilIcon,
  RefreshCwIcon,
  SendHorizontalIcon,
  PaperclipIcon,
  FileIcon,
  Globe,
} from "lucide-react";
import { cn } from "@/lib/utils";

import { Button } from "@/components/ui/button";
import { MarkdownText } from "@/components/assistant-ui/markdown-text";
import { TooltipIconButton } from "@/components/assistant-ui/tooltip-icon-button";
import { ToolFallback } from "./tool-fallback";
import { StepManager } from "./step-manager";
import { AIThoughtCard } from "./ai-thought-card";
import { useThoughtCardWithStreaming } from "./thought-card-context";
import { CSVPreviewTable } from "./csv-preview-table";
import { QuickActionsCard } from "./quick-actions-card";
import { BrowserAutomationViewer } from "./browser-automation-viewer";
import { motion, AnimatePresence } from 'framer-motion';
import { Activity, CheckCircle, AlertCircle, FileTextIcon, DownloadIcon } from 'lucide-react';

interface ThreadProps {
  forceBrowserAutomation?: boolean;
}

export const Thread: FC<ThreadProps> = ({ forceBrowserAutomation = false }) => {
  return (
    <ThreadPrimitive.Root
      className="bg-background box-border flex h-full flex-col overflow-hidden"
      style={{
        ["--thread-max-width" as string]: "56rem",
      }}
    >
      <ThreadPrimitive.Viewport 
        className="flex h-full flex-col items-center overflow-y-scroll scroll-smooth bg-inherit px-4 pt-8"
        data-viewport="true"
      >
        <ThreadWelcome />

        <ThreadPrimitive.Messages
          components={{
            UserMessage: UserMessage,
            EditComposer: EditComposer,
            AssistantMessage: (props) => <AssistantMessage {...props} forceBrowserAutomation={forceBrowserAutomation} />,
          }}
        />

        <ThreadPrimitive.If empty={false}>
          <div className="min-h-8 flex-grow" />
        </ThreadPrimitive.If>

        <div className="sticky bottom-0 mt-3 flex w-full max-w-[var(--thread-max-width)] flex-col items-center justify-end rounded-t-lg bg-inherit pb-4">
          <ThreadScrollToBottom />
          <Composer />
        </div>
      </ThreadPrimitive.Viewport>
    </ThreadPrimitive.Root>
  );
};

const ThreadScrollToBottom: FC = () => {
  return (
    <ThreadPrimitive.ScrollToBottom asChild>
      <TooltipIconButton
        tooltip="Scroll to bottom"
        variant="outline"
        className="absolute -top-8 rounded-full disabled:invisible"
      >
        <ArrowDownIcon />
      </TooltipIconButton>
    </ThreadPrimitive.ScrollToBottom>
  );
};

const ThreadWelcome: FC = () => {
  return (
    <ThreadPrimitive.Empty>
      <div className="flex w-full max-w-[var(--thread-max-width)] flex-grow flex-col">
        <div className="flex w-full flex-grow flex-col items-center justify-center">
          <p className="mt-4 font-medium">How can I help you today?</p>
        </div>
        <ThreadWelcomeSuggestions />
      </div>
    </ThreadPrimitive.Empty>
  );
};

const ThreadWelcomeSuggestions: FC = () => {
  return (
    <div className="mt-3 flex w-full items-stretch justify-center gap-4">
      <ThreadPrimitive.Suggestion
        className="hover:bg-muted/80 flex max-w-sm grow basis-0 flex-col items-center justify-center rounded-lg border p-3 transition-colors ease-in"
        prompt="What is the weather in Tokyo?"
        method="replace"
        autoSend
      >
        <span className="line-clamp-2 text-ellipsis text-sm font-semibold">
          What is the weather in Tokyo?
        </span>
      </ThreadPrimitive.Suggestion>
      <ThreadPrimitive.Suggestion
        className="hover:bg-muted/80 flex max-w-sm grow basis-0 flex-col items-center justify-center rounded-lg border p-3 transition-colors ease-in"
        prompt="What is assistant-ui?"
        method="replace"
        autoSend
      >
        <span className="line-clamp-2 text-ellipsis text-sm font-semibold">
          What is assistant-ui?
        </span>
      </ThreadPrimitive.Suggestion>
      <ThreadPrimitive.Suggestion
        className="hover:bg-muted/80 flex max-w-sm grow basis-0 flex-col items-center justify-center rounded-lg border p-3 transition-colors ease-in"
        prompt="Tell me about Claude's capabilities"
        method="replace"
        autoSend
      >
        <span className="line-clamp-2 text-ellipsis text-sm font-semibold">
          Tell me about Claude's capabilities
        </span>
      </ThreadPrimitive.Suggestion>
    </div>
  );
};

const Composer: FC = () => {
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);
  const [csvContent, setCsvContent] = useState<string>('');
  const [showPreview, setShowPreview] = useState(false);
  const [isProcessingFile, setIsProcessingFile] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const scrollToBottomRef = useRef<() => void>(null);

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    // Check if it's a CSV file
    if (file.type !== 'text/csv' && !file.name.endsWith('.csv')) {
      alert('Please upload a CSV file');
      return;
    }

    setIsProcessingFile(true);
    setUploadedFile(file);

    try {
      // Read the CSV file content
      const text = await file.text();
      setCsvContent(text);
      setShowPreview(true);
      
    } catch (error) {
      console.error('Error processing file:', error);
      alert('Error processing file. Please try again.');
      setUploadedFile(null);
    } finally {
      setIsProcessingFile(false);
    }
  };

  const handlePreviewConfirm = async (cleanCsvContent: string) => {
    try {
      // Auto-populate the composer input with Apollo processing command
      const composerInput = document.querySelector('[data-testid="composer-input"]') as HTMLTextAreaElement;
      if (composerInput) {
        const apolloCommand = `Process this CSV file through Apollo workflow:

CSV Content:
${cleanCsvContent}

Please use the apollo_process tool to handle this domains CSV file.`;
        
        composerInput.value = apolloCommand;
        composerInput.dispatchEvent(new Event('input', { bubbles: true }));
      }
      
      // Hide preview
      setShowPreview(false);
      setUploadedFile(null);
      setCsvContent('');
      
    } catch (error) {
      console.error('Error processing file:', error);
      alert('Error processing file. Please try again.');
    }
  };

  const handlePreviewCancel = () => {
    setShowPreview(false);
    setUploadedFile(null);
    setCsvContent('');
    // Reset file input
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  return (
    <div className="w-full">
      {/* CSV Preview Table */}
      {showPreview && uploadedFile && (
        <CSVPreviewTable
          csvContent={csvContent}
          fileName={uploadedFile.name}
          onConfirm={handlePreviewConfirm}
          onCancel={handlePreviewCancel}
        />
      )}
      
      {/* Composer */}
      <ComposerPrimitive.Root className="focus-within:border-ring/20 flex w-full flex-wrap items-end rounded-lg border bg-inherit px-2.5 shadow-sm transition-colors ease-in">
        <div className="flex items-center gap-2 flex-grow">
          <input
            ref={fileInputRef}
            type="file"
            accept=".csv"
            onChange={handleFileUpload}
            className="hidden"
          />
          <TooltipIconButton
            tooltip="Upload CSV file for Apollo processing"
            variant="ghost"
            className="my-2.5 size-8 p-2 transition-opacity ease-in"
            onClick={() => fileInputRef.current?.click()}
            disabled={isProcessingFile}
          >
            {isProcessingFile ? (
              <div className="animate-spin rounded-full h-4 w-4 border-2 border-current border-t-transparent" />
            ) : (
              <PaperclipIcon />
            )}
          </TooltipIconButton>
          <ComposerPrimitive.Input
            rows={1}
            autoFocus
            placeholder="Write a message... or upload a CSV file"
            className="placeholder:text-muted-foreground max-h-40 flex-grow resize-none border-none bg-transparent px-2 py-4 text-sm outline-none focus:ring-0 disabled:cursor-not-allowed"
            data-testid="composer-input"
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                // Auto-scroll when Enter is pressed to send message
                setTimeout(() => {
                  const viewport = document.querySelector('[data-viewport="true"]') as HTMLElement;
                  if (viewport) {
                    viewport.scrollTo({
                      top: viewport.scrollHeight,
                      behavior: 'smooth'
                    });
                  }
                }, 150);
              }
            }}
          />
        </div>
        <ComposerAction />
      </ComposerPrimitive.Root>
    </div>
  );
};

const ComposerAction: FC = () => {
  const handleSend = () => {
    // Auto-scroll to bottom when message is sent
    setTimeout(() => {
      const viewport = document.querySelector('[data-viewport="true"]') as HTMLElement;
      if (viewport) {
        viewport.scrollTo({
          top: viewport.scrollHeight,
          behavior: 'smooth'
        });
      }
    }, 100);
  };

  return (
    <>
      <ThreadPrimitive.If running={false}>
        <ComposerPrimitive.Send asChild>
          <TooltipIconButton
            tooltip="Send"
            variant="default"
            className="my-2.5 size-8 p-2 transition-opacity ease-in"
            onClick={handleSend}
            data-testid="send-button"
          >
            <SendHorizontalIcon />
          </TooltipIconButton>
        </ComposerPrimitive.Send>
      </ThreadPrimitive.If>
      <ThreadPrimitive.If running>
        <ComposerPrimitive.Cancel asChild>
          <TooltipIconButton
            tooltip="Cancel"
            variant="default"
            className="my-2.5 size-8 p-2 transition-opacity ease-in"
          >
            <CircleStopIcon />
          </TooltipIconButton>
        </ComposerPrimitive.Cancel>
      </ThreadPrimitive.If>
    </>
  );
};

const UserMessage: FC = () => {
  return (
    <MessagePrimitive.Root className="grid auto-rows-auto grid-cols-[minmax(72px,1fr)_auto] gap-y-2 [&:where(>*)]:col-start-2 w-full max-w-[var(--thread-max-width)] py-4">
      <UserActionBar />

      <div className="bg-muted text-foreground max-w-[calc(var(--thread-max-width)*0.8)] break-words rounded-3xl px-5 py-2.5 col-start-2 row-start-2">
        <MessagePrimitive.Content />
      </div>

      <BranchPicker className="col-span-full col-start-1 row-start-3 -mr-1 justify-end" />
    </MessagePrimitive.Root>
  );
};

const UserActionBar: FC = () => {
  return (
    <ActionBarPrimitive.Root
      hideWhenRunning
      autohide="not-last"
      className="flex flex-col items-end col-start-1 row-start-2 mr-3 mt-2.5"
    >
      <ActionBarPrimitive.Edit asChild>
        <TooltipIconButton tooltip="Edit">
          <PencilIcon />
        </TooltipIconButton>
      </ActionBarPrimitive.Edit>
    </ActionBarPrimitive.Root>
  );
};

const EditComposer: FC = () => {
  return (
    <ComposerPrimitive.Root className="bg-muted my-4 flex w-full max-w-[var(--thread-max-width)] flex-col gap-2 rounded-xl">
      <ComposerPrimitive.Input className="text-foreground flex h-8 w-full resize-none bg-transparent p-4 pb-0 outline-none" />

      <div className="mx-3 mb-3 flex items-center justify-center gap-2 self-end">
        <ComposerPrimitive.Cancel asChild>
          <Button variant="ghost">Cancel</Button>
        </ComposerPrimitive.Cancel>
        <ComposerPrimitive.Send asChild>
          <Button>Send</Button>
        </ComposerPrimitive.Send>
      </div>
    </ComposerPrimitive.Root>
  );
};

const AssistantMessage: FC<{ forceBrowserAutomation?: boolean }> = ({ forceBrowserAutomation = false }) => {
  const thoughtCard = useThoughtCardWithStreaming();
  const [messageActions, setMessageActions] = useState<any[]>([]);
  const [showActions, setShowActions] = useState(false);
  const [showBrowserAutomation, setShowBrowserAutomation] = useState(false);
  const messageRef = useRef<HTMLDivElement>(null);
  
  // Generate relevant follow-up question based on message content
  const generateFollowUpQuestion = (messageContent: string): string => {
    const content = messageContent.toLowerCase();
    
    // Simple heuristics to generate relevant questions
    if (content.includes('weather') || content.includes('temperature')) {
      return 'What about the weather forecast for the next few days?';
    } else if (content.includes('code') || content.includes('function') || content.includes('programming')) {
      return 'Can you show me a practical example of this in action?';
    } else if (content.includes('explain') || content.includes('how') || content.includes('what')) {
      return 'What are some common use cases or applications?';
    } else if (content.includes('install') || content.includes('setup') || content.includes('configure')) {
      return 'What are the next steps after this setup?';
    } else if (content.includes('error') || content.includes('problem') || content.includes('issue')) {
      return 'How can I prevent this issue in the future?';
    } else if (content.includes('benefits') || content.includes('advantages')) {
      return 'What are the potential drawbacks or limitations?';
    } else if (content.includes('compare') || content.includes('difference')) {
      return 'Which option would you recommend and why?';
    } else {
      return 'Can you provide a specific example or use case?';
    }
  };
  
  // Check if message content suggests browser automation
  const shouldShowBrowserAutomation = (messageContent: string): boolean => {
    const content = messageContent.toLowerCase();
    return content.includes('browser') || 
           content.includes('automation') || 
           content.includes('automate') ||
           content.includes('scrape') || 
           content.includes('navigate') || 
           content.includes('website') ||
           content.includes('page') ||
           content.includes('live video') ||
           content.includes('screenshot') ||
           content.includes('playwright') ||
           content.includes('puppeteer') ||
           content.includes('browser-use') ||
           (content.includes('browser') && content.includes('automate'));
  };
  
  // Generate quick actions when message completes
  useEffect(() => {
    if (thoughtCard.status === 'completed') {
      // Get the message content from this specific message
      const messageContent = messageRef.current?.textContent || '';
      
      // Check if we should show browser automation (either forced or detected)
      if (forceBrowserAutomation || shouldShowBrowserAutomation(messageContent)) {
        setShowBrowserAutomation(true);
      }
      
      const followUpQuestion = generateFollowUpQuestion(messageContent);
      
      const quickAction = {
        id: '1',
        title: followUpQuestion,
        description: 'Click to ask this follow-up question',
        type: 'custom' as const,
        action: () => {
          const composerInput = document.querySelector('[data-testid="composer-input"]') as HTMLTextAreaElement;
          const sendButton = document.querySelector('[data-testid="send-button"]') as HTMLButtonElement;
          
          if (composerInput) {
            composerInput.value = followUpQuestion;
            composerInput.dispatchEvent(new Event('input', { bubbles: true }));
            
            // Auto-send the message
            setTimeout(() => {
              if (sendButton && !sendButton.disabled) {
                sendButton.click();
              }
            }, 100);
          }
        }
      };
      
      setMessageActions([quickAction]);
      setShowActions(true);
    }
  }, [thoughtCard.status, forceBrowserAutomation]);

  return (
    <MessagePrimitive.Root className="grid grid-cols-[auto_auto_1fr] grid-rows-[auto_1fr] relative w-full max-w-[var(--thread-max-width)] py-4">
      <div className="text-foreground max-w-[calc(var(--thread-max-width)*0.8)] break-words leading-7 col-span-2 col-start-2 row-start-1 my-1.5">
        <div ref={messageRef} data-testid="message-content">
          <MessagePrimitive.Content
            components={{ Text: MarkdownText, tools: { Fallback: ToolFallback } }}
          />
        </div>
        
        {/* Inline AI Thought Process */}
        {(thoughtCard.isVisible || thoughtCard.steps.length > 0 || thoughtCard.isTyping) && (
          <InlineThoughtCard thoughtCard={thoughtCard} />
        )}

        {/* Browser Automation Viewer - appears when relevant */}
        {showBrowserAutomation && (
          <BrowserAutomationViewer
            isVisible={showBrowserAutomation}
            onClose={() => setShowBrowserAutomation(false)}
          />
        )}

        {/* Inline Quick Actions - appears after message content */}
        {showActions && messageActions.length > 0 && (
          <QuickActionsCard
            actions={messageActions}
            isVisible={showActions}
            onClose={() => setShowActions(false)}
          />
        )}
      </div>

      <AssistantActionBar />

      <BranchPicker className="col-start-2 row-start-2 -ml-2 mr-2" />
    </MessagePrimitive.Root>
  );
};

const AssistantActionBar: FC = () => {
  return (
    <ActionBarPrimitive.Root
      hideWhenRunning
      autohide="not-last"
      autohideFloat="single-branch"
      className="text-muted-foreground flex gap-1 col-start-3 row-start-2 -ml-1 data-[floating]:bg-background data-[floating]:absolute data-[floating]:rounded-md data-[floating]:border data-[floating]:p-1 data-[floating]:shadow-sm"
    >
      <ActionBarPrimitive.Copy asChild>
        <TooltipIconButton tooltip="Copy">
          <MessagePrimitive.If copied>
            <CheckIcon />
          </MessagePrimitive.If>
          <MessagePrimitive.If copied={false}>
            <CopyIcon />
          </MessagePrimitive.If>
        </TooltipIconButton>
      </ActionBarPrimitive.Copy>
      <ActionBarPrimitive.Reload asChild>
        <TooltipIconButton tooltip="Refresh">
          <RefreshCwIcon />
        </TooltipIconButton>
      </ActionBarPrimitive.Reload>
    </ActionBarPrimitive.Root>
  );
};

const BranchPicker: FC<BranchPickerPrimitive.Root.Props> = ({
  className,
  ...rest
}) => {
  return (
    <BranchPickerPrimitive.Root
      hideWhenSingleBranch
      className={cn(
        "text-muted-foreground inline-flex items-center text-xs",
        className
      )}
      {...rest}
    >
      <BranchPickerPrimitive.Previous asChild>
        <TooltipIconButton tooltip="Previous">
          <ChevronLeftIcon />
        </TooltipIconButton>
      </BranchPickerPrimitive.Previous>
      <span className="font-medium">
        <BranchPickerPrimitive.Number /> / <BranchPickerPrimitive.Count />
      </span>
      <BranchPickerPrimitive.Next asChild>
        <TooltipIconButton tooltip="Next">
          <ChevronRightIcon />
        </TooltipIconButton>
      </BranchPickerPrimitive.Next>
    </BranchPickerPrimitive.Root>
  );
};

const FileWritingPreview: FC<{ fileData: any }> = ({ fileData }) => {
  const isMarkdown = fileData.file_type === 'md' || fileData.file_type === 'markdown';
  const [showMarkdown, setShowMarkdown] = useState(isMarkdown); // Default to markdown view for .md files
  
  const getFileIcon = (fileType: string) => {
    switch (fileType) {
      case 'md':
      case 'markdown':
        return '📝';
      case 'txt':
        return '📄';
      case 'json':
        return '📋';
      case 'csv':
        return '📊';
      default:
        return '📁';
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      className="bg-white/60 backdrop-blur-sm rounded-xl border border-gray-300/50 overflow-hidden shadow-lg"
    >
      {/* File Header */}
      <div className="flex items-center justify-between p-3 bg-white/30 border-b border-gray-300/30">
        <div className="flex items-center gap-2">
          <span className="text-lg">{getFileIcon(fileData.file_type)}</span>
          <div>
            <h4 className="font-medium text-black text-sm">{fileData.filename}</h4>
            <p className="text-xs text-gray-600">{fileData.file_path}</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {fileData.progress !== undefined && (
            <div className="flex items-center gap-1">
              <div className="w-20 h-1.5 bg-gray-200 rounded-full overflow-hidden">
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${fileData.progress}%` }}
                  className="h-full bg-blue-500 rounded-full"
                />
              </div>
              <span className="text-xs text-gray-600">{fileData.progress}%</span>
            </div>
          )}
          {isMarkdown && !fileData.writing && (
            <button
              onClick={() => setShowMarkdown(!showMarkdown)}
              className="text-xs px-2 py-1 bg-blue-500 text-white rounded hover:bg-blue-600 transition-colors"
            >
              {showMarkdown ? 'Raw' : 'Preview'}
            </button>
          )}
        </div>
      </div>

      {/* File Content */}
      <div className="p-3 max-h-64 overflow-y-auto">
        {isMarkdown && showMarkdown && !fileData.writing ? (
          <div className="bg-gray-900 p-4 rounded-lg border border-gray-700 shadow-lg">
            <div className="font-mono text-sm text-gray-200 leading-relaxed whitespace-pre-wrap">
              {fileData.content.split('\n').map((line: string, index: number) => (
                <div key={index} className="leading-6">
                  {line.startsWith('# ') ? (
                    <span className="text-yellow-400 font-bold">{line}</span>
                  ) : line.startsWith('## ') ? (
                    <span className="text-blue-400 font-semibold">{line}</span>
                  ) : line.startsWith('### ') ? (
                    <span className="text-green-400 font-medium">{line}</span>
                  ) : line.startsWith('- ') || line.startsWith('* ') ? (
                    <span>
                      <span className="text-orange-400">{line.substring(0, 2)}</span>
                      <span className="text-gray-200">{line.substring(2)}</span>
                    </span>
                  ) : line.trim().startsWith('**') && line.trim().endsWith('**') ? (
                    <span className="text-red-400 font-bold">{line}</span>
                  ) : (
                    <span className="text-gray-200">{line}</span>
                  )}
                </div>
              ))}
            </div>
          </div>
        ) : (
          <div className="relative">
            <pre className="whitespace-pre-wrap text-xs font-mono text-black bg-gray-50/50 p-2 rounded border">
              {fileData.content}
              {fileData.writing && (
                <motion.span
                  animate={{ opacity: [1, 0.3, 1] }}
                  transition={{ duration: 0.8, repeat: Infinity }}
                  className="inline-block ml-1 w-2 h-3 bg-blue-500"
                />
              )}
            </pre>
          </div>
        )}
      </div>

      {/* File Status */}
      <div className="px-3 py-2 bg-white/20 border-t border-gray-300/30 text-xs text-gray-600">
        {fileData.writing ? (
          <div className="flex items-center gap-1">
            <div className="w-1.5 h-1.5 bg-blue-500 rounded-full animate-pulse" />
            Writing to file...
          </div>
        ) : (
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-1">
              <div className="w-1.5 h-1.5 bg-green-500 rounded-full" />
              File saved successfully
            </div>
            {fileData.size && (
              <span>{(fileData.size / 1024).toFixed(1)} KB</span>
            )}
          </div>
        )}
      </div>
    </motion.div>
  );
};

const InlineThoughtCard: FC<{ thoughtCard: any }> = ({ thoughtCard }) => {
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [isFinalized, setIsFinalized] = useState(false);
  
  const formatThinkingTime = (seconds: number) => {
    if (seconds < 60) return `${Math.floor(seconds)}s`;
    return `${Math.floor(seconds / 60)}m ${Math.floor(seconds % 60)}s`;
  };

  const getStatusIcon = () => {
    switch (thoughtCard.status) {
      case 'processing':
        return <Activity className="h-3 w-3 animate-spin text-blue-500" />;
      case 'completed':
        return <CheckCircle className="h-3 w-3 text-green-500" />;
      case 'error':
        return <AlertCircle className="h-3 w-3 text-red-500" />;
      default:
        return <Activity className="h-3 w-3 text-gray-500" />;
    }
  };

  // Auto-collapse and finalize when completed
  useEffect(() => {
    if (thoughtCard.status === 'completed' && !isFinalized) {
      setIsFinalized(true);
      const timer = setTimeout(() => {
        setIsCollapsed(true);
      }, 2000); // Auto-collapse after 2 seconds
      return () => clearTimeout(timer);
    }
  }, [thoughtCard.status, isFinalized]);

  // Stabilize thinking time display to prevent flickering
  const formattedThinkingTime = useMemo(() => {
    const stableTime = Math.floor(thoughtCard.thinkingTime || 0);
    return formatThinkingTime(stableTime);
  }, [Math.floor(thoughtCard.thinkingTime || 0)]);

  // Don't render if finalized and collapsed
  if (isFinalized && isCollapsed) {
    return null;
  }

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0, height: 0 }}
        animate={{ opacity: 1, height: 'auto' }}
        exit={{ opacity: 0, height: 0 }}
        transition={{ duration: 0.3 }}
        className="mt-4 bg-white/40 backdrop-blur-md rounded-xl p-4 space-y-2 border border-gray-300/60 shadow-xl ring-1 ring-gray-400/30"
      >
        {/* Header */}
        <div 
          className="flex items-center gap-2 text-sm font-medium text-black cursor-pointer hover:bg-white/20 rounded-md p-2 -m-2 transition-all duration-200"
          onClick={() => setIsCollapsed(!isCollapsed)}
        >
          {getStatusIcon()}
          <span>AI Thinking Process</span>
          {thoughtCard.thinkingTime > 0 && (
            <span className="text-xs text-black ml-auto">
              {formattedThinkingTime}
            </span>
          )}
          <motion.div
            animate={{ rotate: isCollapsed ? 180 : 0 }}
            transition={{ duration: 0.2 }}
            className="ml-1"
          >
            <ChevronDownIcon className="h-3 w-3 text-black" />
          </motion.div>
        </div>

        {/* Collapsible Content */}
        <AnimatePresence>
          {!isCollapsed && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              transition={{ duration: 0.3 }}
              className="space-y-2"
            >
              {/* Steps */}
              {thoughtCard.steps.length > 0 && (
                <div className="space-y-1.5">
                  {thoughtCard.steps.map((step: any, index: number) => (
                    <motion.div
                      key={step.id}
                      initial={{ opacity: 0, x: -10 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ duration: 0.2, delay: index * 0.05 }}
                      className="flex items-start gap-2 text-sm"
                    >
                      <div className={`w-1.5 h-1.5 rounded-full mt-2 flex-shrink-0 ${
                        step.type === 'complete' ? 'bg-green-500' :
                        step.type === 'executing' ? 'bg-yellow-500' :
                        step.type === 'thinking' ? 'bg-orange-500' :
                        'bg-gray-400'
                      }`} />
                      <div className="flex-1">
                        <p className="text-black leading-relaxed">
                          {step.text}
                        </p>
                        {step.meta && (
                          <code className="font-mono text-black text-xs mt-1 block bg-white/50 backdrop-blur-sm px-2 py-1 rounded border border-gray-300/40 shadow-sm">
                            {step.meta}
                          </code>
                        )}
                      </div>
                    </motion.div>
                  ))}
                </div>
              )}

              {/* File Writing Preview */}
              {thoughtCard.fileWriting && (
                <FileWritingPreview fileData={thoughtCard.fileWriting} />
              )}

              {/* Live Text */}
              {thoughtCard.liveText && (
                <div className="bg-white/50 backdrop-blur-md rounded-lg p-3 border border-gray-300/40 shadow-sm">
                  <p className="text-sm font-mono text-black">
                    {thoughtCard.liveText}
                    {thoughtCard.isTyping && (
                      <motion.span
                        initial={{ opacity: 1 }}
                        animate={{ opacity: [1, 0.3, 1] }}
                        transition={{ duration: 1, repeat: Infinity }}
                        className="inline-block ml-1"
                      >
                        █
                      </motion.span>
                    )}
                  </p>
                </div>
              )}

              {/* Status Footer */}
              <div className="flex items-center justify-between text-xs text-black pt-2 border-t border-gray-300/40">
                <span>
                  {thoughtCard.status === 'processing' && 'Processing...'}
                  {thoughtCard.status === 'completed' && 'Completed ✓'}
                  {thoughtCard.status === 'error' && 'Error ✗'}
                </span>
                {thoughtCard.steps.length > 0 && (
                  <span>
                    {thoughtCard.steps.length} step{thoughtCard.steps.length !== 1 ? 's' : ''}
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

const CircleStopIcon = () => {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 16 16"
      fill="currentColor"
      width="16"
      height="16"
    >
      <rect width="10" height="10" x="3" y="3" rx="2" />
    </svg>
  );
};

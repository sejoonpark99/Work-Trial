import { FC, useState, useEffect } from "react";
import { cn } from "@/lib/utils";
import { FileTextIcon, DownloadIcon, CopyIcon, CheckIcon, FileIcon } from "lucide-react";
import { MarkdownText } from "./markdown-text";

interface FilePreviewProps {
  content: string;
  path: string;
  filename?: string;
  fileType?: string;
}

export const FilePreview: FC<FilePreviewProps> = ({
  content,
  path,
  filename,
  fileType
}) => {
  const [displayedContent, setDisplayedContent] = useState("");
  const [isTyping, setIsTyping] = useState(true);
  const [isCopied, setIsCopied] = useState(false);
  const [showPreview, setShowPreview] = useState(true);

  // Determine file type from path if not provided
  const detectedFileType = fileType || path.split('.').pop()?.toLowerCase() || 'txt';
  const displayFilename = filename || path.split('/').pop() || 'file';
  
  // Typewriter effect
  useEffect(() => {
    if (content && content.length > 0) {
      setDisplayedContent("");
      setIsTyping(true);
      
      let index = 0;
      const timer = setInterval(() => {
        if (index < content.length) {
          setDisplayedContent(content.slice(0, index + 1));
          index++;
        } else {
          setIsTyping(false);
          clearInterval(timer);
        }
      }, 15); // Slightly faster than email for file writing

      return () => clearInterval(timer);
    }
  }, [content]);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(content);
      setIsCopied(true);
      setTimeout(() => setIsCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy text: ', err);
    }
  };

  const handleDownload = () => {
    const blob = new Blob([content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = displayFilename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const getFileIcon = () => {
    switch (detectedFileType) {
      case 'md':
      case 'markdown':
        return '📝';
      case 'txt':
        return '📄';
      case 'json':
        return '📋';
      case 'csv':
        return '📊';
      case 'html':
        return '🌐';
      default:
        return '📁';
    }
  };

  const getFileTypeLabel = () => {
    switch (detectedFileType) {
      case 'md':
      case 'markdown':
        return 'Markdown File';
      case 'txt':
        return 'Text File';
      case 'json':
        return 'JSON File';
      case 'csv':
        return 'CSV File';
      case 'html':
        return 'HTML File';
      default:
        return 'File';
    }
  };

  const isMarkdown = detectedFileType === 'md' || detectedFileType === 'markdown';

  return (
    <div className="my-4 border border-gray-200 rounded-lg bg-white shadow-sm">
      {/* Header */}
      <div className="px-4 py-3 border-b border-gray-200 bg-gray-50 rounded-t-lg">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="font-semibold text-sm text-gray-900 flex items-center gap-2">
              <span className="text-lg">{getFileIcon()}</span>
              {getFileTypeLabel()} Preview
            </h3>
            <p className="text-xs text-gray-600 mt-1">
              <span className="font-medium">{displayFilename}</span> • Saved to: {path}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={handleCopy}
              className="p-1.5 rounded-md hover:bg-gray-200 transition-colors"
              title="Copy content"
            >
              {isCopied ? (
                <CheckIcon className="h-4 w-4 text-green-600" />
              ) : (
                <CopyIcon className="h-4 w-4 text-gray-600" />
              )}
            </button>
            <button
              onClick={handleDownload}
              className="p-1.5 rounded-md hover:bg-gray-200 transition-colors"
              title="Download file"
            >
              <DownloadIcon className="h-4 w-4 text-gray-600" />
            </button>
            {isMarkdown && (
              <button
                onClick={() => setShowPreview(!showPreview)}
                className="px-3 py-1.5 bg-blue-600 text-white text-xs rounded-md hover:bg-blue-700 transition-colors"
              >
                {showPreview ? 'Show Raw' : 'Show Preview'}
              </button>
            )}
          </div>
        </div>
      </div>

      {/* File Content with Typewriter Effect */}
      <div className="p-4">
        {isMarkdown && showPreview && !isTyping ? (
          // Rendered markdown preview
          <div className="prose prose-sm max-w-none">
            <MarkdownText>{displayedContent}</MarkdownText>
          </div>
        ) : (
          // Raw content with typewriter effect
          <div className="relative">
            <pre className="whitespace-pre-wrap font-mono text-sm leading-relaxed text-gray-900 bg-gray-50 p-3 rounded border">
              {displayedContent}
              {isTyping && (
                <span className="inline-block w-2 h-5 bg-blue-600 animate-pulse ml-1"></span>
              )}
            </pre>
          </div>
        )}
      </div>

      {/* File Stats Footer */}
      <div className="px-4 py-2 border-t border-gray-200 bg-gray-50 rounded-b-lg">
        <div className="flex items-center justify-between text-xs text-gray-600">
          <span>{content.length} characters • {content.split('\n').length} lines</span>
          {isTyping && (
            <span className="flex items-center gap-1 text-blue-600">
              <div className="w-2 h-2 bg-blue-600 rounded-full animate-pulse"></div>
              Writing file...
            </span>
          )}
          {!isTyping && (
            <span className="flex items-center gap-1 text-green-600">
              <div className="w-2 h-2 bg-green-600 rounded-full"></div>
              File saved successfully
            </span>
          )}
        </div>
      </div>
    </div>
  );
};
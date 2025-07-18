import { FC, useState, useEffect } from "react";
import { cn } from "@/lib/utils";
import { SendIcon, CopyIcon, CheckIcon } from "lucide-react";

interface EmailPreviewProps {
  content: string;
  subject: string;
  toEmail: string;
  path: string;
  onSendEmail?: (toEmail: string, subject: string, content: string) => void;
}

export const EmailPreview: FC<EmailPreviewProps> = ({
  content,
  subject,
  toEmail,
  path,
  onSendEmail
}) => {
  const [displayedContent, setDisplayedContent] = useState("");
  const [isTyping, setIsTyping] = useState(true);
  const [showSendForm, setShowSendForm] = useState(false);
  const [recipientEmail, setRecipientEmail] = useState(toEmail);
  const [isCopied, setIsCopied] = useState(false);

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
      }, 20); // Adjust speed here (20ms = fast typewriter)

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

  const handleSend = () => {
    if (onSendEmail && recipientEmail) {
      onSendEmail(recipientEmail, subject, content);
      setShowSendForm(false);
    }
  };

  return (
    <div className="my-4 border border-gray-200 rounded-lg bg-white shadow-sm">
      {/* Header */}
      <div className="px-4 py-3 border-b border-gray-200 bg-gray-50 rounded-t-lg">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="font-semibold text-sm text-gray-900">📧 Email Draft Preview</h3>
            <p className="text-xs text-gray-600 mt-1">Saved to: {path}</p>
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
              onClick={() => setShowSendForm(true)}
              className="px-3 py-1.5 bg-blue-600 text-white text-xs rounded-md hover:bg-blue-700 transition-colors flex items-center gap-1"
            >
              <SendIcon className="h-3 w-3" />
              Send
            </button>
          </div>
        </div>
      </div>

      {/* Email Content with Typewriter Effect */}
      <div className="p-4">
        <div className="mb-3 space-y-1">
          <div className="text-sm"><strong>To:</strong> {toEmail || '[Recipient Email]'}</div>
          <div className="text-sm"><strong>Subject:</strong> {subject}</div>
        </div>
        
        <hr className="my-3" />
        
        <div className="relative">
          <pre className="whitespace-pre-wrap font-sans text-sm leading-relaxed text-gray-900">
            {displayedContent}
            {isTyping && (
              <span className="inline-block w-2 h-5 bg-blue-600 animate-pulse ml-1"></span>
            )}
          </pre>
        </div>
      </div>

      {/* Send Email Form */}
      {showSendForm && (
        <div className="px-4 py-3 border-t border-gray-200 bg-gray-50 rounded-b-lg">
          <div className="space-y-3">
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">
                Send to email address:
              </label>
              <input
                type="email"
                value={recipientEmail}
                onChange={(e) => setRecipientEmail(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="recipient@example.com"
              />
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={handleSend}
                disabled={!recipientEmail}
                className="px-4 py-2 bg-blue-600 text-white text-sm rounded-md hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
              >
                Send Email
              </button>
              <button
                onClick={() => setShowSendForm(false)}
                className="px-4 py-2 bg-gray-200 text-gray-700 text-sm rounded-md hover:bg-gray-300 transition-colors"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
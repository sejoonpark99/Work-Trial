import { ToolCallContentPartComponent } from "@assistant-ui/react";
import { CheckIcon, ChevronDownIcon, ChevronUpIcon } from "lucide-react";
import { useState, useEffect } from "react";
import { Button } from "../ui/button";
import { ThoughtCard } from "./thought-card";
import { addStepData, clearAllSteps, StepManager } from "./step-manager";
import { EmailPreview } from "./email-preview";
import { useThoughtCard } from "./thought-card-context";
import { CaseStudyTool } from "./case-study-tool";

export const ToolFallback: ToolCallContentPartComponent = ({
  toolName,
  argsText,
  result,
}) => {
  const [cardData, setCardData] = useState(null);
  const thoughtCard = useThoughtCard();
  
  console.log("ToolFallback called with:", { toolName, argsText, result });
  
  // Handle thought cards specially
  useEffect(() => {
    if (toolName === "thought_card") {
      try {
        console.log("ToolFallback - Processing thought card:", { 
          toolName, 
          argsText, 
          argsTextType: typeof argsText,
          argsTextLength: argsText?.length || 0,
          result,
          timestamp: new Date().toISOString()
        });
        
        // Skip empty or whitespace-only argsText during streaming
        if (!argsText || (typeof argsText === 'string' && !argsText.trim())) {
          console.log("Skipping empty argsText during streaming");
          return;
        }
        
        // argsText should be a JSON string from our backend
        let parsedCardData;
        if (typeof argsText === 'string') {
          const trimmed = argsText.trim();
          
          // Skip obviously incomplete JSON (empty or doesn't start with { or ")
          if (!trimmed || (!trimmed.startsWith('{') && !trimmed.startsWith('"'))) {
            console.log("Skipping incomplete JSON during streaming:", trimmed);
            return;
          }
          
          try {
            // Handle double-escaped JSON strings
            let parsed = JSON.parse(trimmed);
            if (typeof parsed === 'string') {
              // If we get a string, parse it again (double-escaped)
              parsed = JSON.parse(parsed);
            }
            parsedCardData = parsed;
          } catch (parseError) {
            console.log("Failed to parse JSON during streaming:", parseError);
            return;
          }
        } else {
          // If argsText is already an object (sometimes happens with streaming)
          parsedCardData = argsText;
        }
        
        // Skip empty cards
        if (!parsedCardData || !parsedCardData.content || !parsedCardData.card_type) {
          console.log("Skipping incomplete card data:", parsedCardData);
          return;
        }
        
        console.log("✅ ADDING TO STEP:", {
          card_type: parsedCardData.card_type,
          step: parsedCardData.step,
          content: parsedCardData.content.substring(0, 100) + "...",
          timestamp: new Date().toISOString()
        });
        
        // Clear all previous steps if this is step 1 thinking (new conversation)
        if (parsedCardData.step === 1 && parsedCardData.card_type === 'thinking') {
          console.log("🔄 NEW CONVERSATION DETECTED - Clearing previous steps");
          clearAllSteps();
          thoughtCard.reset();
        }
        
        // Start thought card if not visible
        if (!thoughtCard.isVisible && parsedCardData.card_type === 'thinking') {
          thoughtCard.startThinking("Starting analysis...");
        }
        
        // Add step to AI thought card
        switch (parsedCardData.card_type) {
          case 'thinking':
            thoughtCard.addStep(parsedCardData.content, parsedCardData.tool_name, 'thinking');
            break;
          case 'executing':
            thoughtCard.addStep(parsedCardData.content, parsedCardData.tool_name, 'executing');
            break;
          case 'final_answer':
            thoughtCard.addStep(parsedCardData.content, undefined, 'complete');
            thoughtCard.complete();
            break;
          default:
            thoughtCard.addStep(parsedCardData.content, parsedCardData.tool_name, 'step');
        }
        
        // Also add to step manager for backward compatibility
        addStepData(parsedCardData.step, parsedCardData.card_type, parsedCardData);
        setCardData(parsedCardData);
        
      } catch (e) {
        console.error("Error parsing thought card:", e);
        console.error("Raw argsText was:", argsText);
      }
    }
  }, [toolName, argsText, result]);

  if (toolName === "thought_card") {
    // Return null to avoid duplicate renders - StepManager will be rendered elsewhere
    return null;
  }

  // Handle case_study_lookup tool specially
  if (toolName === "case_study_lookup") {
    try {
      let caseStudyData;
      if (typeof result === 'string') {
        caseStudyData = JSON.parse(result);
      } else {
        caseStudyData = result;
      }

      if (caseStudyData && caseStudyData.company_domain) {
        return (
          <CaseStudyTool
            companyDomain={caseStudyData.company_domain}
            summary={caseStudyData.summary}
            allResults={caseStudyData.all_results}
            totalFound={caseStudyData.total_found}
            onSaveAsMarkdown={() => {
              // Trigger save as markdown functionality
              console.log("Save as markdown triggered for", caseStudyData.company_domain);
            }}
          />
        );
      }
    } catch (e) {
      console.error("Error parsing case study data:", e);
    }
  }

  // Handle email_write tool specially
  if (toolName === "email_write") {
    try {
      let emailData;
      if (typeof result === 'string') {
        emailData = JSON.parse(result);
      } else {
        emailData = result;
      }

      if (emailData && emailData.subject && emailData.content) {
        return (
          <EmailPreview
            content={emailData.content}
            subject={emailData.subject}
            toEmail={emailData.to_email || ""}
            path={emailData.path || ""}
            onSendEmail={async (toEmail, subject, content) => {
              try {
                const response = await fetch('http://localhost:8000/send-email', {
                  method: 'POST',
                  headers: {
                    'Content-Type': 'application/json',
                  },
                  body: JSON.stringify({
                    to_email: toEmail,
                    subject: subject,
                    content: content
                  })
                });
                
                const result = await response.json();
                if (result.success) {
                  alert(`✅ Email sent successfully to ${toEmail}!`);
                } else {
                  alert(`❌ Failed to send email: ${result.error || result.message}`);
                }
              } catch (error) {
                console.error('Error sending email:', error);
                alert(`❌ Error sending email: ${error.message}`);
              }
            }}
          />
        );
      }
    } catch (e) {
      console.error("Error parsing email data:", e);
    }
  }

  // Default tool fallback
  const [isCollapsed, setIsCollapsed] = useState(true);
  return (
    <div className="mb-4 flex w-full flex-col gap-3 rounded-lg border py-3">
      <div className="flex items-center gap-2 px-4">
        <CheckIcon className="size-4" />
        <p className="">
          Used tool: <b>{toolName}</b>
        </p>
        <div className="flex-grow" />
        <Button onClick={() => setIsCollapsed(!isCollapsed)}>
          {isCollapsed ? <ChevronUpIcon /> : <ChevronDownIcon />}
        </Button>
      </div>
      {!isCollapsed && (
        <div className="flex flex-col gap-2 border-t pt-2">
          <div className="px-4">
            <pre className="whitespace-pre-wrap">{argsText}</pre>
          </div>
          {result !== undefined && (
            <div className="border-t border-dashed px-4 pt-2">
              <p className="font-semibold">Result:</p>
              <pre className="whitespace-pre-wrap">
                {typeof result === "string"
                  ? result
                  : JSON.stringify(result, null, 2)}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

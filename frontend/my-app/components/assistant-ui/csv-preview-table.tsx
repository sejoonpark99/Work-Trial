import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { CheckIcon, XIcon, FileTextIcon } from "lucide-react";

interface CSVPreviewTableProps {
  csvContent: string;
  fileName: string;
  onConfirm: (csvContent: string) => void;
  onCancel: () => void;
}

interface DomainRow {
  domain: string;
  isValid: boolean;
  rowNumber: number;
}

export const CSVPreviewTable: React.FC<CSVPreviewTableProps> = ({
  csvContent,
  fileName,
  onConfirm,
  onCancel,
}) => {
  const [isProcessing, setIsProcessing] = useState(false);

  // Parse CSV content to extract domains
  const parseDomains = (csvContent: string): DomainRow[] => {
    const lines = csvContent.split('\n').filter(line => line.trim());
    const domains: DomainRow[] = [];
    
    // Skip header row if it exists
    const startIndex = lines[0]?.toLowerCase().includes('domain') ? 1 : 0;
    
    lines.slice(startIndex).forEach((line, index) => {
      const cleanLine = line.trim().replace(/[",]/g, '');
      if (cleanLine) {
        // Clean up domain (remove http/https, www)
        let domain = cleanLine.replace(/^https?:\/\//, '').replace(/^www\./, '');
        if (domain.endsWith('/')) {
          domain = domain.slice(0, -1);
        }
        
        // Basic domain validation
        const isValid = /^[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$/.test(domain);
        
        domains.push({
          domain,
          isValid,
          rowNumber: startIndex + index + 1
        });
      }
    });
    
    return domains;
  };

  const domains = parseDomains(csvContent);
  const validDomains = domains.filter(d => d.isValid);
  const invalidDomains = domains.filter(d => !d.isValid);

  const handleConfirm = async () => {
    if (validDomains.length === 0) {
      alert('No valid domains found in the CSV file');
      return;
    }
    
    setIsProcessing(true);
    
    // Create clean CSV with only valid domains
    const cleanCsv = `domain\n${validDomains.map(d => d.domain).join('\n')}`;
    
    try {
      onConfirm(cleanCsv);
    } catch (error) {
      console.error('Error processing domains:', error);
      alert('Error processing domains. Please try again.');
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <Card className="w-full max-w-2xl mx-auto my-4">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <FileTextIcon className="h-5 w-5" />
          CSV Preview: {fileName}
        </CardTitle>
        <CardDescription>
          Review your domains before processing. We found {validDomains.length} valid domains
          {invalidDomains.length > 0 && ` and ${invalidDomains.length} invalid entries`}.
        </CardDescription>
      </CardHeader>
      
      <CardContent>
        <div className="max-h-64 overflow-y-auto border rounded-lg">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 sticky top-0">
              <tr>
                <th className="px-4 py-2 text-left font-medium text-gray-600">#</th>
                <th className="px-4 py-2 text-left font-medium text-gray-600">Domain</th>
                <th className="px-4 py-2 text-left font-medium text-gray-600">Status</th>
              </tr>
            </thead>
            <tbody>
              {domains.map((domain, index) => (
                <tr key={index} className={`border-t ${!domain.isValid ? 'bg-red-50' : 'hover:bg-gray-50'}`}>
                  <td className="px-4 py-2 text-gray-500">{domain.rowNumber}</td>
                  <td className="px-4 py-2 font-mono text-sm">
                    {domain.domain}
                  </td>
                  <td className="px-4 py-2">
                    {domain.isValid ? (
                      <div className="flex items-center gap-1 text-green-600">
                        <CheckIcon className="h-4 w-4" />
                        <span className="text-xs">Valid</span>
                      </div>
                    ) : (
                      <div className="flex items-center gap-1 text-red-600">
                        <XIcon className="h-4 w-4" />
                        <span className="text-xs">Invalid</span>
                      </div>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        
        {invalidDomains.length > 0 && (
          <div className="mt-4 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
            <p className="text-sm text-yellow-800">
              <strong>Note:</strong> Invalid domains will be excluded from processing.
            </p>
          </div>
        )}
        
        <div className="flex items-center justify-between mt-6">
          <div className="text-sm text-gray-500">
            Ready to process {validDomains.length} domain{validDomains.length !== 1 ? 's' : ''}
          </div>
          
          <div className="flex gap-2">
            <Button
              variant="outline"
              onClick={onCancel}
              disabled={isProcessing}
            >
              Cancel
            </Button>
            <Button
              onClick={handleConfirm}
              disabled={isProcessing || validDomains.length === 0}
            >
              {isProcessing ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-2 border-current border-t-transparent mr-2" />
                  Processing...
                </>
              ) : (
                `Process ${validDomains.length} Domain${validDomains.length !== 1 ? 's' : ''}`
              )}
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};
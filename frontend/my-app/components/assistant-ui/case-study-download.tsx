"use client"

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Download, FileText, Eye, Loader2, Sparkles } from 'lucide-react'

interface CaseStudyDownloadProps {
  onReportGenerated?: (reportData: any) => void
}

interface ReportData {
  ok: boolean
  report_id?: string
  download_url?: string
  generated_files?: Array<{type: string, path: string}>
  ai_design?: {
    report_title?: string
    executive_summary?: string
    key_messages?: string[]
    design_rationale?: string
  }
  error?: {type: string, message: string}
}

export function CaseStudyDownload({ onReportGenerated }: CaseStudyDownloadProps) {
  const [companyDomain, setCompanyDomain] = useState('')
  const [context, setContext] = useState('')
  const [repDomain, setRepDomain] = useState('')
  const [isGenerating, setIsGenerating] = useState(false)
  const [reportData, setReportData] = useState<ReportData | null>(null)
  const [error, setError] = useState('')

  const generateReport = async () => {
    if (!companyDomain.trim()) {
      setError('Company domain is required')
      return
    }

    if (!repDomain.trim()) {
      setError('Rep domain is required for site filtering')
      return
    }

    setIsGenerating(true)
    setError('')
    setReportData(null)

    try {
      const response = await fetch('/api/case-study/generate-report', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          company_domain: companyDomain.trim(),
          context: context.trim(),
          rep_domain: repDomain.trim(),
          format_type: 'both' // Generate both HTML and PDF
        }),
      })

      const data: ReportData = await response.json()

      if (data.ok) {
        setReportData(data)
        onReportGenerated?.(data)
      } else {
        setError(data.error?.message || 'Failed to generate report')
      }
    } catch (err) {
      setError('Network error. Please try again.')
      console.error('Report generation error:', err)
    } finally {
      setIsGenerating(false)
    }
  }

  const downloadPDF = () => {
    if (reportData?.download_url) {
      window.open(reportData.download_url, '_blank')
    }
  }

  const viewHTML = () => {
    if (reportData?.report_id) {
      window.open(`/api/case-study/view-report/${reportData.report_id}`, '_blank')
    }
  }

  return (
    <Card className="w-full max-w-2xl mx-auto">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Sparkles className="w-5 h-5 text-purple-600" />
          AI Case Study Report Generator
        </CardTitle>
        <CardDescription>
          Generate professional, AI-designed case study reports with intelligent layout and visualizations
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Input Form */}
        <div className="space-y-3">
          <div>
            <label className="text-sm font-medium">Company Domain (Prospect)</label>
            <Input
              placeholder="e.g., nike.com"
              value={companyDomain}
              onChange={(e) => setCompanyDomain(e.target.value)}
              disabled={isGenerating}
            />
          </div>
          
          <div>
            <label className="text-sm font-medium">Rep Domain (Your Company)</label>
            <Input
              placeholder="e.g., bloomreach.com"
              value={repDomain}
              onChange={(e) => setRepDomain(e.target.value)}
              disabled={isGenerating}
            />
          </div>
          
          <div>
            <label className="text-sm font-medium">Context (Optional)</label>
            <Input
              placeholder="e.g., ecommerce, personalization, automation"
              value={context}
              onChange={(e) => setContext(e.target.value)}
              disabled={isGenerating}
            />
          </div>
        </div>

        {/* Generate Button */}
        <Button 
          onClick={generateReport} 
          disabled={isGenerating || !companyDomain.trim() || !repDomain.trim()}
          className="w-full"
          size="lg"
        >
          {isGenerating ? (
            <>
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              Generating AI Report...
            </>
          ) : (
            <>
              <Sparkles className="w-4 h-4 mr-2" />
              Generate Professional Report
            </>
          )}
        </Button>

        {/* Error Display */}
        {error && (
          <div className="p-3 bg-red-50 border border-red-200 rounded-md">
            <p className="text-red-600 text-sm">{error}</p>
          </div>
        )}

        {/* Success - Show Report Info and Download Options */}
        {reportData?.ok && (
          <div className="space-y-4 p-4 bg-green-50 border border-green-200 rounded-lg">
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 bg-green-500 rounded-full"></div>
              <span className="font-medium text-green-800">Report Generated Successfully!</span>
            </div>

            {/* AI Design Info */}
            {reportData.ai_design && (
              <div className="space-y-2">
                <h4 className="font-medium text-gray-800">
                  📊 {reportData.ai_design.report_title || 'AI-Designed Report'}
                </h4>
                {reportData.ai_design.executive_summary && (
                  <p className="text-sm text-gray-600">
                    {reportData.ai_design.executive_summary}
                  </p>
                )}
                {reportData.ai_design.key_messages && reportData.ai_design.key_messages.length > 0 && (
                  <div className="flex flex-wrap gap-1">
                    {reportData.ai_design.key_messages.slice(0, 3).map((message, idx) => (
                      <Badge key={idx} variant="secondary" className="text-xs">
                        {message.length > 30 ? message.substring(0, 30) + '...' : message}
                      </Badge>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Download Buttons */}
            <div className="flex gap-3">
              <Button 
                onClick={downloadPDF}
                className="flex-1 bg-blue-600 hover:bg-blue-700"
                disabled={!reportData.download_url}
              >
                <Download className="w-4 h-4 mr-2" />
                Download PDF
              </Button>
              
              <Button 
                onClick={viewHTML}
                variant="outline"
                className="flex-1"
                disabled={!reportData.report_id}
              >
                <Eye className="w-4 h-4 mr-2" />
                Preview Report
              </Button>
            </div>

            {/* Files Generated */}
            {reportData.generated_files && reportData.generated_files.length > 0 && (
              <div className="text-xs text-gray-500">
                Generated: {reportData.generated_files.map(f => f.type.toUpperCase()).join(', ')}
              </div>
            )}
            
            {/* AI Design Note */}
            {reportData.ai_design?.design_rationale && (
              <div className="text-xs text-gray-500 italic">
                AI Design: {reportData.ai_design.design_rationale}
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
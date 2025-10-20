"use client";

import ReactMarkdown from "react-markdown";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Download, FileText } from "lucide-react";

interface ResultsViewerProps {
  result: any;
  sessionId?: string;
}

export default function ResultsViewer({ result, sessionId }: ResultsViewerProps) {
  const handleDownload = async () => {
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const finalSessionId = sessionId || result.session_id || window.location.pathname.split("/").pop();

      const response = await fetch(`${apiUrl}/api/sessions/${finalSessionId}/pdf`);

      if (!response.ok) {
        throw new Error("Failed to download PDF");
      }

      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `feasibility-report-${new Date().toISOString().split('T')[0]}.pdf`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (error) {
      console.error("Error downloading PDF:", error);
      alert("Failed to download PDF. Please try again.");
    }
  };

  const report = result.final_report || result.report || "No report generated";

  // Extract feasibility rating for visual indicator
  const getFeasibilityRating = (reportText: string) => {
    // Check for new emoji-based ratings first
    if (reportText.includes("🟢 GUT GEEIGNET") || reportText.includes("**🟢 GUT GEEIGNET**")) {
      return { rating: "🟢 GUT GEEIGNET", color: "text-green-600 bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800" };
    } else if (reportText.includes("🟡 MACHBAR") || reportText.includes("**🟡 MACHBAR**")) {
      return { rating: "🟡 MACHBAR", color: "text-yellow-600 bg-yellow-50 dark:bg-yellow-900/20 border-yellow-200 dark:border-yellow-800" };
    } else if (reportText.includes("🔴 SCHWIERIG") || reportText.includes("**🔴 SCHWIERIG**")) {
      return { rating: "🔴 SCHWIERIG", color: "text-red-600 bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800" };
    }
    // Fallback to old format for backward compatibility
    else if (reportText.includes("**GUT GEEIGNET**")) {
      return { rating: "🟢 GUT GEEIGNET", color: "text-green-600 bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800" };
    } else if (reportText.includes("**MACHBAR**")) {
      return { rating: "🟡 MACHBAR", color: "text-yellow-600 bg-yellow-50 dark:bg-yellow-900/20 border-yellow-200 dark:border-yellow-800" };
    } else if (reportText.includes("**SCHWIERIG**")) {
      return { rating: "🔴 SCHWIERIG", color: "text-red-600 bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800" };
    }
    return null;
  };

  const feasibilityInfo = getFeasibilityRating(report);

  return (
    <div className="space-y-4">
      {/* Action Bar */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <div className="flex items-center space-x-2">
            <FileText className="h-5 w-5 text-primary" />
            <h2 className="text-lg font-semibold">Feasibility Study Report</h2>
          </div>
          {feasibilityInfo && (
            <div className={`px-4 py-2 rounded-lg border-2 font-bold text-sm ${feasibilityInfo.color}`}>
              {feasibilityInfo.rating}
            </div>
          )}
        </div>
        <Button onClick={handleDownload} variant="outline" size="sm">
          <Download className="h-4 w-4 mr-2" />
          Download Report
        </Button>
      </div>

      {/* Statistics */}
      {(result.num_subagents || result.errors || result.warnings) && (
        <div className="grid grid-cols-3 gap-4">
          {result.num_subagents && (
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  Agents Used
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-2xl font-bold">{result.num_subagents}</p>
              </CardContent>
            </Card>
          )}
          {result.errors && result.errors.length > 0 && (
            <Card className="border-red-200">
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-medium text-red-600">
                  Errors
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-2xl font-bold text-red-600">
                  {result.errors.length}
                </p>
              </CardContent>
            </Card>
          )}
          {result.warnings && result.warnings.length > 0 && (
            <Card className="border-yellow-200">
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-medium text-yellow-600">
                  Warnings
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-2xl font-bold text-yellow-600">
                  {result.warnings.length}
                </p>
              </CardContent>
            </Card>
          )}
        </div>
      )}

      {/* Report Content */}
      <Card>
        <CardContent className="pt-6">
          <article className="prose prose-slate prose-lg max-w-none dark:prose-invert prose-headings:font-bold prose-h2:text-2xl prose-h2:font-bold prose-h2:mt-12 prose-h2:mb-6 prose-h3:text-lg prose-h3:font-semibold prose-h3:mt-6 prose-h3:mb-4 prose-ul:list-disc prose-ul:pl-6 prose-ul:space-y-3 prose-ul:my-4 prose-li:my-0 prose-li:leading-relaxed prose-p:my-0 prose-p:mb-4 prose-p:leading-relaxed prose-strong:text-primary prose-strong:font-bold">
            <ReactMarkdown
              components={{
                h2: ({ node, ...props }) => (
                  <h2 className="text-primary border-l-4 border-primary pl-4 text-2xl font-bold mt-12 first:mt-0 mb-6" {...props} />
                ),
                h3: ({ node, ...props }) => (
                  <h3 className="text-slate-800 dark:text-slate-200 text-lg font-semibold mt-6 mb-4" {...props} />
                ),
                ul: ({ node, ...props }) => (
                  <ul className="space-y-3 my-4 list-disc pl-6" {...props} />
                ),
                li: ({ node, ...props }) => (
                  <li className="text-slate-700 dark:text-slate-300 leading-relaxed" {...props} />
                ),
                p: ({ node, ...props }) => (
                  <p className="text-slate-700 dark:text-slate-300 mb-4 leading-relaxed" {...props} />
                ),
                strong: ({ node, ...props }) => (
                  <strong className="text-primary font-bold text-lg" {...props} />
                ),
              }}
            >
              {report}
            </ReactMarkdown>
          </article>
        </CardContent>
      </Card>
    </div>
  );
}

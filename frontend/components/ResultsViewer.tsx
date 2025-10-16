"use client";

import ReactMarkdown from "react-markdown";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Download, FileText } from "lucide-react";

interface ResultsViewerProps {
  result: any;
}

export default function ResultsViewer({ result }: ResultsViewerProps) {
  const handleDownload = () => {
    const report = result.final_report || "No report available";
    const blob = new Blob([report], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `feasibility-report-${new Date().toISOString().split('T')[0]}.md`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const report = result.final_report || result.report || "No report generated";

  return (
    <div className="space-y-4">
      {/* Action Bar */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <FileText className="h-5 w-5 text-primary" />
          <h2 className="text-lg font-semibold">Feasibility Study Report</h2>
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
          <article className="prose prose-slate max-w-none dark:prose-invert">
            <ReactMarkdown>{report}</ReactMarkdown>
          </article>
        </CardContent>
      </Card>
    </div>
  );
}

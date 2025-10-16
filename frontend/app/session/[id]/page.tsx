"use client";

import { useParams } from "next/navigation";
import { useSSE } from "@/hooks/useSSE";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import AgentVisualization from "@/components/AgentVisualization";
import ResultsViewer from "@/components/ResultsViewer";
import { CheckCircle2, Circle, Loader2, XCircle, AlertCircle } from "lucide-react";

export default function SessionPage() {
  const params = useParams();
  const sessionId = params.id as string;
  const { status, result, error } = useSSE(sessionId);

  const getStatusInfo = () => {
    switch (status) {
      case "connecting":
      case "connected":
        return {
          icon: <Loader2 className="h-6 w-6 animate-spin text-blue-500" />,
          title: "Connecting...",
          description: "Establishing connection to agent system",
          progress: 5,
        };
      case "pending":
        return {
          icon: <Circle className="h-6 w-6 text-gray-400" />,
          title: "Pending",
          description: "Waiting to start processing",
          progress: 10,
        };
      case "processing":
        return {
          icon: <Loader2 className="h-6 w-6 animate-spin text-blue-500" />,
          title: "Processing",
          description: "AI agents are analyzing your documents",
          progress: 50,
        };
      case "completed":
        return {
          icon: <CheckCircle2 className="h-6 w-6 text-green-500" />,
          title: "Completed",
          description: "Feasibility study completed successfully",
          progress: 100,
        };
      case "failed":
        return {
          icon: <XCircle className="h-6 w-6 text-red-500" />,
          title: "Failed",
          description: error || "An error occurred during processing",
          progress: 0,
        };
      case "error":
        return {
          icon: <AlertCircle className="h-6 w-6 text-red-500" />,
          title: "Connection Error",
          description: error || "Failed to connect to server",
          progress: 0,
        };
      default:
        return {
          icon: <Circle className="h-6 w-6 text-gray-400" />,
          title: status,
          description: "Unknown status",
          progress: 0,
        };
    }
  };

  const statusInfo = getStatusInfo();

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold mb-2">Feasibility Study</h1>
        <p className="text-muted-foreground">Session ID: {sessionId}</p>
      </div>

      {/* Status Card */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              {statusInfo.icon}
              <div>
                <CardTitle>{statusInfo.title}</CardTitle>
                <CardDescription>{statusInfo.description}</CardDescription>
              </div>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <Progress value={statusInfo.progress} className="h-2" />
        </CardContent>
      </Card>

      {/* Main Content */}
      {status === "completed" && result ? (
        <Tabs defaultValue="report" className="w-full">
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="report">Final Report</TabsTrigger>
            <TabsTrigger value="analysis">Agent Analysis</TabsTrigger>
            <TabsTrigger value="timeline">Timeline</TabsTrigger>
          </TabsList>

          <TabsContent value="report" className="mt-6">
            <ResultsViewer result={result} />
          </TabsContent>

          <TabsContent value="analysis" className="mt-6">
            <Card>
              <CardHeader>
                <CardTitle>Agent Analysis Details</CardTitle>
                <CardDescription>
                  Detailed findings from each specialized agent
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {result.extracted_facts && (
                    <div>
                      <h3 className="font-semibold mb-2">Extracted Facts</h3>
                      <pre className="bg-muted p-4 rounded-md overflow-x-auto text-xs">
                        {JSON.stringify(result.extracted_facts, null, 2)}
                      </pre>
                    </div>
                  )}
                  {result.risk_assessment && (
                    <div>
                      <h3 className="font-semibold mb-2">Risk Assessment</h3>
                      <pre className="bg-muted p-4 rounded-md overflow-x-auto text-xs">
                        {JSON.stringify(result.risk_assessment, null, 2)}
                      </pre>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="timeline" className="mt-6">
            <AgentVisualization sessionId={sessionId} />
          </TabsContent>
        </Tabs>
      ) : status === "processing" || status === "pending" ? (
        <div className="space-y-6">
          {/* Agent Visualization */}
          <AgentVisualization sessionId={sessionId} />

          {/* Agent Stages */}
          <Card>
            <CardHeader>
              <CardTitle>Processing Stages</CardTitle>
              <CardDescription>
                Multi-agent workflow progress
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {[
                  { name: "EXTRACTOR", desc: "Extracting facts from documents" },
                  { name: "PLANNER", desc: "Creating specialized analysis agents" },
                  { name: "SUBAGENTS", desc: "Parallel analysis execution" },
                  { name: "RISK ASSESSOR", desc: "Evaluating technical and commercial risks" },
                  { name: "WRITER", desc: "Generating final report" },
                ].map((stage, index) => (
                  <div key={index} className="flex items-center space-x-3 p-3 bg-muted/50 rounded-md">
                    <Loader2 className="h-4 w-4 animate-spin text-primary" />
                    <div>
                      <p className="font-medium text-sm">{stage.name}</p>
                      <p className="text-xs text-muted-foreground">{stage.desc}</p>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      ) : null}

      {/* Error Display */}
      {(status === "failed" || status === "error") && error && (
        <Card className="border-red-200 bg-red-50">
          <CardHeader>
            <CardTitle className="text-red-900">Error Details</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-red-700">{error}</p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

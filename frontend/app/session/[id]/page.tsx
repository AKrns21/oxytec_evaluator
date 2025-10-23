"use client";

import { useParams } from "next/navigation";
import { useState, useEffect } from "react";
import { useSSE } from "@/hooks/useSSE";
import { usePromptData } from "@/hooks/usePromptData";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import AgentVisualization from "@/components/AgentVisualization";
import ResultsViewer from "@/components/ResultsViewer";
import PromptVersionCard from "@/components/PromptVersionCard";
import { CheckCircle2, Circle, Loader2, XCircle, AlertCircle } from "lucide-react";

export default function SessionPage() {
  const params = useParams();
  const sessionId = params.id as string;
  const { status, result, error } = useSSE(sessionId);
  const { data: promptData, loading: promptLoading, error: promptError } = usePromptData(sessionId);
  const [agentProgress, setAgentProgress] = useState(0);

  // Calculate progress based on completed agents (20% per agent for 5 agents)
  useEffect(() => {
    const fetchAgentProgress = async () => {
      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
        const response = await fetch(`${apiUrl}/api/sessions/${sessionId}/debug`);
        if (!response.ok) return;

        const data = await response.json();
        const outputs = data.agent_outputs || [];

        // Count unique agents that have completed (have duration_ms > 0)
        const agentOrder = ["extractor", "planner", "subagent", "risk_assessor", "writer"];
        const completedAgents = new Set<string>();

        outputs.forEach((output: any) => {
          if (output.duration_ms && output.duration_ms > 0) {
            completedAgents.add(output.agent_type);
          }
        });

        // Count how many agents from our ordered list have completed
        const numCompleted = agentOrder.filter(type => completedAgents.has(type)).length;

        // Calculate progress: 20% per completed agent
        // 0% = no agents started, 20% = 1 completed, 40% = 2 completed, etc.
        const progress = numCompleted * 20;
        setAgentProgress(progress);
      } catch (error) {
        console.error("Failed to fetch agent progress:", error);
      }
    };

    if (status === "processing" || status === "pending") {
      fetchAgentProgress();
      const interval = setInterval(fetchAgentProgress, 2000);
      return () => clearInterval(interval);
    }
  }, [sessionId, status]);

  const getStatusInfo = () => {
    switch (status) {
      case "connecting":
      case "connected":
        return {
          icon: <Loader2 className="h-6 w-6 animate-spin text-blue-500" />,
          title: "Connecting...",
          description: "Establishing connection to agent system",
          progress: 0,
        };
      case "pending":
        return {
          icon: <Circle className="h-6 w-6 text-gray-400" />,
          title: "Pending",
          description: "Waiting to start processing",
          progress: 0,
        };
      case "processing":
        return {
          icon: <Loader2 className="h-6 w-6 animate-spin text-blue-500" />,
          title: "Processing",
          description: "AI agents are analyzing your documents",
          progress: agentProgress,
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
            <TabsTrigger value="prompts">Prompt Versions</TabsTrigger>
            <TabsTrigger value="timeline">Timeline</TabsTrigger>
          </TabsList>

          <TabsContent value="report" className="mt-6">
            <ResultsViewer result={result} sessionId={sessionId} />
          </TabsContent>

          <TabsContent value="prompts" className="mt-6">
            <Card>
              <CardHeader>
                <CardTitle>Prompt Versions Used</CardTitle>
                <CardDescription>
                  View the exact prompt versions used by each agent for this analysis
                </CardDescription>
              </CardHeader>
              <CardContent>
                {promptLoading ? (
                  <div className="flex items-center justify-center py-12">
                    <Loader2 className="h-8 w-8 animate-spin text-primary" />
                    <span className="ml-3 text-muted-foreground">Loading prompt data...</span>
                  </div>
                ) : promptError ? (
                  <div className="p-4 bg-red-50 border border-red-200 rounded-md">
                    <p className="text-red-900 font-medium">Failed to load prompt data</p>
                    <p className="text-red-700 text-sm mt-1">{promptError}</p>
                  </div>
                ) : promptData ? (
                  <div className="space-y-4">
                    {/* Display agents in execution order */}
                    {Object.keys(promptData)
                      .filter(key => ["extractor", "planner", "subagent", "risk_assessor", "writer"].includes(key))
                      .sort((a, b) => {
                        // Define execution order
                        const order = ["extractor", "planner", "subagent", "risk_assessor", "writer"];
                        return order.indexOf(a) - order.indexOf(b);
                      })
                      .map((agentType) => {
                        const agentData = promptData[agentType];
                        if (!agentData) return null;

                        return (
                          <PromptVersionCard
                            key={agentType}
                            agentName={agentType}
                            agentType={agentType}
                            version={agentData.version}
                            changelog={agentData.changelog}
                            promptText={agentData.prompt_text}
                            systemPrompt={agentData.system_prompt}
                            previousVersion={agentData.previous_version}
                            tokensUsed={agentData.tokens_used}
                            durationMs={agentData.duration_ms}
                          />
                        );
                      })}
                  </div>
                ) : (
                  <div className="text-center py-12 text-muted-foreground">
                    No prompt data available for this session
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="timeline" className="mt-6">
            <AgentVisualization sessionId={sessionId} />
          </TabsContent>
        </Tabs>
      ) : status === "processing" || status === "pending" ? (
        <AgentVisualization sessionId={sessionId} />
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

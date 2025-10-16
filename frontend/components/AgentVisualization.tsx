"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { CheckCircle2, Circle, Loader2, ArrowRight } from "lucide-react";

interface AgentVisualizationProps {
  sessionId: string;
}

interface AgentNode {
  name: string;
  status: "pending" | "running" | "completed" | "failed";
  description: string;
}

export default function AgentVisualization({ sessionId }: AgentVisualizationProps) {
  const [agents, setAgents] = useState<AgentNode[]>([
    { name: "EXTRACTOR", status: "pending", description: "Extract structured facts" },
    { name: "PLANNER", status: "pending", description: "Plan agent strategy" },
    { name: "SUBAGENTS", status: "pending", description: "Parallel analysis" },
    { name: "RISK ASSESSOR", status: "pending", description: "Risk evaluation" },
    { name: "WRITER", status: "pending", description: "Report generation" },
  ]);

  useEffect(() => {
    // Simulate agent progress (in real implementation, this would come from SSE)
    const interval = setInterval(() => {
      setAgents((prev) => {
        const pending = prev.findIndex((a) => a.status === "pending");
        const running = prev.findIndex((a) => a.status === "running");

        if (running !== -1) {
          // Complete the running agent
          const updated = [...prev];
          updated[running] = { ...updated[running], status: "completed" };
          return updated;
        } else if (pending !== -1) {
          // Start the next pending agent
          const updated = [...prev];
          updated[pending] = { ...updated[pending], status: "running" };
          return updated;
        }

        return prev;
      });
    }, 8000); // Update every 8 seconds

    return () => clearInterval(interval);
  }, []);

  const getAgentIcon = (status: AgentNode["status"]) => {
    switch (status) {
      case "pending":
        return <Circle className="h-6 w-6 text-gray-300" />;
      case "running":
        return <Loader2 className="h-6 w-6 animate-spin text-blue-500" />;
      case "completed":
        return <CheckCircle2 className="h-6 w-6 text-green-500" />;
      case "failed":
        return <Circle className="h-6 w-6 text-red-500" />;
    }
  };

  const getAgentColor = (status: AgentNode["status"]) => {
    switch (status) {
      case "pending":
        return "bg-gray-50 border-gray-200";
      case "running":
        return "bg-blue-50 border-blue-300 shadow-sm";
      case "completed":
        return "bg-green-50 border-green-300";
      case "failed":
        return "bg-red-50 border-red-300";
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Agent Workflow</CardTitle>
        <CardDescription>
          Real-time visualization of the multi-agent system
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {agents.map((agent, index) => (
            <div key={agent.name}>
              <div
                className={`
                  flex items-center space-x-4 p-4 rounded-lg border-2 transition-all
                  ${getAgentColor(agent.status)}
                `}
              >
                <div className="flex-shrink-0">{getAgentIcon(agent.status)}</div>

                <div className="flex-1">
                  <div className="flex items-center justify-between">
                    <h3 className="font-semibold">{agent.name}</h3>
                    <span
                      className={`
                        text-xs font-medium px-2 py-1 rounded-full
                        ${
                          agent.status === "pending"
                            ? "bg-gray-200 text-gray-700"
                            : agent.status === "running"
                            ? "bg-blue-200 text-blue-700"
                            : agent.status === "completed"
                            ? "bg-green-200 text-green-700"
                            : "bg-red-200 text-red-700"
                        }
                      `}
                    >
                      {agent.status}
                    </span>
                  </div>
                  <p className="text-sm text-muted-foreground mt-1">
                    {agent.description}
                  </p>

                  {/* Progress bar for running agent */}
                  {agent.status === "running" && (
                    <div className="mt-2">
                      <div className="h-1 bg-blue-200 rounded-full overflow-hidden">
                        <div className="h-full bg-blue-500 animate-pulse w-3/4"></div>
                      </div>
                    </div>
                  )}
                </div>
              </div>

              {/* Arrow connector */}
              {index < agents.length - 1 && (
                <div className="flex justify-center py-2">
                  <ArrowRight className="h-5 w-5 text-gray-300" />
                </div>
              )}
            </div>
          ))}
        </div>

        {/* Info Note */}
        <div className="mt-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
          <p className="text-sm text-blue-900">
            <strong>Note:</strong> The SUBAGENTS stage creates 3-8 specialized agents
            that execute in parallel. Each analyzes a different aspect (VOC chemistry,
            product selection, energy analysis, etc.) simultaneously.
          </p>
        </div>
      </CardContent>
    </Card>
  );
}

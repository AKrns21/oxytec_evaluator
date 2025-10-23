"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { CheckCircle2, Circle, Loader2, Clock } from "lucide-react";

interface AgentVisualizationProps {
  sessionId: string;
}

interface AgentTiming {
  agent_type: string;
  duration_ms: number;
  created_at: string;
  status: "pending" | "running" | "completed";
}

export default function AgentVisualization({ sessionId }: AgentVisualizationProps) {
  const [agentTimings, setAgentTimings] = useState<AgentTiming[]>([]);
  const [totalDuration, setTotalDuration] = useState<number>(0);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchTimings = async () => {
      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
        const response = await fetch(`${apiUrl}/api/sessions/${sessionId}/debug`);

        if (!response.ok) {
          console.error("Failed to fetch debug data");
          return;
        }

        const data = await response.json();
        const outputs = data.agent_outputs || [];

        // Group by agent_type and sum durations
        const timingsMap: Record<string, { duration: number; created_at: string }> = {};

        outputs.forEach((output: any) => {
          const agentType = output.agent_type;

          if (!timingsMap[agentType]) {
            timingsMap[agentType] = {
              duration: 0,
              created_at: output.created_at
            };
          }
          timingsMap[agentType].duration += output.duration_ms || 0;
          // Keep the earliest created_at
          if (output.created_at < timingsMap[agentType].created_at) {
            timingsMap[agentType].created_at = output.created_at;
          }
        });

        // Convert to array with proper order and determine status
        const agentOrder = ["extractor", "planner", "subagent", "risk_assessor", "writer"];

        // Count how many agents have completed (have duration > 0)
        const completedAgents = agentOrder.filter(type => timingsMap[type]?.duration > 0);
        const numCompleted = completedAgents.length;

        // Determine currently running agent index
        // If all agents are done, no one is running
        // Otherwise, the currently running agent is at index = numCompleted
        let currentlyRunningIndex = numCompleted < agentOrder.length ? numCompleted : -1;

        const timings: AgentTiming[] = agentOrder.map((type, index) => {
          const hasDuration = timingsMap[type]?.duration > 0;

          // Determine status:
          // - If index < numCompleted: completed (has finished and next agent has started or is last)
          // - If index === numCompleted: running (currently executing)
          // - If index > numCompleted: pending (not started yet)
          let status: AgentTiming["status"] = "pending";
          if (index < numCompleted) {
            status = "completed";
          } else if (index === currentlyRunningIndex) {
            status = "running";
          }

          return {
            agent_type: type,
            duration_ms: timingsMap[type]?.duration || 0,
            created_at: timingsMap[type]?.created_at || "",
            status
          };
        });

        // Calculate total duration
        const total = Object.values(timingsMap).reduce((sum, t) => sum + t.duration, 0);

        setAgentTimings(timings);
        setTotalDuration(total);
        setLoading(false);
      } catch (error) {
        console.error("Error fetching agent timings:", error);
        setLoading(false);
      }
    };

    fetchTimings();

    // Poll every 2 seconds for updates during processing
    const interval = setInterval(fetchTimings, 2000);

    return () => clearInterval(interval);
  }, [sessionId]);

  const formatDuration = (ms: number) => {
    if (ms === 0) return "-";
    return `${(ms / 1000).toFixed(2)}s`;
  };

  const getAgentIcon = (status: AgentTiming["status"]) => {
    switch (status) {
      case "pending":
        return <Circle className="h-6 w-6 text-gray-300" />;
      case "running":
        return <Loader2 className="h-6 w-6 animate-spin text-blue-500" />;
      case "completed":
        return <CheckCircle2 className="h-6 w-6 text-blue-500" />;
    }
  };

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Timeline</CardTitle>
          <CardDescription>Agent execution timeline</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-6 w-6 animate-spin text-primary mr-3" />
            <span className="text-muted-foreground">Loading timeline...</span>
          </div>
        </CardContent>
      </Card>
    );
  }

  // Check if all agents are completed
  const allCompleted = agentTimings.length > 0 && agentTimings.every(t => t.status === "completed");

  return (
    <Card>
      <CardHeader>
        <CardTitle>Timeline</CardTitle>
        <CardDescription>
          Agent execution timeline with actual durations
        </CardDescription>
        {allCompleted && totalDuration > 0 && (
          <div className="flex items-center space-x-2 mt-2 text-blue-600">
            <Clock className="h-5 w-5" />
            <span className="font-semibold text-lg">{formatDuration(totalDuration)}</span>
          </div>
        )}
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {agentTimings.map((timing) => (
            <div
              key={timing.agent_type}
              className="flex items-center space-x-3 p-3 bg-white border border-gray-200 rounded-lg"
            >
              {getAgentIcon(timing.status)}
              <div className="flex-1">
                <span className="font-medium text-base">{timing.agent_type}</span>
              </div>
              <div className="text-sm text-muted-foreground font-medium">
                {formatDuration(timing.duration_ms)}
              </div>
            </div>
          ))}
        </div>

        {agentTimings.every(t => t.status === "pending") && (
          <div className="mt-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
            <p className="text-sm text-blue-900">
              <strong>Note:</strong> The timeline will update automatically as agents complete their execution.
              Each agent's actual execution time will be displayed here.
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

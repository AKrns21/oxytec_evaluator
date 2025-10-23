import { useState, useEffect } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface PromptMetadata {
  version: string;
  changelog: string;
  prompt_text: string;
  system_prompt: string;
  available_versions: string[];
  previous_version?: string;
  tokens_used?: number;
  duration_ms?: number;
  error?: string;
}

export interface PromptData {
  [agentType: string]: PromptMetadata;
}

export function usePromptData(sessionId: string) {
  const [data, setData] = useState<PromptData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!sessionId) {
      setLoading(false);
      return;
    }

    const fetchPromptData = async () => {
      try {
        setLoading(true);
        setError(null);

        const response = await fetch(`${API_URL}/api/sessions/${sessionId}/prompts`);

        if (!response.ok) {
          throw new Error(`Failed to fetch prompt data: ${response.statusText}`);
        }

        const promptData: PromptData = await response.json();
        setData(promptData);
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : "Unknown error occurred";
        setError(errorMessage);
        console.error("Error fetching prompt data:", err);
      } finally {
        setLoading(false);
      }
    };

    fetchPromptData();
  }, [sessionId]);

  return { data, loading, error };
}

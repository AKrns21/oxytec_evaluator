"use client";

import { useEffect, useState } from "react";

interface SSEEvent {
  type: string;
  status?: string;
  updated_at?: string;
  result?: any;
  error?: string;
}

export function useSSE(sessionId: string) {
  const [events, setEvents] = useState<SSEEvent[]>([]);
  const [status, setStatus] = useState<string>("connecting");
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    const eventSource = new EventSource(
      `${apiUrl}/api/sessions/${sessionId}/stream`
    );

    eventSource.onopen = () => {
      setStatus("connected");
    };

    eventSource.addEventListener("status", (event) => {
      const data = JSON.parse(event.data);
      setEvents((prev) => [...prev, data]);
      setStatus(data.status);
    });

    eventSource.addEventListener("final", (event) => {
      const data = JSON.parse(event.data);
      setEvents((prev) => [...prev, data]);
      setStatus(data.status);

      if (data.status === "completed") {
        setResult(data.result);
      } else if (data.status === "failed") {
        setError(data.error || "Unknown error occurred");
      }

      eventSource.close();
    });

    eventSource.addEventListener("error", (event: any) => {
      const data = event.data ? JSON.parse(event.data) : {};
      setError(data.error || "Connection error");
      setStatus("error");
      eventSource.close();
    });

    eventSource.onerror = () => {
      setStatus("error");
      setError("Failed to connect to server");
      eventSource.close();
    };

    return () => {
      eventSource.close();
    };
  }, [sessionId]);

  return { events, status, result, error };
}

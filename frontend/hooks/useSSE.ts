"use client";

import { useEffect, useState } from "react";
import { SSEEvent, SessionResult, SessionStatus } from "@/types/session";

/**
 * Custom hook for Server-Sent Events (SSE) to track session progress
 *
 * @param sessionId - UUID of the session to monitor
 * @returns Object containing events, status, result, and error state
 */
export function useSSE(sessionId: string) {
  const [events, setEvents] = useState<SSEEvent[]>([]);
  const [status, setStatus] = useState<SessionStatus | "connecting" | "connected" | "error">("connecting");
  const [result, setResult] = useState<SessionResult | null>(null);
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
      try {
        const data = JSON.parse(event.data) as SSEEvent;
        setEvents((prev) => [...prev, data]);
        if (data.status) {
          setStatus(data.status);
        }
      } catch (parseError) {
        console.error("Failed to parse status event:", parseError);
        setError("Failed to parse server response");
      }
    });

    eventSource.addEventListener("final", (event) => {
      try {
        const data = JSON.parse(event.data) as SSEEvent;
        setEvents((prev) => [...prev, data]);
        if (data.status) {
          setStatus(data.status);
        }

        if (data.status === "completed" && data.result) {
          setResult(data.result);
        } else if (data.status === "failed") {
          setError(data.error || "Unknown error occurred");
        }

        eventSource.close();
      } catch (parseError) {
        console.error("Failed to parse final event:", parseError);
        setError("Failed to parse final result");
        eventSource.close();
      }
    });

    eventSource.addEventListener("error", (event: MessageEvent) => {
      try {
        const data = event.data ? JSON.parse(event.data) : {};
        setError(data.error || "Connection error");
        setStatus("error");
      } catch (parseError) {
        setError("Connection error");
        setStatus("error");
      }
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

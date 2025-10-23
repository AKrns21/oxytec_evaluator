"use client";

import { useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ChevronDown, ChevronRight, Code2, FileText, GitCompare, Clock, Zap, Copy, Check } from "lucide-react";

interface PromptVersionCardProps {
  agentName: string;
  agentType: string;
  version: string;
  changelog: string;
  promptText: string;
  systemPrompt?: string;
  previousVersion?: string;
  tokensUsed?: number;
  durationMs?: number;
}

export default function PromptVersionCard({
  agentName,
  agentType,
  version,
  changelog,
  promptText,
  systemPrompt,
  previousVersion,
  tokensUsed,
  durationMs,
}: PromptVersionCardProps) {
  const [showChangelog, setShowChangelog] = useState(false);
  const [showPrompt, setShowPrompt] = useState(false);
  const [showDiff, setShowDiff] = useState(false);
  const [copiedChangelog, setCopiedChangelog] = useState(false);
  const [copiedPrompt, setCopiedPrompt] = useState(false);

  // Don't display changelog summary - removed per user request
  const hasFullChangelog = changelog && changelog.trim().length > 0;

  // Copy to clipboard function
  const copyToClipboard = async (text: string, setCopied: (value: boolean) => void) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error("Failed to copy:", err);
    }
  };

  // Get agent emoji
  const getAgentEmoji = (type: string) => {
    const emojiMap: Record<string, string> = {
      extractor: "📄",
      planner: "🎯",
      subagent: "🤖",
      risk_assessor: "⚠️",
      writer: "✍️",
    };
    return emojiMap[type.toLowerCase()] || "🔧";
  };

  // Format duration
  const formatDuration = (ms?: number) => {
    if (!ms) return "N/A";
    if (ms < 1000) return `${ms}ms`;
    return `${(ms / 1000).toFixed(1)}s`;
  };

  // Format token count
  const formatTokens = (tokens?: number) => {
    if (!tokens) return "N/A";
    if (tokens >= 1000) return `${(tokens / 1000).toFixed(1)}k`;
    return tokens.toString();
  };

  return (
    <Card className="mb-4">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div>
              <CardTitle className="text-lg">{agentType}</CardTitle>
            </div>
          </div>
          <div className="flex items-center space-x-2">
            <span className="px-3 py-1 bg-primary/10 text-primary rounded-full text-xs font-semibold">
              {version}
            </span>
          </div>
        </div>

        {/* Stats Row */}
        {(tokensUsed || durationMs) && (
          <div className="flex items-center space-x-4 mt-3 pt-3 border-t">
            {tokensUsed && (
              <div className="flex items-center space-x-1 text-xs text-muted-foreground">
                <Zap className="h-3 w-3" />
                <span>{formatTokens(tokensUsed)} tokens</span>
              </div>
            )}
            {durationMs && (
              <div className="flex items-center space-x-1 text-xs text-muted-foreground">
                <Clock className="h-3 w-3" />
                <span>{formatDuration(durationMs)}</span>
              </div>
            )}
          </div>
        )}
      </CardHeader>

      <CardContent className="space-y-2">
        {/* Full Changelog */}
        {hasFullChangelog && (
          <div>
            <button
              onClick={() => setShowChangelog(!showChangelog)}
              className="flex items-center space-x-2 text-sm font-medium text-primary hover:underline w-full text-left py-2"
            >
              {showChangelog ? (
                <ChevronDown className="h-4 w-4" />
              ) : (
                <ChevronRight className="h-4 w-4" />
              )}
              <FileText className="h-4 w-4" />
              <span>View Full Changelog</span>
            </button>
            {showChangelog && (
              <div className="ml-6 p-3 bg-muted rounded-md text-xs relative">
                <button
                  onClick={() => copyToClipboard(changelog, setCopiedChangelog)}
                  className="absolute top-2 right-2 p-1.5 rounded hover:bg-background/80 transition-colors"
                  title="Copy changelog"
                >
                  {copiedChangelog ? (
                    <Check className="h-4 w-4 text-green-600" />
                  ) : (
                    <Copy className="h-4 w-4 text-muted-foreground" />
                  )}
                </button>
                <pre className="whitespace-pre-wrap font-mono pr-8">{changelog}</pre>
              </div>
            )}
          </div>
        )}

        {/* Full Prompt Text */}
        <div>
          <button
            onClick={() => setShowPrompt(!showPrompt)}
            className="flex items-center space-x-2 text-sm font-medium text-primary hover:underline w-full text-left py-2"
          >
            {showPrompt ? (
              <ChevronDown className="h-4 w-4" />
            ) : (
              <ChevronRight className="h-4 w-4" />
            )}
            <Code2 className="h-4 w-4" />
            <span>View Full Prompt</span>
            <span className="text-xs text-muted-foreground">
              ({(promptText.length / 1000).toFixed(1)}k chars)
            </span>
          </button>
          {showPrompt && (
            <div className="ml-6 p-3 bg-muted rounded-md overflow-x-auto relative">
              <button
                onClick={() => {
                  const fullPrompt = systemPrompt && systemPrompt !== "Default system prompt"
                    ? `${promptText}\n\n--- System Prompt ---\n${systemPrompt}`
                    : promptText;
                  copyToClipboard(fullPrompt, setCopiedPrompt);
                }}
                className="absolute top-2 right-2 p-1.5 rounded hover:bg-background/80 transition-colors z-10"
                title="Copy prompt"
              >
                {copiedPrompt ? (
                  <Check className="h-4 w-4 text-green-600" />
                ) : (
                  <Copy className="h-4 w-4 text-muted-foreground" />
                )}
              </button>
              <pre className="whitespace-pre-wrap font-mono text-xs max-h-96 overflow-y-auto pr-8">
                {promptText}
              </pre>
              {systemPrompt && systemPrompt !== "Default system prompt" && (
                <div className="mt-3 pt-3 border-t">
                  <p className="text-xs font-semibold mb-2">System Prompt:</p>
                  <pre className="whitespace-pre-wrap font-mono text-xs">
                    {systemPrompt}
                  </pre>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Version Diff */}
        {previousVersion && (
          <div>
            <button
              onClick={() => setShowDiff(!showDiff)}
              className="flex items-center space-x-2 text-sm font-medium text-primary hover:underline w-full text-left py-2"
            >
              {showDiff ? (
                <ChevronDown className="h-4 w-4" />
              ) : (
                <ChevronRight className="h-4 w-4" />
              )}
              <GitCompare className="h-4 w-4" />
              <span>Compare with {previousVersion}</span>
            </button>
            {showDiff && (
              <div className="ml-6 p-3 bg-muted rounded-md text-xs">
                <div className="mb-2 p-2 bg-blue-50 border border-blue-200 rounded">
                  <p className="text-blue-900 font-medium">Version Comparison</p>
                  <p className="text-blue-700 text-xs mt-1">
                    Showing changes from {previousVersion} → {version}
                  </p>
                </div>
                <div className="p-2 bg-yellow-50 border border-yellow-200 rounded">
                  <p className="text-yellow-900 text-xs">
                    🚧 Diff view not yet implemented. This will show a side-by-side comparison
                    of prompt changes with notes explaining why each change was made.
                  </p>
                </div>
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

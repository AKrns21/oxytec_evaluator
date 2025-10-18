# LangSmith Integration Guide

This document explains how to enable and use LangSmith tracing for the Oxytec Multi-Agent Feasibility Platform.

## Overview

LangSmith provides comprehensive tracing and monitoring for LLM applications. It captures:
- Agent execution flows through the LangGraph workflow
- Individual LLM calls (Claude and OpenAI)
- Timing and token usage metrics
- Input/output data for debugging
- Error tracking and performance analytics

## Setup Instructions

### 1. Get LangSmith API Key

1. Sign up for LangSmith at https://smith.langchain.com/
2. Create a new project or use an existing one
3. Generate an API key from your account settings

### 2. Configure Environment Variables

Edit your `.env` file and add:

```bash
# LangSmith Tracing
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=your_langsmith_api_key_here
LANGCHAIN_PROJECT=oxytec-feasibility-platform
```

**Environment Variables:**
- `LANGCHAIN_TRACING_V2`: Set to `true` to enable tracing (default: `false`)
- `LANGCHAIN_API_KEY`: Your LangSmith API key
- `LANGCHAIN_PROJECT`: Project name in LangSmith (can be customized)

### 3. Restart Backend Server

The tracing configuration is loaded at startup:

```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

You should see this log message if tracing is enabled:
```
langsmith_tracing_enabled project=oxytec-feasibility-platform
langsmith_graph_tracing_enabled project=oxytec-feasibility-platform
```

## What Gets Traced

### LangGraph Workflow
- Complete execution flow: EXTRACTOR → PLANNER → SUBAGENTS → RISK_ASSESSOR → WRITER
- State transitions between agents
- Parallel subagent execution timing
- Error propagation

### LLM Calls
- **Claude API calls** (Anthropic):
  - WRITER agent (report generation)
  - Tool-calling agents (if using Claude)
- **OpenAI API calls**:
  - EXTRACTOR (JSON extraction)
  - PLANNER (subagent planning)
  - SUBAGENTS (parallel analysis)
  - RISK_ASSESSOR (risk evaluation)
  - Embedding generation (RAG)

### Captured Metadata
- Session ID
- Agent type and instance name
- Prompt and system prompt
- Model configuration (name, temperature/reasoning_effort)
- Response content
- Token usage
- Execution duration
- Errors and warnings

## Viewing Traces

### 1. Access LangSmith Dashboard

Visit: https://smith.langchain.com/

### 2. Navigate to Your Project

Select your project (default: `oxytec-feasibility-platform`)

### 3. View Traces

Each session creates a trace showing:

```
run_agent_graph (session_id: xxx)
├── extractor_node
│   └── OpenAI Chat Completion (gpt-5)
├── planner_node
│   └── OpenAI Chat Completion (gpt-5-mini)
├── execute_subagents_parallel
│   ├── subagent_1 (parallel)
│   │   └── OpenAI Chat Completion (gpt-5-nano)
│   ├── subagent_2 (parallel)
│   │   └── OpenAI Chat Completion (gpt-5-nano)
│   └── subagent_N (parallel)
│       └── OpenAI Chat Completion (gpt-5-nano)
├── risk_assessor_node
│   └── OpenAI Chat Completion (gpt-5)
└── writer_node
    └── Anthropic Chat Completion (claude-sonnet-4-5)
```

### 4. Analyze Performance

**Timing Analysis:**
- Identify slowest agents
- Measure parallel execution efficiency
- Track end-to-end session duration

**Token Usage:**
- Monitor costs per agent
- Identify high-token prompts
- Optimize for cost efficiency

**Debugging:**
- Inspect exact prompts sent to models
- View full LLM responses
- Trace error origins through the workflow

## Cost Considerations

LangSmith tracing adds minimal overhead:
- **Latency**: <50ms per trace
- **Cost**: Free tier includes 5,000 traces/month
- **Data**: Traces are stored for 14 days (free tier)

For production use, consider:
- Enabling tracing only for specific sessions (debugging)
- Using sampling (e.g., 10% of sessions)
- Upgrading to paid tier for longer retention

## Disabling Tracing

To disable tracing, set in `.env`:

```bash
LANGCHAIN_TRACING_V2=false
```

Or remove the environment variable entirely. Restart the backend server.

## Troubleshooting

### Traces Not Appearing

1. **Check environment variables:**
   ```bash
   echo $LANGCHAIN_TRACING_V2
   echo $LANGCHAIN_API_KEY
   echo $LANGCHAIN_PROJECT
   ```

2. **Verify API key:**
   - Ensure key is valid in LangSmith dashboard
   - Check for typos in `.env` file

3. **Check logs:**
   Look for `langsmith_tracing_enabled` message on startup

### Connection Errors

If you see connection errors to LangSmith:
- Check internet connectivity
- Verify firewall settings
- Try using a different network

The application will continue to work even if LangSmith is unreachable - tracing failures are non-blocking.

## Advanced Usage

### Custom Project Names Per Environment

```bash
# Development
LANGCHAIN_PROJECT=oxytec-feasibility-dev

# Staging
LANGCHAIN_PROJECT=oxytec-feasibility-staging

# Production
LANGCHAIN_PROJECT=oxytec-feasibility-prod
```

### Filtering Traces

Use LangSmith's filter features:
- Filter by session ID
- Filter by agent type
- Filter by execution time
- Filter by error status

### Exporting Data

LangSmith allows exporting:
- Individual traces (JSON)
- Aggregate metrics (CSV)
- Custom dashboards

## Integration with Database Logging

This project also logs to PostgreSQL:
- `session_logs`: High-level session events
- `agent_outputs`: Agent-specific outputs

LangSmith complements this by providing:
- Visual trace viewer
- LLM-specific insights
- Cross-session analytics
- Prompt optimization tools

Use both systems together for comprehensive observability.

## Support

For LangSmith-specific issues:
- Documentation: https://docs.smith.langchain.com/
- Support: support@langchain.com

For integration issues with this project:
- Check application logs in `backend/backend.log`
- Review database logs in `session_logs` table
- Contact Oxytec development team

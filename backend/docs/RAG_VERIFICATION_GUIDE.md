# RAG System Verification Guide

**Date**: 2025-10-21
**Purpose**: Verify that subagents successfully use the `oxytec_knowledge_search` tool to retrieve Oxytec technology information

## Changes Implemented

### 1. Model Selection Fix (CRITICAL)
**File**: `backend/app/agents/nodes/subagent.py` (Lines 288-322)

**Problem**: Subagents were using OpenAI GPT-5-nano by default, which cannot use Claude-format tool definitions.

**Solution**: Always use Claude Haiku when tools are detected:
```python
if tools:
    # ALWAYS use Claude for tool calling - tools are in Claude/Anthropic format
    result = await llm_service.execute_with_tools(
        prompt=prompt,
        tools=tools,
        max_iterations=5,
        system_prompt=system_prompt,
        temperature=settings.subagent_temperature,
        model="claude-3-haiku-20240307"  # Fast, cost-effective
    )
```

### 2. Enhanced Logging (VISIBILITY)
**File**: `backend/app/agents/nodes/subagent.py` (Lines 199-233)

**Added**:
- Tool extraction validation logging
- Tool retrieval confirmation logging
- Critical alert if technology screening agent missing RAG tool

**Key Log Events**:
```
tools_extracted_from_task
tools_retrieved
technology_screening_missing_rag_tool (ERROR if RAG missing)
subagent_using_claude_for_tools (when tools present)
subagent_using_openai_text_only (when no tools)
```

### 3. Robust Tool Extraction (RELIABILITY)
**File**: `backend/app/agents/nodes/subagent.py` (Lines 381-439)

**Improvements**:
- Support multiple tool line formats: "Tools needed:" or "Tools:"
- Flexible tool name matching (handles variations)
- Better error handling with warnings for unparseable lines
- Logging at each decision point

### 4. Strengthened Planner Prompt (ROOT CAUSE)
**File**: `backend/app/agents/nodes/planner.py` (Lines 190-260)

**Added**:
- Explicit technology selection mandate
- Tool specification requirements with examples
- Critical rules about exact formatting
- Validation checklist

**Required Format**:
```
Tools needed: oxytec_knowledge_search
```

## Verification Steps

### Before Testing
1. ✅ Backend reloaded successfully (PID: 16675)
2. ✅ Frontend running (http://localhost:3000)
3. ✅ All changes verified in codebase

### During Test Session

#### Step 1: Monitor Log Stream
```bash
# In separate terminal, monitor for RAG activity
tail -f /tmp/backend.log | grep -i "oxytec_knowledge\|tool_execution\|subagent_using"
```

#### Step 2: Upload Test Document
1. Navigate to http://localhost:3000
2. Upload a customer inquiry document with VOC requirements
3. Start processing

#### Step 3: Watch for Success Indicators

**Expected Log Sequence**:
```
1. planner_completed_validated (num_subagents >= 3)
2. subagents_execution_started (parallel=true)
3. tools_extracted_from_task (tool_names contains "oxytec_knowledge_search")
4. tools_retrieved (retrieved_tools contains "oxytec_knowledge_search")
5. subagent_using_claude_for_tools (model: claude-3-haiku-20240307)
6. tool_execution_started (tool: oxytec_knowledge_search, query: "...")
7. tool_execution_completed (tool: oxytec_knowledge_search, results_count: X)
8. subagents_execution_completed (successful > 0)
```

### Success Criteria

#### ✅ RAG System Working If You See:
- [ ] `tools_extracted_from_task` with `oxytec_knowledge_search` in tool_names
- [ ] `subagent_using_claude_for_tools` (not `subagent_using_openai_text_only`)
- [ ] `tool_execution_started` with tool: "oxytec_knowledge_search"
- [ ] `tool_execution_completed` with results_count > 0
- [ ] Technology screening subagent result contains specific Oxytec technology names (NTP, UV/ozone, hybrid systems)

#### ⚠️ Warning Signs:
- `tools_line_found_but_unparseable` - Planner not following format
- `no_tools_line_in_task` - Planner omitted tool specification
- `technology_screening_missing_rag_tool` (ERROR) - Critical failure

#### ❌ Failure Indicators:
- Only seeing `subagent_using_openai_text_only` (tools not detected)
- Zero `tool_execution_started` events
- Technology screening result is generic/vague (no specific Oxytec products)

## Quick Verification Commands

```bash
# Count RAG tool invocations
grep -c "tool_execution_started.*oxytec_knowledge" /tmp/backend.log

# Show all technology screening agents
grep "technology" /tmp/backend.log | grep -i "subagent\|screening"

# Show model selection decisions
grep "subagent_using_" /tmp/backend.log

# Show tool extraction details
grep "tools_extracted_from_task" /tmp/backend.log | tail -10
```

## Expected Outcome

After a successful test run, you should see:
1. **Planner** creates "Technology Screening" subagent with `oxytec_knowledge_search` tool
2. **Subagent executor** detects tools and switches to Claude Haiku
3. **Tool executor** invokes RAG search with customer pollutant query
4. **RAG service** returns relevant Oxytec technology knowledge
5. **Subagent result** contains specific technology recommendations based on RAG data

## Troubleshooting

### If tools still not being used:

1. **Check planner output**:
   ```bash
   grep "planner_plan" /tmp/backend.log | tail -1 | jq '.plan.subagents[0]'
   ```
   Verify task description includes "Tools needed: oxytec_knowledge_search"

2. **Check tool extraction**:
   ```bash
   grep "tools_extracted_from_task" /tmp/backend.log | tail -5
   ```
   Should show non-empty tool_names list

3. **Check model selection**:
   ```bash
   grep "subagent_using_" /tmp/backend.log | tail -10
   ```
   Should see `subagent_using_claude_for_tools` for technology agents

### If RAG queries return no results:

1. Check technology_embeddings table has data:
   ```sql
   SELECT COUNT(*) FROM technology_embeddings;
   -- Should return 95
   ```

2. Check vector index exists:
   ```sql
   SELECT indexname FROM pg_indexes WHERE tablename = 'technology_embeddings';
   -- Should show 'technology_embeddings_embedding_idx'
   ```

## Next Steps After Verification

If RAG system working:
- ✅ Mark issue as resolved
- Document successful test session ID
- Monitor for consistent behavior across multiple runs

If still not working:
- Capture full session logs
- Check LangSmith trace (if enabled)
- Investigate specific failure point (planner, extraction, or execution)

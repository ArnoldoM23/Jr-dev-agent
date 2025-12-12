# 📋 Project Plan: Synthetic Memory Enhancements

## 🎯 Goal
Enhance the Synthetic Memory system to capture richer context about development sessions, specifically tracking what changes were required and what was actually implemented, ensuring this data is stored in the user's project workspace.

## ✅ Completed Tasks

### 1. Data Model & Storage Updates
- [X] Add `change_required` field to `FinalizeSessionArgs` (MCP Protocol)
- [X] Update `summary.json` schema to include:
    - `change_required` (Task summary)
    - `changes_made` (Implementation summary)
    - `pr_url` (Pull Request Link)
- [X] Update `agent_run.json` to store `full_prompt` for historical context

### 2. Architecture Refactoring (Agent-Driven)
- [X] **Design Decision**: Move summary generation from Server to Agent (Cursor/LLM) to avoid server-side OpenAI API dependencies.
- [X] Update Prompt Templates (`PromptBuilder`) to instruct the agent to:
    - Generate `change_required` summary based on the ticket.
    - Generate `changes_made` summary based on its work.
    - Pass both to `finalize_session`.
- [X] Remove legacy `generate_task_summary` method from `PromptBuilder`.

### 3. Session & Memory Location Fixes
- [X] **Bug Fix**: Fix session ID mismatch in `prepare_agent_task` (was creating phantom IDs).
- [X] Store `project_root` in session metadata.
- [X] Update `finalize_session` to retrieve `project_root` and initialize `SyntheticMemory` in the **correct user directory** (e.g., `ce-cartxo/syntheticMemory`) instead of the server root.

### 4. Tooling Updates
- [X] Update `finalize_session` tool signature to accept new summary fields.
- [X] Add fallback logic: Use `feedback` as `changes_made` if the explicit field is missing.
- [X] Update `demo_mcp_workflow.py` to use correct session ID propagation.

### 5. Verification & Testing
- [X] Create `tests/e2e/test_mcp_full_flow.py`
    - [X] Test Happy Path (Full API flow)
    - [X] Test Fallback Scenarios (Missing fields)
    - [X] Test Custom Project Root (Verify memory location)
- [X] Verify manually with Demo script.

## 🔜 Next Steps
- [ ] Monitor PESS scores with new summaries to validate context improvement.
- [ ] Consider exposing summaries in the `prepare_agent_task` output for developer review.

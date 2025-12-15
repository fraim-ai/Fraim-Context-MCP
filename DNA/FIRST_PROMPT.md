# First Prompt for Cursor

Copy and paste this prompt into Cursor after adding the DNA folder to your project:

---

## The Prompt

```
I've added a DNA folder to this project containing the complete specification for Fraim Context MCP v5.1 — a semantic search MCP server for project documentation.

Please:

1. **Read these files in order:**
   - DNA/.cursorrules (your constraints — MEMORIZE the critical constraints section)
   - DNA/MANIFEST.md (project navigation)
   - DNA/DEVELOPMENT_PLAN.md (TDD stages and current progress)
   - DNA/specs/ARCHITECTURE.md (system design)
   - DNA/specs/CONTRACTS.md (API/DB schemas)
   - DNA/specs/DEPENDENCIES.md (pinned versions)

2. **Then tell me:**
   - What is this project building?
   - What stage are we at in DEVELOPMENT_PLAN.md?
   - What are the next 3 specific tasks to complete?
   - What files/directories need to be created first?

3. **Important constraints:**
   - All specs in DNA/specs/ are READ-ONLY — do not modify them
   - We use TDD: write tests FIRST, then implementation
   - All secrets come from Doppler (never create .env files)
   - LLM access is via Pydantic AI Gateway (not direct provider calls)

4. **To get started, I need you to:**
   - Copy DNA/.cursorrules to the project root as .cursorrules
   - Copy DNA/pyproject.toml to the project root
   - Create the initial directory structure (src/fraim_mcp/, tests/)
   - Create Stage 0 test files

Let's begin!
```

---

## What Happens Next

After you send this prompt, Cursor should:

1. ✅ Read all the DNA files to understand the project
2. ✅ Confirm it's at Stage 0 (Environment Setup)
3. ✅ List the first tasks (Doppler setup, secrets verification)
4. ✅ Create the project structure and initial test files
5. ✅ Start writing Stage 0 tests for:
   - Doppler CLI availability
   - Required secrets present
   - PostgreSQL connectivity
   - Redis connectivity
   - LLM API reachability

## Follow-Up Prompts

After the initial setup, use these prompts:

**To check progress:**
```
What tasks are complete in DEVELOPMENT_PLAN.md? What's next?
```

**To run tests:**
```
Run the Stage 0 tests and tell me what passed/failed.
```

**To proceed to next stage:**
```
All Stage 0 tests pass. Update DEVELOPMENT_PLAN.md and start Stage 1.
```

**To get help:**
```
I'm stuck on [specific issue]. Check DNA/specs/ for the relevant contract and help me fix it.
```

## Slash Commands

Once .cursorrules is in place, you can use these shortcuts:

| Command | What It Does |
|---------|--------------|
| `/test-all` | Run entire test suite |
| `/test-unit` | Run Stage 0-1 tests only |
| `/sync-deps` | Install dependencies with uv |
| `/verify-env` | Check environment setup |
| `/init-db` | Initialize PostgreSQL schema |
| `/launch-server` | Start the HTTP server |
| `/launch-ui` | Start Streamlit test UI |

---

**Ready? Copy the prompt above and send it to Cursor!**

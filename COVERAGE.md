# C3 requirement coverage

No numerical C3 rubric was supplied; no point allocation or grade is invented.

| Requirement | Identifiable evidence | Verification |
|---|---|---|
| 1. Fictional name, mission, services, team, value proposition | me/about_business.pdf, both summary filenames; solution section 1 | One-page PDF visually inspected; source loading checked |
| 2. Separate persona and instructions | agent.py PERSONA and INSTRUCTIONS; notebook | Explicit independent blocks |
| 3. Router before generation with three intents | route_intent, ROUTE_GUIDANCE; router tests and live traces | General, lead, feedback/unknown exercised; multi-turn lead verified |
| 4. Required interest/feedback functions | ToolContext, native_tools, dispatch; genuine tool observations | Actual records contain supplied fields and feedback/question text |
| 4. MCP-style tool documentation | tool_schemas.json; common.py; solution tool table | Name/input/output documented; no MCP-server claim |
| 5. Prompt uses PDF and summary | BusinessKnowledge.load and prompt_context; PDF-only policy test | Both real files read, not decorative attachments |
| 6. History, native tool calls, returned observations, model reply | BusinessAgent.run; application tests; live checks and UI traces | Genuine model/tool round trips preserved |
| 7. Gradio ChatInterface | app.py; evidence/ui_verification.json and ui_demo interaction records | Six real UI turns, including logging refusal |
| Successful reproducible execution | evidence/verification.json; notebook_execution.json; live_results_index.json | Local application tests, fresh local Jupyter run, genuine Gemini and browser checks |
| Secret configuration and exclusions | .env.example; .gitignore; package_audit.json and archive scan | Real key excluded; no key in source, outputs, video, or ZIP |
| Required demonstration video | demo/C3_demonstration.webm; demo/README.md | Actual automated browser footage, not fabricated outputs |
| Required GitHub repository | Complete repository-ready files and video | Course repository destination/publication remains pending |
| Bonus reflection | Actual draft/revision events in live/UI traces | Executed; unchanged drafts are reported honestly |
| Bonus Hugging Face deployment | Prepared README metadata/setup | Not deployed; no bonus completion claim |

The local solution is complete. The required external repository remains a separate unresolved submission item. No instructor submission has been made. Counts, versions, and actual execution scopes are recorded in the evidence files.

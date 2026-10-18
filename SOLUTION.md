# C3 solution

Habib Shouman | EECE 503P/798S: Agentic Systems

## Requirements and interpretation

The three-page C3 brief asks for a fictional business, a PDF and summary, separately labeled persona and instructions, a three-intent router, two model-called logging functions, short-term chat history, a Gemini/OpenAI chatbot, and Gradio. Submission also requires a GitHub repository and demonstration video. Reflection and Hugging Face deployment are bonuses. No point weights are given.

The brief uses both `summary.txt` and `business_summary.txt`; identical files are supplied. The project tree places them in `me/`, which this implementation follows. The old `openai.ChatCompletion` SDK spelling is implemented using the maintained `client.chat.completions.create` API. Gemini uses Google's documented compatible endpoint, with the same native tool-call message contract. This is an API-version adaptation, not a change to the required model/tool behavior. See `SOURCES.md`.

## 1. Create the business identity

CircuitBridge Learning teaches practical AI, Python, and electronics through small workshops. Its customers are adult beginners, students, and small teams. The mission, fictional team, services, prerequisites, and unique value proposition appear in both the summary and profile. The PDF additionally specifies prices, session counts, hours, group discounts, rescheduling, and explicit unknowns.

The profile is generated from `business_data.json`; the quote tool used in the C4 extension reads the same catalog. C3 actually reads both the TXT and PDF using `BusinessKnowledge.load`. A test checks a PDF-only fact, the 48-hour rescheduling notice, so the PDF is not merely a decorative attachment.

## 2. Define persona and instructions

`PERSONA` describes Mira's identity, tone, vocabulary, and audience. `INSTRUCTIONS` separately specifies grounding, unknown-question handling, lead fields, save authorization, receipts, and error handling. A friendly style cannot override a refusal to share an email, an unknown fact, or a failed save.

## 3. Add the router

The deterministic router returns exactly one of `general`, `lead`, or `feedback_unknown` before generation. Feedback keywords take precedence; an interest/registration request or email indicates a lead. Retained dialogue keeps the lead context while the customer supplies their name, email, and notes across separate turns; an explicit cancellation or save receipt closes that context. Otherwise the default is a general question. Each result selects a different handling instruction and permitted tool list. The general route still exposes `record_feedback`, since whether a question is answerable may become apparent only during generation.

This intentionally simple heuristic is a routing baseline. Mixed intent, paraphrases, and long conversational dependencies can be misclassified. Keyword examples demonstrate its operation; they do not estimate real-user classification accuracy.

## 4. Create the tools

| Tool | Required inputs | Success output | Failure output |
|---|---|---|---|
| `record_customer_interest(email, name, message)` | User-supplied email and name; verbatim interest notes | `ok=true`, `status=saved` or `already_recorded`, `record_id` | `ok=false`, `error` |
| `record_feedback(question)` | Verbatim feedback or unanswered customer question | Same receipt fields | Same error form |

These names identify bound session-specific callables in `ToolContext`; they are the actual names exposed to the model. `TOOL_DEFINITIONS` documents each name, description, input JSON schema, and output contract in an MCP-style format. This is not a claim to implement an MCP server. `native_tools` adapts those definitions to the provider's function schema.

Tools append genuine JSONL records and print a receipt without printing the customer's email. A per-turn content key deduplicates identical retries. Successful tool observations contain record IDs; exceptions and storage failures return error observations. No arbitrary model text is evaluated as Python. File logging is single-process and thread-safe; it is not a multi-process transactional database.

Lead writes additionally require a valid supplied email, a supplied name, verbatim notes, and explicit saving/contact permission. Logging refusals persist through the retained conversation until an explicit new logging request. When logging is declined, the application also suppresses persistent turn traces. The provider still receives the text necessary to answer; declining local logging is not an offline or provider-retention guarantee.

## 5. Assemble the system prompt

The system prompt contains `PERSONA`, `INSTRUCTIONS`, the extracted summary, the extracted PDF, and the selected route instruction. Business facts are treated as the source of truth. Unknown tax treatment, accreditation, dates, availability, and refund policy must not be filled in from general model knowledge.

## 6. Agent interaction

For each turn, the application sanitizes incoming roles and retains at most eight complete user/assistant pairs within a 16,000-character history budget. It appends the new user text and calls the actual model with native tool schemas. When native `tool_calls` appear, the application parses their JSON arguments, validates the tool whitelist and argument shape, executes the corresponding callable, and appends a tool observation with the matching `tool_call_id`. The model sees that observation on the next call. Plain generated text becomes the draft reply.

At most five main-loop model calls and six tool calls are permitted per turn. Each provider call has a 30-second timeout and one SDK retry; this is a request-level timeout, not a strict total wall-clock guarantee. Input is limited to 6,000 characters. Complete pair eviction avoids orphaned turns but can remove earlier lead details; the model must request them again. Character bounds are conservative application limits, not exact token counting.

The environment is a conversation plus the business records. Observations include user text, business facts, and tool results. Actions are native logging requests. Short-term memory is bounded conversation history; persistent records are not exposed as a customer-search tool. The objective is helpful, grounded assistance with correctly recorded requests. The outer workflow is fixed, while the model chooses whether and how to act within it. This is a constrained tool-using conversational agent, not an autonomous sales system or a multi-agent system.

## 7. Gradio interface

`app.py` constructs a Gradio `ChatInterface` around the actual agent. Gradio supplies the current message and session history. The backend does not hold a shared conversation history between users. A hashed UI session identifier separates record scopes, and requests are queued with concurrency one. Feedback/lead logging behavior is described in the interface. Gradio 6.30.0 was launched and exercised in an isolated Chrome browser. Six live turns demonstrate general advice, multi-turn lead collection, feedback, an unknown question, and refusal to log; see `evidence/ui_verification.json` and the actual demonstration video.

## 8. Optional reflection

The enabled reflection pass supplies the conversation, tool receipts, and draft to the model with tools disabled. It checks instruction compliance and returns the revised customer reply. The trace records both draft and revision, even if they match. Reflection failures preserve the draft and record an error type. A conservative application receipt check blocks some unsupported save claims; it is not a complete semantic detector.

Reflection adds at most one model invocation. A self-check does not prove factual correctness, and scripted reflection tests do not show that a live model reliably corrects itself. No such reliability claim is made.

## Verification and remaining work

`evidence/verification.json` and `evidence/test_output.txt` contain actual local application results. Native tool round trips, persisted customer values, malformed/unknown tool requests, storage failure, input/history limits, duplicate writes, reflection logging, and receipt handling are tested. The installed SDK is exercised through an in-memory HTTP transport. These application tests use controlled protocol inputs. Separate genuine Gemini checks and browser interactions are recorded in `evidence/live_results_index.json` and `evidence/ui_verification.json`. The actual video is `demo/C3_demonstration.webm`. Code, notebook, PDF, evidence, and video are published at https://github.com/HabibShouman/C3-Agentic-Systems; every file blob in the first full publication was verified. The optional Hugging Face bonus remains incomplete after two genuine HTTP 402 creation failures.


## Actual live verification

Four live API cases passed. The real browser demonstration then verified six turns, including an incomplete lead followed by supplied name/email/notes, exact persisted values, two feedback records, and no new record or trace when logging was declined. Actual reflection logs contain both draft and revision; an unchanged reply is not represented as an improvement. These small checks establish observed behavior on these cases, not general LLM reliability. An initial live reply promised future contact; the instructions were tightened to state that this prototype cannot send messages or promise staff follow-up, and the final live/UI evidence uses that revised source.

The source-text validator checks normalized substring membership. Prompts request verbatim values, but the check is not semantic verification or exact whole-message equality. History eviction can remove earlier details or a logging preference; the guarantee is limited to the retained dialogue.

The browser run stored 'Please add evening sessions.' without the input's routing label 'Feedback:'. The original full-string comparison failed and remains visible in ui_verification.json; an explicit content review confirms that the feedback body is unchanged. Raw responses and records are unchanged. The original video is preserved; the delivered copy only changes encoding and frame rate, as documented below. A separate semantic limitation remains: the lead confirmation says the team cannot confirm availability/reservations, whereas the profile limits the assistant. The correct claim is that this assistant cannot confirm availability or book. The receipt checks validate persistence, not every generated statement, and reflection did not catch that overstatement.

## 9. Publication and optional hosting

The required GitHub repository includes the complete source, executed notebook, business assets, actual video, and recorded evidence. `evidence/repository.json` identifies the first full publication commit and records verification of all 79 Git blob hashes. The delivered videos are compact VP8 derivatives: no sequence cuts, speed changes, or model-response replacement were made. Frame-rate conversion adds less than 0.4 seconds of final-frame padding; original/derivative hashes and playback checks are preserved.

The Hugging Face write token authenticated as the intended account. CPU Basic creation was rejected with HTTP 402 because PRO is required. The documented free ZeroGPU option was also rejected for current account eligibility. No Space was created or live app tested; this bonus is not claimed. The complete `tools/deploy_space.py` helper uses official APIs, configures the Gemini key as a secret and the public bind address, and uploads only runtime files. It can be rerun when hosting eligibility is available. Local JSONL storage would remain ephemeral on a default Space.

# C3 defense notes

**Why is this more than a chatbot?** The model can issue structured native actions that change local business records. The application validates and executes them, then returns observations. A response saying “saved” alone does not create a record.

**Why separate persona and instructions?** Persona governs who Mira is and how she speaks. Instructions govern grounding, fields, consent, and tool use. A friendly tone cannot justify inventing a price or ignoring a failed write.

**What does the router do?** It chooses a primary handling path before the model responds. It is a transparent heuristic baseline. Unknown questions can start in the general route and subsequently call the feedback tool.

**How is the PDF actually used?** Text is extracted from it and passed alongside the summary. The rescheduling policy exists only in the PDF, and a test verifies its presence.

**Who executes the tool?** The model proposes a function name and JSON arguments. Python validates them and calls an allowlisted session-bound function. The model cannot invoke arbitrary Python through `eval`.

**What does a receipt prove?** It proves that the local logging function returned success for that action. It does not prove a human contacted the learner, that a booking exists, or that the model selected the correct action.

**What does the passing test suite prove?** On controlled inputs, the application routes, serializes, dispatches, persists, recovers, and terminates as checked. It does not establish live-model helpfulness, factual accuracy, UI operation, or general reliability.

**What are the main tradeoffs?** A simple router is inspectable but misses paraphrases. Full small-document context avoids retrieval misses but grows poorly with a large knowledge base. Bounded history controls input size but can forget details. Reflection can revise unsupported wording but adds latency and can itself make errors.

**What should be shown live?** A general question, a lead completed across multiple turns, exact stored fields, feedback, an unknown business question, a declined logging request, and draft/revision traces. Keep actual API keys off screen.


**How should the live results be defended?** Show the actual native call, returned observation, stored customer values, and rendered reply. These small demonstrations establish behavior on these cases. The saved receipt does not establish that every sentence is grounded; the UI lead reply overstates the human team's limitations, as explained in SOLUTION.md. Reflection did not catch that statement.

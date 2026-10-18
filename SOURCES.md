# Sources and implementation adaptations

Primary specification: supplied **C3 - Introduction to Agents**, EECE 503P/798S: Agentic Systems, all three pages. No separate lecture notes or starter files were provided.

Official documentation consulted on 18 October 2026:

- Google, [OpenAI compatibility](https://ai.google.dev/gemini-api/docs/openai): Gemini's compatible base URL and native tool schema/message examples. This supports using the maintained OpenAI client to call Gemini.
- OpenAI, [official Python SDK](https://github.com/openai/openai-python): current client construction and Chat Completions usage. The legacy spelling in the assignment is adapted to `client.chat.completions.create`.
- Gradio, [ChatInterface source and docstrings](https://github.com/gradio-app/gradio/blob/main/gradio/chat_interface.py): callback contract, messages-style history, additional inputs, and examples. No obsolete `type='messages'` constructor parameter is used.
- Google, [model catalog](https://ai.google.dev/gemini-api/docs/models): the configurable Gemini model identifier. The configured model was available and used in the genuine recorded runs; later account/model access may differ.

The installed local SDK was also inspected and tested using a synthetic in-memory HTTP transport. The external references support API structure; they do not establish that this app ran successfully against a real provider or a hosted UI. The fictional business content is original scenario data, not a claim about a real organization.


- Google, [Gemini rate limits](https://ai.google.dev/gemini-api/docs/rate-limits): request/token/day limits apply per project and depend on the account. This informed local pacing after an actual smoke-run rate-limit error.
- Microsoft, [Playwright Python videos](https://playwright.dev/python/docs/videos): isolated browser-test recording saved after context closure; used for the actual demonstration footage.
- Hugging Face, [Spaces configuration reference](https://huggingface.co/docs/hub/spaces-config-reference): README metadata for the prepared optional Gradio Space. No hosting is claimed.

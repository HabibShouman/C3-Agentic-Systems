"""Run with python app.py. Gradio and provider dependencies load only when needed."""
from pathlib import Path
import hashlib
import os
from common import ROOT, LiveBackend, BusinessKnowledge, JsonlStore, default_config
from agent import BusinessAgent


def build_demo():
    import gradio as gr
    knowledge = BusinessKnowledge.load()
    backend = LiveBackend()
    config = default_config()
    store = JsonlStore(Path(os.getenv("DATA_DIR", str(ROOT / "logs" / "records"))))
    agent = BusinessAgent(backend, knowledge, store, config=config, reflection=True)

    def respond(message, history, request: gr.Request):
        session = hashlib.sha256((request.session_hash or "local").encode()).hexdigest()[:20]
        return agent.run(message, history, session)["answer"]

    return gr.ChatInterface(fn=respond, title="CircuitBridge Learning | Mira",
        description="Fictional workshop concierge. Feedback and authorized contact details are logged locally. "
                    "Say 'do not log' to decline. This assistant cannot confirm a booking.",
        examples=["Which beginner workshops do you offer?",
                  "I am interested in Python Launchpad. Please contact me.",
                  "Feedback: I would like evening sessions.",
                  "Do you offer a government-accredited certificate?"],
        concurrency_limit=1)


if __name__ == "__main__":
    build_demo().launch(server_name=os.getenv("SERVER_NAME", "127.0.0.1"),
                        server_port=int(os.getenv("PORT", "7860")), share=False)

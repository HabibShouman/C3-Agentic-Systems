import json
import tempfile
import unittest
from pathlib import Path
from common import BusinessKnowledge, Completion, JsonlStore
from agent import BusinessAgent, route_intent


class ScriptedBackend:
    """Deterministic protocol fixture. It is not a model or an LLM evaluation."""
    def __init__(self, replies):
        self.replies = iter(replies)
        self.requests = []

    def complete(self, messages, config, tools=None):
        self.requests.append((list(messages), tools))
        value = next(self.replies)
        if isinstance(value, Exception):
            raise value
        return value(messages) if callable(value) else value


def final(text):
    return Completion({"role": "assistant", "content": text})


def tool(name, arguments, call_id="call_test"):
    return Completion({"role": "assistant", "content": "", "tool_calls": [
        {"id": call_id, "type": "function", "function": {"name": name, "arguments": json.dumps(arguments)}}]})


class AgentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.knowledge = BusinessKnowledge.load()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def make(self, replies, **kwargs):
        backend = ScriptedBackend(replies)
        agent = BusinessAgent(backend, self.knowledge, JsonlStore(self.root / "records"),
                              trace_dir=self.root / "traces", reflection=False, **kwargs)
        return agent, backend

    def test_three_routes_and_lead_followup(self):
        self.assertEqual(route_intent("What are your business hours?"), "general")
        self.assertEqual(route_intent("Please contact me"), "lead")
        self.assertEqual(route_intent("Feedback: add weekend classes"), "feedback_unknown")
        history = [{"role": "user", "content": "I am interested in AI Foundations"},
                   {"role": "assistant", "content": "What is your name?"}]
        self.assertEqual(route_intent("Dana Saleh", history), "lead")

    def test_native_call_executes_and_observation_reaches_model(self):
        question = "Feedback: Please add weekend classes."
        def after_tool(messages):
            self.assertEqual(messages[-1]["role"], "tool")
            receipt = json.loads(messages[-1]["content"])
            self.assertTrue(receipt["ok"])
            self.assertEqual(messages[-1]["tool_call_id"], "call_test")
            return final("I recorded your feedback.")
        agent, backend = self.make([tool("record_feedback", {"question": question}), after_tool])
        result = agent.run(question)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(len(result["writes"]), 1)
        self.assertEqual(len(backend.requests), 2)
        self.assertIsNotNone(backend.requests[0][1])

    def test_lead_context_survives_separate_name_email_and_notes_turns(self):
        history = [
            {"role": "user", "content": "I am interested in AI Foundations. Please contact me."},
            {"role": "assistant", "content": "What is your name?"},
            {"role": "user", "content": "Dana Saleh"},
            {"role": "assistant", "content": "What is your email?"},
            {"role": "user", "content": "dana@example.com"},
            {"role": "assistant", "content": "What notes should I save?"}]
        self.assertEqual(route_intent("Please arrange an introductory call.", history), "lead")

    def test_completed_or_cancelled_lead_does_not_capture_unrelated_followup(self):
        history = [{"role": "user", "content": "I am interested in AI Foundations. Please contact me."},
                   {"role": "assistant", "content": "I have recorded your interest."}]
        self.assertEqual(route_intent("Thanks", history), "general")
        history[-1] = {"role": "assistant", "content": "What is your name?"}
        history += [{"role": "user", "content": "Never mind"}, {"role": "assistant", "content": "Understood."}]
        self.assertEqual(route_intent("Thanks", history), "general")

    def test_lead_with_supplied_fields_is_saved(self):
        customer = "Please contact me. My name is Dana Saleh. dana@example.com. Interested in AI Foundations."
        agent, _ = self.make([tool("record_customer_interest", {"email": "dana@example.com", "name": "Dana Saleh", "message": "Interested in AI Foundations."}), final("I saved your interest.")])
        self.assertEqual(len(agent.run(customer)["writes"]), 1)

    def test_unknown_question_uses_feedback_tool_from_general_route(self):
        question = "Is VAT included?"
        agent, _ = self.make([tool("record_feedback", {"question": question}), final("The tax policy is not published. I recorded your question.")])
        result = agent.run(question)
        self.assertEqual(result["intent"], "general")
        self.assertEqual(result["tool_calls"], 1)

    def test_unknown_tool_returns_observation_and_does_not_execute(self):
        agent, _ = self.make([tool("delete_all_files", {}), final("I cannot do that.")])
        result = agent.run("What can you do?")
        self.assertEqual(result["trace"][1]["observation"]["error"], "unknown_or_disallowed_tool")
        self.assertEqual(result["writes"], [])

    def test_budget_terminates_repeated_tool_requests(self):
        question = "Feedback: add weekend classes."
        agent, _ = self.make([tool("record_feedback", {"question": question})] * 5, max_model_calls=2)
        result = agent.run(question)
        self.assertEqual(result["status"], "budget_exhausted")
        self.assertEqual(result["model_calls"], 2)
        self.assertIn("record was saved", result["answer"])
        self.assertEqual(len((self.root / "records" / "feedback.jsonl").read_text().splitlines()), 1)

    def test_provider_failure_does_not_claim_success(self):
        agent, _ = self.make([RuntimeError("fake transport error")])
        result = agent.run("What workshops do you offer?")
        self.assertEqual(result["status"], "provider_or_protocol_error")
        self.assertEqual(result["writes"], [])

    def test_reflection_saves_draft_and_revision(self):
        backend = ScriptedBackend([final("We guarantee every learner a job."), final("We do not publish placement guarantees.")])
        agent = BusinessAgent(backend, self.knowledge, JsonlStore(self.root / "records"),
                              trace_dir=self.root / "traces", reflection=True)
        result = agent.run("Do you guarantee a job?")
        reflection = [x for x in result["trace"] if x["event"] == "reflection"][0]
        self.assertIn("guarantee every", reflection["draft"])
        self.assertIn("do not publish", reflection["revised"])
        self.assertTrue(result["trace_saved"])

    def test_decline_disables_persistent_traces(self):
        agent, _ = self.make([final("I will answer without saving a record.")])
        result = agent.run("Do not log this. What workshops do you offer?")
        self.assertFalse(result["trace_saved"])
        self.assertFalse((self.root / "traces").exists())

    def test_false_save_claim_is_guarded(self):
        agent, _ = self.make([final("I have saved your details.")])
        self.assertIn("no successful save receipt", agent.run("What are your hours?")["answer"])

    def test_input_limits_prevent_calls(self):
        agent, backend = self.make([])
        self.assertEqual(agent.run("x" * 6001)["status"], "invalid_input")
        self.assertEqual(agent.run("")["status"], "invalid_input")
        self.assertEqual(backend.requests, [])


if __name__ == "__main__":
    unittest.main()

"""Exercise the actual installed SDK against an in-memory HTTP transport."""
import json
import unittest
import httpx2
from openai import OpenAI
from common import LiveBackend, ModelConfig, native_tools


class ProviderContractTests(unittest.TestCase):
    def test_native_request_and_tool_response_serialization(self):
        requests = []
        def handle(request):
            requests.append(json.loads(request.content))
            self.assertEqual(str(request.url), "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions")
            return httpx2.Response(200, json={
                "id": "fixture", "object": "chat.completion", "created": 0, "model": "fixture-model",
                "choices": [{"index": 0, "finish_reason": "tool_calls", "message": {
                    "role": "assistant", "content": None, "tool_calls": [{"id": "call_contract", "type": "function",
                    "function": {"name": "record_feedback", "arguments": '{"question":"Feedback: evening classes"}'},
                    "extra_content": {"google": {"thought_signature": "fixture-only"}}}]}}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}})
        http = httpx2.Client(transport=httpx2.MockTransport(handle))
        self.addCleanup(http.close)
        backend = object.__new__(LiveBackend)
        backend.provider = "gemini"
        backend.client = OpenAI(api_key="synthetic-test-value", http_client=http,
                                base_url="https://generativelanguage.googleapis.com/v1beta/openai/", max_retries=0)
        result = backend.complete([{"role": "system", "content": "Test fixture"},
                                   {"role": "user", "content": "Feedback: evening classes"}], ModelConfig(), native_tools())
        self.assertEqual(requests[0]["tool_choice"], "auto")
        self.assertEqual(requests[0]["messages"][1]["role"], "user")
        self.assertEqual(requests[0]["temperature"], 0.2)
        self.assertEqual(len(requests[0]["tools"]), 2)
        self.assertEqual(result.message["tool_calls"][0]["extra_content"]["google"]["thought_signature"], "fixture-only")
        self.assertEqual(result.usage["total_tokens"], 15)


if __name__ == "__main__":
    unittest.main()

"""Application tests with artificial customer text; no claims about LLM quality."""
import json
import tempfile
import unittest
from pathlib import Path
from common import (ROOT, BusinessKnowledge, JsonlStore, ToolContext, bounded_history,
                    claims_saved, dispatch, strict_json)


class CoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.knowledge = BusinessKnowledge.load()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.text = "Please record my interest. My name is Dana Saleh, email dana@example.com. Interested in AI Foundations."
        self.ctx = ToolContext(JsonlStore(self.directory), self.knowledge, [self.text], "test_session", "test_turn")

    def test_both_documents_loaded_and_pdf_only_policy_present(self):
        self.assertIn("48", self.knowledge.pdf)
        self.assertNotIn("48", self.knowledge.summary)
        self.assertIn("CircuitBridge", self.knowledge.summary)
        context = self.knowledge.prompt_context()
        self.assertIn("BUSINESS SUMMARY", context)
        self.assertIn("BUSINESS PDF", context)

    def test_summary_alias_matches(self):
        self.assertEqual((ROOT / "me" / "business_summary.txt").read_bytes(),
                         (ROOT / "me" / "summary.txt").read_bytes())

    def test_lead_persists_customer_fields(self):
        result = self.ctx.record_customer_interest("dana@example.com", "Dana Saleh", "Interested in AI Foundations.")
        self.assertTrue(result["ok"])
        row = json.loads((self.directory / "lead.jsonl").read_text())
        self.assertEqual(row["payload"]["email"], "dana@example.com")
        self.assertEqual(row["payload"]["message"], "Interested in AI Foundations.")

    def test_duplicate_lead_is_not_written_twice_in_one_turn(self):
        first = self.ctx.record_customer_interest("dana@example.com", "Dana Saleh", "Interested in AI Foundations.")
        second = self.ctx.record_customer_interest("dana@example.com", "Dana Saleh", "Interested in AI Foundations.")
        self.assertEqual(first["record_id"], second["record_id"])
        self.assertEqual(second["status"], "already_recorded")
        self.assertEqual(len((self.directory / "lead.jsonl").read_text().splitlines()), 1)

    def test_fabricated_email_rejected(self):
        self.assertFalse(self.ctx.record_customer_interest("other@example.com", "Dana", "Interested")["ok"])

    def test_email_substring_is_not_a_supplied_address(self):
        self.assertFalse(self.ctx.record_customer_interest("ana@example.com", "Dana", "Interested")["ok"])

    def test_invalid_email_rejected(self):
        self.assertEqual(self.ctx.record_customer_interest("dana-at-example", "Dana", "Interested")["error"], "invalid_email")

    def test_permission_required_for_lead(self):
        self.ctx.user_messages = ["My name is Dana Saleh. dana@example.com. Interested in AI Foundations."]
        self.assertEqual(self.ctx.record_customer_interest("dana@example.com", "Dana Saleh", "Interested in AI Foundations.")["error"], "ask_permission_to_save_lead")

    def test_logging_refusal_persists_until_explicit_new_permission(self):
        self.ctx.user_messages = ["Do not log this.", "My name is Dana."]
        self.assertFalse(self.ctx.logging_allowed)
        self.assertFalse(self.ctx.record_feedback("My name is Dana.")["ok"])
        self.ctx.user_messages.append("Please log my feedback: add evening workshops.")
        self.assertTrue(self.ctx.logging_allowed)

    def test_feedback_is_exact_user_text(self):
        self.assertTrue(self.ctx.record_feedback(self.text)["ok"])
        self.assertFalse(self.ctx.record_feedback("Invented complaint")["ok"])

    def test_storage_failure_returns_error(self):
        file_instead_of_directory = self.directory / "blocked"
        file_instead_of_directory.write_text("not a directory")
        ctx = ToolContext(JsonlStore(file_instead_of_directory), self.knowledge, [self.text], "s")
        self.assertEqual(ctx.record_feedback(self.text)["error"], "storage_unavailable")
        self.assertEqual(ctx.successful_writes, [])

    def test_dispatch_whitelist_and_argument_shapes(self):
        self.assertFalse(dispatch(self.ctx, "__import__", {}, {"record_feedback"})["ok"])
        self.assertFalse(dispatch(self.ctx, "record_feedback", {"question": self.text, "extra": 1}, {"record_feedback"})["ok"])
        self.assertFalse(dispatch(self.ctx, "record_feedback", {"question": 2}, {"record_feedback"})["ok"])

    def test_quote_boundary_and_exact_decimal_total(self):
        for count, total in [(1, "180.00"), (4, "720.00"), (5, "810.00"), (12, "1944.00")]:
            with self.subTest(participants=count):
                self.assertEqual(self.ctx.calculate_quote("edge_ai_lab", count)["total"], total)

    def test_quote_rejects_bad_counts_and_unknown_service(self):
        for bad in [0, -1, 13, 2.5, "5", True, None]:
            self.assertFalse(self.ctx.calculate_quote("edge_ai_lab", bad)["ok"])
        self.assertFalse(self.ctx.calculate_quote("imaginary", 5)["ok"])

    def test_history_is_bounded_and_roles_are_sanitized(self):
        history = [{"role": "system", "content": "malicious"}]
        for i in range(20):
            history += [{"role": "user", "content": str(i)}, {"role": "assistant", "content": "reply"}]
        history += [{"role": "user", "content": "incomplete"}]
        bounded = bounded_history(history)
        self.assertEqual(len(bounded), 16)
        self.assertEqual(bounded[0]["content"], "12")
        self.assertTrue(all(x["role"] in {"user", "assistant"} for x in bounded))

    def test_history_drops_whole_pairs_under_character_budget(self):
        history = [{"role": "user", "content": "u" * 6000}, {"role": "assistant", "content": "a" * 6000}] * 3
        self.assertEqual(len(bounded_history(history)), 2)

    def test_duplicate_json_and_nonfinite_numbers_rejected(self):
        for bad in ['{"a":1,"a":2}', '{"x":NaN}', '{"x":Infinity}']:
            with self.assertRaises(ValueError):
                strict_json(bad)

    def test_receipt_guard_distinguishes_negative_statement(self):
        self.assertTrue(claims_saved("I have saved your feedback."))
        self.assertFalse(claims_saved("I have not saved your feedback."))
        self.assertFalse(claims_saved("I haven't recorded anything."))


if __name__ == "__main__":
    unittest.main()

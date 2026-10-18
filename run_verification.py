"""Run local application checks and record the actual result, without API access."""
import contextlib
import io
import json
import platform
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

ROOT = Path(__file__).resolve().parent


class EvidenceResult(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.outcomes = []

    def addSuccess(self, test):
        super().addSuccess(test)
        self.outcomes.append({"test": test.id(), "status": "passed"})

    def addFailure(self, test, error):
        super().addFailure(test, error)
        self.outcomes.append({"test": test.id(), "status": "failed"})

    def addError(self, test, error):
        super().addError(test, error)
        self.outcomes.append({"test": test.id(), "status": "error"})

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        self.outcomes.append({"test": test.id(), "status": "skipped", "reason": reason})


def main():
    # Keep test-created files inside this project, including in restricted Windows runtimes.
    temp_root = (ROOT / ".test_tmp").resolve()
    if not temp_root.is_relative_to(ROOT.resolve()):
        raise RuntimeError("Test directory escaped project root")
    temp_root.mkdir(exist_ok=True)
    tempfile.tempdir = str(temp_root)
    suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"))
    output, tool_output = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(tool_output):
        result = unittest.TextTestRunner(stream=output, verbosity=2, resultclass=EvidenceResult).run(suite)
    versions = {}
    for package in ("openai", "langgraph", "gradio", "pypdf", "nbformat", "nbclient"):
        try:
            versions[package] = version(package)
        except PackageNotFoundError:
            versions[package] = None
    if versions["pypdf"] is None:
        try:
            import pypdf
            versions["pypdf"] = pypdf.__version__ + " (module supplied via local test path)"
        except ImportError:
            pass
    evidence = {"mode": "LOCAL_APPLICATION_CHECKS_WITH_SCRIPTED_BACKENDS",
                "executed_utc": datetime.now(timezone.utc).isoformat(),
                "python": sys.version, "platform": platform.platform(), "package_versions": versions,
                "tests_run": result.testsRun, "failures": len(result.failures),
                "errors": len(result.errors), "skipped": len(result.skipped),
                "successful": result.wasSuccessful(), "checks": result.outcomes,
                "live_api_executed": False, "gradio_launched": False, "colab_executed": False,
                "note": "These checks establish application behavior on controlled protocol inputs, not live-model reliability or persona performance."}
    directory = ROOT / "evidence"
    directory.mkdir(exist_ok=True)
    (directory / "verification.json").write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    (directory / "test_output.txt").write_text(output.getvalue(), encoding="utf-8")
    print(output.getvalue())
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())

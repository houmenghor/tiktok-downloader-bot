import os
import sys
import time
import unittest

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from tests.test_models import TestCoreModels
from tests.test_ui import TestUIAndKeyboards
from tests.test_helpers import TestHelpers
from tests.test_bypass import TestBypassManager
from tests.test_handlers import TestHandlersIntegration
from tests.test_commands import TestCommandsIntegration
from tests.test_download_pipeline import TestDownloadPipelineQA


def run_qa_suite() -> bool:
    print("=" * 70)
    print("🚀 STARTING TIKTOK DOWNLOADER QA & TEST SUITE")
    print("=" * 70)

    suite = unittest.TestSuite()
    loader = unittest.TestLoader()

    suite.addTests(loader.loadTestsFromTestCase(TestCoreModels))
    suite.addTests(loader.loadTestsFromTestCase(TestUIAndKeyboards))
    suite.addTests(loader.loadTestsFromTestCase(TestHelpers))
    suite.addTests(loader.loadTestsFromTestCase(TestBypassManager))
    suite.addTests(loader.loadTestsFromTestCase(TestHandlersIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestCommandsIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestDownloadPipelineQA))

    start_time = time.time()
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    elapsed = time.time() - start_time

    print("=" * 70)
    print("📊 QA TEST SUMMARY REPORT")
    print(f"⏱️  Duration: {elapsed:.2f} seconds")
    print(f"🧪 Total Tests Run: {result.testsRun}")
    print(f"✅ Passed: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"❌ Failures: {len(result.failures)}")
    print(f"💥 Errors: {len(result.errors)}")
    print("=" * 70)

    if result.wasSuccessful():
        print("🎉 ALL TESTS PASSED! Quality assurance verified.")
        return True
    else:
        print("⚠️ SOME TESTS FAILED. Review output above.")
        return False


if __name__ == "__main__":
    success = run_qa_suite()
    sys.exit(0 if success else 1)

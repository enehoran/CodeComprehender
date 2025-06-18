import os
import sys
import unittest

# Add the parent directory to sys.path to import the modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import test modules
from tests.test_llm_handler import TestLLMHandler
from tests.test_code_parser import TestCodeParser
from tests.test_diagram_builder import TestDiagramBuilder


def run_tests():
    """Run all tests and print a summary."""
    # Create a test suite
    test_suite = unittest.TestSuite()

    # Add test cases
    test_suite.addTest(unittest.defaultTestLoader.loadTestsFromTestCase(TestLLMHandler))
    test_suite.addTest(unittest.defaultTestLoader.loadTestsFromTestCase(TestCodeParser))
    test_suite.addTest(unittest.defaultTestLoader.loadTestsFromTestCase(TestDiagramBuilder))

    # Run the tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)

    # Print summary
    print("\nTest Summary:")
    print(f"Ran {result.testsRun} tests")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")

    # Return exit code based on test results
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(run_tests())

import os
import sys
import unittest
from unittest.mock import patch, MagicMock, mock_open

# Add the parent directory to sys.path to import the modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import code_parser


class TestCodeParser(unittest.TestCase):

    def test_get_code_from_lines(self):
        """Test that get_code_from_lines correctly extracts code from a list of lines."""
        lines = ["line1\n", "line2\n", "line3\n", "line4\n"]

        # Test normal extraction
        result = code_parser.get_code_from_lines(lines, 2, 4)
        self.assertEqual(result, "line2\nline3\nline4\n")

        # Test with invalid start/end lines
        result = code_parser.get_code_from_lines(lines, None, 3)
        self.assertEqual(result, "")

        result = code_parser.get_code_from_lines(lines, 2, None)
        self.assertEqual(result, "")

    def test_get_start_line(self):
        """Test that get_start_line correctly returns the starting line of a node."""
        # Create a mock node with position
        node = MagicMock()
        node.position = MagicMock()
        node.position.line = 10

        result = code_parser.get_start_line(node)
        self.assertEqual(result, 10)

        # Test with node that has no position
        node = MagicMock()
        node.position = None

        result = code_parser.get_start_line(node)
        self.assertEqual(result, 0)

    def test_get_end_line(self):
        """Test that get_end_line correctly calculates the ending line of a node."""
        # Create a mock node with position and children
        node = MagicMock()
        node.position = MagicMock()
        node.position.line = 10

        # Mock the walk_tree function to return child nodes
        child1 = MagicMock()
        child1.position = MagicMock()
        child1.position.line = 15

        child2 = MagicMock()
        child2.position = MagicMock()
        child2.position.line = 20

        with patch('javalang.ast.walk_tree', return_value=[('child1', child1), ('child2', child2)]):
            result = code_parser.get_end_line(node)
            self.assertEqual(result, 21)  # max line (20) + 1

    def test_parse_methods(self):
        """Test that parse_methods correctly extracts method information."""
        # Create a mock class declaration with methods
        class_decl = MagicMock()

        # Create mock methods
        method1 = MagicMock()
        method1.name = "method1"
        method1.modifiers = ["public"]
        method1.position.line = 10

        method2 = MagicMock()
        method2.name = "method2"
        method2.modifiers = ["private"]
        method2.position.line = 20

        # Mock the filter function to return methods
        class_decl.filter.return_value = [('method1', method1), ('method2', method2)]

        # Mock get_start_line, get_end_line, and get_code_from_lines
        with patch('code_parser.get_start_line', side_effect=[10, 20]):
            with patch('code_parser.get_end_line', side_effect=[15, 25]):
                with patch('code_parser.get_code_from_lines', side_effect=["method1 code", "method2 code"]):
                    lines = ["line1", "line2"]  # Dummy lines
                    known_classes = set()  # Dummy known classes

                    result = code_parser.parse_methods(class_decl, lines, known_classes)

                    self.assertEqual(len(result), 2)
                    self.assertEqual(result[0]['name'], "method1")
                    self.assertEqual(result[0]['modifiers'], ["public"])
                    self.assertEqual(result[0]['code_snippet'], "method1 code")
                    self.assertEqual(result[1]['name'], "method2")
                    self.assertEqual(result[1]['modifiers'], ["private"])
                    self.assertEqual(result[1]['code_snippet'], "method2 code")

    def test_build_class_index(self):
        """Test that build_class_index correctly builds an index of class names to package names."""
        # Mock file content with a class declaration
        file_content = """
        package com.example;
        
        public class TestClass {
            // Class content
        }
        """

        # Mock open to return the file content
        with patch('builtins.open', mock_open(read_data=file_content)):
            # Mock javalang.parse.parse to return a tree with a package and class
            mock_tree = MagicMock()
            mock_tree.package = MagicMock()
            mock_tree.package.name = "com.example"

            mock_class = MagicMock()
            mock_class.name = "TestClass"

            mock_tree.filter.return_value = [('class', mock_class)]

            with patch('javalang.parse.parse', return_value=mock_tree):
                result = code_parser.build_class_index(["test.java"])

                self.assertEqual(result, {"TestClass": "com.example"})


if __name__ == '__main__':
    unittest.main()

import unittest
from unittest.mock import patch, MagicMock, mock_open
import sys
import os
from io import StringIO

# Add the parent directory to sys.path to import the modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import diagram_builder
from pathlib import Path

class TestDiagramBuilder(unittest.TestCase):
    
    def test_write_uml(self):
        """Test that write_uml correctly writes UML content to a file."""
        with patch('builtins.open', mock_open()) as mock_file:
            file_path = "test.puml"
            content = "@startuml\nclass Test\n@enduml"
            description = "test"
            
            diagram_builder.write_uml(file_path, content, description)
            
            mock_file.assert_called_once_with(file_path, 'w', encoding='utf-8')
            mock_file().write.assert_called_once_with(content)
    
    def test_format_field(self):
        """Test that format_field correctly formats a field for PlantUML."""
        # Test public field
        field = {
            'name': 'testField',
            'type': 'String',
            'modifiers': ['public']
        }
        result = diagram_builder.format_field(field)
        self.assertEqual(result, "+ testField : String")
        
        # Test private field with static and final modifiers
        field = {
            'name': 'testField',
            'type': 'int',
            'modifiers': ['private', 'static', 'final']
        }
        result = diagram_builder.format_field(field)
        self.assertEqual(result, "- testField : int {{static, final}}")
        
        # Test protected field
        field = {
            'name': 'testField',
            'type': 'boolean',
            'modifiers': ['protected']
        }
        result = diagram_builder.format_field(field)
        self.assertEqual(result, "# testField : boolean")
        
        # Test package-private field (no visibility modifier)
        field = {
            'name': 'testField',
            'type': 'Object',
            'modifiers': []
        }
        result = diagram_builder.format_field(field)
        self.assertEqual(result, "~ testField : Object")
    
    def test_format_method(self):
        """Test that format_method correctly formats a method for PlantUML."""
        # Test public method
        method = {
            'name': 'testMethod',
            'modifiers': ['public']
        }
        result = diagram_builder.format_method(method)
        self.assertEqual(result, "+ testMethod()")
        
        # Test private method with static modifier
        method = {
            'name': 'testMethod',
            'modifiers': ['private', 'static']
        }
        result = diagram_builder.format_method(method)
        self.assertEqual(result, "- testMethod() {{static}}")
        
        # Test abstract method
        method = {
            'name': 'testMethod',
            'modifiers': ['public', 'abstract']
        }
        result = diagram_builder.format_method(method)
        self.assertEqual(result, "+ testMethod() {{abstract}}")
    
    def test_write_class_block(self):
        """Test that write_class_block correctly writes a class block to a StringIO."""
        # Test regular class
        class_data = {
            'name': 'TestClass',
            'modifiers': ['public'],
            'fields': [
                {'name': 'field1', 'type': 'String', 'modifiers': ['private']}
            ],
            'methods': [
                {'name': 'method1', 'modifiers': ['public']}
            ]
        }
        
        output = StringIO()
        diagram_builder.write_class_block(output, class_data)
        result = output.getvalue()
        
        self.assertIn("class TestClass", result)
        self.assertIn("- field1 : String", result)
        self.assertIn("+ method1()", result)
        
        # Test interface
        class_data = {
            'name': 'TestInterface',
            'modifiers': ['public', 'interface'],
            'fields': [],
            'methods': [
                {'name': 'method1', 'modifiers': ['public']}
            ]
        }
        
        output = StringIO()
        diagram_builder.write_class_block(output, class_data)
        result = output.getvalue()
        
        self.assertIn("interface TestInterface <<interface>>", result)
        self.assertIn("+ method1()", result)
        
        # Test abstract class
        class_data = {
            'name': 'TestAbstractClass',
            'modifiers': ['public', 'abstract'],
            'fields': [],
            'methods': [
                {'name': 'method1', 'modifiers': ['public', 'abstract']}
            ]
        }
        
        output = StringIO()
        diagram_builder.write_class_block(output, class_data)
        result = output.getvalue()
        
        self.assertIn("abstract class TestAbstractClass <<abstract>>", result)
        self.assertIn("+ method1() {{abstract}}", result)
    
    def test_diagram_builder_class(self):
        """Test the DiagramBuilder class functionality."""
        builder = diagram_builder.DiagramBuilder()
        
        # Test add_class
        class_data = {
            'name': 'TestClass',
            'modifiers': ['public'],
            'fields': [],
            'methods': []
        }
        builder.add_class("com.example", class_data)
        self.assertEqual(len(builder.packages["com.example"]), 1)
        
        # Test add_relationship
        builder.add_relationship("Child", "Parent", "extends")
        builder.add_relationship("Implementation", "Interface", "implements")
        builder.add_relationship("User", "Service", "uses")
        
        self.assertEqual(len(builder.relationships), 3)
        
        # Test build
        result = builder.build()
        
        # Check that the result contains expected elements
        self.assertIn("@startuml", result)
        self.assertIn("package \"com.example\"", result)
        self.assertIn("class TestClass", result)
        self.assertIn("Parent <|-- Child : extends", result)
        self.assertIn("Interface <|.. Implementation : implements", result)
        self.assertIn("User ..> Service : uses", result)
        self.assertIn("@enduml", result)

if __name__ == '__main__':
    unittest.main()
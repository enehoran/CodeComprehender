import os
import argparse
import logging
from pathlib import Path
import time
import javalang
from google import genai
from dotenv import load_dotenv
import re
from tqdm import tqdm

# --- LLM Connector Module ---

def configure_llm(api_key):
    """Configures the generative AI model."""
    client = genai.Client(api_key=api_key)
    logging.info("Generative AI model configured successfully.")
    return client



def get_llm_comment(client, code_snippet, element_type, model_name="gemini-2.0-flash", num_retries=8):
    """
    Generates a comment for a given code snippet using the LLM.
    """
    if not client:
        return f"/**\n * LLM not configured. Placeholder for {element_type}.\n */"
    initial_retry_delay = 2
    prompt = f"Generate a concise Javadoc comment for the following Java {element_type}. Describe its purpose, parameters, and return value if applicable. Do not include the original code in your response.\n\nCode:\n```java\n{code_snippet}\n```"

    for attempt in range(num_retries):
        try:
            response = client.models.generate_content(
                model=model_name,
                config=genai.types.GenerateContentConfig(
                system_instruction="You are a helpful Java documentation assistant."),
                contents=prompt
            )
            if response.text:
                # Basic cleanup of the response
                cleaned_text = response.text.replace("```java", "").replace("```", "").strip()
                if not cleaned_text.startswith("/**"):
                    cleaned_text = "/**\n * " + cleaned_text
                if not cleaned_text.endswith("*/"):
                    cleaned_text = cleaned_text + "\n */"
                return cleaned_text
        except Exception as e:
            logging.warning(f"Error calling LLM API on attempt {attempt + 1}: {e}")

        if attempt < num_retries - 1:
            wait_time = initial_retry_delay * (2 ** attempt)
            logging.info(f"Retrying LLM call in {wait_time} seconds...")
            time.sleep(wait_time)

    logging.error(f"LLM returned an empty or failed response after {num_retries} attempts for a {element_type}.")
    return f"/**\n * Failed to generate comment for this {element_type} after multiple retries.\n */"


# --- 1. Java Parser Module ---

def get_code_from_lines(lines, start_line, end_line):
    """Extracts a snippet of code from a list of lines."""
    if not start_line or not end_line:
        return ""
    return "".join(lines[start_line - 1: end_line])


def parse_java_file(file_path, original_lines):
    """
    Parses a single Java file to extract its structure.
    """
    logging.debug(f"Parsing file: {file_path}")
    try:
        content = "".join(original_lines)
        tree = javalang.parse.parse(content)
        package = tree.package.name if tree.package else "default"

        # Get a list of all class names defined in this file for context
        defined_class_names = [node.name for _, node in tree.filter(javalang.tree.ClassDeclaration)]

        classes = []
        for _, class_declaration in tree.filter(javalang.tree.ClassDeclaration):
            methods = []
            fields = []
            dependencies = set()
            for _, method_declaration in class_declaration.filter(javalang.tree.MethodDeclaration):
                method_end_line = max(node.position.line for node in
                                      method_declaration.body) + 1 if method_declaration.body else method_declaration.position.line

                # Find method invocations to detect dependencies
                for _, invocation in method_declaration.filter(javalang.tree.MethodInvocation):
                    # Heuristic: if the method is called on a type that's a known class, it's a dependency
                    if isinstance(invocation.qualifier, str) and invocation.qualifier in defined_class_names:
                        dependencies.add(invocation.qualifier)

                # Heuristic for member references (e.g. someObject.someMethod())
                for _, member_ref in method_declaration.filter(javalang.tree.MemberReference):
                    if isinstance(member_ref.qualifier, str) and member_ref.qualifier in defined_class_names:
                        dependencies.add(member_ref.qualifier)

                methods.append({
                    'name': method_declaration.name,
                    'start_line': method_declaration.position.line,
                    'code_snippet': get_code_from_lines(original_lines, method_declaration.position.line,
                                                        method_end_line),
                    'modifiers': list(method_declaration.modifiers)
                })

            # Analyze field declarations for dependencies and extract field information
            for _, field_decl in class_declaration.filter(javalang.tree.FieldDeclaration):
                field_type = field_decl.type.name if hasattr(field_decl.type, 'name') else None
                if field_type in defined_class_names:
                    dependencies.add(field_type)

                # Extract field information for each variable declarator in this field declaration
                for variable in field_decl.declarators:
                    fields.append({
                        'name': variable.name,
                        'type': field_type if field_type else "Object",
                        'modifiers': list(field_decl.modifiers)
                    })

            # Analyze import statements
            for import_decl in tree.imports:
                import_parts = import_decl.path.split('.')
                if import_parts[-1] in defined_class_names:
                    # This is importing a class defined in this project
                    dependencies.add(import_parts[-1])

            # Find the end line of the class
            class_end_line = max(node.position.line for node in class_declaration.body) + 1 if class_declaration.body else class_declaration.position.line

            classes.append({
                'name': class_declaration.name,
                'methods': methods,
                'fields': fields,
                'start_line': class_declaration.position.line,
                'extends': class_declaration.extends.name if class_declaration.extends else None,
                'implements': [impl.name for impl in class_declaration.implements] if class_declaration.implements else [],
                'dependencies': list(dependencies),
                'code_snippet': get_code_from_lines(original_lines, class_declaration.position.line, class_end_line),
            })

        return {
            'file_path': str(file_path),
            'package': package,
            'classes': classes
        }

    except (javalang.tokenizer.LexerError, javalang.parser.JavaSyntaxError) as e:
        logging.error(f"Failed to parse {file_path}: {e}", exc_info=True)
    except Exception:
        logging.error(f"An unexpected error occurred while parsing {file_path}", exc_info=True)
    return None


# --- 2. Comment Generator Module ---

def generate_comments_for_structure(parsed_structure, client):
    """
    Generates comments for classes and methods using the configured LLM.
    """
    logging.debug(f"Generating comments for {parsed_structure['file_path']}...")
    if not client:
        logging.warning("LLM model is not available. Skipping comment generation.")
        return parsed_structure

    for class_info in parsed_structure.get('classes', []):
        class_info['comment'] = get_llm_comment(client, class_info['code_snippet'], 'class')
        for method_info in class_info.get('methods', []):
            method_info['comment'] = get_llm_comment(client, method_info['code_snippet'], 'method')

    return parsed_structure


# --- 3. Comment Inserter Module ---

def create_commented_file(parsed_structure_with_comments, output_dir):
    """
    Creates a new Java file with generated comments inserted.
    """
    original_path = Path(parsed_structure_with_comments['file_path'])
    output_filename = original_path.stem + "_commented.java"
    # Ensure package directory structure is created in output
    package_path = output_dir / parsed_structure_with_comments['package'].replace('.', '/')
    package_path.mkdir(parents=True, exist_ok=True)
    output_file_path = package_path / output_filename

    logging.debug(f"Creating commented file: {output_file_path}")

    try:
        with open(original_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        comment_map = {}
        for class_info in parsed_structure_with_comments.get('classes', []):
            if 'comment' in class_info:
                comment_map[class_info['start_line']] = class_info['comment']
            for method_info in class_info.get('methods', []):
                if 'comment' in method_info:
                    comment_map[method_info['start_line']] = method_info['comment']

        with open(output_file_path, 'w', encoding='utf-8') as f:
            for i, line in enumerate(lines):
                line_num = i + 1
                if line_num in comment_map:
                    indentation = ' ' * (len(line) - len(line.lstrip(' ')))
                    comment = comment_map[line_num]
                    indented_comment = '\n'.join([f"{indentation}{cline}" for cline in comment.split('\n')])
                    f.write(f"{indented_comment}\n")
                f.write(line)

    except Exception as e:
        logging.error(f"Could not write to {output_file_path}", exc_info=True)


# --- 4. Architecture Extractor Module ---
def generate_architecture_diagram(all_parsed_data, output_dir):
    """Generates a comprehensive PlantUML architecture diagram with detailed relationships and methods."""
    output_path = output_dir / "architecture.puml"
    logging.info(f"Generating comprehensive architecture diagram at {output_path}")

    packages = {}
    relationships = set()
    all_classes = {}  # Store all class info for easy lookup

    # First pass: collect all classes and packages
    for file_data in all_parsed_data:
        if not file_data: continue
        package_name = file_data['package']
        if package_name not in packages: packages[package_name] = []
        for class_info in file_data['classes']:
            packages[package_name].append(class_info)
            all_classes[class_info['name']] = class_info  # Store for easy lookup

    # Second pass: determine relationships
    for file_data in all_parsed_data:
        if not file_data: continue
        for class_info in file_data['classes']:
            class_name = class_info['name']
            # Inheritance relationships
            if class_info.get('extends'):
                relationships.add(f"{class_info['extends']} <|-- {class_name} : extends")
            # Implementation relationships
            if class_info.get('implements'):
                for interface in class_info['implements']:
                    relationships.add(f"{interface} <|.. {class_name} : implements")
            # Dependency relationships
            if class_info.get('dependencies'):
                for dep in class_info['dependencies']:
                    if dep != class_name:  # Avoid self-references in the diagram
                        relationships.add(f"{class_name} ..> {dep} : uses")

    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("@startuml\n")
            # Enhanced styling for better visualization
            f.write("skinparam packageStyle rect\n")
            f.write("skinparam classAttributeIconSize 0\n")
            f.write("skinparam classFontStyle bold\n")
            f.write("skinparam classAttributeFontStyle normal\n")
            f.write("skinparam classAttributeFontSize 11\n")
            f.write("skinparam linetype ortho\n")
            f.write("skinparam packageBackgroundColor aliceblue\n")
            f.write("skinparam classBackgroundColor lightyellow\n")
            f.write("skinparam interfaceBackgroundColor lightgreen\n")
            f.write("skinparam arrowColor black\n")
            f.write("skinparam shadowing true\n\n")

            # Title and legend
            f.write("title Comprehensive Architecture Diagram\n\n")
            f.write("legend right\n")
            f.write("  Legend:\n")
            f.write("  Visibility:\n")
            f.write("    + public\n")
            f.write("    # protected\n")
            f.write("    ~ package private\n")
            f.write("    - private\n")
            f.write("  \n")
            f.write("  Stereotypes:\n")
            f.write("    {abstract} - abstract method\n")
            f.write("    {static} - static method/field\n")
            f.write("    {final} - final field\n")
            f.write("  \n")
            f.write("  Relationships:\n")
            f.write("    ⟶ dependency (uses)\n")
            f.write("    ◀-- inheritance (extends)\n")
            f.write("    ◁.. implementation (implements)\n")
            f.write("endlegend\n\n")

            # Add a detailed note about the diagram
            f.write("note as N1\n")
            f.write("  This comprehensive architecture diagram shows:\n")
            f.write("  - All classes, abstract classes, and interfaces\n")
            f.write("  - Fields with visibility, types, and stereotypes (static, final)\n")
            f.write("  - Methods with visibility and stereotypes (abstract, static)\n")
            f.write("  - Detailed inheritance, implementation, and dependency relationships\n")
            f.write("  - Package organization and structure\n")
            f.write("endnote\n\n")

            # Calculate overall statistics
            total_packages = len(packages)
            total_classes = sum(len(classes_info) for classes_info in packages.values())
            total_interfaces = sum(
                sum(1 for c in classes_info if hasattr(c, 'modifiers') and 'interface' in c.get('modifiers', []))
                for classes_info in packages.values()
            )
            total_abstract_classes = sum(
                sum(1 for c in classes_info if hasattr(c, 'modifiers') and 'abstract' in c.get('modifiers', []) and 'interface' not in c.get('modifiers', []))
                for classes_info in packages.values()
            )
            total_methods = sum(
                sum(len(c.get('methods', [])) for c in classes_info)
                for classes_info in packages.values()
            )
            total_fields = sum(
                sum(len(c.get('fields', [])) for c in classes_info)
                for classes_info in packages.values()
            )

            # Add a summary note with overall statistics
            f.write("note as SummaryStats\n")
            f.write("  <b>Project Summary</b>\n")
            f.write(f"  Packages: {total_packages}\n")
            f.write(f"  Classes: {total_classes}\n")
            f.write(f"  Interfaces: {total_interfaces}\n")
            f.write(f"  Abstract Classes: {total_abstract_classes}\n")
            f.write(f"  Methods: {total_methods}\n")
            f.write(f"  Fields: {total_fields}\n")
            f.write("end note\n\n")

            # Generate individual package statistics as comments
            f.write("' Package Statistics\n")
            for package_name, classes_info in packages.items():
                class_count = len(classes_info)
                interface_count = sum(1 for c in classes_info if hasattr(c, 'modifiers') and 'interface' in c.get('modifiers', []))
                method_count = sum(len(c.get('methods', [])) for c in classes_info)
                field_count = sum(len(c.get('fields', [])) for c in classes_info)
                f.write(f"' {package_name}: {class_count} classes, {interface_count} interfaces, {method_count} methods, {field_count} fields\n")
            f.write("\n")

            # Generate packages and classes with detailed information
            for package_name, classes_info in packages.items():
                # Calculate package statistics
                class_count = len(classes_info)
                method_count = sum(len(c.get('methods', [])) for c in classes_info)
                field_count = sum(len(c.get('fields', [])) for c in classes_info)

                # Add package with a unique alias
                package_alias = package_name.replace(".", "_")
                f.write(f'package "{package_name}" as {package_alias} {{\n')

                # Add a note with package statistics
                f.write(f'  note as {package_alias}_stats\n')
                f.write(f'    {class_count} classes\n')
                f.write(f'    {method_count} methods\n')
                f.write(f'    {field_count} fields\n')
                f.write(f'  end note\n')
                for class_data in classes_info:
                    # Determine if it's an interface or abstract class
                    is_interface = False
                    is_abstract = False

                    # Check modifiers in the class declaration if available
                    if hasattr(class_data, 'modifiers') and class_data.get('modifiers'):
                        if 'interface' in class_data.get('modifiers'):
                            is_interface = True
                        elif 'abstract' in class_data.get('modifiers'):
                            is_abstract = True

                    # Heuristic: If class name starts with 'I' and has only interface methods, it might be an interface
                    if not is_interface and class_data['name'].startswith('I') and len(class_data['name']) > 1:
                        # Check if all methods lack implementation (interface methods)
                        all_methods_abstract = all(
                            'abstract' in method.get('modifiers', []) 
                            for method in class_data.get('methods', [])
                        )
                        if all_methods_abstract and class_data.get('methods'):
                            is_interface = True

                    # Class, abstract class, or interface declaration
                    if is_interface:
                        f.write(f"  interface {class_data['name']} {{\n")
                    elif is_abstract:
                        f.write(f"  abstract class {class_data['name']} {{\n")
                    else:
                        f.write(f"  class {class_data['name']} {{\n")

                    # Add fields with types and visibility
                    for field in class_data.get('fields', []):
                        # Determine visibility
                        visibility = "+"  # default to public
                        if 'private' in field.get('modifiers', []):
                            visibility = "-"
                        elif 'protected' in field.get('modifiers', []):
                            visibility = "#"
                        elif not any(mod in ['public', 'private', 'protected'] for mod in field.get('modifiers', [])):
                            visibility = "~"  # package private

                        # Check for special field types (static, final)
                        field_modifiers = field.get('modifiers', [])
                        is_static = 'static' in field_modifiers
                        is_final = 'final' in field_modifiers

                        # Add stereotypes for special field types
                        stereotypes = []
                        if is_static:
                            stereotypes.append("static")
                        if is_final:
                            stereotypes.append("final")

                        # Format field with type and stereotypes if any
                        field_type = field.get('type', 'Object')
                        if stereotypes:
                            stereotype_str = f" {{{{{', '.join(stereotypes)}}}}}"
                            f.write(f"    {visibility} {field['name']} : {field_type}{stereotype_str}\n")
                        else:
                            f.write(f"    {visibility} {field['name']} : {field_type}\n")

                    # Add methods with visibility
                    for method in class_data.get('methods', []):
                        # Determine visibility
                        visibility = "+"  # default to public
                        if 'private' in method.get('modifiers', []):
                            visibility = "-"
                        elif 'protected' in method.get('modifiers', []):
                            visibility = "#"
                        elif not any(mod in ['public', 'private', 'protected'] for mod in method.get('modifiers', [])):
                            visibility = "~"  # package private

                        # Since parameters and return types aren't extracted in the current implementation,
                        # we'll leave these blank for now
                        params = ""
                        return_type = ""

                        # This could be enhanced by parsing the method code_snippet to extract parameters and return type
                        # For now, we'll just show the method name with its visibility

                        # Check for special method types (abstract, static)
                        method_modifiers = method.get('modifiers', [])
                        is_abstract = 'abstract' in method_modifiers
                        is_static = 'static' in method_modifiers

                        # Add stereotypes for special method types
                        stereotypes = []
                        if is_abstract:
                            stereotypes.append("abstract")
                        if is_static:
                            stereotypes.append("static")

                        # Format the method with stereotypes if any
                        if stereotypes:
                            stereotype_str = f" {{{{{', '.join(stereotypes)}}}}}"
                            f.write(f"    {visibility} {method['name']}({params}){return_type}{stereotype_str}\n")
                        else:
                            f.write(f"    {visibility} {method['name']}({params}){return_type}\n")

                    f.write("  }\n")
                f.write("}\n\n")

            # Write relationships with descriptive labels
            if relationships:
                f.write("\n' Class Relationships\n")
                for rel in sorted(list(relationships)):
                    f.write(f"{rel}\n")

            f.write("\n@enduml\n")
    except Exception as e:
        logging.error(f"Failed to generate PlantUML diagram: {e}", exc_info=True)


# --- Main CLI Logic ---

def main():
    """Main function to run the CLI."""
    load_dotenv()

    parser = argparse.ArgumentParser(description="CodeComprehender: A tool for automated Java code documentation.")
    parser.add_argument("source_dir", type=str, help="The source directory containing Java files.")
    parser.add_argument("output_dir", type=str, help="The directory to save commented files and diagrams.")
    parser.add_argument("--api_key", type=str, default=os.environ.get("GEMINI_API_KEY"),
                        help="API key for the Gemini LLM. Can also be set via GEMINI_API_KEY environment variable.")
    parser.add_argument("--exclude", nargs='*', default=[],
                        help="A list of regex patterns to exclude files/directories. "
                             "Example: --exclude '.*Test.java' 'build/.*'")
    parser.add_argument("--verbose", type=bool, default=False, help="Verbose output.")
    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    else:
        logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

    if not args.api_key:
        logging.error(
            "Gemini API key is required. Please provide it with --api_key or set the GEMINI_API_KEY environment variable.")
        return

    source_path = Path(args.source_dir)
    output_path = Path(args.output_dir)

    try:
        exclude_patterns = [re.compile(p) for p in args.exclude]
    except re.error as e:
        logging.error(f"Invalid regex pattern in --exclude list: {e}", exc_info=True)
        return

    if not source_path.is_dir():
        logging.error(f"Source directory not found: {source_path}")
        return

    output_path.mkdir(parents=True, exist_ok=True)

    try:
        client = configure_llm(args.api_key)
    except Exception as e:
        logging.error(f"Failed to configure Gemini LLM: {e}", exc_info=True)
        return

    all_parsed_data = []
    java_files = list(source_path.rglob("*.java"))
    filtered_java_files = []

    for file_path in java_files:
        path_str = str(file_path.as_posix())
        if any(pattern.search(path_str) for pattern in exclude_patterns):
            logging.debug(f"Skipping excluded file: {file_path}")
            continue
        filtered_java_files.append(file_path)

    logging.info(f"Found {len(filtered_java_files)} Java files to process.")
    for file_path in tqdm(filtered_java_files, desc="Processing Java files", unit="files", total=len(filtered_java_files)):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except Exception as e:
            logging.error(f"Could not read file {file_path}: {e}", exc_info=True)
            continue

        parsed_structure = parse_java_file(file_path, lines)
        if parsed_structure:
            all_parsed_data.append(parsed_structure)

            # structure_with_comments = generate_comments_for_structure(parsed_structure, client)
            # create_commented_file(structure_with_comments, output_path)

    if all_parsed_data:
        generate_architecture_diagram(all_parsed_data, output_path)

    logging.info("Processing complete.")


if __name__ == "__main__":
    main()

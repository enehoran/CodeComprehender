import logging

import javalang


def get_code_from_lines(lines, start_line, end_line):
    """Extracts a snippet of code from a list of lines."""
    if not start_line or not end_line:
        return ""
    return "".join(lines[start_line - 1: end_line])


def get_start_line(node):
    """
    Gets the starting line number of a Java AST node.

    Args:
        node: A javalang AST node

    Returns:
        The line number where the node starts, or 0 if position information is not available
    """
    return node.position.line if hasattr(node, 'position') and node.position else 0


def get_end_line(node):
    """
    Calculates the ending line number of a Java AST node by finding the maximum line number
    of all its child nodes.

    Args:
        node: A javalang AST node

    Returns:
        The line number where the node ends (max child line + 1)
    """
    max_line = get_start_line(node)
    for _, child in javalang.ast.walk_tree(node):
        if child.position is None:
            continue
        if child.position.line > max_line:
            max_line = child.position.line
    return max_line + 1


def parse_methods(class_decl, lines, known_classes):
    """
    Extracts method information from a Java class declaration.

    Args:
        class_decl: A javalang ClassDeclaration node
        lines: List of source code lines
        known_classes: Set of known class names in the project

    Returns:
        List of dictionaries containing method information (name, start_line, modifiers, code_snippet)
    """
    methods = []
    for _, method in class_decl.filter(javalang.tree.MethodDeclaration):
        start_line = get_start_line(method)
        end_line = get_end_line(method)
        snippet = get_code_from_lines(lines, start_line, end_line)
        modifiers = list(getattr(method, 'modifiers', []))
        methods.append({
            'name': method.name,
            'start_line': start_line,
            'modifiers': modifiers,
            'code_snippet': snippet,
        })
    return methods


def parse_fields(class_decl, known_classes):
    """
    Extracts field information from a Java class declaration.

    Args:
        class_decl: A javalang ClassDeclaration node
        known_classes: Set of known class names in the project

    Returns:
        List of dictionaries containing field information (name, type, modifiers)
    """
    fields = []
    for _, field in class_decl.filter(javalang.tree.FieldDeclaration):
        field_type = getattr(field.type, 'name', 'Object')
        for var in field.declarators:
            fields.append({
                'name': var.name,
                'type': field_type,
                'modifiers': list(getattr(field, 'modifiers', []))
            })
    return fields


def collect_class_dependencies(class_decl, known_classes):
    """
    Identifies dependencies between classes by analyzing method invocations, field types,
    reference types, and type arguments.

    Args:
        class_decl: A javalang ClassDeclaration node
        known_classes: Set of known class names in the project

    Returns:
        Set of class names that this class depends on
    """
    deps = set()
    for _, method in class_decl.filter(javalang.tree.MethodDeclaration):
        for _, node in method.filter(javalang.tree.MethodInvocation):
            if isinstance(node.qualifier, str) and node.qualifier in known_classes:
                deps.add(node.qualifier)
        for _, ref in method.filter(javalang.tree.MemberReference):
            if isinstance(ref.qualifier, str) and ref.qualifier in known_classes:
                deps.add(ref.qualifier)

    for _, field in class_decl.filter(javalang.tree.FieldDeclaration):
        field_type = getattr(field.type, 'name', None)
        if field_type in known_classes:
            deps.add(field_type)

    for _, ref_type in class_decl.filter(javalang.tree.ReferenceType):
        ref_name = getattr(ref_type, 'name', None)
        if ref_name in known_classes:
            deps.add(ref_name)

    for _, type_arg in class_decl.filter(javalang.tree.TypeArgument):
        type_arg_name = getattr(type_arg, 'name', None)
        if type_arg_name in known_classes:
            deps.add(type_arg_name)

    return set(deps)


def build_class_index(java_files):
    """
    Returns a dict: class name → package name
    Example: { "UserService": "com.myapp.service" }
    """
    class_index = {}
    for file_path in java_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            tree = javalang.parse.parse(content)
            package = tree.package.name if tree.package else "default"
            for _, class_decl in tree.filter(javalang.tree.ClassDeclaration):
                class_index[class_decl.name] = package
        except Exception as e:
            logging.warning(f"Could not open {file_path}. Skipping file. {e}")
    return class_index


def is_top_level_class(path):
    return isinstance(path[1], list) and len(path[1]) == 1


def parse_java_file(file_path, original_lines, project_class_index):
    """
    Parses a single Java file to extract class structure, methods, fields, and dependencies.
    """
    logging.debug(f"Parsing file: {file_path}")
    try:
        content = "".join(original_lines)
        tree = javalang.parse.parse(content)
        package = tree.package.name if tree.package else "default"
        known_classes = set(project_class_index.keys())

        classes = []
        for path, class_decl in tree.filter(javalang.tree.ClassDeclaration):
            # Only process top-level classes (path length 1 means root-level node)
            if not is_top_level_class(path):
                continue

            # Get classes details.
            class_start = get_start_line(class_decl)
            class_end = get_end_line(class_decl)
            class_info = {
                'name': class_decl.name,
                'start_line': class_start,
                'extends': class_decl.extends.name if class_decl.extends else None,
                'implements': [impl.name for impl in class_decl.implements] if class_decl.implements else [],
                'annotations': [ann.name for ann in getattr(class_decl, 'annotations', [])],
                'modifiers': list(getattr(class_decl, 'modifiers', [])),
                'methods': parse_methods(class_decl, original_lines, known_classes),
                'fields': parse_fields(class_decl, known_classes),
                'dependencies': collect_class_dependencies(class_decl, known_classes),
                'code_snippet': get_code_from_lines(original_lines, class_start, class_end),
            }
            classes.append(class_info)

        return {
            'file_path': str(file_path),
            'package': package,
            'classes': classes
        }

    except (javalang.tokenizer.LexerError, javalang.parser.JavaSyntaxError) as e:
        logging.warning(f"Syntax error in {file_path}. Skipping parsing for this file.: {e}", exc_info=True)
    except Exception as e:
        logging.error(f"Unexpected error in {file_path}. Skipping parsing for this file.: {e}", exc_info=True)
    return None

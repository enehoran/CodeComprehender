import javalang
import logging

def get_code_from_lines(lines, start_line, end_line):
    """Extracts a snippet of code from a list of lines."""
    if not start_line or not end_line:
        return ""
    return "".join(lines[start_line - 1: end_line])

def get_position_safe(node):
    return node.position.line if hasattr(node, 'position') and node.position else 0

def get_max_line(nodes, default=0):
    return max((get_position_safe(n) for n in nodes), default=default) + 1

def parse_methods(class_decl, lines, known_classes):
    methods = []
    for _, method in class_decl.filter(javalang.tree.MethodDeclaration):
        start_line = get_position_safe(method)
        end_line = get_max_line(method.body or [], default=start_line)
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

    return list(deps)


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
            logging.warning(f"Skipping {file_path}: {e}")
    return class_index



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
        for _, class_decl in tree.filter(javalang.tree.ClassDeclaration):
            class_start = get_position_safe(class_decl)
            class_end = get_max_line(class_decl.body, default=class_start)

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
        logging.error(f"Syntax error in {file_path}: {e}", exc_info=True)
    except Exception as e:
        logging.error(f"Unexpected error in {file_path}: {e}", exc_info=True)
    return None
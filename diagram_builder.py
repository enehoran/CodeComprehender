from collections import defaultdict
import logging

# Architecture Extractor Module

def format_field(field):
    visibility = "+"
    if 'private' in field.get('modifiers', []): visibility = "-"
    elif 'protected' in field.get('modifiers', []): visibility = "#"
    elif not any(mod in field.get('modifiers', []) for mod in ['public', 'private', 'protected']): visibility = "~"

    stereotypes = []
    if 'static' in field.get('modifiers', []): stereotypes.append("static")
    if 'final' in field.get('modifiers', []): stereotypes.append("final")
    stereotype_str = f" {{{{{', '.join(stereotypes)}}}}}" if stereotypes else ""

    field_type = field.get('type', 'Object')
    return f"{visibility} {field['name']} : {field_type}{stereotype_str}"

def format_method(method):
    visibility = "+"
    if 'private' in method.get('modifiers', []): visibility = "-"
    elif 'protected' in method.get('modifiers', []): visibility = "#"
    elif not any(mod in method.get('modifiers', []) for mod in ['public', 'private', 'protected']): visibility = "~"

    stereotypes = []
    if 'abstract' in method.get('modifiers', []): stereotypes.append("abstract")
    if 'static' in method.get('modifiers', []): stereotypes.append("static")
    stereotype_str = f" {{{{{', '.join(stereotypes)}}}}}" if stereotypes else ""

    return f"{visibility} {method['name']}(){stereotype_str}"

def write_class_block(f, class_data):
    """
    Writes a PlantUML class/interface/abstract class block.
    """
    name = class_data['name']
    modifiers = class_data.get('modifiers', [])
    fields = class_data.get('fields', [])
    methods = class_data.get('methods', [])

    is_interface = 'interface' in modifiers
    is_abstract = 'abstract' in modifiers and not is_interface

    stereotype = "<<interface>>" if is_interface else "<<abstract>>" if is_abstract else ""

    if is_interface:
        f.write(f"  interface {name} {stereotype} {{\n")
    elif is_abstract:
        f.write(f"  abstract class {name} {stereotype} {{\n")
    else:
        f.write(f"  class {name} {stereotype} {{\n")

    for field in fields:
        f.write(f"    {format_field(field)}\n")

    for method in methods:
        f.write(f"    {format_method(method)}\n")

    f.write("  }\n")


def write_class_block_inline(class_data):
    """
    Returns a string representing a class/interface block in PlantUML.
    """
    from io import StringIO
    buf = StringIO()
    write_class_block(buf, class_data)
    return buf.getvalue()

def generate_architecture_diagram(all_parsed_data, output_dir):
    output_path = output_dir / "architecture.puml"
    builder = DiagramBuilder()

    for file_data in all_parsed_data:
        if not file_data:
            continue
        pkg = file_data['package']
        for class_info in file_data['classes']:
            builder.add_class(pkg, class_info)

            if class_info.get('extends'):
                builder.add_relationship(class_info['name'], class_info['extends'], 'extends')
            if class_info.get('implements'):
                for iface in class_info['implements']:
                    builder.add_relationship(class_info['name'], iface, 'implements')
            for dep in class_info.get('dependencies', []):
                if dep != class_info['name']:
                    builder.add_relationship(class_info['name'], dep, 'uses')

    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(builder.build())
        logging.info(f"Diagram generated at {output_path}")
    except Exception as e:
        logging.error(f"Failed to write PlantUML diagram: {e}", exc_info=True)


class DiagramBuilder:
    def __init__(self):
        self.packages = defaultdict(list)
        self.relationships = set()
        self.buffer = []

    def add_class(self, package_name, class_data):
        self.packages[package_name].append(class_data)

    def add_relationship(self, source, target, rel_type):
        arrow = {
            "extends": f"{target} <|-- {source} : extends",
            "implements": f"{target} <|.. {source} : implements",
            "uses": f"{source} ..> {target} : uses"
        }.get(rel_type)
        if arrow:
            self.relationships.add(arrow)

    def build(self):
        self._write_header()
        self._write_packages()
        self._write_relationships()
        self._write_footer()
        return "\n".join(self.buffer)

    def _write_header(self):
        self.buffer.append("@startuml")
        self.buffer.append("skinparam packageStyle rect")
        self.buffer.append("title CodeComprehender Architecture Diagram\n")

    def _write_packages(self):
        for package_name, classes in self.packages.items():
            alias = package_name.replace(".", "_")
            self.buffer.append(f'package "{package_name}" as {alias} {{')
            for class_data in classes:
                self.buffer.append(write_class_block_inline(class_data))
            self.buffer.append("}")

    def _write_relationships(self):
        self.buffer.append("\n' Relationships")
        for r in sorted(self.relationships):
            self.buffer.append(r)

    def _write_footer(self):
        self.buffer.append("\n@enduml")

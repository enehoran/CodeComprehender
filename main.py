import argparse
import logging
import os
import re
from pathlib import Path

from dotenv import load_dotenv
from tqdm import tqdm

import code_parser
import comment_inserter
import diagram_builder
import llm_handler


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
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output.")
    parser.add_argument("--no_generate_suggestions", action="store_false",
                        help="By default, the tool adds suggestions within added comments in the form of TODOs, and creates a markdown document with high-level comments in the specified output directory. If set, these features are skipped.")
    args = parser.parse_args()
    generate_suggestions = not args.no_generate_suggestions

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
        logging.info("Verbose mode is enabled.")
    else:
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

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
        client = llm_handler.configure_llm(args.api_key)
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

    # First pass: build index of all project classes to enable tracking dependencies.
    project_class_index = code_parser.build_class_index(java_files)

    # Second pass: parse contents of all classes.
    # TODO: consider using parallel processing for a future version. I'm limited right now because of the LLM quota anyways.
    for file_path in tqdm(filtered_java_files, desc="Processing Java files", unit="files",
                          total=len(filtered_java_files)):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except Exception as e:
            logging.error(f"Could not read file {file_path}: {e}", exc_info=True)
            continue

        parsed_structure = code_parser.parse_java_file(file_path, lines, project_class_index)
        if parsed_structure:
            all_parsed_data.append(parsed_structure)

            structure_with_comments = llm_handler.generate_comments_for_structure(parsed_structure, client,
                                                                                  generate_suggestions)
            comment_inserter.create_commented_file(structure_with_comments, output_path)

    if all_parsed_data:
        # Generate a document with high-level documentation and comments.
        if generate_suggestions:
            high_level_comment = llm_handler.generate_high_level_comments(all_parsed_data, client, source_path)
            try:
                with open(output_path / "README_CODECOMPREHENDER.md", 'w', encoding='utf-8') as f:
                    f.write(high_level_comment)
                logging.info(f"High-level comments generated at {output_path}/README_CODECOMPREHENDER.md")
            except Exception as e:
                logging.error(f"Failed to write high-level comments: {e}", exc_info=True)

        # Create fully comprehensive UML specifications (often much too complex to read clearly).
        uml_code = diagram_builder.generate_architecture_diagram(all_parsed_data, output_path)
        # Simplify UML using LLM to reduce visual clutter.
        simplified_uml = llm_handler.generate_simplified_uml(client, source_path, uml_code)

        simplified_file = output_path / "architecture_simplified_view.puml"
        full_file = output_path / "architecture_full.puml"
        diagram_builder.write_uml(simplified_file, simplified_uml, "simplified architecture")
        diagram_builder.write_uml(full_file, uml_code, "full architecture")
    logging.info("Processing complete.")


if __name__ == "__main__":
    main()

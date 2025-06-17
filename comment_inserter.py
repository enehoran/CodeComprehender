from pathlib import Path
import logging


def create_commented_file(parsed_structure_with_comments, output_dir):
    """
    Creates a new Java file with generated comments inserted.
    """
    original_path = Path(parsed_structure_with_comments['file_path'])
    output_filename = original_path.stem + "_commented.java"
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

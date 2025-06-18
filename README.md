# CodeComprehender

CodeComprehender is a powerful tool for automated Java code documentation. It analyzes Java source code, generates comprehensive comments using Google's Gemini LLM (Large Language Model), creates UML diagrams to visualize the code architecture, and produces high-level documentation for better code understanding.

## Features

- Parse Java code to extract class structure, methods, fields, and dependencies
- Generate detailed JavaDoc-style comments for classes and methods using LLMs
- Create both detailed and simplified UML diagrams to visualize code architecture
- Produce high-level documentation with project overview
- Customizable output with regex-based file/directory exclusion
- Optional suggestion mode for code improvements

## Installation

### Prerequisites

- Python 3.8 or higher
- Graphviz (required for UML diagram generation)
  - Download and install from: https://graphviz.org/download/
- Google Gemini API key

### Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/CodeComprehender.git
   cd CodeComprehender
   ```

2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up your Gemini API key in a `.env` file or as an environment variable:
   ```
   GEMINI_API_KEY=your_api_key_here
   ```

## Usage

Basic usage:

```bash
python main.py <source_dir> <output_dir> [options]
```

### Arguments

- `source_dir`: The source directory containing Java files
- `output_dir`: The directory to save commented files and diagrams

### Options

- `--api_key KEY`: API key for the Gemini LLM (can also be set via GEMINI_API_KEY environment variable)
- `--exclude PATTERN [PATTERN ...]`: A list of regex patterns to exclude files/directories (e.g., `--exclude '.*Test.java' 'build/.*'`)
- `--verbose`: Enable verbose output
- `--generate_suggestions`: Generates suggestions within added comments in the form of TODOs, and creates a markdown document with high-level comments

### Example

```bash
# Basic usage: outputs saved directly in output directory
python main.py ./my-java-project ./my-java-project-output

# Basic usage: outputs saved directly in source directory
python main.py ./my-java-project ./my-java-project

# Exclude test and build files and use verbose mode
python main.py ./my-java-project ./documentation --exclude '.*Test.java' 'build/.*' --verbose

# Use a specific API key
python main.py ./my-java-project ./documentation --api_key YOUR_API_KEY_HERE
```

## Output

The tool generates:

1. Commented Java files with the suffix "_commented" in the output directory, preserving the package structure.
   - If using `--generate_suggestions`, the comments also contain TODO suggestions to improve code structure and readability.
2. UML diagrams:
   - `architecture_full.puml`: Complete architecture diagram with all classes and relationships.
      - For large code directories, it is NOT recommended to use this directly. In such cases, it is recommended to use the simplified view instead, described below.
   - `architecture_simplified_view.puml`: Simplified architecture diagram for better readability.
     - This view is optimized for reducing visual clutter while preserving the most important architectural relationships and structures.
   - To view the generated diagrams, you may use a PlantUML server such as [PlantText](https://www.planttext.com/) or [PlantUML Web Server](plantuml.com).
3. `README_CODECOMPREHENDER.md`: High-level documentation of the source project with suggestions for code improvement 
   (when using `--generate_suggestions`)

## How It Works

1. **Parsing**: Uses the javalang library to parse Java source code.
2. **Analysis**: Programmatically extracts class structure, methods, fields, and dependencies.
3. **Documentation Generation**: Uses Google's Gemini LLM to generate comments, using the structure analysis as input.
4. **UML Creation**: Generates PlantUML diagrams showing class relationships. This is implemented as two steps:
   1. **Programmatic Step**: Programmatic generation of a highly comprehensive PlantUML code for an architecture diagram based on the structure analysis.
   2. **LLM-Based Step**: The comprehensive PlantUML code is input into an LLM, and the LLM simplifies the PlantUML code as much as needed 
      based on the complexity of the class structures and relationships. This step ensures an appropriate amount of
      granularity of the output diagram that is optimmized for reducing visual clutter while preserving the key
      architectural relationships and structures.

## Dependencies

- google-genai: For Google's Gemini API
- javalang: For parsing Java code
- graphviz: For creating architecture diagrams
- plantweb: For rendering PlantUML diagrams
- python-dotenv: For loading environment variables
- gitpython: For cloning git repositories (if needed)

## Project Structure

- `main.py`: Entry point of the application
- `code_parser.py`: Functions for parsing Java code
- `llm_handler.py`: Functions for interacting with LLMs
- `diagram_builder.py`: Functions for generating UML diagrams
- `comment_inserter.py`: Functions for inserting comments into Java files
- `prompts.py`: Prompts for the LLM
- `tests/`: Unit tests for the project

## Testing

The project includes a suite of unit tests for the main components. To run the tests:

```bash
python tests/run_tests.py
```

For more information about the tests, see the [tests README](tests/README.md).

## License

[MIT License](LICENSE)

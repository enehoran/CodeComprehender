# CodeComprehender

CodeComprehender is a tool for automated Java code documentation. It analyzes Java code, generates comments using LLMs (Language Learning Models), and creates UML diagrams to visualize the code architecture.

## Features

- Parse Java code to extract class structure, methods, fields, and dependencies
- Generate comments for classes and methods using LLMs
- Create UML diagrams to visualize code architecture
- Output commented code and diagrams to a specified directory

## Installation

1. Clone the repository
2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Set up your Gemini API key in a `.env` file or as an environment variable:
   ```
   GEMINI_API_KEY=your_api_key_here
   ```

## Usage

```bash
python main.py <source_dir> <output_dir> [options]
```

### Arguments

- `source_dir`: The source directory containing Java files
- `output_dir`: The directory to save commented files and diagrams

### Options

- `--api_key`: API key for the Gemini LLM (can also be set via GEMINI_API_KEY environment variable)
- `--exclude`: A list of regex patterns to exclude files/directories
- `--verbose`: Enable verbose output
- `--generate_suggestions`: Include suggestions within added comments in the form of TODOs, and creates a markdown document with high-level comments

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
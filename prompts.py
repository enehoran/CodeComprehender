JAVA_COMMENT_GENERATION_PROMPT = """Generate a concise Javadoc comment for the following Java {element_type}. Describe its purpose, parameters, and return value if applicable. Do not include the original code in your response.\n\nCode:\n```java\n{code_snippet}\n```
"""

JAVA_COMMENT_GENERATION_PROMPT_WITH_SUGGESTIONS = """Generate a concise Javadoc comment for the following Java {element_type}.
First, describe its purpose, parameters, and return value if applicable.
Then, if you notice any issues related to code quality, outdated or inconsistent code, or uncaught bugs, provide a short suggestion in the form of a TODO. Most likely, you will not have anything to add.
Do not include the original code in your response.\n\nCode:\n```java\n{code_snippet}\n```
"""

README_GENERATION_PROMPT = """
Generate a detailed markdown README.md file for the provided Java code.
Then, if you notice any high-level issues related to tech debt, Java or OOP coding standards, or uncaught bugs, provide a few bullet points with suggestions for improvement. You might not have anything to add.
Do not include the original code in your response.
Output your response in Markdown format only, without any additional text explaining your response.

Parsed Java data:
{all_parsed_data}
"""

SIMPLIFY_UML_PROMPT = """You are an expert software architect. Your task is to simplify a PlantUML class diagram to make it more readable and focused for architectural understanding.

INPUT:
Below is a PlantUML diagram describing the class structure of a Java project. It may include classes, interfaces, abstract classes, fields, methods, and relationships such as inheritance, implementation, and usage.

PlantUML code:
{plantuml_code}

Your goal is to reduce visual clutter while preserving the most important architectural relationships and structures.
You will determine the optimal level of granularity in which to display the architecture diagram, and simplify the diagram as needed according to your judgment.

PLANTUML:
\"\"\"
@startuml
skinparam classAttributeIconSize 0
...
@enduml
\"\"\"

SIMPLIFICATION RULES:
1. **Hide Internal Details** (if needed):
   - Remove private and protected fields and methods.
   - Keep only public methods that define the external API.
   - Omit class fields unless they are `public static final` or essential to understanding the structure.

2. **Flatten the Structure**:
   - Remove nested classes or represent them as standalone top-level classes (if relevant).
   - Remove trivial relationships (e.g., "uses" links to utility or logger classes).

3. **Group & Rename**:
   - Group classes by high-level packages.
   - Use aliases for verbose package names (e.g., `com.company.module.api` → `api`).

4. **Prune the Diagram**:
   - Exclude test classes or test-related packages.
   - Collapse redundant classes/interfaces.
   - Limit to at most 30 key classes/interfaces.

5. **Improve Layout Readability**:
   - Use `skinparam linetype ortho`
   - Use `hide empty members`
   - Add comments to sections if necessary (e.g., `// Service Layer`)

OUTPUT:
Return the updated PlantUML code with the simplifications applied.

IMPORTANT:
- Do not generate new classes; only simplify what is already there.
- Maintain valid PlantUML syntax from `@startuml` to `@enduml`.
- Return only PlantUML code. Do not add any text or explanations before @startuml or after @enduml.
"""
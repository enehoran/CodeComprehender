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
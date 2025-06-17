JAVA_COMMENT_GENERATION_PROMPT = """
Generate a concise Javadoc comment for the following Java {element_type}. Describe its purpose, parameters, and return value if applicable. Do not include the original code in your response.\n\nCode:\n```java\n{code_snippet}\n```
"""
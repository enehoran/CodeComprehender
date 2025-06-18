import logging
from google import genai
import time
import prompts

_initial_retry_delay = 2

def configure_llm(api_key):
    """Configures the generative AI model."""
    client = genai.Client(api_key=api_key)
    logging.info("Generative AI model configured successfully.")
    return client

def get_llm_comment(client, code_snippet, element_type, model_name="gemini-2.0-flash", prompt=prompts.JAVA_COMMENT_GENERATION_PROMPT, num_retries=8):
    """
    Generates a comment for a given code snippet using the LLM.
    """
    if not client:
        return f"/**\n * LLM not configured. Placeholder for {element_type}.\n */"
    prompt = prompt.format(element_type=element_type, code_snippet=code_snippet)
    for attempt in range(num_retries):
        try:
            response = client.models.generate_content(
                model=model_name,
                config=genai.types.GenerateContentConfig(
                system_instruction="You are a helpful Java documentation assistant."),
                contents=prompt
            )
            if response.text:
                # Basic cleanup of the response
                cleaned_text = response.text.replace("```java", "").replace("```", "").strip()
                if not cleaned_text.startswith("/**"):
                    cleaned_text = "/**\n * " + cleaned_text
                if not cleaned_text.endswith("*/"):
                    cleaned_text = cleaned_text + "\n */"
                return cleaned_text
        except Exception as e:
            logging.warning(f"Error calling LLM API on attempt {attempt + 1}: {e}")

        if attempt < num_retries - 1:
            wait_time = _initial_retry_delay * (2 ** attempt)
            logging.info(f"Retrying LLM call in {wait_time} seconds...")
            time.sleep(wait_time)

    logging.error(f"LLM returned an empty or failed response after {num_retries} attempts for a {element_type}.")
    return f"/**\n * Failed to generate comment for this {element_type} after multiple retries.\n */"


def generate_comments_for_structure(parsed_structure, client):
    """
    Generates comments for classes and methods using the configured LLM.
    """
    logging.debug(f"Generating comments for {parsed_structure['file_path']}...")
    if not client:
        logging.warning("LLM model is not available. Skipping comment generation.")
        return parsed_structure

    for class_info in parsed_structure.get('classes', []):
        class_info['comment'] = get_llm_comment(client, class_info['code_snippet'], 'class', prompt=prompts.JAVA_COMMENT_GENERATION_PROMPT_WITH_SUGGESTIONS)
        for method_info in class_info.get('methods', []):
            method_info['comment'] = get_llm_comment(client, method_info['code_snippet'], 'method',  prompt=prompts.JAVA_COMMENT_GENERATION_PROMPT_WITH_SUGGESTIONS)

    return parsed_structure


def generate_high_level_comments(all_parsed_data, client, directory, model_name="gemini-2.0-flash", num_retries=8):
    logging.debug(f"Generating overall comments for {directory}...")
    if not client:
        logging.warning("LLM model is not available. Skipping overall comments generation.")
        return None
    for attempt in range(num_retries):
        try:
            response = client.models.generate_content(
                model=model_name,
                config=genai.types.GenerateContentConfig(
                    system_instruction="You are a helpful Java documentation assistant."),
                contents=prompts.README_GENERATION_PROMPT.format(all_parsed_data=all_parsed_data),
            )
            if response.text:
                return response.text.strip().removeprefix("```markdown").removesuffix("```")
        except Exception as e:
            logging.warning(f"Error calling LLM API on attempt {attempt + 1}: {e}")

        if attempt < num_retries - 1:
            wait_time = _initial_retry_delay * (2 ** attempt)
            logging.info(f"Retrying LLM call in {wait_time} seconds...")
            time.sleep(wait_time)

    logging.error(f"LLM returned an empty or failed response after {num_retries} attempts for a directory-level comment.")
    return None


def generate_simplified_uml(client, directory, uml_buffer, model_name="gemini-2.0-flash", num_retries=8):
    logging.debug(f"Simplifying architecture diagram for {directory}...")
    if not client:
        logging.warning("LLM model is not available. Skipping overall comments generation.")
        return None
    for attempt in range(num_retries):
        try:
            response = client.models.generate_content(
                model=model_name,
                config=genai.types.GenerateContentConfig(
                    temperature=0.1
                ),
                contents=prompts.SIMPLIFY_UML_PROMPT.format(plantuml_code=uml_buffer),
            )
            if response.text:
                return response.text.strip().removeprefix("```plantuml").removesuffix("```")
        except Exception as e:
            logging.warning(f"Error calling LLM API on attempt {attempt + 1}: {e}")

        if attempt < num_retries - 1:
            wait_time = _initial_retry_delay * (2 ** attempt)
            logging.info(f"Retrying LLM call in {wait_time} seconds...")
            time.sleep(wait_time)

    logging.error(f"LLM returned an empty or failed response after {num_retries} attempts for a directory-level comment.")
    return None
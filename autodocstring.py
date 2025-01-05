import ast
import os
from argparse import ArgumentParser

import google.generativeai as genai
from dotenv import load_dotenv
from google.api_core.exceptions import InternalServerError, NotFound


def check_env():
    """Checks if required environment variables are set.

  This function verifies the presence of a necessary environment variable.

  Args:
    None

  Returns:
    None.  The function implicitly returns None if the environment variable is found.

  Raises:
    ValueError: If the 'GEMINI_API_KEY' environment variable is not set.

  Examples:
    >>> check_env()  # Raises ValueError if GEMINI_API_KEY is not set.
    >>> os.environ['GEMINI_API_KEY'] = 'my_api_key'
    >>> check_env()  # Does not raise any error.

  """
    load_dotenv()
    if not os.getenv('GEMINI_API_KEY'):
        raise ValueError('No Gemini API key found in your PATH.')


def generate_docstring(function_code, model, tries=2):
    """Generates a Google style docstring for a given Python function code.

  This function utilizes a language model to analyze provided Python function code
  and automatically generate a comprehensive docstring adhering to Google style
  guidelines.  The docstring includes a description of the function's purpose,
  parameter explanations, return value details, potential exceptions, and usage
  examples.

  Args:
    function_code: The Python function code as a string.  This should be valid
                   Python code representing a single function.
    model: A language model object capable of generating text based on a prompt.
           The model must have a `generate_content` method that accepts a string
           prompt and returns a response object with a `.text` attribute containing
           the generated text.
    tries: The number of attempts to generate a docstring before raising an
           exception. Defaults to 2.

  Returns:
    A string containing the generated Google style docstring.  Returns an empty
    string if no docstring could be extracted from the model's response.

  Raises:
    Exception: If a valid docstring cannot be generated after multiple attempts.
               This typically occurs if the language model fails to produce a
               response containing a properly formatted docstring.
    """
    prompt = "Analyze the following python function and generate a google style docstring that includes:\n    * A description of the function's purpose without revealing internal details.\n    * An explanation of each parameter, including their types and expected values.\n    * A description of the function's return value, including its type and possible values.\n    * Any potential exceptions that the function might raise.\n    * A few examples of how to use the function.{}"
    while tries > 0:
        response = model.generate_content(prompt.format(function_code))
        raw_docstring = response.text
        docstring = raw_docstring.find('"""')
        if docstring != -1:
            docstring_start = docstring + 3
            docstring_end = raw_docstring.find('"""', docstring_start)
            if docstring_end == -1:
                docstring_end = len(raw_docstring)
                raw_docstring += '"""'
            final_docstring = raw_docstring[docstring_start:docstring_end]
            return final_docstring
        else:
            print(
                f'Could not find opening triple quotes for function, regenerating... {node.name}')
            tries -= 1
    raise Exception(
        f'Failed to generate docstring after multiple attempts for function {node.name}')


def main(file_path, model_name):
    """Automates the generation and insertion of docstrings into Python functions within a file.

  This function processes a Python source code file, identifies functions, and uses a specified
  language model to generate docstrings for each function.  The generated docstrings are then
  inserted into the source code file, updating it in place.

  Args:
    file_path: The path to the Python source code file.  Must be a readable and writable file.
    model_name: The name of the Generative AI model to use for docstring generation.  
                Must be a valid model name supported by the underlying AI service.

  Returns:
    None. Modifies the input file directly by adding docstrings to functions.

  Raises:
    FileNotFoundError: If the specified file_path does not exist.
    PermissionError: If the script does not have permission to read or write to the file.
    Exception: If there's an error during AST parsing, docstring generation, or file writing.  
               Specific exceptions may include `NotFound`, `InternalServerError` from the AI service,
               or syntax errors from the Python parser.  The specific error message will be printed to the console.

  Examples:
    main("my_script.py", "models/my-docstring-model")
    main("/path/to/my/code/functions.py", "text-bison-001")
  """
    genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
    try:
        model = genai.GenerativeModel(model_name)
    except NotFound as e:
        print(f'Error: Invalid model: {e}')
        exit(1)
    except InternalServerError as e:
        print(f'Error: Internal google error: {e}')
        exit(1)
    with open(file_path, 'r') as f:
        src = f.read()
        try:
            tree = ast.parse(src)
        except Exception as e:
            print(f'Error: Invalid syntax in file: {e}')
            exit(1)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
                function_code = ast.get_source_segment(src, node)
                print(f'Generating docstring to {node.name}...')
                try:
                    docstring = generate_docstring(function_code, model)
                except Exception as e:
                    print(
                        f'Error generating docstring for {node.name} after several retries: {e}')
                    continue
                node.body = [ast.Expr(value=ast.Constant(
                    value=docstring, kind=None))] + node.body
                updated_src = ast.unparse(tree)
                with open(file_path, 'w') as f:
                    f.write(updated_src)


if __name__ == '__main__':
    check_env()
    args = ArgumentParser()
    args.add_argument('module', help='Path to the python module.')
    args.add_argument('--model', help='Choose available model.',
                      default='gemini-1.5-flash')
    parsed_args = args.parse_args()
    file_path = parsed_args.module
    model = parsed_args.model
    if not os.path.exists(file_path) or file_path[-3:] != '.py':
        raise FileNotFoundError(
            f'Error: File not found or invalid python file: {file_path}')
    main(file_path, model)

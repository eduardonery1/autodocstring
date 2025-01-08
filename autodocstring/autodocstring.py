import ast
import logging
import os
import sys
from argparse import ArgumentParser

import google.generativeai as genai
from dotenv import load_dotenv
from google.api_core.exceptions import InternalServerError, NotFound


class DocstringGenerationError(Exception):
    """ Custom exception for docstring generation errors. """
    pass

def generate_docstring(function_code, function_name, model, tries=2, extensive=False):
    """Generate a docstring for a given Python function.

Args:
  function_code (str): The code of the Python function.
  function_name (str): The name of the Python function.
  model: A language model capable of generating text.  Must have a `generate_content` method.
  tries (int, optional): The number of times to retry generating the docstring if an error occurs. Defaults to 2.
  extensive (bool, optional): If True, generates a more extensive docstring including examples. Defaults to False.

Returns:
  str: The generated docstring, or None if generation fails after multiple tries.

Raises:
  Exception: If the language model's `generate_content` method raises an exception.
"""

    prompt_extensive = "Analyze the following python function and generate a google style docstring that includes:\n    * A description of the function's purpose without revealing internal details.\n    * An explanation of each parameter, including their types and expected values.\n    * A description of the function's return value, including its type and possible values.\n    * Any potential exceptions that the function might raise.\n    * A few examples of how to use the function. Include the triple quotes at the beginning and the end of the text.{}"
    prompt_simple = "Analyze the following python function and generate a short and consise google style docstring that includes:\n    * A description of the function's purpose without revealing internal details.\n    * An explanation of each parameter, including their types and expected values.\n    * A description of the function's return value, including its type and possible values.\n    * Any potential exceptions that the function might raise. Include the triple quotes at the beginning and the end of the text. {}"
    prompt = prompt_extensive if extensive else prompt_simple

    for attempt in range(tries):
        try:
            response = model.generate_content(prompt.format(function_code))
        except Exception:
            logging.exception(
                f'Error generating docstring at attempt {attempt + 1}.')
            continue
        raw_docstring = response.text
        logging.debug(f"Generated this docstring for {function_name}: {raw_docstring}")

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
            logging.warning(
                f'Could not find opening triple quotes for function, regenerating... {function_name}')
    logging.error(
        f'Could not generate docstrings in a good format for this method: {function_name}.')
    raise DocstringGenerationError


def generate_all_docstrings(file_path, model, methods, overwrite, extensive):
    """Generates docstrings for functions in a Python file.

Args:
  file_path (str): Path to the Python file.
  model: The model used to generate docstrings.  Type varies depending on the specific model used.
  methods (list, optional): List of function names to generate docstrings for. Defaults to generating docstrings for all functions.
  extensive (bool, optional): Whether to generate extensive docstrings. Defaults to False.

Returns:
  str: The modified source code with generated docstrings.  Returns None if any error occurs during docstring generation for all functions.

Raises:
  Exception: If there's a syntax error in the input file.
"""

    with open(file_path, 'r') as f:
        src = f.read()

    try:
        tree = ast.parse(src)
    except Exception as e:
        logging.exception(f'Error: Invalid syntax in file:')
        sys.exit()

    if not methods:
        methods = []

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
            private_method = node.name.startswith('_')
            not_listed_method = node.name not in methods
            current_docstring = ast.get_docstring(node)
            has_docstring = current_docstring is not None

            logging.debug("Params for method checking {}: {}".format(node.name, {
                'private_method': private_method,
                'listed_method': not_listed_method,
                'has_docstring': has_docstring,
                'overwrite': overwrite
                }))

            # methods and private and not listed and (docstring or overwrite)
            if  (methods is not None and 
                ((private_method and not_listed_method) or (has_docstring and not overwrite))
                 ):
                continue
             
            function_code = ast.get_source_segment(src, node)
            print(f'Generating docstring to {node.name}...')
            
            try:
                docstring = generate_docstring(
                    function_code, node.name, model, extensive=extensive)
            except DocstringGenerationError:
                logging.exception(f"Couldn't generate a docstring for {node.name}")
                continue

            if has_docstring and overwrite: 
                logging.debug(f"Element 0 at body: {ast.unparse(node.body[0])}")
                del node.body[0] 
            node.body = [ast.Expr(value=ast.Constant(value=docstring, kind=None))] + node.body
            logging.debug(f"Method's body after editing: {ast.unparse(node)}")
    try:
        return ast.unparse(tree)
    except Exception:
        logging.exception("Exception unparsing file:")


def main():
    available_models = ['gemini-2.0-flash-exp', 'gemini-1.5-flash',
                        'gemini-1.5-flash-8b', 'gemini-1.5-pro', 'gemini-1.0-pro']
    default_model = available_models[1]

    args = ArgumentParser()
    args.add_argument('module', help='Path to the python module.')
    args.add_argument(
        '--methods', help='Choose specific methods in the module. If left blank all public methods will be documented.', nargs='+')
    args.add_argument(
        '--model', help=f'Choose available model. {available_models}', default=default_model)
    args.add_argument('--no-backup', help='Choose not create a backup for the original file',
                      default=False, action='store_true')
    args.add_argument('--extensive', help='Choose to use an extensive docstring with examples in Google style.',
                      default=False, action='store_true')
    args.add_argument('--debug', action='store_true', default=False)
    args.add_argument('--overwrite', action='store_true', default=False)

    parsed_args = args.parse_args()
    file_path = parsed_args.module
    methods = parsed_args.methods
    model_name = parsed_args.model
    no_backup = parsed_args.no_backup
    extensive = parsed_args.extensive
    debug = parsed_args.debug
    overwrite = parsed_args.overwrite

    logging_level = logging.DEBUG if debug else logging.WARNING
    logging.basicConfig(level=logging_level)
    logging.debug(vars(parsed_args))
    
    # Checking environment and arguments
    valid_extensions = {'.py', '.pyi', '.pyw', '.py.bak'}
    if not os.path.exists(file_path) or not any((ext in file_path for ext in valid_extensions)):
        raise FileNotFoundError(
            f'Error: File not found or invalid python file: {file_path}')

    load_dotenv()
    if not os.getenv('GEMINI_API_KEY'):
        raise EnvironmentError('No Gemini API key found in your PATH.')

    if model_name not in available_models:
        raise ValueError(
            f'Error: Model "{model_name}" not found. Choose one of: {available_models}')
    
    # Loading model
    genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
    try:
        model = genai.GenerativeModel(model_name)
    except NotFound as e:
        logging.exception(f'Error: Invalid model "{model_name}":')
        sys.exit()
    except InternalServerError as e:
        logging.exception(f'Error: Internal google error:')
        sys.exit()
    
    # Generating and modifying file 
    updated_src = generate_all_docstrings(file_path, model, methods, overwrite, extensive)

    if not no_backup:
        backup_file = file_path + '.bak'
        if os.path.exists(backup_file):
            os.remove(backup_file)
        os.rename(file_path, backup_file)

    with open(file_path, 'w') as f:
        f.write(updated_src)

if __name__ == '__main__':
    main()

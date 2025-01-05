import os
import ast
from argparse import ArgumentParser
from dotenv import load_dotenv
import google.generativeai as genai
from google.api_core.exceptions import NotFound, InternalServerError


def check_env():
    load_dotenv()
    if not os.getenv('GEMINI_API_KEY'):
        raise ValueError("No Gemini API key found in your PATH.")

def generate_docstring(function_code, model, tries = 2):
    prompt = """
    Analyze the following python function and generate a google style docstring that includes:
    * A description of the function's purpose without revealing internal details.
    * An explanation of each parameter, including their types and expected values.
    * A description of the function's return value, including its type and possible values.
    * Any potential exceptions that the function might raise.
    * A few examples of how to use the function.{}"""
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
            print(f"Could not find opening triple quotes for function, regenerating... {node.name}")
            tries -= 1
    raise Exception(f"Failed to generate docstring after multiple attempts for function {node.name}")

def main(file_path, model_name):
    genai.configure(api_key=os.getenv('GEMINI_API_KEY'))

    try:
        model = genai.GenerativeModel(model_name)
    except NotFound as e:
        print(f"Error: Invalid model: {e}")
        exit(1)
    except InternalServerError as e:
        print(f"Error: Internal google error: {e}")
        exit(1)

    with open(file_path, "r") as f:
        src = f.read()
        try:
            tree = ast.parse(src)
        except Exception as e:
            print(f"Error: Invalid syntax in file: {e}")
            exit(1)

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
                function_code = ast.get_source_segment(src, node)
                print(f"Generating docstring to {node.name}...")
                try:
                    docstring = generate_docstring(function_code, model)
                except Exception as e:
                    print(f"Error generating docstring for {node.name} after several retries: {e}")
                    continue

                node.body = [ast.Expr(value=ast.Constant(value=docstring, kind=None))] + node.body
                #Rewrite the file with the updated AST
                updated_src = ast.unparse(tree)
                with open(file_path, "w") as f:
                    f.write(updated_src)

if __name__=="__main__":
    check_env()

    args = ArgumentParser()
    args.add_argument("module", help="Path to the python module.")
    args.add_argument("--model", help="Choose available model.", default="gemini-1.5-flash")

    parsed_args = args.parse_args()
    file_path = parsed_args.module
    model = parsed_args.model
    if not os.path.exists(file_path) or file_path[-3:] != ".py":
        raise FileNotFoundError(f"Error: File not found or invalid python file: {file_path}")

    main(file_path, model)
    


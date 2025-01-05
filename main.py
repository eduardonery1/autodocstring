import os
import ast
from argparse import ArgumentParser
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()
API_KEY=os.getenv('GEMINI_API_KEY')

args = ArgumentParser()
args.add_argument("--module", help="path to the python module", required=True)
parsed_args = args.parse_args()

file_path = parsed_args.module
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

with open(file_path, "r") as f:
    src = f.read()
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            function_code = ast.get_source_segment(src, node)
            response = model.generate_content(f"""
Analyze the following python function and generate a comprehensive docstring in google style that includes:
* A description of the function's purpose.
* A detailed explanation of each parameter, including their types and expected values.
* A description of the function's return value, including its type and possible values.
* Any potential exceptions that the function might raise.
* Examples of how to use the function. DON'T REWRITE THE FUNCTION, WRITE ONLY THE DOCSTRING.{function_code}""")
            raw_docstring = response.text
            docstring = raw_docstring.find('"""')
            if docstring != -1:
                docstring_start = docstring + 3
                docstring_end = raw_docstring.find('"""', docstring_start)
                if docstring_end != -1:
                    final_docstring = raw_docstring[docstring_start:docstring_end]
                    print(final_docstring)
                    # Insert the generated docstring into the AST
                    node.body = [ast.Expr(value=ast.Constant(value=final_docstring, kind=None))] + node.body
                    
                    #Rewrite the file with the updated AST
                    updated_src = ast.unparse(tree)
                    with open(file_path, "w") as f:
                        f.write(updated_src)
                else:
                    print(f"Could not find closing triple quotes for function {node.name}")
            else:
                print(f"Could not find opening triple quotes for function {node.name}")

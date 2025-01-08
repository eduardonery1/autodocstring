# Autodocstring
I made this tool to improve code quality without much headache.

Have ```GEMINI_API_KEY``` defined in your PATH. You can do this by [following these steps](https://ai.google.dev/gemini-api/docs/api-key).
```bash
pip install autodocstring
```
Run this to generate docstrings to all your public methods at the desired python module.
```bash
autodocstring path/to/file
```
You may also want to target specific methods by using the ```--methods```parameter. The tool generates a backup file by default.

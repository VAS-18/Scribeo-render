import re
def extract_python_code(markdown_text: str):
    match = re.search(r"```python\n(.*?)```", markdown_text, re.DOTALL)
    if match:
        return match.group(1)
    return None
"""Small strict reader for generated KiCad S-expressions, including EOF checks."""
import json
import re

def read(path):
    stack = []
    roots = []
    for token in re.findall(r'"(?:\\.|[^"\\])*"|[()]|[^\s()"]+', path.read_text(encoding='utf-8')):
        if token == '(':
            node = []
            (stack[-1] if stack else roots).append(node)
            stack.append(node)
        elif token == ')':
            if not stack:
                raise ValueError(f'Unexpected closing parenthesis in {path}')
            stack.pop()
        else:
            if not stack:
                raise ValueError(f'Unexpected content after root in {path}')
            stack[-1].append(json.loads(token) if token.startswith('"') else token)
    if stack or len(roots) != 1:
        raise ValueError(f'Incomplete or multiple root expressions in {path}')
    return roots[0]

def children(node, name):
    return [v for v in node if isinstance(v,list) and v and v[0] == name]

from pathlib import Path
import re

path = Path('src/app/page.tsx')
text = path.read_text(encoding='utf-8')
lines = text.splitlines()
stack = []
for i, line in enumerate(lines, 1):
    tokens = re.findall(r'</div>|<div(?:\s|>)', line)
    for token in tokens:
        if token.startswith('<div'):
            stack.append((i, line.strip()))
        elif token == '</div>':
            if stack:
                stack.pop()
            else:
                print('extra closing div at', i)
    if i in [170, 180, 190, 210, 240, 280, 320, 340, 360, 380, 400, 420, 426]:
        print('line', i, 'stack depth', len(stack), 'top', stack[-3:])

print('final stack depth', len(stack))
print('remaining opens', stack[-20:])

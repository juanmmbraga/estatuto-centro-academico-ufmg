#!/usr/bin/env python3
import argparse
import re
from pathlib import Path

parser = argparse.ArgumentParser(
    description='Converte os TODOs do estatuto em notas de rodapé.'
)
parser.add_argument(
    '--remove-comments',
    action='store_true',
    help='Remove os TODOs classificados como comentários.',
)
parser.add_argument(
    '--remove-references',
    action='store_true',
    help='Remove os TODOs classificados como referências.',
)
parser.add_argument(
    '--remove-updates',
    action='store_true',
    help='Remove os TODOs classificados como atualizações.',
)
args = parser.parse_args()

src = Path('estatuto.tex')
out = Path('footnote.tex')
text = src.read_text(encoding='utf-8')

categories_to_remove = {
    category
    for flag, category in [
        (args.remove_comments, 'Comentário'),
        (args.remove_references, 'Referência'),
        (args.remove_updates, 'Update'),
    ]
    if flag
}

def classify(content):
    low = content.lower()
    if any(k in low for k in ['art.', 'artigo', 'artigo', 'art ']):
        return 'Referência'
    if any(k in low for k in ['referênc', 'ref:', 'refere']):
        return 'Referência'
    if 'update' in low:
        return 'Update'
    return 'Comentário'


def normalize_content(content):
    cleaned = content.strip()
    cleaned = re.sub(r'^\\textbf\{(Comentário|Referência|Update):\}\s*', '', cleaned)
    cleaned = re.sub(r'^(Comentário|Referência|Update):\s*', '', cleaned)
    return cleaned

# Scanner to replace \todo[...]{...} while skipping occurrences on commented lines
res = []
i = 0
L = len(text)

while i < L:
    idx = text.find('\\todo[inline', i)
    if idx == -1:
        res.append(text[i:])
        break
    # check if this occurrence is on a commented line (there is a % before it on same line)
    line_start = text.rfind('\n', 0, idx)
    if line_start == -1:
        line_start = 0
    else:
        line_start += 1
    prefix = text[line_start:idx]
    if '%' in prefix:
        # skip this occurrence; leave as-is
        res.append(text[i:idx+1])
        i = idx+1
        continue
    # append text up to idx
    res.append(text[i:idx])
    # now parse optional bracket [...] after \todo
    j = idx + len('\\todo')
    if j < L and text[j] == '[':
        # find closing ] matching (no nesting in options expected)
        k = j+1
        while k < L and text[k] != ']':
            k += 1
        # now expect {
        k += 1
    else:
        # no optional arg: look for {
        k = j
    # skip whitespace to find first brace
    while k < L and text[k].isspace():
        k += 1
    if k >= L or text[k] != '{':
        # malformed, copy and skip
        res.append('\\todo')
        i = j
        continue
    # Now extract brace-balanced content starting at k
    brace_level = 0
    m = k
    while m < L:
        if text[m] == '{':
            brace_level += 1
        elif text[m] == '}':
            brace_level -= 1
            if brace_level == 0:
                m += 1
                break
        m += 1
    content = text[k+1:m-1]
    category = classify(content)
    content = normalize_content(content)
    if category not in categories_to_remove:
        # Keep original content trimmed
        replacement = f"\\footnote{{\\textbf{{{category}:}} {content}}}"
        res.append(replacement)
    i = m

new_text = ''.join(res)
# Insert footnote-number sizing snippet after the estatuto-config package line
snippet = (
    "\n\\makeatletter\n"
    "% Apenas o marcador no texto (superscript) será maior e em negrito, com grifo amarelo.\n"
    "% O marcador que aparece no rodapé permanece no tamanho normal; o texto da nota usa #1 corretamente.\n"
    "\\renewcommand{\\@makefnmark}{\\textsuperscript{\\setlength{\\fboxsep}{1.5pt}\\colorbox{yellow}{\\normalfont\\large\\textbf{\\color{black}\\@thefnmark}}}}\n"
    "\\renewcommand{\\@makefntext}[1]{\\noindent\\makebox[1.8em][r]{\\textsuperscript{\\normalfont\\@thefnmark}}\\,#1}\n"
    "\\makeatother\n\n"
)
pkg = '\\usepackage{estatuto-config}'
pos = new_text.find(pkg)
if pos != -1:
    # find end of the line that contains the package declaration
    line_end = new_text.find('\n', pos)
    if line_end == -1:
        # append at end if no newline
        new_text = new_text + '\n' + snippet
    else:
        insert_at = line_end + 1
        new_text = new_text[:insert_at] + snippet + new_text[insert_at:]
else:
    # fallback: prepend snippet to ensure it's present
    new_text = snippet + new_text
out.write_text(new_text, encoding='utf-8')
print('Wrote', out)

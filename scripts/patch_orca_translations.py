"""Give Orca's multi-argument messages names while retaining existing translations."""
import ast
import json
from pathlib import Path
import re
import sys


FIELDS = {
    'CELL_RANGE_SELECTED': ('first', 'last'),
    'CELL_RANGE_UNSELECTED': ('first', 'last'),
    'CLI_SPEECH_SYSTEM_ERROR': ('requested', 'available'),
    'CPU_AND_MEMORY_USAGE_LEVELS': ('cpu', 'memory'),
    'SIZE_AND_POSITION_BRIEF': ('width', 'height', 'x', 'y'),
    'SIZE_AND_POSITION_FULL': ('width', 'height', 'x', 'y'),
    'TABLE_COLUMN_RANGE_SELECTED': ('first', 'last'),
    'TABLE_COLUMN_RANGE_UNSELECTED': ('first', 'last'),
    'TABLE_ROW_RANGE_SELECTED': ('first', 'last'),
    'TABLE_ROW_RANGE_UNSELECTED': ('first', 'last'),
}
FORMAT = re.compile(r'%%|%([-+ #0]*\d*(?:\.\d+)?[sd])')
PO_FIELD = re.compile(r'^(msgid|msgstr|msgctxt) ("(?:[^"\\]|\\.)*")'
                      r'((?:\n"(?:[^"\\]|\\.)*")*)', re.M)


def named_format(value, names):
    matches = [match for match in FORMAT.finditer(value) if match[1] is not None]
    if len(matches) != len(names):
        raise ValueError(f'Unexpected format arguments: {value!r}')
    iterator = iter(names)
    return FORMAT.sub(lambda match: ('%(' + next(iterator) + ')' + match[1])
                      if match[1] is not None else match[0], value)


def migrate_catalog(text, messages):
    blocks = text.split('\n\n')
    changed = 0
    for index, block in enumerate(blocks):
        fields = {}
        for match in PO_FIELD.finditer(block):
            value = ''.join(ast.literal_eval(line) for line in
                            (match[2] + match[3]).splitlines())
            fields[match[1]] = (value, match)
        if 'msgid' not in fields:
            continue
        key = (fields.get('msgctxt', ('',))[0], fields['msgid'][0])
        if key not in messages:
            continue
        names = messages[key]
        replacements = []
        for field in ('msgid', 'msgstr'):
            if field not in fields:
                raise ValueError(f'Missing {field} in translation entry {key}')
            value, match = fields[field]
            if field == 'msgstr' and not value:
                continue
            try:
                value = named_format(value, names)
            except ValueError:
                # Already-fuzzy catalog entries are inactive translator work in progress.
                # Retain their text and fuzzy flag; gettext keeps using the source message.
                if field == 'msgstr' and re.search(r'^#,.*\bfuzzy\b', block, re.M):
                    continue
                raise
            replacements.append((match.start(), match.end(),
                                 field + ' ' + json.dumps(value, ensure_ascii=False)))
        for start, end, replacement in sorted(replacements, reverse=True):
            block = block[:start] + replacement + block[end:]
        blocks[index] = block
        changed += 1
    return '\n\n'.join(blocks), changed


def patch(root):
    messages_file = root / 'src/orca/messages.py'
    text = messages_file.read_text(encoding='utf-8')
    lines = text.splitlines(keepends=True)
    catalogs = {}
    found = set()
    for node in ast.parse(text).body:
        if not isinstance(node, ast.Assign) or not isinstance(node.targets[0], ast.Name):
            continue
        name = node.targets[0].id
        if name not in FIELDS:
            continue
        call = node.value
        if not isinstance(call, ast.Call) or not isinstance(call.func, ast.Name):
            raise ValueError(f'Unexpected message definition: {name}')
        if node.lineno != node.end_lineno:
            raise ValueError(f'Multiline message definition needs review: {name}')
        old = ast.literal_eval(call.args[-1])
        context = ast.literal_eval(call.args[0]) if call.func.id == 'C_' else ''
        names = FIELDS[name]
        catalogs[(context, old)] = names
        new = named_format(old, names)
        args = [repr(context), repr(new)] if context else [repr(new)]
        lines[node.lineno - 1] = name + ' = ' + call.func.id + '(' + ', '.join(args) + ')\n'
        found.add(name)
    if found != set(FIELDS):
        raise ValueError(f'Missing pinned message definitions: {set(FIELDS) - found}')

    updates = {messages_file: ''.join(lines)}
    uses = set()
    for path in (root / 'src').rglob('*'):
        if not (path.name.endswith('.py') or path.name.endswith('.py.in')):
            continue
        source = path.read_text(encoding='utf-8')
        nodes = ast.parse(source)
        offsets = [0]
        for line in source.splitlines(keepends=True):
            offsets.append(offsets[-1] + len(line.encode('utf-8')))
        edits = []
        for node in ast.walk(nodes):
            if not isinstance(node, ast.BinOp) or not isinstance(node.op, ast.Mod):
                continue
            if not isinstance(node.left, ast.Attribute) or node.left.attr not in FIELDS:
                continue
            name = node.left.attr
            if not isinstance(node.right, ast.Tuple) or len(node.right.elts) != len(FIELDS[name]):
                raise ValueError(f'Unexpected formatter in {path}: {name}')
            values = [ast.get_source_segment(source, value) for value in node.right.elts]
            replacement = '{' + ', '.join(repr(key) + ': ' + value for key, value in
                                         zip(FIELDS[name], values)) + '}'
            target = node.right
            edits.append((offsets[target.lineno - 1] + target.col_offset,
                          offsets[target.end_lineno - 1] + target.end_col_offset,
                          replacement.encode('utf-8')))
            uses.add(name)
        data = source.encode('utf-8')
        for start, end, replacement in sorted(edits, reverse=True):
            data = data[:start] + replacement + data[end:]
        if edits:
            updated = data.decode('utf-8')
            ast.parse(updated)
            updates[path] = updated
    if uses != set(FIELDS):
        raise ValueError(f'Missing formatter call sites: {set(FIELDS) - uses}')

    entries = 0
    for path in (root / 'po').glob('*.po'):
        updated, count = migrate_catalog(path.read_text(encoding='utf-8'), catalogs)
        if count:
            updates[path] = updated
            entries += count
    # Write only after every source and catalog has validated successfully.
    for path, updated in updates.items():
        path.write_text(updated, encoding='utf-8')
    print(f'Migrated {len(found)} message formats and {entries} translation entries.')


if __name__ == '__main__':
    patch(Path(sys.argv[1]))

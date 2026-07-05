"""Static (AST) collection of every t() key under src/ - the drift guard between
code and locale catalogs. The catalog-parity test derives the required key set
from here, so a new t('...') without translations fails the suite instead of
silently falling back to English in production.

Resolvable key sources: string literals, module-level string constants,
module-level dicts of strings (label dicts, wrapped at lookup), and class-level
string/dict attributes (e.g. cancelled_text on TypedInputNode subclasses).
Anything else t() is called with is reported as a violation - dynamic keys
can't be translated ahead of time.
"""
import ast
import os


def collect_translation_keys(src_root: str) -> tuple[set[str], list[str]]:
    modules = []
    for root, _dirs, files in os.walk(src_root):
        if '__pycache__' in root:
            continue
        for file in files:
            if file.endswith('.py'):
                path = os.path.join(root, file)
                with open(path, encoding='utf-8') as handle:
                    modules.append((path, ast.parse(handle.read())))

    name_strings, name_dicts, attr_strings, attr_dicts = _collect_constants(modules)

    keys: set[str] = set()
    violations: list[str] = []
    for path, tree in modules:
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                    and node.func.id == 't' and node.args):
                continue
            resolved = _resolve_key(node.args[0], name_strings, name_dicts, attr_strings, attr_dicts)
            if resolved is None:
                violations.append(f'{path}:{node.lineno}: t() key is not statically resolvable')
            else:
                keys.update(resolved)
    return keys, violations


def _collect_constants(modules) -> tuple[dict, dict, dict, dict]:
    # Module-level names are resolved per name (first definition wins - names are
    # unique enough across this codebase); class attributes accumulate across ALL
    # classes, because e.g. every TypedInputNode subclass defines its own
    # cancelled_text and t(self.cancelled_text) can mean any of them.
    name_strings: dict[str, str] = {}
    name_dicts: dict[str, list[str]] = {}
    attr_strings: dict[str, set[str]] = {}
    attr_dicts: dict[str, set[str]] = {}
    for _path, tree in modules:
        for name, value in _string_assignments(tree.body):
            name_strings.setdefault(name, value)
        for name, values in _dict_assignments(tree.body):
            name_dicts.setdefault(name, values)
        for class_def in [n for n in tree.body if isinstance(n, ast.ClassDef)]:
            for name, value in _string_assignments(class_def.body):
                attr_strings.setdefault(name, set()).add(value)
            for name, values in _dict_assignments(class_def.body):
                attr_dicts.setdefault(name, set()).update(values)
    return name_strings, name_dicts, attr_strings, attr_dicts


def _single_name_assignments(statements):
    for statement in statements:
        if (isinstance(statement, ast.Assign) and len(statement.targets) == 1
                and isinstance(statement.targets[0], ast.Name)):
            yield statement.targets[0].id, statement.value


def _string_assignments(statements):
    for name, value in _single_name_assignments(statements):
        if isinstance(value, ast.Constant) and isinstance(value.value, str):
            yield name, value.value


def _dict_assignments(statements):
    for name, value in _single_name_assignments(statements):
        if isinstance(value, ast.Dict):
            strings = [v.value for v in value.values
                       if isinstance(v, ast.Constant) and isinstance(v.value, str)]
            if strings:
                yield name, strings


def _resolve_key(arg, name_strings, name_dicts, attr_strings, attr_dicts) -> list[str] | None:
    if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
        return [arg.value]
    if isinstance(arg, ast.Name):
        value = name_strings.get(arg.id)
        return [value] if value is not None else None
    if isinstance(arg, ast.Subscript):
        container = arg.value
        if isinstance(container, ast.Name) and container.id in name_dicts:
            return list(name_dicts[container.id])
        if isinstance(container, ast.Attribute):
            # self.LABELS[...] class dicts, or OtherModule.LABELS[...] module dicts.
            if container.attr in attr_dicts:
                return list(attr_dicts[container.attr])
            if container.attr in name_dicts:
                return list(name_dicts[container.attr])
        return None
    if isinstance(arg, ast.Attribute):
        # self.X / cls.X class attributes, or OtherModule.CONSTANT module constants.
        if arg.attr in attr_strings:
            return list(attr_strings[arg.attr])
        if arg.attr in name_strings:
            return [name_strings[arg.attr]]
    return None

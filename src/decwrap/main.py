import ast
import argparse
import re
from typing import Any, Optional
from pathlib import Path

from .models import ClassDef, Prototype
from .dump_class_def import dump_class_def


PROTOTYPE_PATTERN = (
    "(?P<return>[a-zA-Z][a-zA-Z0-9_*]*)"
    " +(?P<function>[a-zA-Z]\w*)"
    " *[(](?P<arguments>[a-zA-Z0-9_*, ]*)[)]"
)


def parse_prototype(prototype: str) -> Prototype:
    match = re.match(PROTOTYPE_PATTERN, prototype)
    assert match is not None
    group = match.groupdict()
    return Prototype(
        restype=group["return"],
        function=group["function"],
        argtypes=group["arguments"].replace(" ", "").split(","),
    )


class InitVisitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.ctors: set[str] = set()

    def visit_Call(self, node: ast.Call) -> None:
        if isinstance(node.func, ast.Attribute):
            self.ctors.add(node.func.attr)


class ClassVisitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.type_name: Optional[str] = None
        self.prototypes: list[tuple[str, str, bool]] = []
        self.ctors: set[str] = set()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        if node.name != "__init__":
            return

        visitor = InitVisitor()
        for stmt in node.body:
            visitor.visit(stmt)
        self.ctors |= visitor.ctors

    def visit_Assign(self, node: ast.Assign) -> Any:
        assert len(node.targets) == 1
        target = node.targets[0]

        if not isinstance(target, ast.Name):
            return

        if target.id == "TYPE_NAME":
            assert isinstance(node.value, ast.Constant)
            self.type_name = node.value.value
            return

        if (
            isinstance(node.value, ast.Call)
            and isinstance(node.value.func, ast.Name)
            and node.value.func.id == "ResPrototype"
        ):
            assert len(node.value.args) == 1
            arg = node.value.args[0]

            assert len(node.value.keywords) <= 1
            bind = True
            if node.value.keywords:
                kw = node.value.keywords[0]
                assert kw.arg == "bind"
                assert isinstance(kw.value, ast.Constant)
                assert isinstance(kw.value.value, bool)
                bind = kw.value.value

            assert isinstance(arg, ast.Constant)
            assert isinstance(arg.value, str)
            self.prototypes.append((target.id, arg.value, bind))


class ModuleVisitor(ast.NodeVisitor):
    def __init__(self) -> None:
        super().__init__()

        self.class_defs: list[ClassDef] = []

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        # Check that this class inherits from BaseCClass
        # (non-transitively)
        for base in node.bases:
            if not isinstance(base, ast.Name):
                continue
            if base.id == "BaseCClass":
                break
        else:
            return self.generic_visit(node)

        visitor = ClassVisitor()
        for stmt in node.body:
            visitor.visit(stmt)

        prototypes = {n: (parse_prototype(p), b) for n, p, b in visitor.prototypes}
        for ctor in visitor.ctors:
            if ctor in prototypes:
                prototypes[ctor][0].ctor = True

        self.class_defs.append(
            ClassDef(
                name=node.name,
                type_name=visitor.type_name,
                prototypes=prototypes,
            )
        )


class PrototypeVistor(ast.NodeVisitor):
    def visit_Call(self, node: ast.Call) -> None:
        if not isinstance(node.func, ast.Name):
            return self.generic_visit(node)
        if node.func.id != "ResPrototype":
            return self.generic_visit(node)

        assert isinstance(node.args[0], ast.Constant)
        # print(node.args[0].value)
        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign) -> None:
        if not isinstance(node.value, ast.Call):
            return self.generic_visit(node)
        if not isinstance(node.value.func, ast.Name):
            return self.generic_visit(node)
        if node.value.func.id != "ResPrototype":
            return self.generic_visit(node)

        # Get attribute name
        name = ""
        assert len(node.targets) == 1
        target = node.targets[0]
        if isinstance(target, ast.Name):
            name = target.id
        elif isinstance(target, ast.Attribute):
            name = target.attr
        else:
            raise NotImplementedError

        # Get prototype
        assert len(node.value.args) == 1
        assert isinstance(node.value.args[0], ast.Constant)
        proto = node.value.args[0].value

        print(f"({name}) <- ({proto})")

        self.generic_visit(node)


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser()
    ap.add_argument("lib", type=str, help="Path to libecl/libres")

    return ap.parse_args()


def main():
    args = parse_args()

    visitor = ModuleVisitor()
    for pyfile in Path(args.lib).glob("**/*.py"):
        py = compile(pyfile.read_text(), str(pyfile), "exec", ast.PyCF_ONLY_AST)

        visitor.visit(py)

    for class_ in visitor.class_defs:
        for proto, _ in class_.prototypes.values():
            if not proto.ctor or proto.restype == "void*":
                continue
            print(f"{class_.name} :: {proto.function} :: {proto.restype}")

    # genpath = Path.cwd() / "generated"
    # genpath.mkdir(exist_ok=True)
    # for class_ in visitor.class_defs:
    #     (genpath / f"{class_.name}.cpp").write_text(dump_class_def(class_))


if __name__ == "__main__":
    main()

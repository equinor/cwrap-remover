import re
import ast
from typing import Any, Optional
from decwrap.models import ClassDef, Prototype


BASECLASSES = ("EclPrototype", "ResPrototype", "VectorTemplate")


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


class PrototypeVistor(ast.NodeVisitor):
    def visit_Call(self, node: ast.Call) -> None:
        if not isinstance(node.func, ast.Name):
            return self.generic_visit(node)
        if node.func.id not in BASECLASSES:
            return self.generic_visit(node)

        assert isinstance(node.args[0], ast.Constant)
        # print(node.args[0].value)
        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign) -> None:
        if not isinstance(node.value, ast.Call):
            return self.generic_visit(node)
        if not isinstance(node.value.func, ast.Name):
            return self.generic_visit(node)
        if node.value.func.id not in BASECLASSES:
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


class InitVisitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.ctors: set[str] = set()

    def visit_Call(self, node: ast.Call) -> None:
        if isinstance(node.func, ast.Attribute):
            self.ctors.add(node.func.attr)


class ClassFuncVisitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.used: set[str] = set()

    def visit_Attribute(self, node: ast.Attribute) -> Any:
        if node.attr[0] == "_":
            self.used.add(node.attr)
        self.generic_visit(node)


class ClassVisitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.type_name: Optional[str] = None
        self.prototypes: list[tuple[str, str, bool]] = []
        self.ctors: set[str] = set()
        self.used: set[str] = set()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        if node.name == "__init__":
            visitor = InitVisitor()
            for stmt in node.body:
                visitor.visit(stmt)
                self.ctors |= visitor.ctors

        visitor = ClassFuncVisitor()
        for stmt in node.body:
            visitor.visit(stmt)
            self.used |= visitor.used

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
            and node.value.func.id in BASECLASSES
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
        for used in visitor.used:
            if used in prototypes:
                prototypes[used][0].used = True

        self.class_defs.append(
            ClassDef(
                name=node.name,
                type_name=visitor.type_name,
                prototypes=prototypes,
            )
        )

    def visit_Assign(self, node: ast.Assign) -> None:
        if len(node.targets) != 1 or not isinstance(node.targets[0], ast.Attribute) or not isinstance(node.value, ast.Call):
            return
        exit()


def parse_basecclass(node: ast.AST) -> list[ClassDef]:
    visitor = ModuleVisitor()
    visitor.visit(node)
    return visitor.class_defs

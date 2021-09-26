from .models import ClassDef, Prototype


TEMPLATE = """\
#include <string>
#include <vector>
#include <pybind11/pybind11.h>
#include "cwrap_types.hpp"

namespace py = pybind11;
namespace ct = generated::cwrap_types;

void init_{class_name}(py::module_ &m) {{
    {body}
}}
"""


PRIMARY = {"void", "long", "int", "bool"}


def py_type(type_: str) -> str:
    if type_ in PRIMARY:
        return type_
    if type_ == "char*":
        return "std::string"
    if type_ == "double*":
        return "std::vector<double>"
    if type_ == "float*":
        return "std::vector<float>"
    if type_ == "long*":
        return "std::vector<long>"
    if type_ == "void*":
        return "ct::voidp"

    if "*" in type_:
        raise NotImplementedError(type_)
    if type_.endswith("_obj") or type_.endswith("_ref"):
        type_ = type_[:-3]
    return f"ct::{type_}"


def c_type(type_: str) -> str:
    if type_ in PRIMARY:
        return type_
    return "void*"


def make_param(type_: str, arg: str) -> str:
    if type_ in PRIMARY:
        return arg
    if type_ == "char*":
        return f"{arg}.c_str()"
    return f"{arg}.get()"


def defun(name: str, proto: Prototype, bind: bool) -> str:
    c_name = proto.function
    py_name = name

    c_args = ", ".join(c_type(type_) for type_ in proto.argtypes)
    py_args = ", ".join(
        f"{py_type(type_)} arg{index}" for index, type_ in enumerate(proto.argtypes)
    )

    c_res = py_type(proto.restype)
    py_res = py_type(proto.restype)

    params = ", ".join(
        make_param(type_, f"arg{index}") for index, type_ in enumerate(proto.argtypes)
    )

    # Can't 'return' a void in C++
    return_ = "" if c_res == "void" else "return "

    return (
        f'  m.def("{py_name}", []({py_args}) -> {py_res} {{\n'
        f'    extern "C" {c_res} {c_name}({c_args});\n'
        f"    {return_}{c_name}({params});\n"
        "  });\n"
    )


def dump_class_def(class_def: ClassDef) -> str:
    return TEMPLATE.format(
        class_name=class_def.name,
        body="\n".join(defun(name, proto, bind) for name, proto, bind in class_def.prototypes),
    )

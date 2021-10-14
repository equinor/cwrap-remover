from .models import ClassDef
from .util import is_primitive


TEMPLATE = """\
#ifndef _GENERATED_CWRAP_TYPES_HPP_
#define _GENERATED_CWRAP_TYPES_HPP_

#include <string_view>
#include <pybind11/pybind11.h>

namespace generated {{
namespace cwrap_types {{

class voidp : public pybind11::object {{
public:
  PYBIND11_OBJECT_CVT(voidp, pybind11::object, PYBIND11_LONG_CHECK, PyNumber_Long)
  voidp(): object(PyLong_FromVoidPtr(nullptr), pybind11::stolen_t{{}}) {{}}
  voidp(void* ptr) { m_ptr = PyLong_FromVoidPtr(ptr); }
  operator void*() const { return PyLong_AsVoidPtr(m_ptr); }
}};

class type {{
public:
  virtual ~type();
  type(pybind11::object);
  type(std::string_view type_name, void*);
  void *get();
}};

{body}

}}
}}

#endif //_GENERATED_CWRAP_TYPES_HPP_
"""

CWRAP_TYPE = """\
class {type_name} : public type {{
public:
  using type::type;
  {type_name}(void *ptr):
    type("{type_name}", ptr) {{}}
}};
"""


def collect_types(class_def: ClassDef) -> set[str]:
    types: list[str] = []
    for _, proto, _ in class_def.prototypes:
        types.append(proto.restype)
        types.extend(proto.argtypes)
    return set(types)


def dump_types(class_defs: list[ClassDef]) -> str:
    types = set()
    for class_def in class_defs:
        types |= collect_types(class_def)

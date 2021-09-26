#include <pybind11/pybind11.h>

#include "cwrap_types.hpp"

namespace py = pybind11;
namespace ct = generated::cwrap_types;

namespace {

}

ct::type::type(py::object obj) {
    py::modlue cwrap = py::module_::import("cwrap");
    if (!py::isinstance(obj, cwrap.attr("BaseCClass")))
        throw py::value_error("obj must be of type BaseCClass");
    ct::voidp cptr = obj.attr("_BaseCClass__c_pointer");

    m_ptr = cptr;
}

ct::type::operator py::object() {
    py::module cwrap = py::module_::import("cwrap");
    py::dict types = cwrap.attr(this->p_type_name());
    py::object type = types[type_name];
}

from typing import Optional
from pydantic import BaseModel


class Prototype(BaseModel):
    function: str
    restype: str
    argtypes: list[str]
    ctor: bool = False
    used: bool = False


class ClassDef(BaseModel):
    name: str
    type_name: Optional[str]
    prototypes: dict[str, tuple[Prototype, bool]]

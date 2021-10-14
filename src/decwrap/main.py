import ast
import argparse
import re
import networkx as nx
import matplotlib.pyplot as plt
import pydot
from pathlib import Path
from decwrap.models import ClassDef
from decwrap.parse_basecclass import parse_basecclass


PRIMITIVES = {"", "int", "bool", "float", "void", "void*", "long", "char*", "double", "time_t", "double*", "float*"}


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser()
    ap.add_argument("lib", type=str, help="Path to libecl/libres")

    return ap.parse_args()


def main():
    args = parse_args()

    class_defs: list[ClassDef] = []
    for pyfile in Path(args.lib).glob("**/*.py"):
        py = compile(pyfile.read_text(), str(pyfile), "exec", ast.PyCF_ONLY_AST)
        class_defs.extend(parse_basecclass(py))

    types = {cd.type_name for cd in class_defs}
    # argtypes = sorted({arg for cd in class_defs for p, _ in cd.prototypes.values() for arg in p.argtypes})
    # print(argtypes)
    # exit(1)

    graph = pydot.Dot()
    for class_def in class_defs:
        if class_def.name == "_RealEnKFMain":
            class_def.type_name = "enkf_main"
        elif class_def.name == "Matrix":
            class_def.type_name = "matrix"
        elif class_def.type_name is None:
            # print("Ignoring", class_def.name)
            # continue
            class_def.type_name = f"::{class_def.name}::"

        # Return types
        graph.add_node(pydot.Node(class_def.type_name))
        for proto, _ in class_def.prototypes.values():
            restype = proto.restype
            if restype.endswith("_ref") or restype.endswith("_obj"):
                restype = restype[:-4]
            if restype in PRIMITIVES:
                continue

            # Return types
            if graph.get_edge(class_def.type_name, restype) == []:
                if restype not in types:
                    graph.add_node(pydot.Node(restype, style="dashed"))
                graph.add_edge(pydot.Edge(class_def.type_name, restype))

        # for proto, _ in class_def.prototypes.values():
        #     for argtype in proto.argtypes:
        #         if argtype in PRIMITIVES:
        #             continue

        #         if graph.get_edge(argtype, class_def.type_name) == []:
        #             if argtype not in types:
        #                 graph.add_node(pydot.Node(argtype, style="dashed"))
        #             graph.add_edge(pydot.Edge(argtype, class_def.type_name, style="dashed"))

    # graph.write_png("filename.png")

    # pos = nx.fruchterman_reingold_layout(graph)
    # nx.draw_networkx_nodes(graph, pos, node_size=5)
    # nx.draw_networkx_edges(graph, pos, width=0.1, arrowsize=2, node_size=5)
    # nx.draw_networkx_labels(graph, pos, font_size=4, verticalalignment="bottom")

    # plt.savefig("filename.png", dpi=1200, pad_inches="tight")

    # genpath = Path.cwd() / "generated"
    # genpath.mkdir(exist_ok=True)
    # for class_ in visitor.class_defs:
    #     (genpath / f"{class_.name}.cpp").write_text(dump_class_def(class_))


if __name__ == "__main__":
    main()

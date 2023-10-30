import understand
import json
import os
import argparse


def extract_understand_entities(db_path, result_path):
    # db = understand.open("/root/project_example/coreutils/project.udb.und")
    db = understand.open(db_path)

    function_to_refs = {}

    for func_entity in db.ents("function"):
        func_relname = func_entity.longname()
        print(func_relname)
        kind = func_entity.kind()
        if "Function" not in kind.longname().split():
            continue
        func_id = func_entity.id()
        function_to_refs[func_id] = {}
        func_parent = func_entity.parent()
        total_line = func_entity.metric(['CountLine'])['CountLine']

        function_to_refs[func_id]["info"] = {"parent": func_parent.longname() if func_parent else None, "total_line": total_line,
                                              "contents": func_entity.contents(), "name": func_relname}
        entity_ref = {}
        refs = func_entity.refs("call")
        entity_ref["call"] = []
        for ref in refs:
            if ref.ent().parent():
                call_entity = ref.ent().longname()
                call_entity_type = ref.ent().type()
                call_entity_kind = ref.ent().kind().longname()
                if "Function" not in call_entity_kind:
                    continue
                call_file = ref.ent().parent().longname()
                ref_line = ref.line()
                ref_column = ref.column()
                entity_ref["call"].append(
                    {"file": call_file, "entity": call_entity, "type": call_entity_type,
                     "kind": call_entity_kind, "line_number": ref_line, "column": ref_column})
            else:
                call_entity = ref.ent().longname()
                call_entity_type = ref.ent().type()
                call_entity_kind = ref.ent().kind().longname()
                if "Function" not in call_entity_kind:
                    continue
                call_file = ref.ent().parent()
                ref_line = ref.line()
                ref_column = ref.column()
                entity_ref["call"].append(
                    {"file": call_file, "entity": call_entity, "type": call_entity_type,
                     "kind": call_entity_kind, "line_number": ref_line,
                     "column": ref_column})
        function_to_refs[func_id]["call"] = entity_ref["call"]
    # print(file_contains_entity)
    # result_path = "/root/project_example/coreutils/"
    json_file = open(result_path, "w")
    json_str = json.dumps(function_to_refs, indent=2)
    json_file.write(json_str)
    json_file.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--db_path", type=str, help="path of understand database")
    parser.add_argument("--result_path", type=str, help="path of result file")
    args = parser.parse_args()
    db_path_arg, result_path_arg = args.db_path, args.result_path
    extract_understand_entities(db_path_arg, result_path_arg)

import csv
import json
import os
import pickle
import random

from tree_sitter import Parser, Language


def read_json(file_path):
    with open(file_path, "r") as f:
        file_content = json.load(f)
        return file_content


def write_json(file_path, obj):
    with open(file_path, "w") as f:
        json_str = json.dumps(obj, indent=2)
        f.write(json_str)


def write_pickle(obj, file_path):
    with open(file_path, "wb") as f:
        pickle.dump(obj, f)


def read_pickle(pickle_file):
    with open(pickle_file, "rb") as f:
        return pickle.load(f)


def extract_call_site_associated_call_pairs_and_labels(call_sites_to_call_pairs, call_sites_info):
    call_sites_and_call_pairs_per_project = {}
    call_sites_labels = {}
    for compiler in call_sites_info:
        for opt in call_sites_info[compiler]:
            for call_site_kind in call_sites_info[compiler][opt]:
                for call_site in call_sites_info[compiler][opt][call_site_kind]:
                    file_name, function_name, call_site_line, call_site_column, callee_file, callee_function = \
                        call_site.split("+")
                    callee = "+".join([callee_file, callee_function])
                    call_site_key = \
                        "+".join([file_name, function_name, str(call_site_line), str(call_site_column), callee])
                    call_site_pairs = call_sites_to_call_pairs[call_site_key]
                    caller, callee = call_site_pairs["caller"], call_site_pairs["callee"]
                    project_name = file_name.split("/")[0]
                    if project_name not in call_sites_and_call_pairs_per_project:
                        call_sites_and_call_pairs_per_project[project_name] = []
                    if [file_name, function_name, call_site_line, call_site_column, caller, callee] not in \
                            call_sites_and_call_pairs_per_project[project_name]:
                        call_sites_and_call_pairs_per_project[project_name].append(
                            [file_name, function_name, call_site_line, call_site_column, caller, callee])
                    if call_site_key not in call_sites_labels:
                        call_sites_labels[call_site_key] = {}
                    if compiler not in call_sites_labels[call_site_key]:
                        call_sites_labels[call_site_key][compiler] = {}
                    call_sites_labels[call_site_key][compiler][opt] = call_site_kind
    return call_sites_and_call_pairs_per_project, call_sites_labels


def get_all_call_sites(source_project_fcg):
    all_call_pairs = []
    for u, v, keys, call_site in source_project_fcg.edges(data="call_site_location", keys=True):
        all_call_pairs.append([u, v, keys, call_site])
    return all_call_pairs


def extract_call_pairs_from_fcgs(source_fcgs):
    call_sites_to_call_pairs = {}
    for project in source_fcgs:
        project_fcg = source_fcgs[project]
        all_call_pairs = get_all_call_sites(project_fcg)
        for call_pairs in all_call_pairs:
            caller, callee, key, call_site_info = call_pairs
            call_site_file, call_site_function, call_site_line, call_site_column = \
                call_site_info["file"], call_site_info["function"], call_site_info["line_number"], call_site_info["column"]
            call_site_key = "+".join([call_site_file, call_site_function, str(call_site_line), str(call_site_column), callee])
            if call_site_key not in call_sites_to_call_pairs:
                call_sites_to_call_pairs[call_site_key] = {"caller": caller, "callee": callee}
            else:
                continue
    return call_sites_to_call_pairs


def get_function_content(file_name, function_name, call_site_line, function_content_per_project):
    if file_name not in function_content_per_project or function_name not in function_content_per_project[file_name]:
        return None, None
    function_range = None
    function_content = None
    function_content_dict_or_list = function_content_per_project[file_name][function_name]
    if type(function_content_dict_or_list) is dict:
        function_content = function_content_dict_or_list["content"]
        function_range = {"start_point": function_content_dict_or_list["start_point"],
                          "end_point": function_content_dict_or_list["end_point"]}
    elif type(function_content_dict_or_list) is list:
        for function_info in function_content_dict_or_list:
            if call_site_line is None:
                # print("cannot determine callee... select the first")
                function_content = function_info["content"]
                function_range = {"start_point": function_info["start_point"],
                                  "end_point": function_info["end_point"]}
                break
            if int(function_info["start_point"][0]) < int(call_site_line) < int(function_info["end_point"][0]):
                function_content = function_info["content"]
                function_range = {"start_point": function_info["start_point"],
                                  "end_point": function_info["end_point"]}
                break
    return function_content, function_range


def write_function_content(caller_content, function_key, project_name, call_site_features_dir):
    project_dir = os.path.join(call_site_features_dir, project_name)
    if not os.path.exists(project_dir):
        os.makedirs(project_dir)
    function_key = str(function_key)
    file_path = os.path.join(project_dir, function_key + ".json")
    if not os.path.exists(file_path):
        write_json(file_path, caller_content)


def traverse_tree(tree):
    cursor = tree.walk()

    reached_root = False
    while reached_root == False:
        yield cursor.node

        if cursor.goto_first_child():
            continue

        if cursor.goto_next_sibling():
            continue

        retracing = True
        while retracing:
            if not cursor.goto_parent():
                retracing = False
                reached_root = True

            if cursor.goto_next_sibling():
                retracing = False


def extract_function_intra_features(caller_content, tree_sitter_lib_path):
    tree_sitter_parser = get_tree_sitter_parser(tree_sitter_lib_path)
    tree = tree_sitter_parser.parse(bytes(caller_content, "utf8"))
    function_keywords = []
    while_statement_count = 0
    switch_statement_count = 0
    switch_statement_list = []
    if_statement_count = 0
    declaration_statement_count = 0
    for_statement_count = 0
    return_statement_count = 0

    expression_statement_count = 0
    call_expression_statement_count = 0

    all_statement_types_count = 0
    for node in traverse_tree(tree):
        # print(node)
        if node.type == "function_definition":
            for function_child_node in node.children:
                if function_child_node.type == "primitive_type" or function_child_node.type == "ERROR" or \
                        function_child_node.type == "compound_statement":
                    break
                for sub_child in traverse_tree(function_child_node):
                    if sub_child.text.decode('utf-8') not in function_keywords:
                        # if sub_child.text != b'static' and sub_child.text != b'const' and sub_child.text != b'XALLOC_INLINE':
                        #     print(sub_child.text)
                        function_keywords.append(sub_child.text.decode('utf-8'))
                if function_child_node.type == "storage_class_specifier":
                    break

        all_statement_types_count += 1
        if node.type == "while_statement":
            while_statement_count += 1
        elif node.type == "switch_statement":
            switch_statement_count += 1
            cases_branch = node.children[2]
            switch_case_count = 0
            for case_child in cases_branch.children:
                if case_child.type == "case_statement":
                    switch_case_count += 1
            switch_statement_list.append(switch_case_count)
        elif node.type == "if_statement":
            if_statement_count += 1
        elif node.type == "declaration":
            declaration_statement_count += 1
        elif node.type == "expression_statement":
            expression_statement_count += 1
        elif node.type == "for_statement":
            for_statement_count += 1
        elif node.type == "return_statement":
            return_statement_count += 1
        elif node.type == "call_expression":
            call_expression_statement_count += 1
        # else:
        #     print(node.type)

    function_features_count = {"all_statement": all_statement_types_count, "while": while_statement_count,
                               "switch": {"count": switch_statement_count, "cases": switch_statement_list},
                               "if": if_statement_count, "for": for_statement_count, "return": return_statement_count,
                               "declare": declaration_statement_count, "expression": expression_statement_count,
                               "call_expression": call_expression_statement_count, "keywords": function_keywords}
    return function_features_count


def mapping_line_to_point(caller_function_range, call_site_line):
    call_site_point = int(call_site_line) - int(caller_function_range['start_point'][0]) - 1
    return call_site_point


def extract_call_site_features(caller_content, caller_function_range, call_site_line, tree_sitter_lib_path):
    # call_site_features = {}
    tree_sitter_parser = get_tree_sitter_parser(tree_sitter_lib_path)
    tree = tree_sitter_parser.parse(bytes(caller_content, "utf8"))
    call_site_point = mapping_line_to_point(caller_function_range, call_site_line)
    call_site_traverse_trace = []
    arguments = []
    constant_argument = []
    call_site_location_label = {"in_for": False, "in_while": False, "in_switch": False, "in_if": False}
    for node in traverse_tree(tree):
        # print(node)
        node_start_line = node.start_point[0]
        node_end_line = node.end_point[0]
        if node_start_line <= call_site_point <= node_end_line:
            call_site_traverse_trace.append(node)
            if node.type == "while_statement":
                call_site_location_label["in_while"] = True
            elif node.type == "switch_statement":
                call_site_location_label["in_switch"] = True
            elif node.type == "if_statement":
                call_site_location_label["in_if"] = True
            elif node.type == "for_statement":
                call_site_location_label["in_for"] = True
            if node.type == "call_expression":
                argument_list = node.children[1]
                for argument_candidate in argument_list.children:
                    if argument_candidate.type != '(' and argument_candidate.type != ')' and argument_candidate.type != ",":
                        arguments.append(argument_candidate.text)
                        if argument_candidate.type in ["string_literal", 'concatenated_string', "null",
                                                       'number_literal']:
                            constant_argument.append(argument_candidate.text)
    call_site_features = {"call_site_path_length": len(call_site_traverse_trace),
                          "call_site_location": call_site_location_label,
                          "call_site_arguments": len(arguments),
                          "call_site_constant_arguments": len(constant_argument)
                          }
    return call_site_features


def extract_function_inter_features(source_fcg, fcg_node):
    if fcg_node not in source_fcg:
        return None
    inter_features = {"total_node": len(source_fcg.nodes()), "total_edge": len(source_fcg.edges()),
                      "function_in_degree": source_fcg.in_degree(fcg_node),
                      "function_out_degree": source_fcg.out_degree(fcg_node)}
    return inter_features


def extract_function_features(project_name, file_name, function_name, caller_content,
                              function_to_features, tree_sitter_lib_path, source_fcg):
    caller_key = "+".join([project_name, file_name, function_name])
    fcg_node = "+".join([file_name, function_name])
    if caller_key not in function_to_features:
        caller_intra_features = extract_function_intra_features(caller_content, tree_sitter_lib_path)
        caller_inter_features = extract_function_inter_features(source_fcg, fcg_node)
        if caller_inter_features is None:
            return None, function_to_features
        function_features = {**caller_intra_features, **caller_inter_features}
        function_to_features[caller_key] = function_features
    else:
        function_features = function_to_features[caller_key]

    return function_features, function_to_features


def extract_call_site_features_per_project(call_sites_and_call_pairs_per_project, function_contents_folder,
                                           source_fcgs, tree_sitter_lib_path):
    all_call_site_features = {}
    for project_name in call_sites_and_call_pairs_per_project:
        print("processing project {}".format(project_name))
        call_sites_and_call_pairs = call_sites_and_call_pairs_per_project[project_name]
        function_contents = extract_function_contents(function_contents_folder, project_name)
        source_fcg = source_fcgs[project_name]

        if project_name not in all_call_site_features:
            all_call_site_features[project_name] = {}

        function_to_features = {}
        for call_site in call_sites_and_call_pairs:
            file_name, function_name, call_site_line, call_site_column, caller, callee = call_site
            # project_name = file_name.split("/")[0]
            function_content_per_project = function_contents[project_name]
            caller_content, caller_function_range = get_function_content(file_name, function_name, call_site_line,
                                                                         function_content_per_project)
            callee_file_name, callee_function = callee.split("+")
            callee_function_dict = source_fcg.nodes[callee]["node_attribute"]
            if "begin_line" in callee_function_dict:
                line_inside = (int(callee_function_dict["begin_line"]) + int(callee_function_dict["end_line"])) / 2
                callee_content, _ = get_function_content(callee_file_name, callee_function, line_inside,
                                                         function_content_per_project)
            else:
                callee_content, _ = get_function_content(callee_file_name, callee_function, None,
                                                         function_content_per_project)
            if not caller_content or not callee_content:
                continue

            caller_features, function_to_features = \
                extract_function_features(project_name, file_name, function_name, caller_content,
                                          function_to_features, tree_sitter_lib_path, source_fcg)

            callee_features, function_to_features = \
                extract_function_features(project_name, callee_file_name, callee_function, callee_content,
                                          function_to_features, tree_sitter_lib_path, source_fcg)

            if not caller_features or not callee_features:
                continue

            call_site_key = "+".join([file_name, function_name, str(call_site_line), str(call_site_column), callee])

            call_site_features = extract_call_site_features(caller_content, caller_function_range, call_site_line,
                                                            tree_sitter_lib_path)

            all_call_site_features[project_name][call_site_key] = {"caller": caller_features,
                                                                   "callee": callee_features,
                                                                   "call_site": call_site_features}
        # break
    return all_call_site_features


def extract_function_contents(function_contents_folder, selected_project_name):
    function_contents = {}
    for function_content_file_name in os.listdir(function_contents_folder):
        if function_content_file_name.endswith("_function_range_content.json") and \
                function_content_file_name.startswith(selected_project_name):
            function_content_file_path = os.path.join(function_contents_folder, function_content_file_name)
            function_content_per_project = read_json(function_content_file_path)
            project_name = function_content_file_name.replace("_function_range_content.json", "")
            function_contents[selected_project_name] = function_content_per_project
            break
    return function_contents


def processing_all_call_site(call_sites_info, source_fcgs):
    print("processing all call sites ...")
    call_sites_to_call_pairs = extract_call_pairs_from_fcgs(source_fcgs)
    call_sites_and_call_pairs_per_project, call_sites_labels = \
        extract_call_site_associated_call_pairs_and_labels(call_sites_to_call_pairs, call_sites_info)
    return call_sites_and_call_pairs_per_project, call_sites_labels


def get_tree_sitter_parser(tree_sitter_lib_path):
    C_language = Language(tree_sitter_lib_path, "c")
    parser = Parser()
    parser.set_language(C_language)
    return parser


def select_call_sites_by_its_label(call_sites_labels):
    call_sites_labels_per_project = {}
    record_not_complete_num = 0
    for call_site_key in call_sites_labels:
        project_name = call_site_key.split("/")[0]

        clang_labels = {}
        call_site_clang_opt_num = 0
        for clang_compiler in ["clang-7.0"]:
            if clang_compiler not in call_sites_labels[call_site_key]:
                continue
            call_site_clang_opt_num = len(list(call_sites_labels[call_site_key][clang_compiler].keys()))
            if call_site_clang_opt_num == 4:
                clang_labels = call_sites_labels[call_site_key][clang_compiler]
                break

        call_site_gcc_opt_num = 0
        gcc_labels = {}
        for gcc_compiler in ["gcc-7.3.0"]:
            if gcc_compiler not in call_sites_labels[call_site_key]:
                continue
            call_site_gcc_opt_num = len(list(call_sites_labels[call_site_key][gcc_compiler].keys()))
            if call_site_gcc_opt_num == 4:
                gcc_labels = call_sites_labels[call_site_key][gcc_compiler]
                break

        if call_site_clang_opt_num != 4 or call_site_gcc_opt_num != 4:
            record_not_complete_num += 1
            continue

        if project_name not in call_sites_labels_per_project:
            call_sites_labels_per_project[project_name] = {}

        label_list = []
        for compiler_dict in [gcc_labels, clang_labels]:
            for opt_key in opt_list:
                if compiler_dict[opt_key] == "normal_call_sites":
                    label_list.append(0)
                else:
                    label_list.append(1)
        call_sites_labels_per_project[project_name][call_site_key] = label_list
    print("{} call sites do not have all compilation labels".format(record_not_complete_num))
    return call_sites_labels_per_project


def convert_function_features_to_list(call_site_features_per_function, caller_callee_features_list, call_site_csv_list):
    for caller_callee_feature in caller_callee_features_list:
        if caller_callee_feature.startswith("switch"):
            if caller_callee_feature == "switch":
                call_site_csv_list.append(call_site_features_per_function["switch"]["count"])
            elif caller_callee_feature == "switch_cases":
                call_site_csv_list.append(sum(call_site_features_per_function["switch"]["cases"]))
            else:
                raise Exception
        elif caller_callee_feature.startswith("keyword"):
            if caller_callee_feature == "keywords_inline_macro":
                inline_macro_count = 0
                for keyword in call_site_features_per_function["keywords"]:
                    if keyword != "inline" and "inline" in keyword or "INLINE" in keyword:
                        inline_macro_count += 1
                call_site_csv_list.append(inline_macro_count)
            else:
                keyword_count = 0
                inspected_keyword = caller_callee_feature.split("_")[-1]
                for keyword in call_site_features_per_function["keywords"]:
                    if keyword == inspected_keyword:
                        keyword_count += 1
                call_site_csv_list.append(keyword_count)
        else:
            call_site_csv_list.append(call_site_features_per_function[caller_callee_feature])
    return call_site_csv_list


def add_call_site_features_to_list(call_site_csv_list, only_call_site_features, call_site_features_list):
    for call_site_feature_key in call_site_features_list:
        if call_site_feature_key.startswith("in"):
            if only_call_site_features["call_site_location"][call_site_feature_key]:
                call_site_csv_list.append(1)
            else:
                call_site_csv_list.append(0)
        else:

            call_site_csv_list.append(only_call_site_features[call_site_feature_key])
    return call_site_csv_list


def convert_features_to_csv(call_sites_labels_per_project, call_site_to_features):
    call_site_feature_and_labels = []
    caller_callee_features_list = ["all_statement", "while", "switch", "switch_cases", "if", "for", "return", "declare",
                                   "expression", "call_expression", "total_node", "total_edge", "function_in_degree",
                                   "function_out_degree", "keywords_inline", "keywords_inline_macro", "keywords_static",
                                   "keyword_macro"]
    function_features_keys = ["caller", "callee"]
    call_site_features_list = ["call_site_path_length", "in_for", "in_while", "in_switch", "in_if",
                               "call_site_arguments", "call_site_constant_arguments"]
    title = ["project_name"]
    for call_item in function_features_keys:
        for item in caller_callee_features_list:
            title.append(call_item + "_" + item)
    title += call_site_features_list
    for compiler in ["gcc", "clang"]:
        for opt in opt_list:
            title.append(compiler + "-" + opt)
    # title.append("label")
    call_site_feature_and_labels.append(title)
    call_site_without_features_num = 0
    for project in call_sites_labels_per_project:
        for call_site_key in call_sites_labels_per_project[project]:
            if call_site_key in call_site_to_features[project]:
                call_site_csv_list = []
                call_site_csv_list.append(project)
                call_site_features = call_site_to_features[project][call_site_key]
                call_site_label = call_sites_labels_per_project[project][call_site_key]
                for function_key in function_features_keys:
                    call_site_features_per_function = call_site_features[function_key]
                    call_site_csv_list = convert_function_features_to_list(call_site_features_per_function,
                                                                           caller_callee_features_list,
                                                                           call_site_csv_list)
                only_call_site_features = call_site_features["call_site"]
                call_site_csv_list = add_call_site_features_to_list(call_site_csv_list, only_call_site_features,
                                                                    call_site_features_list)
                # if call_site_label[-1] == 1:
                #     call_site_csv_list.append("inline")
                # else:
                #     call_site_csv_list.append("normal")
                # call_site_csv_list += [call_site_label[-1]]
                call_site_csv_list += call_site_label
                call_site_feature_and_labels.append(call_site_csv_list)
            else:
                call_site_without_features_num += 1
                # print("call site {} do not have features".format(call_site_key))\
    print("{} call sites do not have features".format(call_site_without_features_num))
    return call_site_feature_and_labels


def write_csv(call_site_csv_file, call_site_feature_and_labels):
    csv_writer = csv.writer(open(call_site_csv_file, "w", newline=""))
    for line in call_site_feature_and_labels:
        csv_writer.writerow(line)


def split_dataset_by_projects(call_site_feature_and_labels, train_percent = 0.9):
    all_project_name = []
    for line in call_site_feature_and_labels[1:]:
        if line[0] not in all_project_name:
            all_project_name.append(line[0])
    train_csv_content = [call_site_feature_and_labels[0][1:]]
    test_csv_content = [call_site_feature_and_labels[0][1:]]
    train_project_length = int(len(all_project_name)* train_percent)
    train_projects = random.sample(all_project_name, train_project_length)
    for line in call_site_feature_and_labels[1:]:
        if line[0] in train_projects:
            train_csv_content.append(line[1:])
        else:
            test_csv_content.append(line[1:])
    return train_csv_content, test_csv_content


def main():
    call_site_file_path = r"1.inlining_ground_truth_labelining\normal_and_inlined_call_sites_by_infer.json"
    source_fcgs_file = r"0.preprocessing\Source_FCG_extraction\source_fcgs.pkl"
    function_contents_folder = r"2.feature_extraction\features_per_function\function_contents"

    call_sites_info = read_json(call_site_file_path)
    source_fcgs = read_pickle(source_fcgs_file)
    call_sites_pairs_per_project_record_file = "all_sites_pairs_per_project.json"
    call_site_labels_record_file = "call_site_labels.json"
    if not os.path.exists(call_sites_pairs_per_project_record_file) or not os.path.exists(
            call_site_labels_record_file):
        call_sites_and_call_pairs_per_project, call_sites_labels = \
            processing_all_call_site(call_sites_info, source_fcgs)
        write_json(call_sites_pairs_per_project_record_file, call_sites_and_call_pairs_per_project)
        write_json(call_site_labels_record_file, call_sites_labels)
    else:
        call_sites_and_call_pairs_per_project = read_json(call_sites_pairs_per_project_record_file)
        call_sites_labels = read_json(call_site_labels_record_file)
    tree_sitter_lib_path = "C_Cpp.so"

    call_site_features_file = "call_site_features.json"
    if not os.path.exists(call_site_features_file):
        call_site_to_features = extract_call_site_features_per_project(call_sites_and_call_pairs_per_project,
                                                                       function_contents_folder,
                                                                       source_fcgs, tree_sitter_lib_path)
        write_json(call_site_features_file, call_site_to_features)
    else:
        call_site_to_features = read_json(call_site_features_file)
    print("initial call sites count: {}".format(len(list(call_sites_labels.keys()))))
    call_sites_labels_per_project = select_call_sites_by_its_label(call_sites_labels)
    call_site_feature_and_labels = convert_features_to_csv(call_sites_labels_per_project, call_site_to_features)
    print("suitable call sites count: {}".format(len(call_site_feature_and_labels)-1))
    call_site_csv_file = "call_site_feature_and_labels.csv"
    write_csv(call_site_csv_file, call_site_feature_and_labels)
    # train_csv_file = "train_set.csv"
    # test_csv_file = "test_set.csv"
    # train_csv_content, test_csv_content = split_dataset_by_projects(call_site_feature_and_labels)
    # write_csv(train_csv_file, train_csv_content)
    # write_csv(test_csv_file, test_csv_content)


if __name__ == '__main__':
    clang_compiler_list = ["clang-4.0", "clang-5.0", "clang-6.0", "clang-7.0"]
    gcc_compiler_list = ["gcc-4.9.4", "gcc-5.5.0", "gcc-6.4.0", "gcc-7.3.0"]
    compiler_list = gcc_compiler_list + clang_compiler_list
    opt_list = ["O0", "O1", "O2", "O3"]
    main()

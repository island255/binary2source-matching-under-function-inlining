import joblib
import numpy
from tqdm import tqdm

from utils import read_pickle, read_json, write_json, read_csv, split_dataset_by_projects, extract_datas_and_target, \
    get_all_call_sites
from using_ground_truth import extract_call_site_features_for_prediction, convert_dict_to_lists, write_pickle, \
    load_pickle, extract_function_sets_after_inlining, combine_several_lists, get_inline_mapped_functions, \
    extract_nodes_in_call_sites, extract_inlined_edges, get_strong_connected_graph, get_root_node, classify_call_pairs, \
    generate_full_sub_graphs_from_root_node, generate_sub_graphs_with_optional_edges
import os


def use_random_forest_prediction(source_project_call_site_features, random_forest):
    inlined_call_sites = {}
    record = []
    all_call_site_features = []
    for project in source_project_call_site_features:
        print("processing project {}".format(project))
        for call_site in source_project_call_site_features[project]:
            call_site_features_list = source_project_call_site_features[project][call_site]
            record.append([project, call_site])
            all_call_site_features.append(call_site_features_list)
    predict_labels = random_forest.predict(all_call_site_features)
    for index in range(len(predict_labels)):
        if predict_labels[index] == "1":
            project, call_site = record[index]
            if project not in inlined_call_sites:
                inlined_call_sites[project] = {}
            inlined_call_sites[project][call_site] = 1
    return inlined_call_sites


def use_model_predict(source_project_call_site_features, model_with_best_para, test_projects):
    inlined_call_sites = {}
    record = []
    all_call_site_features = []
    for project in test_projects:
        print("processing project {}".format(project))
        for call_site in source_project_call_site_features[project]:
            call_site_features_list = source_project_call_site_features[project][call_site]
            record.append([project, call_site])
            all_call_site_features.append(call_site_features_list)
    predict_labels = model_with_best_para.predict(numpy.array(all_call_site_features))
    print(type(predict_labels))
    if type(predict_labels) is not numpy.ndarray:
        predict_labels = predict_labels.toarray()
    for opt_index in range(8):
        for index in range(len(predict_labels)):
            item_debug = predict_labels[index][opt_index]
            if predict_labels[index][opt_index] == 1:
                project, call_site = record[index]
                if opt_index not in inlined_call_sites:
                    inlined_call_sites[opt_index] = {}
                if project not in inlined_call_sites[opt_index]:
                    inlined_call_sites[opt_index][project] = {}
                inlined_call_sites[opt_index][project][call_site] = 1
    return inlined_call_sites


def extract_function_sets_after_inlining_for_multi_label_classifier(inlined_call_sites, call_site_to_caller_and_callee,
                                                                    source_fcgs, caller_callee_to_call_sites):
    all_function_sets = []
    for opt_index in inlined_call_sites:
        function_combined_sets = []
        for project_name in inlined_call_sites[opt_index]:
            print("processing project {}".format(project_name))
            # call_site_to_caller_and_callee_per_project = call_site_to_caller_and_callee[project_name]
            # all_mapped_functions = get_inline_mapped_functions(inlined_call_sites[opt_index], project_name,
            #                                                    call_site_to_caller_and_callee_per_project)
            caller_callee_to_call_sites_per_project = caller_callee_to_call_sites[project_name]
            inlined_call_sites_per_project = list(inlined_call_sites[opt_index][project_name].keys())

            project_fcg = source_fcgs[project_name]
            all_project_edges = get_all_call_sites(project_fcg)

            node_to_in_call_sites_in_project_fcg, call_site_to_edge = extract_nodes_in_call_sites(all_project_edges)
            inlined_edges = extract_inlined_edges(inlined_call_sites_per_project, all_project_edges)
            mapped_fcg = project_fcg.edge_subgraph(inlined_edges).copy()
            trees = get_strong_connected_graph(mapped_fcg)
            # print("processing trees")
            validbar = tqdm(desc='Generate', total=len(trees), leave=True)
            for tree in trees:
                tree_nodes = list(tree.nodes())
                if len(tree_nodes) <= 2:
                    sub_root_node = get_root_node(tree)
                    # if sub_root_node != tree_nodes[0]:
                    #     raise Exception
                    tree_nodes.sort()
                    function_combined_sets.append({"root_node": sub_root_node, "content": tree_nodes})
                else:

                    root_node_list, need_to_combined_function_pair, optional_function_pairs = \
                        classify_call_pairs(tree, node_to_in_call_sites_in_project_fcg, inlined_call_sites_per_project,
                                            caller_callee_to_call_sites_per_project)
                    if not optional_function_pairs:
                        sub_tree_nodes, root_nodes_record = generate_full_sub_graphs_from_root_node(tree,
                                                                                                    root_node_list)
                        for index in range(len(root_nodes_record)):
                            sub_tree_nodes[index].sort()
                            function_combined_sets.append({"root_node": root_nodes_record[index],
                                                           "content": sub_tree_nodes[index]})
                    else:
                        sub_tree_nodes, root_nodes_record = \
                            generate_sub_graphs_with_optional_edges(tree, root_node_list, optional_function_pairs)
                        for index in range(len(root_nodes_record)):
                            sub_tree_nodes[index].sort()
                            function_combined_sets.append({"root_node": root_nodes_record[index],
                                                           "content": sub_tree_nodes[index]})

                validbar.update()
            validbar.close()
        all_function_sets.append(function_combined_sets)
    return all_function_sets


def generate_dataset_using_old_test_projects(call_site_feature_and_labels, test_projects):
    all_project_name = []
    for line in call_site_feature_and_labels[1:]:
        if line[0] not in all_project_name:
            all_project_name.append(line[0])
    train_csv_content = [call_site_feature_and_labels[0][1:]]
    test_csv_content = [call_site_feature_and_labels[0][1:]]
    for line in call_site_feature_and_labels[1:]:
        if line[0] not in test_projects:
            train_csv_content.append(line[1:])
        else:
            test_csv_content.append(line[1:])
    train_projects = list(set(all_project_name).difference(set(test_projects)))
    return train_csv_content, test_csv_content, train_projects, test_projects


def conduct_bingo_inlining(binary_func_1, binary_fcg_1, binary_features_1):
    bingo_functions = []
    if binary_func_1 not in binary_fcg_1:
        return None
    successors = list(binary_fcg_1.successors(binary_func_1))
    covered_binary_functions = []
    while successors:
        successor = successors.pop(0)
        if successor in covered_binary_functions:
            continue
        else:
            covered_binary_functions.append(successor)
        if "is_library" in binary_fcg_1.nodes[successor]['node_attribute'] and \
                binary_fcg_1.nodes[successor]['node_attribute']["is_library"]:
            continue
        if successor.startswith("unknown"):
            continue
        if successor not in binary_features_1:
            bingo_functions.append(successor)
            continue
        binary_func_feature_1 = binary_features_1[successor]
        in_degree, out_degree, library_call, terminate_lib_call, recurse_flag, function_len = binary_func_feature_1
        if recurse_flag:
            bingo_functions.append(successor)
            successors = list(binary_fcg_1.successors(successor)) + successors
        else:
            if out_degree == library_call:
                if library_call - terminate_lib_call >= terminate_lib_call:
                    bingo_functions.append(successor)
                    # successors = binary_fcg_1.successors(successor) + successors
                elif library_call - terminate_lib_call < terminate_lib_call:
                    continue
            else:
                alpha = out_degree / (out_degree + in_degree)
                if alpha < 0.01:
                    bingo_functions.append(successor)
                    successors = list(binary_fcg_1.successors(successor)) + successors
                else:
                    continue
    return bingo_functions


def conduct_asm2vec_inlining(binary_func_1, binary_fcg_1, binary_features_1):
    bingo_functions = []
    if binary_func_1 not in binary_fcg_1 or binary_func_1 not in binary_features_1:
        return None
    _, _, _, _, _, BF_function_len = binary_features_1[binary_func_1]
    successors = binary_fcg_1.successors(binary_func_1)
    for successor in successors:
        if "is_library" in binary_fcg_1.nodes[successor]['node_attribute'] and \
                binary_fcg_1.nodes[successor]['node_attribute']["is_library"]:
            continue
        if successor.startswith("unknown"):
            continue
        if successor not in binary_features_1:
            bingo_functions.append(successor)
            continue
        binary_func_feature_1 = binary_features_1[successor]
        in_degree, out_degree, library_call, terminate_lib_call, recurse_flag, function_len = binary_func_feature_1
        if recurse_flag:
            bingo_functions.append(successor)
        else:
            if out_degree == library_call:
                if library_call - terminate_lib_call >= terminate_lib_call:
                    if BF_function_len < 10 or function_len / BF_function_len < 0.6:
                        bingo_functions.append(successor)
                    else:
                        continue
                elif library_call - terminate_lib_call < terminate_lib_call:
                    continue
            else:
                alpha = out_degree / (out_degree + in_degree)
                if alpha < 0.01:
                    if BF_function_len < 10 or function_len / BF_function_len < 0.6:
                        bingo_functions.append(successor)
                else:
                    continue
    return bingo_functions


def get_in_and_out_degrees(project_fcg, NBF):
    if NBF in project_fcg:
        return project_fcg.in_degree(NBF), project_fcg.out_degree(NBF)
    else:
        return None, None


def get_library_call_degree(project_fcg, NSF):
    library_call = 0
    terminate_lib_call = 0
    if NSF not in project_fcg:
        return library_call, terminate_lib_call
    successors = project_fcg.successors(NSF)

    for successor in successors:
        # if successor not in list(project_fcg.nodes()):
        #     continue
        if "is_library" in project_fcg.nodes[successor] and project_fcg.nodes[successor]["is_library"]:
            library_call += 1
            if "exit" in project_fcg.nodes[successor]["function_name"]:
                terminate_lib_call += 1
    return library_call, terminate_lib_call


def find_recurse_call(ISF, project_fcg):
    if ISF not in project_fcg:
        return None
    func_list = project_fcg.predecessors(ISF)
    for func in func_list:
        if func == ISF:
            continue
        if project_fcg.has_edge(func, ISF) and project_fcg.has_edge(ISF, func):
            if project_fcg.in_degree(func) + project_fcg.out_degree(ISF) > project_fcg.in_degree(
                    ISF) + project_fcg.out_degree(func):
                return True
    return False


def extract_source_features(source_fcg):
    source_features = {}
    for function in list(source_fcg.nodes()):
        in_degree, out_degree = get_in_and_out_degrees(source_fcg, function)
        if "node_attribute" not in source_fcg.nodes[function] or \
                "end_line" not in source_fcg.nodes[function]["node_attribute"] or \
                "begin_line" not in source_fcg.nodes[function]["node_attribute"]:
            continue
        function_len = int(source_fcg.nodes[function]["node_attribute"]["end_line"]) - \
                       int(source_fcg.nodes[function]["node_attribute"]["begin_line"])
        library_call, terminate_lib_call = get_library_call_degree(source_fcg, function)
        recurse_flag = find_recurse_call(function, source_fcg)
        source_features[function] = [in_degree, out_degree, library_call, terminate_lib_call, recurse_flag,
                                     function_len]
    return source_features


def use_bingo_and_asm2vec_predict(source_fcgs, test_projects, model_name):
    function_combined_sets = []
    for test_project in test_projects:
        source_fcg = source_fcgs[test_project]
        source_functions = list(source_fcg.nodes())
        source_features = extract_source_features(source_fcg)
        if model_name == "bingo":
            for source_function in source_functions:
                bingo_functions = conduct_bingo_inlining(source_function, source_fcg, source_features)
                if bingo_functions:
                    function_combined_sets.append({"root_node": source_function,
                                                   "content": bingo_functions + [source_function]})
        elif model_name == "asm2vec":
            for source_function in source_functions:
                bingo_functions = conduct_asm2vec_inlining(source_function, source_fcg, source_features)
                if bingo_functions:
                    function_combined_sets.append({"root_node": source_function,
                                                   "content": bingo_functions + [source_function]})
    return function_combined_sets


def main():
    call_site_csv_file = "call_site_feature_and_labels.csv"
    call_site_feature_and_labels = read_csv(call_site_csv_file)
    iter_times = 10

    source_fcg_file = "D:\\tencent_works\\binary2source_matching_under_inlining\\" \
                      "0.preprocessing-source_and_binary_FCG_construction\\Source_FCG_extraction\\source_fcgs.pkl"
    source_fcgs = read_pickle(source_fcg_file)
    function_contents_folder = "D:\\tencent_works\\binary2source_matching_under_inlining\\2.feature_extraction" \
                               "\\features_per_function\\function_contents"
    tree_sitter_lib_path = "C_Cpp.so"

    source_project_call_site_features_file = "source_project_call_site_features.json"
    call_site_to_caller_and_callee_file = "call_site_to_caller_and_callee.json"
    caller_callee_to_call_sites_file = "caller_callee_to_call_sites.pkl"

    all_projects = list(source_fcgs.keys())

    if not os.path.exists(source_project_call_site_features_file) or not os.path.exists(
            call_site_to_caller_and_callee_file) or not os.path.exists(caller_callee_to_call_sites_file):
        source_project_call_site_features, call_site_to_caller_and_callee, caller_callee_to_call_sites = \
            extract_call_site_features_for_prediction(source_fcgs, all_projects, function_contents_folder,
                                                      tree_sitter_lib_path)
        source_project_call_site_features = convert_dict_to_lists(source_project_call_site_features)
        write_json(source_project_call_site_features_file, source_project_call_site_features)
        write_json(call_site_to_caller_and_callee_file, call_site_to_caller_and_callee)
        write_pickle(caller_callee_to_call_sites_file, caller_callee_to_call_sites)
    else:
        source_project_call_site_features = read_json(source_project_call_site_features_file)
        call_site_to_caller_and_callee = read_json(call_site_to_caller_and_callee_file)
        caller_callee_to_call_sites = load_pickle(caller_callee_to_call_sites_file)

    # return
    old_folder = "D:\\tencent_works\\binary2source_matching_under_inlining\\4.apply_classifier_to_test_projects" \
                 "\\multi-label_classifiers\\classifier_models"
    classifier_folder = "D:\\tencent_works\\binary2source_matching_under_inlining\\4.apply_classifier_to_test_projects" \
                        "\\multi-label_classifiers\\bingo_and_asm2vec"
    for x in range(iter_times):
        print("iter times: {}".format(str(x)))
        classifier_iter_folder = os.path.join(classifier_folder, str(x))
        if os.path.exists(classifier_iter_folder) is False:
            os.mkdir(classifier_iter_folder)

        old_test_project_file_path = os.path.join(old_folder, str(x), "test_projects.json")
        test_projects = read_json(old_test_project_file_path)

        train_csv_content, test_csv_content, train_projects, test_projects = \
            generate_dataset_using_old_test_projects(call_site_feature_and_labels, test_projects)

        test_project_file_path = os.path.join(classifier_iter_folder, "test_projects.json")
        write_json(test_project_file_path, test_projects)

        for model_name in ["bingo", "asm2vec"]:
            all_function_combined_sets = use_bingo_and_asm2vec_predict(source_fcgs, test_projects, model_name)
            function_combined_sets_file = os.path.join(classifier_iter_folder, model_name + ".json")
            write_json(function_combined_sets_file, all_function_combined_sets)


if __name__ == '__main__':
    main()

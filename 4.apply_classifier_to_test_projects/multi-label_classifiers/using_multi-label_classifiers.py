from multiprocessing import Pool

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
from models_with_best_para import RFPCT, RFDTBR, ECCJ48, EBRJ48, adaboost, ECOCCJ48


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


def generating_SFSs_using_model(parameters):
    model, training_data, training_label, source_project_call_site_features, test_projects, call_site_to_caller_and_callee, source_fcgs, caller_callee_to_call_sites, classifier_iter_folder = parameters
    model_with_best_para = model()
    model_name = model_with_best_para.get_name()
    print("  using model {}".format(model_name))
    model_with_best_para.train(training_data, training_label)

    inlined_call_sites = use_model_predict(source_project_call_site_features, model_with_best_para,
                                           test_projects)
    function_combined_sets = \
        extract_function_sets_after_inlining_for_multi_label_classifier(inlined_call_sites,
                                                                        call_site_to_caller_and_callee,
                                                                        source_fcgs,
                                                                        caller_callee_to_call_sites)

    all_function_combined_sets = combine_several_lists(function_combined_sets)
    function_combined_sets_file = os.path.join(classifier_iter_folder, model_name + ".json")
    write_json(function_combined_sets_file, all_function_combined_sets)


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

    classifier_folder = "D:\\tencent_works\\binary2source_matching_under_inlining\\4.apply_classifier_to_test_projects" \
                        "\\multi-label_classifiers\\generated_SFSs"
    parameter_list = []
    for x in range(iter_times):
        print("iter times: {}".format(str(x)))
        classifier_iter_folder = os.path.join(classifier_folder, str(x))
        if os.path.exists(classifier_iter_folder) is False:
            os.mkdir(classifier_iter_folder)

        train_csv_content, test_csv_content, train_projects, test_projects = \
            split_dataset_by_projects(call_site_feature_and_labels, train_percent=0.9)

        test_project_file_path = os.path.join(classifier_iter_folder, "test_projects.json")
        write_json(test_project_file_path, test_projects)

        training_data, training_label = extract_datas_and_target(train_csv_content, type="train")
        for model in [ECOCCJ48, RFPCT, RFDTBR, ECCJ48, EBRJ48, adaboost]:
            parameter_list.append([model, training_data, training_label, source_project_call_site_features, test_projects, call_site_to_caller_and_callee, source_fcgs, caller_callee_to_call_sites, classifier_iter_folder])

    process_num = 12
    p = Pool(int(process_num))
    with tqdm(total=len(parameter_list)) as pbar:
        for i, res in tqdm(enumerate(p.imap_unordered(generating_SFSs_using_model, parameter_list))):
            pbar.update()
    p.close()
    p.join()


if __name__ == '__main__':
    main()

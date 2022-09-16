import copy
import itertools
import json
import os.path
import pickle
from itertools import chain, combinations

import graphviz
import networkx as nx
from matplotlib import pyplot as plt
from tqdm import tqdm

from utils import read_pickle, get_all_call_sites, extract_function_contents, get_function_content, \
    extract_function_features, \
    extract_call_site_features, convert_function_features_to_list, add_call_site_features_to_list, write_json
from sklearn.ensemble import RandomForestClassifier
import joblib


def read_json(file_path):
    with open(file_path, "r") as f:
        file_content = json.load(f)
        return file_content


def extract_call_site_features_for_prediction(source_fcgs, test_projects, function_contents_folder,
                                              tree_sitter_lib_path):
    all_call_site_features = {}
    call_site_to_caller_and_callee = {}
    caller_callee_to_call_sites = {}
    for project_name in test_projects:
        print("extracting call site features from project {}".format(project_name))
        if project_name not in all_call_site_features:
            all_call_site_features[project_name] = {}
        if project_name not in call_site_to_caller_and_callee:
            call_site_to_caller_and_callee[project_name] = {}
        if project_name not in caller_callee_to_call_sites:
            caller_callee_to_call_sites[project_name] = {}
        source_project_fcg = source_fcgs[project_name]
        source_all_call_sites = get_all_call_sites(source_project_fcg)
        function_contents = extract_function_contents(function_contents_folder, project_name)
        function_to_features = {}
        for call_site in source_all_call_sites:
            caller, callee, key, call_site_info = call_site

            file_name, function_name, call_site_line, call_site_column = \
                call_site_info["file"], call_site_info["function"], call_site_info["line_number"], call_site_info[
                    "column"]
            call_site_key = "+".join([file_name, function_name, str(call_site_line), str(call_site_column), callee])

            if (caller, callee) not in caller_callee_to_call_sites[project_name]:
                caller_callee_to_call_sites[project_name][(caller, callee)] = []
            if call_site_key not in caller_callee_to_call_sites[project_name][(caller, callee)]:
                caller_callee_to_call_sites[project_name][(caller, callee)].append(call_site_key)

            function_content_per_project = function_contents[project_name]
            caller_content, caller_function_range = get_function_content(file_name, function_name, call_site_line,
                                                                         function_content_per_project)
            callee_file_name, callee_function = callee.split("+")
            callee_content, _ = get_function_content(callee_file_name, callee_function, None,
                                                     function_content_per_project)
            if not caller_content or not callee_content:
                continue

            call_site_to_caller_and_callee[project_name][call_site_key] = {"caller": caller, "callee": callee,
                                                                           "caller_content": caller_content,
                                                                           "callee_content": callee_content}

            caller_features, function_to_features = \
                extract_function_features(project_name, file_name, function_name, caller_content,
                                          function_to_features, tree_sitter_lib_path, source_project_fcg)

            callee_features, function_to_features = \
                extract_function_features(project_name, callee_file_name, callee_function, callee_content,
                                          function_to_features, tree_sitter_lib_path, source_project_fcg)

            if not caller_features or not callee_features:
                continue

            call_site_features = extract_call_site_features(caller_content, caller_function_range, call_site_line,
                                                            tree_sitter_lib_path)

            all_call_site_features[project_name][call_site_key] = {"caller": caller_features,
                                                                   "caller_content": caller_content,
                                                                   "callee": callee_features,
                                                                   "callee_content": callee_content,
                                                                   "call_site": call_site_features}

    return all_call_site_features, call_site_to_caller_and_callee, caller_callee_to_call_sites


def convert_dict_to_lists(call_sites_features_per_project):
    caller_callee_features_list = ["all_statement", "while", "switch", "switch_cases", "if", "for", "return", "declare",
                                   "expression", "call_expression", "total_node", "total_edge", "function_in_degree",
                                   "function_out_degree", "keywords_inline", "keywords_inline_macro", "keywords_static",
                                   "keyword_macro"]
    function_features_keys = ["caller", "callee"]
    call_site_features_list = ["call_site_path_length", "in_for", "in_while", "in_switch", "in_if",
                               "call_site_arguments", "call_site_constant_arguments"]

    for project in call_sites_features_per_project:
        for call_site_key in call_sites_features_per_project[project]:
            call_site_csv_list = []
            call_site_features = call_sites_features_per_project[project][call_site_key]
            for function_key in function_features_keys:
                call_site_features_per_function = call_site_features[function_key]
                call_site_csv_list = convert_function_features_to_list(call_site_features_per_function,
                                                                       caller_callee_features_list,
                                                                       call_site_csv_list)
            only_call_site_features = call_site_features["call_site"]
            call_site_csv_list = add_call_site_features_to_list(call_site_csv_list, only_call_site_features,
                                                                call_site_features_list)
            call_sites_features_per_project[project][call_site_key] = call_site_csv_list
    return call_sites_features_per_project


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


def write_function_content(caller, caller_content, source_functions_path):
    caller_file_name = caller.replace("/", "+")
    caller_file_path = os.path.join(source_functions_path, caller_file_name + ".json")
    if not os.path.exists(caller_file_path):
        write_json(caller_file_path, caller_content)


def write_caller_callee_content(call_site_call_pair):
    caller, callee = call_site_call_pair["caller"], call_site_call_pair["callee"]
    caller_content, callee_content = call_site_call_pair["caller_content"], call_site_call_pair["callee_content"]
    source_functions_path = "D:\\tencent_works\\function_inlining_prediction\\designing_classifier_for_inlining\\" \
                            "4.applying_classfier_to_test_projects\\source_functions"
    write_function_content(caller, caller_content, source_functions_path)
    write_function_content(callee, callee_content, source_functions_path)


def construct_function_sets(inlined_call_sites, call_site_to_caller_and_callee):
    function_combined_sets = []
    for project_name in inlined_call_sites:
        call_site_to_caller_and_callee_per_project = call_site_to_caller_and_callee[project_name]
        caller_to_callee_dict = {}
        for call_site_key in inlined_call_sites[project_name]:
            if call_site_key not in call_site_to_caller_and_callee_per_project:
                # print(call_site_key)
                continue
            call_site_call_pair = call_site_to_caller_and_callee_per_project[call_site_key]
            caller, callee = call_site_call_pair["caller"], call_site_call_pair["callee"]
            # write_caller_callee_content(call_site_call_pair)

            if caller not in caller_to_callee_dict:
                caller_to_callee_dict[caller] = []
            if callee not in caller_to_callee_dict[caller]:
                caller_to_callee_dict[caller].append(callee)

        # caller_mapped_sets = []
        for caller in caller_to_callee_dict:
            caller_mapped_all_sets = [caller]
            caller_mapped_sets = caller_to_callee_dict[caller]
            while caller_mapped_sets:
                function = caller_mapped_sets.pop(0)
                if function in caller_mapped_all_sets:
                    continue
                else:
                    caller_mapped_all_sets.append(function)
                    if caller_mapped_all_sets not in function_combined_sets:
                        function_combined_sets.append(caller_mapped_all_sets)
                    if function in caller_to_callee_dict:
                        function_mapped_callees = caller_to_callee_dict[function]
                        caller_mapped_sets += function_mapped_callees
            function_combined_sets.append(caller_mapped_all_sets)
    return function_combined_sets


def combine_several_lists(all_function_combined_sets):
    function_combined_sets = []
    for function_combined_set_per_prediction in all_function_combined_sets:
        for function_list in function_combined_set_per_prediction:
            if function_list not in function_combined_sets:
                function_combined_sets.append(function_list)
    return function_combined_sets


def format_call_sites(inlined_call_sites_per_opt, test_projects):
    inlined_call_sites = {}
    for inlined_call_site_list in inlined_call_sites_per_opt:
        file_name, function_name, line, column, callee_file, calle_function = inlined_call_site_list.split("+")
        callee = "+".join([callee_file, calle_function])
        project_name = file_name.split("/")[0]
        if project_name not in test_projects:
            continue
        if project_name not in inlined_call_sites:
            inlined_call_sites[project_name] = {}
        call_site_key = file_name + "+" + function_name + "+" + str(line) + "+" + str(column) + "+" + callee
        inlined_call_sites[project_name][call_site_key] = 1
    return inlined_call_sites


def get_all_sub_sets(function_combined_sets):
    all_sub_function_combined_sets = copy.deepcopy(function_combined_sets)
    for function_list in function_combined_sets:
        sub_function_sets = chain.from_iterable(
            combinations(function_list, n) for n in range(2, len(function_list) + 1))
        for sub_function_set in sub_function_sets:
            sub_function_set = list(sub_function_set)
            if not sub_function_set or len(sub_function_set) == 1:
                continue
            if sub_function_set not in all_sub_function_combined_sets:
                all_sub_function_combined_sets.append(sub_function_set)
    return all_sub_function_combined_sets


def get_strong_connected_graph(call_graph):
    root_nodes_list = []
    for node, degree in call_graph.in_degree():
        if degree == 0:
            # print node
            root_nodes_list.append(node)
    strong_connected_graphs = []
    sub_nodes_set_list = []
    sub_nodes_set_union = set()
    for root_node in root_nodes_list:
        sub_nodes_set = nx.descendants(call_graph, root_node)
        sub_nodes_set = sub_nodes_set.union(set([root_node]))
        sub_graph = call_graph.subgraph(sub_nodes_set).copy()
        if sub_graph not in strong_connected_graphs:
            strong_connected_graphs.append(sub_graph)
            sub_nodes_set_list.append(sub_nodes_set)
            sub_nodes_set_union = sub_nodes_set_union.union(sub_nodes_set)

    return strong_connected_graphs


def classify_call_pairs(tree, node_to_in_call_sites_in_project_fcg, inlined_call_sites_per_project,
                        caller_callee_to_call_sites_per_project):
    tree_edges = get_all_call_sites(tree)
    tree_call_site_keys = []
    caller_callee_to_call_sites_in_tree = {}
    for tree_edge in tree_edges:
        caller, callee = tree_edge[0], tree_edge[1]
        call_site_file_name, call_site_function_name, call_site_line_number, call_site_column = \
            tree_edge[3]["file"], tree_edge[3]["function"], tree_edge[3]["line_number"], tree_edge[3]["column"]
        call_site_key = call_site_file_name + "+" + call_site_function_name + "+" + str(
            call_site_line_number) + "+" + str(call_site_column) + "+" + callee
        tree_call_site_keys.append(call_site_key)
        if (caller, callee) not in caller_callee_to_call_sites_in_tree:
            caller_callee_to_call_sites_in_tree[(caller, callee)] = []
        caller_callee_to_call_sites_in_tree[(caller, callee)].append(call_site_key)

    inlined_call_site_keys = list(
        set(tree_call_site_keys).intersection(set(inlined_call_sites_per_project)))
    if set(inlined_call_site_keys) != set(tree_call_site_keys):
        raise Exception

    root_node_list = []
    need_to_combined_function_pair = []
    optional_function_pairs = []
    node_list = list(tree.nodes())
    for node in node_list:
        try:
            node_in_call_site_keys = node_to_in_call_sites_in_project_fcg[node]
        except:
            root_node_list.append(node)
            continue
        if not set(node_in_call_site_keys).issubset(set(inlined_call_site_keys)):
            root_node_list.append(node)
        # else:
        #     print("node {} cannot serves as a root node!".format(node))
    for (caller, callee) in caller_callee_to_call_sites_in_tree:
        call_site_keys_in_tree = caller_callee_to_call_sites_in_tree[(caller, callee)]
        if (caller, callee) not in caller_callee_to_call_sites_per_project:
            continue
        call_site_keys_in_project = caller_callee_to_call_sites_per_project[(caller, callee)]
        if set(call_site_keys_in_tree) == set(call_site_keys_in_project):
            if (caller, callee) not in need_to_combined_function_pair:
                need_to_combined_function_pair.append((caller, callee))
        else:
            if (caller, callee) not in optional_function_pairs:
                optional_function_pairs.append((caller, callee))
    return root_node_list, need_to_combined_function_pair, optional_function_pairs


def extract_nodes_in_call_sites(all_project_edges):
    node_to_in_call_sites = {}
    call_site_to_edge = {}
    for call_site_edge in all_project_edges:
        caller, callee, key, call_site_dict = call_site_edge
        call_site_file_name, call_site_function_name, call_site_line_number, call_site_column = \
            call_site_edge[3]["file"], call_site_edge[3]["function"], call_site_edge[3]["line_number"], \
            call_site_edge[3]["column"]
        call_site_key = call_site_file_name + "+" + call_site_function_name + "+" + str(
            call_site_line_number) + "+" + str(call_site_column) + "+" + callee
        if callee not in node_to_in_call_sites:
            node_to_in_call_sites[callee] = []
        node_to_in_call_sites[callee].append(call_site_key)
        if call_site_key in call_site_to_edge:
            print("same call site key for")
            print(call_site_edge)
            print(call_site_to_edge[call_site_key])
            print("\n")
        call_site_to_edge[call_site_key] = call_site_edge
    return node_to_in_call_sites, call_site_to_edge


def get_all_connected_sub_graphs(G):
    all_connected_subgraphs = []
    # here we ask for all connected subgraphs that have at least 2 nodes AND have less nodes than the input graph
    for nb_nodes in range(2, G.number_of_nodes()):
        for SG in (G.subgraph(selected_nodes) for selected_nodes in itertools.combinations(G, nb_nodes)):
            try:
                root_node = get_root_node(SG)
                undirected_SG = SG.to_undirected()
                if nx.is_connected(undirected_SG):
                    all_connected_subgraphs.append(SG)
            except:
                continue
            # if nx.is_connected(SG):
            #     print(SG.nodes)

    return all_connected_subgraphs


def get_root_node(sub_tree):
    root_nodes_list = []
    for node, degree in sub_tree.in_degree():
        if degree == 0:
            # print node
            root_nodes_list.append(node)
    if len(root_nodes_list) > 1:
        raise Exception
    return root_nodes_list[0]


def reduce_graphs(all_sub_trees, root_node_list, need_to_combined_function_pair):
    reduced_sub_trees = []
    for sub_tree in all_sub_trees:
        failed_flag = False
        if root_node_list:
            root_node = get_root_node(sub_tree)
            if root_node not in root_node_list:
                failed_flag = True
                continue
        if need_to_combined_function_pair:
            tree_nodes = list(sub_tree.nodes())
            for func_pair in need_to_combined_function_pair:
                caller, callee = func_pair
                if caller in tree_nodes and callee not in tree_nodes:
                    failed_flag = True
                    break
        if not failed_flag:
            reduced_sub_trees.append(sub_tree)
    return reduced_sub_trees


def draw_tree_call_graph(call_graph, filename, inlined_call_sites_per_project):
    G = graphviz.Digraph("tree_call_graph", encoding="utf-8")
    # with G.subgraph() as c:
    #     c.node_attr.update(style='filled', color='red')
    #     for node in bin_call_graph.nodes():
    #         # node_name = str(node).split("-")[-1]
    #         node_name = str(node)
    #         if str(node) in bin_id:
    #             c.node(str(node), label=node_name)
    with G.subgraph() as c:
        # c.node_attr.update(style='filled', color='white')
        for node in call_graph.nodes():
            node_name = str(node)
            c.node(str(node), label=node_name)
    all_edges = get_all_call_sites(call_graph)
    colors = ['green', 'red']
    for tree_edge in all_edges:
        caller, callee = tree_edge[0], tree_edge[1]
        call_site_file_name, call_site_function_name, call_site_line_number, call_site_column = \
            tree_edge[3]["file"], tree_edge[3]["function"], tree_edge[3]["line_number"], tree_edge[3]["column"]
        call_site_key = call_site_file_name + "+" + call_site_function_name + "+" + str(
            call_site_line_number) + "+" + str(call_site_column) + "+" + callee
        if call_site_key in inlined_call_sites_per_project:
            G.edge(caller, callee, color="red")
        else:
            G.edge(caller, callee)
    G.view()


def get_inline_mapped_functions(inlined_call_sites, project_name, call_site_to_caller_and_callee_per_project):
    all_mapped_functions = []
    for call_site_key in inlined_call_sites[project_name]:
        if call_site_key not in call_site_to_caller_and_callee_per_project:
            print(call_site_key)
            continue
        call_site_call_pair = call_site_to_caller_and_callee_per_project[call_site_key]
        caller, callee = call_site_call_pair["caller"], call_site_call_pair["callee"]
        # write_caller_callee_content(call_site_call_pair)

        if caller not in all_mapped_functions:
            all_mapped_functions.append(caller)
        if callee not in all_mapped_functions:
            all_mapped_functions.append(callee)
    return all_mapped_functions


def extract_inlined_edges(inlined_call_sites_per_project, all_project_edges):
    inlined_edges = []
    for edge in all_project_edges:
        caller, callee, key = edge[0], edge[1], edge[2]
        call_site_file_name, call_site_function_name, call_site_line_number, call_site_column = \
            edge[3]["file"], edge[3]["function"], edge[3]["line_number"], edge[3]["column"]
        call_site_key = call_site_file_name + "+" + call_site_function_name + "+" + str(
            call_site_line_number) + "+" + str(call_site_column) + "+" + callee
        if call_site_key in inlined_call_sites_per_project:
            inlined_edges.append((caller, callee, key))
    return inlined_edges


def add_project_edges_to_tree(tree, caller_callee_to_call_sites_per_project, call_site_to_edge):
    tree_edges = get_all_call_sites(tree)
    tree_call_site_keys = []
    added_tree = tree.copy()
    added_flag = False
    for tree_edge in tree_edges:
        caller, callee = tree_edge[0], tree_edge[1]
        call_site_file_name, call_site_function_name, call_site_line_number, call_site_column = \
            tree_edge[3]["file"], tree_edge[3]["function"], tree_edge[3]["line_number"], tree_edge[3]["column"]
        call_site_key = call_site_file_name + "+" + call_site_function_name + "+" + str(
            call_site_line_number) + "+" + str(call_site_column) + "+" + callee
        tree_call_site_keys.append(call_site_key)
    for tree_edge in tree_edges:
        caller, callee, key = tree_edge[0], tree_edge[1], tree_edge[2]
        if (caller, callee) not in caller_callee_to_call_sites_per_project:
            continue
        caller_callee_mapped_call_sites = caller_callee_to_call_sites_per_project[(caller, callee)]
        added_call_sites = set(caller_callee_mapped_call_sites).difference(set(tree_call_site_keys))
        if added_call_sites:
            for call_site_key in added_call_sites:
                edge = call_site_to_edge[call_site_key]
                caller, callee, key, call_site_dict = edge
                if callee not in tree:
                    continue
                added_tree.add_edge(caller, callee, call_site_location=call_site_dict)
                added_flag = True
    return added_tree, added_flag


def generate_full_sub_graphs_from_root_node(tree, root_node_list):
    root_nodes_record = []
    sub_tree_nodes = []
    for root_node in root_node_list:
        sub_nodes_set = nx.descendants(tree, root_node)
        sub_nodes_set = sub_nodes_set.union(set([root_node]))
        if len(list(sub_nodes_set)) < 2:
            continue
        sub_graph = tree.subgraph(sub_nodes_set).copy()
        graph_nodes = list(sub_graph.nodes())
        if graph_nodes not in sub_tree_nodes:
            sub_tree_nodes.append(graph_nodes)
            root_nodes_record.append(root_node)
    return sub_tree_nodes, root_nodes_record


def generate_sub_graphs_with_optional_edges(tree, root_node_list, optional_function_pairs):
    root_nodes_record = []
    sub_tree_nodes = []
    for root_node in root_node_list:
        sub_nodes_set = nx.descendants(tree, root_node)
        sub_nodes_set = sub_nodes_set.union(set([root_node]))
        if len(list(sub_nodes_set)) < 2:
            continue
        sub_graph = tree.subgraph(sub_nodes_set).copy()
        graph_nodes = list(sub_graph.nodes())
        if graph_nodes not in sub_tree_nodes:
            sub_tree_nodes.append(graph_nodes)
            root_nodes_record.append(root_node)
        sub_graph_edges = list(sub_graph.edges())
        include_function_pair = []
        for function_pair in optional_function_pairs:
            if function_pair in sub_graph_edges:
                include_function_pair.append(function_pair)
        include_function_pairs_by_all_sequence = list(itertools.permutations(include_function_pair))
        for include_function_pair_by_one_sequence in include_function_pairs_by_all_sequence:
            sub_graph_for_one_sequence = sub_graph.copy()
            for function_pair in include_function_pair_by_one_sequence:
                sub_graph_for_one_sequence.remove_edge(function_pair[0], function_pair[1])
            sub_graphs_by_split = get_strong_connected_graph(sub_graph_for_one_sequence)
            for sub_graph_by_split in sub_graphs_by_split:
                sub_graph_by_split_nodes = list(sub_graph_by_split.nodes())
                if sub_graph_by_split_nodes not in sub_tree_nodes and len(sub_graph_by_split_nodes) >= 2:
                    sub_tree_nodes.append(sub_graph_by_split_nodes)
                    sub_graph_by_split_root_node = get_root_node(sub_graph_by_split)
                    root_nodes_record.append(sub_graph_by_split_root_node)
    return sub_tree_nodes, root_nodes_record


def extract_function_sets_after_inlining(inlined_call_sites, call_site_to_caller_and_callee, source_fcgs,
                                         caller_callee_to_call_sites):
    function_combined_sets = []
    for project_name in inlined_call_sites:
        print("processing project {}".format(project_name))
        call_site_to_caller_and_callee_per_project = call_site_to_caller_and_callee[project_name]
        all_mapped_functions = get_inline_mapped_functions(inlined_call_sites, project_name,
                                                           call_site_to_caller_and_callee_per_project)
        caller_callee_to_call_sites_per_project = caller_callee_to_call_sites[project_name]
        inlined_call_sites_per_project = list(inlined_call_sites[project_name].keys())

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
                # if 10 < len(tree_nodes) < 6:
                #     continue
                # else:
                # nx.draw_networkx(tree)
                # plt.show()
                # new_tree, added_flag = \
                #     add_project_edges_to_tree(tree, caller_callee_to_call_sites_per_project, call_site_to_edge)
                # if not added_flag:
                #     continue
                # if len(list(new_tree.nodes())) == len(list(tree.nodes())):
                #     draw_tree_call_graph(new_tree, "tree.png", inlined_call_sites_per_project)
                # else:
                #     print("error")
                #     new_tree = add_project_edges_to_tree(tree, caller_callee_to_call_sites_per_project,
                #                                         call_site_to_edge)

                root_node_list, need_to_combined_function_pair, optional_function_pairs = \
                    classify_call_pairs(tree, node_to_in_call_sites_in_project_fcg, inlined_call_sites_per_project,
                                        caller_callee_to_call_sites_per_project)
                if not optional_function_pairs:
                    sub_tree_nodes, root_nodes_record = generate_full_sub_graphs_from_root_node(tree, root_node_list)
                    for index in range(len(root_nodes_record)):
                        sub_tree_nodes[index].sort()
                        function_combined_sets.append({"root_node": root_nodes_record[index],
                                                       "content": sub_tree_nodes[index]})
                # else:
                #     sub_tree_nodes, root_nodes_record = \
                #         generate_sub_graphs_with_optional_edges(tree, root_node_list, optional_function_pairs)
                #     for index in range(len(root_nodes_record)):
                #         sub_tree_nodes[index].sort()
                #         function_combined_sets.append({"root_node": root_nodes_record[index],
                #                                        "content": sub_tree_nodes[index]})

            validbar.update()
        validbar.close()
    return function_combined_sets


def write_pickle(caller_callee_to_call_sites_file, caller_callee_to_call_sites):
    with open(caller_callee_to_call_sites_file, "wb") as f:
        pickle.dump(caller_callee_to_call_sites, f)


def load_pickle(file):
    with open(file, 'rb') as f:
        return pickle.load(f)


def main():
    test_projects_file = "test_projects.json"
    source_fcg_file = "D:\\tencent_works\\function_inlining_prediction\\designing_classifier_for_inlining\\" \
                      "0.preprocessing-source_and_binary_FCG_construction\\Source_FCG_extraction\\source_fcgs.pkl"
    source_fcgs = read_pickle(source_fcg_file)
    function_contents_folder = "D:\\tencent_works\\function_inlining_prediction\\designing_classifier_for_inlining\\" \
                               "2.feature_extraction\\features_per_function\\function_contents"
    tree_sitter_lib_path = "C_Cpp.so"
    test_projects = read_json(test_projects_file)
    source_project_call_site_features_file = "source_project_call_site_features.json"
    call_site_to_caller_and_callee_file = "call_site_to_caller_and_callee.json"
    caller_callee_to_call_sites_file = "caller_callee_to_call_sites.pkl"
    if not os.path.exists(source_project_call_site_features_file) or not os.path.exists(
            call_site_to_caller_and_callee_file) or not os.path.exists(caller_callee_to_call_sites_file):
        source_project_call_site_features, call_site_to_caller_and_callee, caller_callee_to_call_sites = \
            extract_call_site_features_for_prediction(source_fcgs, test_projects, function_contents_folder,
                                                      tree_sitter_lib_path)
        source_project_call_site_features = convert_dict_to_lists(source_project_call_site_features)
        write_json(source_project_call_site_features_file, source_project_call_site_features)
        write_json(call_site_to_caller_and_callee_file, call_site_to_caller_and_callee)
        write_pickle(caller_callee_to_call_sites_file, caller_callee_to_call_sites)
    else:
        source_project_call_site_features = read_json(source_project_call_site_features_file)
        call_site_to_caller_and_callee = read_json(call_site_to_caller_and_callee_file)
        caller_callee_to_call_sites = load_pickle(caller_callee_to_call_sites_file)

    ground_truth_file = "D:\\tencent_works\\function_inlining_prediction\\designing_classifier_for_inlining\\" \
                        "1.inlining_ground_truth_labeling\\inlining_ground_truth_labeling_per_call_site\\" \
                        "call_sites_identification_through_inference\\normal_and_inlined_call_sites_by_infer.json"
    ground_truth = read_json(ground_truth_file)
    compiler_list = ["gcc-8.2.0", "clang-7.0"]
    opt_list = ["O0", "O1", "O2", "O3"]
    all_function_combined_sets = []
    for compiler in compiler_list:
        for opt in opt_list:
            print(compiler + "-" + opt)
            inlined_call_sites_per_opt = ground_truth[compiler][opt]["inlined_call_sites"]
            inlined_call_sites = format_call_sites(inlined_call_sites_per_opt, test_projects)
            function_combined_sets = \
                extract_function_sets_after_inlining(inlined_call_sites, call_site_to_caller_and_callee, source_fcgs,
                                                     caller_callee_to_call_sites)
            all_function_combined_sets.append(function_combined_sets)

    all_function_combined_sets = combine_several_lists(all_function_combined_sets)
    # all_function_combined_sets = get_all_sub_sets(all_function_combined_sets)
    function_combined_sets_file = "function_combined_sets.json"
    write_json(function_combined_sets_file, all_function_combined_sets)


if __name__ == '__main__':
    main()

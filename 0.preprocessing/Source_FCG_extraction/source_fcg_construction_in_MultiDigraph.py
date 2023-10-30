import json
import os

import networkx as nx
import pickle


def read_json(file_path):
    with open(file_path, "r") as f:
        file_content = json.load(f)
        return file_content


def extract_caller_callee_list_from_json(entity_calls_json):
    caller_callee_dict = {}
    function_file_name_dict = {}
    for file_name in entity_calls_json:
        function_dict_list = entity_calls_json[file_name]
        file_name = file_name.replace("D:\\tencent_works\\function_inlining_prediction\\"
                                      "designing_classifier_for_inlining\\src\\","").replace("\\", "/")
        for function_dict in function_dict_list:
            for function_name in function_dict:
                calls_dict = function_dict[function_name]["call"]
                if calls_dict:
                    caller_function_name = function_name
                    caller_function_file = file_name
                    for call_function_dict in calls_dict:
                        callee_function_name = call_function_dict["entity"]
                        call_site_location = {"file": caller_function_file, "function": caller_function_name,
                                              "line_number": call_function_dict["line_number"],
                                              "column": call_function_dict["column"]}
                        if call_function_dict["file"] is None:
                            callee_function_file = "unknown"
                        else:
                            callee_function_file = \
                                call_function_dict["file"].replace("D:\\tencent_works\\function_inlining_prediction"
                                                                   "\\designing_classifier_for_inlining\\src\\",
                                                                   "").replace("\\", "/")
                        caller_function_file_name = caller_function_file + "+" + caller_function_name
                        callee_function_file_name = callee_function_file + "+" + callee_function_name
                        if caller_function_file_name not in function_file_name_dict or caller_function_file_name in function_file_name_dict \
                                and "begin_line" not in function_file_name_dict[caller_function_file_name]:
                            function_file_name_dict[caller_function_file_name] = {"file": caller_function_file,
                                                                                  "function": caller_function_name,
                                                                                  "is_library": False,
                                                                                  "begin_line":
                                                                                      function_dict[function_name][
                                                                                          "begin_line"],
                                                                                  "end_line":
                                                                                      function_dict[function_name][
                                                                                          "end_line"]}
                        if callee_function_file_name not in function_file_name_dict:
                            function_file_name_dict[callee_function_file_name] = {"file": callee_function_file,
                                                                                  "function": callee_function_name,
                                                                                  "is_library": False if
                                                                                  call_function_dict["file"] else True}

                        if caller_function_file_name not in caller_callee_dict:
                            caller_callee_dict[caller_function_file_name] = []
                        caller_callee_dict[caller_function_file_name].append([callee_function_file_name, call_site_location])

                else:
                    caller_function_name = function_name
                    caller_function_file = file_name
                    caller_function_file_name = caller_function_file + "+" + caller_function_name
                    if caller_function_file_name not in function_file_name_dict or caller_function_file_name in function_file_name_dict \
                            and "begin_line" not in function_file_name_dict[caller_function_file_name]:
                        function_file_name_dict[caller_function_file_name] = {"file": caller_function_file,
                                                                              "function": caller_function_name,
                                                                              "is_library": False,
                                                                              "begin_line":
                                                                                  function_dict[function_name][
                                                                                      "begin_line"],
                                                                              "end_line": function_dict[function_name][
                                                                                  "end_line"]}
    return caller_callee_dict, function_file_name_dict


def construct_fcg(fcg_content):
    call_graph = nx.MultiDiGraph()
    caller_callee_dict, function_file_name_dict = extract_caller_callee_list_from_json(fcg_content)
    for caller in caller_callee_dict:
        callees_fuzzy = caller_callee_dict[caller]
        for callee_fuzzy, call_site_location in callees_fuzzy:
            if caller not in list(call_graph.nodes()):
                call_graph.add_node(caller, node_attribute=function_file_name_dict[caller])
            if callee_fuzzy not in list(call_graph.nodes()):
                call_graph.add_node(callee_fuzzy, node_attribute=function_file_name_dict[callee_fuzzy])
            call_graph.add_edge(caller, callee_fuzzy, call_site_location=call_site_location)
    return call_graph


def construct_fcg_considering_call_site(fcg_file_path):
    fcg_file_content = read_json(fcg_file_path)
    call_graph = construct_fcg(fcg_file_content)
    return call_graph


def write_pickle(obj, file_path):
    with open(file_path, "wb") as f:
        pickle.dump(obj, f)


def main():
    # FCG_folder = "D:\\tencent_works\\function_inlining_prediction\\designing_classifier_for_inlining\\" \
    #              "0.preprocessing-source_and_binary_FCG_construction\\Source_FCG_extraction\\FCG"
    FCG_folder = "D:\\tencent_works\\function_inlining_prediction\\designing_classifier_for_inlining\\FCG"
    fcg_files = os.listdir(FCG_folder)
    FCGs_of_all_projects = {}
    for fcg_file in fcg_files:
        print("processing project {}, {} of total {}".format(fcg_file, fcg_files.index(fcg_file) + 1, len(fcg_files)))
        fcg_file_path = os.path.join(FCG_folder, fcg_file)
        fcg_per_project = construct_fcg_considering_call_site(fcg_file_path)
        project_name = fcg_file.split("_")[0]
        FCGs_of_all_projects[project_name] = fcg_per_project
    FCGs_of_all_projects_pickle_file = "source_fcgs.pkl"
    write_pickle(FCGs_of_all_projects, FCGs_of_all_projects_pickle_file)


if __name__ == '__main__':
    main()
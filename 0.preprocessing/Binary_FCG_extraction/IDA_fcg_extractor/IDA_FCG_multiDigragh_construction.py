import json
import os
import pickle
import networkx as nx

def write_json(file_path, obj):
    with open(file_path, "w") as f:
        json_str = json.dumps(obj, indent=2)
        f.write(json_str)


def write_pickle(obj, file_path):
    with open(file_path, "wb") as f:
        pickle.dump(obj, f)


def read_json(file_path):
    with open(file_path, "r") as f:
        file_content = json.load(f)
        return file_content


def read_binary_list(projectdir):
    """
    get all binary file's path
    """
    binary_paths = []
    for root, dirs, files in os.walk(projectdir):
        for file_name in files:
            if file_name.endswith(".elf"):
                file_path = os.path.join(root, file_name)
                binary_paths.append(file_path)
    return binary_paths


def extract_address_to_name_mapping(binary_range):
    binary_function_start_address_to_function_name = {}
    for function_name in binary_range:
        start_address = binary_range[function_name]["start_address"]
        binary_function_start_address_to_function_name[start_address] = function_name
    return binary_function_start_address_to_function_name


def construct_fcg_for_binary(binary_range_file, binary_FCG_file):
    binary_range = read_json(binary_range_file)
    binary_function_start_address_to_function_name = extract_address_to_name_mapping(binary_range)
    binary_FCG_call_pairs = read_json(binary_FCG_file)
    binary_FCG = nx.MultiDiGraph()
    for call_pair in binary_FCG_call_pairs:
        caller_function_address, callee_function_address, call_location = call_pair
        caller_function_name = binary_function_start_address_to_function_name[caller_function_address]
        callee_function_name = binary_function_start_address_to_function_name[callee_function_address]
        if caller_function_name not in binary_FCG:
            binary_FCG.add_node(caller_function_name, node_attribute=binary_range[caller_function_name])
        if callee_function_name not in binary_FCG:
            binary_FCG.add_node(callee_function_name, node_attribute=binary_range[callee_function_name])
        binary_FCG.add_edge(caller_function_name, callee_function_name, call_site_location=call_location)
    return binary_FCG


def extract_function_mapping(binary_range_file):
    binary_address_name_to_function_name_mapping = {}
    binary_function_range = read_json(binary_range_file)
    for function_name in binary_function_range:
        function_start_address_in_10 = binary_function_range[function_name]["start_address"]
        function_address_name = "Func_00" + str(hex(function_start_address_in_10))[2:]
        binary_address_name_to_function_name_mapping[function_address_name] = function_name
    return binary_address_name_to_function_name_mapping


def main():
    binary_project_folder = "D:\\tencent_works\\classifier_for_inlinining_determintation\\" \
                            "designing_classifier_for_inlining\\test_dataset\\gnu_debug"
    project_name_list = os.listdir(binary_project_folder)
    binary_paths_list = []
    for project_name in project_name_list:
        binary_project_dir = os.path.join(binary_project_folder, project_name)
        binary_paths = read_binary_list(binary_project_dir)
        binary_paths_list += binary_paths
    binary_name_mapping = {}
    binary_fcgs = {}
    for binary_path in binary_paths_list:
        print("processing binary {} of {}".format(binary_paths_list.index(binary_path), len(binary_paths_list)))
        binary_range_file = binary_path + ".json"
        binary_FCG_file = binary_path + ".fcg"
        elf_name = os.path.basename(binary_path)
        binary_address_name_to_function_name_mapping = extract_function_mapping(binary_range_file)
        binary_name_mapping[elf_name] = binary_address_name_to_function_name_mapping
        binary_fcg = construct_fcg_for_binary(binary_range_file, binary_FCG_file)
        binary_fcgs[elf_name] = binary_fcg

    binary_mapping_file = "binary_name_mapping.json"
    write_json(binary_mapping_file, binary_name_mapping)
    binary_fcgs_file = "binary_fcgs.pkl"
    write_pickle(binary_fcgs, binary_fcgs_file)


if __name__ == '__main__':
    main()
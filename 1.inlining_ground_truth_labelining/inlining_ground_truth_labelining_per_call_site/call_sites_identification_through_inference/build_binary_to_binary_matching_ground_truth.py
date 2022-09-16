import os
import json


def read_json(file_path):
    with open(file_path, "r") as f:
        file_content = json.load(f)
        return file_content


def write_json(file_path, obj):
    with open(file_path, "w") as f:
        json_str = json.dumps(obj)
        f.write(json_str)


def get_split_parts(compilation_binary):
    split_parts = compilation_binary.split("_")
    binary_project_name = split_parts[0]
    compiler = split_parts[1]
    arch = split_parts[2] + "_" + split_parts[3]
    opt = split_parts[4]
    binary_name = "_".join(split_parts[5:])
    return compiler, opt, arch, binary_name, binary_project_name


def get_binary_name_list(binary_dir):
    binary_name_list = {}
    binary_project_full_name = {}
    for project_name in os.listdir(binary_dir):
        project_binary_folder = os.path.join(binary_dir, project_name)
        binary_name_list[project_name] = []
        for binary_full_name in os.listdir(project_binary_folder):
            if not binary_full_name.endswith(".elf"):
                continue
            binary_full_name = binary_full_name.replace(".elf", "")
            compiler, opt, arch, binary_name, binary_project_name = get_split_parts(binary_full_name)
            if binary_name not in binary_name_list[project_name]:
                binary_name_list[project_name].append(binary_name)
            if project_name not in binary_project_full_name:
                binary_project_full_name[project_name] = binary_project_name
    return binary_name_list, binary_project_full_name


def extract_binary_start_address_to_function(binary_range_1):
    binary_start_address_to_function_1 = {}
    for function_dict in binary_range_1:
        function_name = function_dict["name"]
        function_start_address = function_dict["start"]
        binary_start_address_to_function_1[function_start_address] = function_name
    return binary_start_address_to_function_1


def get_source_function_key_to_binary_function(mapping_content_1):
    source_function_key_to_binary_function_1 = {}
    binary_function_to_source_functions_1 = {}
    for binary_function in mapping_content_1:
        source_functions = mapping_content_1[binary_function]
        if source_functions:
            original_source_function_dict = source_functions[0]
            source_function_key = original_source_function_dict[0] + "+" + original_source_function_dict[1] + "+" + str(
                original_source_function_dict[2][0])
            is_inlined = False
            inlined_function_keys = []
            if len(source_functions) > 1:
                inlined_functions = source_functions[1:]
                is_inlined = True
                for inlined_function_dict in inlined_functions:
                    inlined_function_key = inlined_function_dict[0] + "+" + inlined_function_dict[1] + "+" + str(
                        inlined_function_dict[2][0])
                    if inlined_function_key not in inlined_function_keys:
                        inlined_function_keys.append(inlined_function_key)
            source_function_key_to_binary_function_1[source_function_key] = {"binary_function": binary_function,
                                                                             "is_inlined": is_inlined,
                                                                             "inlined_source_functions": inlined_function_keys}
            binary_function_to_source_functions_1[binary_function] = {"OSF": source_function_key,
                                                                      "is_inlined": is_inlined,
                                                                      "ISFs": inlined_function_keys}
    return source_function_key_to_binary_function_1, binary_function_to_source_functions_1


def is_subset(inlined_functions_1, inlined_functions_2):
    return set(inlined_functions_1).issubset(set(inlined_functions_2))


def get_compared_class(function_dict_1, function_dict_2):
    is_inlined_1 = function_dict_1["is_inlined"]
    is_inlined_2 = function_dict_2["is_inlined"]
    inlined_functions_1 = function_dict_1["inlined_source_functions"]
    inlined_functions_2 = function_dict_2["inlined_source_functions"]
    if not is_inlined_1 and not is_inlined_2:
        return 1
    elif is_inlined_1 and is_inlined_2 and inlined_functions_1 == inlined_functions_2:
        return 2
    elif not is_inlined_1 and is_inlined_2 or is_inlined_1 and not is_inlined_2:
        return 3
    elif is_inlined_1 and is_inlined_2 and (is_subset(inlined_functions_1, inlined_functions_2) or
                                            is_subset(inlined_functions_2, inlined_functions_1)):
        return 4
    elif is_inlined_1 and is_inlined_2 and not set(inlined_functions_1).intersection(set(inlined_functions_2)):
        return 5
    elif is_inlined_1 and is_inlined_2 and set(inlined_functions_1).intersection(set(inlined_functions_2)):
        return 6


def get_binary_functions_with_same_source_key(source_function_key_to_binary_function_1,
                                              source_function_key_to_binary_function_2):
    need_to_matched_function_pairs = []
    # function_pairs_info = []
    for source_function_1 in source_function_key_to_binary_function_1:
        if source_function_1 in source_function_key_to_binary_function_2:
            binary_function_1 = source_function_key_to_binary_function_1[source_function_1]["binary_function"]
            binary_function_2 = source_function_key_to_binary_function_2[source_function_1]["binary_function"]
            compared_class = get_compared_class(source_function_key_to_binary_function_1[source_function_1],
                                                source_function_key_to_binary_function_2[source_function_1])
            need_to_matched_function_pairs.append([binary_function_1, binary_function_2, compared_class])
    return need_to_matched_function_pairs


def get_need_to_matched_function_pairs_per_binary(mapping_content_1, mapping_content_2):
    source_function_key_to_binary_function_1, binary_function_to_source_functions_1 = \
        get_source_function_key_to_binary_function(mapping_content_1)
    source_function_key_to_binary_function_2, binary_function_to_source_functions_2 = \
        get_source_function_key_to_binary_function(mapping_content_2)
    need_to_matched_function_pairs = get_binary_functions_with_same_source_key(source_function_key_to_binary_function_1,
                                                                               source_function_key_to_binary_function_2)
    return need_to_matched_function_pairs, binary_function_to_source_functions_1, binary_function_to_source_functions_2


def main():
    dataset_basedir = "/data/home/angjia/binary2source_dataset/normal_dataset"
    binary_dir = os.path.join(dataset_basedir, "gnu_debug")
    mapping_results_dir = os.path.join(dataset_basedir, "mapping_results_for_gnu_debug")
    opt = ["O0", "O1", "O2", "O3"]
    # project = "coreutils-8.29"
    # compiler = "gcc-8.2.0"
    compiler_list = ["clang-7.0", "gcc-8.2.0"]
    arch = "x86_64"
    binary_name_list, binary_project_full_name = get_binary_name_list(binary_dir)
    for compiler in compiler_list:
        need_to_matched_binary_and_functions = {}
        function_composition = {}
        print(compiler)
        for opt1 in opt:
            print("opt1 {}".format(opt1))
            for opt2 in opt:
                print("  opt2 {}".format(opt2))
                for project in binary_name_list:
                    for binary_name in binary_name_list[project]:
                        binary_name_1 = "_".join(
                            [binary_project_full_name[project], compiler, arch, opt1, binary_name]) + ".elf"
                        # binary_range_file_1 = os.path.join(binary_dir, project, binary_name_1 + ".ghi")
                        # binary_range_1 = read_json(binary_range_file_1)
                        binary_name_2 = "_".join(
                            [binary_project_full_name[project], compiler, arch, opt2, binary_name]) + ".elf"
                        # binary_range_file_2 = os.path.join(binary_dir, project, binary_name_2 + ".ghi")
                        # binary_range_2 = read_json(binary_range_file_2)
                        mapping_file_name_1 = binary_name_1 + "_function_mapping.json"
                        mapping_file_1 = os.path.join(mapping_results_dir, project, mapping_file_name_1)
                        mapping_content_1 = read_json(mapping_file_1)
                        mapping_file_name_2 = binary_name_2 + "_function_mapping.json"
                        mapping_file_2 = os.path.join(mapping_results_dir, project, mapping_file_name_2)
                        mapping_content_2 = read_json(mapping_file_2)
                        need_to_matched_function_pairs, binary_function_to_source_functions_1, \
                            binary_function_to_source_functions_2 = \
                            get_need_to_matched_function_pairs_per_binary(mapping_content_1, mapping_content_2)
                        if binary_name_1 not in need_to_matched_binary_and_functions:
                            need_to_matched_binary_and_functions[binary_name_1] = {}
                        if binary_name_2 not in need_to_matched_binary_and_functions[binary_name_1]:
                            need_to_matched_binary_and_functions[binary_name_1][
                                binary_name_2] = need_to_matched_function_pairs
                        if binary_name_1 not in function_composition:
                            function_composition[binary_name_1] = binary_function_to_source_functions_1
        need_to_matched_binary_and_functions_file = "need_to_matched_binary_and_functions_" + compiler + ".json"
        write_json(need_to_matched_binary_and_functions_file, need_to_matched_binary_and_functions)
        function_composition_file = "function_composition_" + compiler + ".json"
        write_json(function_composition_file, function_composition)



if __name__ == '__main__':
    main()

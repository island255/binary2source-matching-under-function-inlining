import os
import json
import pickle
import re

from tqdm import tqdm


def read_json(file_path):
    if not os.path.exists(file_path):
        raise Exception
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


def get_split_parts(compilation_binary):
    split_parts = compilation_binary.split("_")
    binary_project_name = split_parts[0]
    compiler = split_parts[1]
    arch = split_parts[2] + "_" + split_parts[3]
    opt = split_parts[4]
    binary_name = "_".join(split_parts[5:])
    return compiler, opt, arch, binary_name, binary_project_name


def read_pickle(pickle_file):
    with open(pickle_file, "rb") as f:
        return pickle.load(f)


def get_binary_mapped_source_functions(binary_fcg, binary_function_to_source_function_dict_per_binary):
    binary_nodes = binary_fcg.nodes()
    binary_mapped_source_nodes = []
    for binary_node in binary_nodes:
        if binary_node not in binary_function_to_source_function_dict_per_binary:
            continue
        OSF = binary_function_to_source_function_dict_per_binary[binary_node]["OSF"]
        OSF = "+".join(OSF.split("+")[:-1]).replace("/data", "/apdcephfs/share_1199231")
        if OSF not in binary_mapped_source_nodes:
            binary_mapped_source_nodes.append(OSF)
        ISFs = binary_function_to_source_function_dict_per_binary[binary_node]["ISFs"]
        for ISF in ISFs:
            ISF = "+".join(ISF.split("+")[:-1]).replace("/data", "/apdcephfs/share_1199231")
            if ISF not in binary_mapped_source_nodes:
                binary_mapped_source_nodes.append(ISF)
    return binary_mapped_source_nodes


def remove_redundant_nodes(binary_fcg, source_project_fcg, binary_function_to_source_function_dict_per_binary):
    binary_mapped_source_nodes = get_binary_mapped_source_functions(binary_fcg,
                                                                    binary_function_to_source_function_dict_per_binary)
    source_nodes = list(source_project_fcg.nodes())
    for node in source_nodes:
        if node not in binary_mapped_source_nodes:
            source_project_fcg.remove_node(node)
    return source_project_fcg


def extract_inlined_function_relations(binary_function_to_source_function_dict_per_binary):
    inlined_source_function_relations = []
    all_source_functions = []
    for binary_function in binary_function_to_source_function_dict_per_binary:
        source_function = binary_function_to_source_function_dict_per_binary[binary_function]["OSF"]
        source_function = \
            "+".join(source_function.split("+")[:-1]).replace(
                "/data1/jiaang2022/tencent_works/dataset_I/src/", "")
        ISFs = binary_function_to_source_function_dict_per_binary[binary_function]["ISFs"]
        if source_function not in all_source_functions:
            all_source_functions.append(source_function)
        if ISFs:
            ISFs_normalized_name_list = []
            for ISF in ISFs:
                ISF = "+".join(ISF.split("+")[:-1]).replace(
                    "/data1/jiaang2022/tencent_works/dataset_I/src/", "")
                if ISF not in ISFs_normalized_name_list:
                    ISFs_normalized_name_list.append(ISF)
                if ISF not in all_source_functions:
                    all_source_functions.append(ISF)
            inlined_source_function_relations.append({"OSF": source_function,
                                                      "ISFs": ISFs_normalized_name_list,
                                                      "BFI": binary_function})
    return inlined_source_function_relations, all_source_functions


def infer_inlined_pairs(source_project_fcg, OSF, ISFs):
    all_fcg_edges = list(source_project_fcg.edges())
    inlined_pairs = []
    for ISF in ISFs:
        if (OSF, ISF) in all_fcg_edges:
            inlined_pairs.append((OSF, ISF))
        else:
            for ISF_x in ISFs:
                if (ISF_x, ISF) in all_fcg_edges:
                    inlined_pairs.append((ISF_x, ISF))
    return inlined_pairs


def get_intersection_from_BF(all_call_pairs, all_source_functions):
    included_call_pairs = []
    for call_pair in all_call_pairs:
        caller, callee, key, call_site = call_pair
        if caller in all_source_functions and callee in all_source_functions:
            included_call_pairs.append((caller, callee))
    return included_call_pairs


def get_all_call_sites(source_project_fcg):
    all_call_pairs = []
    for u, v, keys, call_site in source_project_fcg.edges(data="call_site_location", keys=True):
        all_call_pairs.append([u, v, keys, call_site])
    return all_call_pairs


def classify_call_pairs(inlined_source_function_relations, source_project_fcg, all_source_functions):
    inlined_call_pairs = []
    all_source_call_pairs = get_all_call_sites(source_project_fcg)
    included_source_call_pairs = get_intersection_from_BF(all_source_call_pairs, all_source_functions)
    for inlined_function_relation in inlined_source_function_relations:
        OSF = inlined_function_relation["OSF"]
        ISFs = inlined_function_relation["ISFs"]
        inlined_pairs_per_BF = infer_inlined_pairs(source_project_fcg, OSF, ISFs)
        inlined_call_pairs += inlined_pairs_per_BF
    normal_call_pairs = list(set(included_source_call_pairs).difference(set(inlined_call_pairs)))
    # normal_call_pairs = []
    return normal_call_pairs, inlined_call_pairs


def extract_node_degrees(source_project_fcg):
    nodes_in_and_out_degree = {}
    for node in source_project_fcg.nodes():
        node_in_degree = source_project_fcg.in_degree(node)
        node_out_degree = source_project_fcg.out_degree(node)
        nodes_in_and_out_degree[node] = [node_in_degree, node_out_degree]
    return nodes_in_and_out_degree


def convert_list_mapping_to_dict_mapping(binary2source_line_mapping):
    binary2source_line_mapping_dict = {}
    for line_mapping in binary2source_line_mapping:
        source_file, source_line, source_function, source_function_range, binary_function, binary_address = \
            line_mapping
        binary_address = int(binary_address, 16)
        if binary_address not in binary2source_line_mapping_dict:
            binary2source_line_mapping_dict[binary_address] = []
        binary2source_line_mapping_dict[binary_address].append([source_file, source_line, source_function,
                                                                source_function_range, binary_function])
    return binary2source_line_mapping_dict


def find_min_x(distance, x=4):
    import copy
    distance_copy = copy.deepcopy(distance)
    min_number = []
    min_index = []
    for _ in range(x):
        number = min(distance_copy)
        index = distance_copy.index(number)
        distance_copy[index] = 10000
        min_number.append(number)
        min_index.append(index)
    return min_index


def seek_for_nearby_address(binary_address, binary2source_line_mapping):
    binary_address_hex = int(binary_address, 16)
    address_list = []
    distance = []
    for address_str in binary2source_line_mapping:
        address_list.append(int(address_str, 16))
        distance.append(abs(binary_address_hex - int(address_str, 16)))
    nearby_address_index_list = find_min_x(distance, x=2)
    nearby_address_list = [address_list[index] for index in nearby_address_index_list]
    return nearby_address_list


def get_nearby_address_mapped_list(binary_address, binary2source_down_fuzzy_mapping, binary2source_up_fuzzy_mapping):
    if int(binary_address, 16) not in binary2source_down_fuzzy_mapping or \
            int(binary_address, 16) not in binary2source_up_fuzzy_mapping:
        return []
    up_address_mapped_list = binary2source_down_fuzzy_mapping[int(binary_address, 16)]
    down_address_mapped_list = binary2source_up_fuzzy_mapping[int(binary_address, 16)]
    return up_address_mapped_list + down_address_mapped_list


def get_binary_call_site_mapped_source_call_site(binary2source_line_mapping, binary_call_site,
                                                 included_source_call_sites_file_line,
                                                 included_source_call_sites,
                                                 binary_function_to_source_function_dict_per_binary,
                                                 name_to_address,
                                                 binary2source_up_fuzzy_mapping, binary2source_down_fuzzy_mapping):
    binary_caller_function_name, binary_callee_function_name, key, call_site_address = binary_call_site
    binary_caller_address_function = name_to_address[binary_caller_function_name]
    binary_callee_address_function = name_to_address[binary_callee_function_name]
    binary_call_site_mapped_source_call_sites = []
    if binary_caller_address_function not in binary_function_to_source_function_dict_per_binary or \
            binary_callee_address_function not in binary_function_to_source_function_dict_per_binary:
        return []
    else:
        binary_address = str(hex(call_site_address))
        try:
            mapped_source_line_list = binary2source_line_mapping[binary_address]
        except:
            # nearby_address_list = seek_for_nearby_address(binary_address, binary2source_line_mapping)
            # mapped_source_line_list = []
            # for nearby_address in nearby_address_list:
            #     mapped_source_line_list += binary2source_line_mapping[str(hex(nearby_address))]
            mapped_source_line_list = get_nearby_address_mapped_list(binary_address, binary2source_down_fuzzy_mapping,
                                                                     binary2source_up_fuzzy_mapping)
        for mapped_source_line in mapped_source_line_list:
            file_name, line_number, function_name, function_range, binary_function = mapped_source_line
            file_name = file_name.replace("/data1/jiaang2022/tencent_works/dataset_I/src/", "")
            line_number = int(line_number)
            if (file_name, line_number) in included_source_call_sites_file_line:
                call_site_index = included_source_call_sites_file_line.index((file_name, line_number))
                # call_site_info = included_source_call_sites[call_site_index]
                fetched_callee_name = included_source_call_sites[call_site_index][1].split("+")[-1]
                if fetched_callee_name != binary_callee_function_name:
                    if not re.match(fetched_callee_name + "_\d", binary_callee_function_name):
                        continue
                if included_source_call_sites[call_site_index] not in binary_call_site_mapped_source_call_sites:
                    binary_call_site_mapped_source_call_sites.append(included_source_call_sites[call_site_index])
    if binary_call_site_mapped_source_call_sites == []:
        # if binary_address in binary2source_line_mapping:
        #     print("this is missing from source analysis")
        # else:
        #     print("cannot find mapped source call site")
        return []
    else:
        if len(binary_call_site_mapped_source_call_sites) > 1:
            # print("binary call sites maps to more than one call sites")
            reduced_call_sites = []
            for call_site in binary_call_site_mapped_source_call_sites:
                callee_name = call_site[1].split("+")[-1]
                if callee_name == binary_callee_function_name:
                    reduced_call_sites.append(call_site)
            if len(reduced_call_sites) > 1:
                # print("cannot identify which call site it maps!!!")
                if binary_address in binary2source_line_mapping:
                    # print("a binary call site maps more than one source call sites!!!")
                    pass
            return reduced_call_sites
        else:
            return binary_call_site_mapped_source_call_sites


def extract_call_site_line_info(included_source_call_sites):
    included_source_call_sites_file_line = []
    for call_site in included_source_call_sites:
        caller, callee, key, call_site_dict = call_site
        call_site_file = call_site_dict["file"]
        call_site_line = call_site_dict["line_number"]
        included_source_call_sites_file_line.append((call_site_file, call_site_line))
    return included_source_call_sites_file_line


def get_unmapped_call_sites(included_source_call_sites, all_binary_mapped_call_sites):
    unmapped_call_sites = []
    for call_site in included_source_call_sites:
        if call_site not in all_binary_mapped_call_sites:
            unmapped_call_sites.append(call_site)
    return unmapped_call_sites


def get_fuzzy_mappping(binary2source_line_mapping):
    binary2source_up_fuzzy_mapping = {}
    binary2source_down_fuzzy_mapping = {}
    address_list = list(binary2source_line_mapping.keys())
    for index, address in enumerate(address_list):
        if index == 0:
            binary2source_down_fuzzy_mapping[int(address, 16)] = binary2source_line_mapping[address]
        elif index == len(address_list) - 1:
            binary2source_up_fuzzy_mapping[int(address, 16)] = binary2source_line_mapping[address]
        else:
            for address_inter in range(int(address_list[index], 16), int(address_list[index + 1], 16)):
                binary2source_up_fuzzy_mapping[address_inter] = binary2source_line_mapping[address]
            for address_inter in range(int(address_list[index - 1], 16), int(address_list[index], 16)):
                binary2source_down_fuzzy_mapping[address_inter] = binary2source_line_mapping[address]

    return binary2source_up_fuzzy_mapping, binary2source_down_fuzzy_mapping


def get_mapped_source_call_sites(source_project_fcg, binary_fcg, binary_function_to_source_function_dict_per_binary,
                                 binary2source_line_mapping, included_source_call_sites,
                                 binary_address_name_to_function_name_mapping):
    # source call sites: {"file": caller_function_file, "function": caller_function_name,
    #                     "line_number": call_function_dict["line_number"]}
    # binary call sites: address
    binary2source_line_mapping = convert_list_mapping_to_dict_mapping(binary2source_line_mapping)
    binary2source_up_fuzzy_mapping, binary2source_down_fuzzy_mapping = get_fuzzy_mappping(binary2source_line_mapping)
    mapped_call_sites = []
    binary_call_sites = get_all_call_sites(binary_fcg)
    name_to_address = dict(zip(binary_address_name_to_function_name_mapping.values(),
                               binary_address_name_to_function_name_mapping.keys()))
    included_source_call_sites_file_line = extract_call_site_line_info(included_source_call_sites)
    all_binary_mapped_call_sites = []
    for binary_call_site in binary_call_sites:
        binary_call_site_mapped_source_call_site = \
            get_binary_call_site_mapped_source_call_site(binary2source_line_mapping, binary_call_site,
                                                         included_source_call_sites_file_line,
                                                         included_source_call_sites,
                                                         binary_function_to_source_function_dict_per_binary,
                                                         name_to_address,
                                                         binary2source_up_fuzzy_mapping,
                                                         binary2source_down_fuzzy_mapping)
        all_binary_mapped_call_sites += binary_call_site_mapped_source_call_site
    unmapped_call_sites = get_unmapped_call_sites(included_source_call_sites, all_binary_mapped_call_sites)
    return all_binary_mapped_call_sites, unmapped_call_sites


def get_mapped_call_sites(all_call_sites, all_source_functions):
    included_call_sites = []
    for call_sites in all_call_sites:
        caller, callee, key, call_site = call_sites
        if caller in all_source_functions and callee in all_source_functions:
            included_call_sites.append(call_sites)
    return included_call_sites


def identify_inlined_call_sites_through_call_graph_comparison(source_project_fcg, binary_fcg,
                                                              binary_function_to_source_function_dict_per_binary,
                                                              binary_address_name_to_function_name_mapping,
                                                              binary2source_line_mapping):
    inlined_source_function_relations, all_source_functions = extract_inlined_function_relations(
        binary_function_to_source_function_dict_per_binary)
    all_source_call_sites = get_all_call_sites(source_project_fcg)
    included_source_call_sites = get_mapped_call_sites(all_source_call_sites, all_source_functions)
    mapped_call_sites, unmapped_call_sites = get_mapped_source_call_sites(source_project_fcg,
                                                                          binary_fcg,
                                                                          binary_function_to_source_function_dict_per_binary,
                                                                          binary2source_line_mapping,
                                                                          included_source_call_sites,
                                                                          binary_address_name_to_function_name_mapping)

    return mapped_call_sites, unmapped_call_sites


def infer_call_sites_from_address_intersection(call_site_address_intersection_per_binary,
                                               binary_address_name_to_function_name_mapping):
    possible_call_sites = []
    for binary_address_function in call_site_address_intersection_per_binary:
        # binary_function_name = binary_address_name_to_function_name_mapping[binary_address_function]
        address_intersections = call_site_address_intersection_per_binary[binary_address_function]
        for address_intersection in address_intersections:
            address_1, address_2 = address_intersection
            address_1[0] = address_1[0].replace("/data1/jiaang2022/tencent_works/dataset_I/src/", "")
            address_1[2] = int(address_1[2])
            address_2[0] = address_2[0].replace("/data1/jiaang2022/tencent_works/dataset_I/src/", "")
            address_2[2] = int(address_2[2])
            if address_1 not in possible_call_sites:
                possible_call_sites.append(address_1)
            if address_2 not in possible_call_sites:
                possible_call_sites.append(address_2)
    return possible_call_sites


def calculate_distance_between_intersection_and_call_sites(possible_call_sites, call_site_info_tuple):
    distance = []
    for call_site in possible_call_sites:
        if call_site[0] == call_site_info_tuple[0] and call_site[1] == call_site_info_tuple[1]:
            distance.append(abs(call_site[2] - call_site_info_tuple[2]))
    if not distance:
        return 100
    else:
        return min(distance)


def get_inlined_function_pairs(binary_function_to_source_function_dict_per_binary):
    possible_inlined_call_pairs = []
    for binary_function in binary_function_to_source_function_dict_per_binary:
        if binary_function_to_source_function_dict_per_binary[binary_function]["is_inlined"]:
            OSF = binary_function_to_source_function_dict_per_binary[binary_function]["OSF"]
            ISFs = binary_function_to_source_function_dict_per_binary[binary_function]["ISFs"]
            OSF = OSF.replace('/data1/jiaang2022/tencent_works/dataset_I/src/', "")
            OSF = "+".join(OSF.split("+")[:-1])
            for ISF in ISFs:
                ISF = ISF.replace('/data1/jiaang2022/tencent_works/dataset_I/src/', "")
                ISF = "+".join(ISF.split("+")[:-1])
                if [OSF, ISF] not in possible_inlined_call_pairs:
                    possible_inlined_call_pairs.append([OSF, ISF])
                for ISF_2 in ISFs:
                    ISF_2 = ISF_2.replace('/data1/jiaang2022/tencent_works/dataset_I/src/', "")
                    ISF_2 = "+".join(ISF_2.split("+")[:-1])
                    if [ISF, ISF_2] not in possible_inlined_call_pairs:
                        possible_inlined_call_pairs.append([ISF, ISF_2])
    return possible_inlined_call_pairs


def infer_inlined_call_sites(unmapped_call_sites, possible_call_sites,
                             binary_function_to_source_function_dict_per_binary):
    inlined_call_sites = []
    possible_inlined_call_pairs = get_inlined_function_pairs(binary_function_to_source_function_dict_per_binary)
    for unmapped_call_site in unmapped_call_sites:
        caller_function, callee_function, key, call_site_info = unmapped_call_site
        call_site_info_tuple = [call_site_info["file"], call_site_info["function"], call_site_info["line_number"]]
        if call_site_info_tuple in possible_call_sites:
            if [caller_function, callee_function] not in possible_inlined_call_pairs:
                continue
            inlined_call_sites.append(call_site_info_tuple)
        else:
            # call_site_distance = calculate_distance_between_intersection_and_call_sites(possible_call_sites, call_site_info_tuple)
            # if call_site_distance <= 4:
            #     inlined_call_sites.append(call_site_info_tuple)
            continue
    return inlined_call_sites


def identify_inlined_call_sites_through_call_site_inlining_analysis(unmapped_call_sites,
                                                                    call_site_address_intersection_per_binary,
                                                                    binary_address_name_to_function_name_mapping,
                                                                    binary_function_to_source_function_dict_per_binary):
    inlined_call_sites = []
    if call_site_address_intersection_per_binary != {}:
        possible_call_sites = \
            infer_call_sites_from_address_intersection(call_site_address_intersection_per_binary,
                                                       binary_address_name_to_function_name_mapping)
        inlined_call_sites = infer_inlined_call_sites(unmapped_call_sites, possible_call_sites,
                                                      binary_function_to_source_function_dict_per_binary)
    return inlined_call_sites


def remove_redundant_call_sites_and_reformat(record_all_call_sites):
    for compiler in record_all_call_sites:
        for opt in record_all_call_sites[compiler]:
            # for call_site_kind in record_all_call_sites[compiler][opt]:
            #     temp_list = []
            #     for call_site in record_all_call_sites[compiler][opt][call_site_kind]:
            #         if call_site not in temp_list:
            #             temp_list.append(call_site)
            #     record_all_call_sites[compiler][opt][call_site_kind] = temp_list
            for call_site_kind in record_all_call_sites[compiler][opt]:
                record_all_call_sites[compiler][opt][call_site_kind] = \
                    list(set(record_all_call_sites[compiler][opt][call_site_kind]))
    return record_all_call_sites


def reformat_call_sites(mapped_call_sites):
    reformat_mapped_call_sites = []
    for call_site in mapped_call_sites:
        caller, callee, key, call_site_info = call_site
        call_site_file = call_site_info["file"]
        call_site_function = call_site_info["function"]
        call_site_line = call_site_info["line_number"]
        call_site_column = call_site_info["column"]
        call_site_list = [call_site_file, call_site_function, str(call_site_line), str(call_site_column), callee]
        call_site_key = "+".join(call_site_list)
        if call_site_key not in reformat_mapped_call_sites:
            reformat_mapped_call_sites.append(call_site_key)
    return reformat_mapped_call_sites


def get_pairs_to_call_site(all_possible_mapping_call_sites):
    call_pairs_to_call_sites = {}
    for call_sites_infos in all_possible_mapping_call_sites:
        caller, callee, key, call_site_info = call_sites_infos
        if (caller, callee) not in call_pairs_to_call_sites:
            call_pairs_to_call_sites[(caller, callee)] = []
        if call_sites_infos not in call_pairs_to_call_sites[(caller, callee)]:
            call_pairs_to_call_sites[(caller, callee)].append(call_sites_infos)
    return call_pairs_to_call_sites


def traverse_all_inlined_function_pairs(all_possible_mapping_call_sites, inlined_source_function_relations):
    inlined_call_site_per_binary = []
    call_pairs_to_call_sites = get_pairs_to_call_site(all_possible_mapping_call_sites)
    for inlined_source_relation in inlined_source_function_relations:
        OSF = inlined_source_relation["OSF"]
        ISFs = inlined_source_relation["ISFs"]
        SFs = [OSF] + ISFs
        for SF1 in SFs:
            for SF2 in ISFs:
                if SF1 == SF2:
                    continue
                if (SF1, SF2) in call_pairs_to_call_sites:
                    call_sites = call_pairs_to_call_sites[(SF1, SF2)]
                    if len(call_sites) == 1:
                        inlined_call_site_per_binary += call_sites
                    else:
                        inlined_call_site_per_binary += call_sites
                        # print("caller and callee have more than call relations")
    return inlined_call_site_per_binary


def get_difference(all_possible_mapping_call_sites, inlined_call_site_per_binary):
    normal_call_site_per_binary = []
    for call_site in all_possible_mapping_call_sites:
        if call_site not in inlined_call_site_per_binary:
            normal_call_site_per_binary.append(call_site)
    return normal_call_site_per_binary


def get_binary_mapped_source_call_sites(binary_call_sites, binary2source_line_mapping, binary_name_mapping):
    all_binary_mapped_source_call_sites = []
    binary2source_line_mapping = convert_list_mapping_to_dict_mapping(binary2source_line_mapping)
    for binary_call_site in binary_call_sites:
        caller, callee, key, address = binary_call_site
        if address in binary2source_line_mapping:
            binary_mapped_lines = binary2source_line_mapping[address]
            for line_info_list in binary_mapped_lines:
                source_file, line, function_name, function_range, binary_function_name = line_info_list
                source_file = source_file.replace("/data1/jiaang2022/tencent_works/dataset_I/src/", "")
                line = int(line)
                if (source_file, line) not in all_binary_mapped_source_call_sites:
                    all_binary_mapped_source_call_sites.append((source_file, line))
    return all_binary_mapped_source_call_sites


def remove_binary_mapped_call_sites(inlined_call_site_per_binary, binary_mapped_source_call_sites):
    new_inlined_call_site_per_binary = []
    for inlined_call_site in inlined_call_site_per_binary:
        inlined_call_site_info = inlined_call_site[-1]
        file_name, line = inlined_call_site_info["file"], inlined_call_site_info["line_number"]
        if (file_name, line) not in binary_mapped_source_call_sites:
            new_inlined_call_site_per_binary.append(inlined_call_site)
    return new_inlined_call_site_per_binary


def classify_call_site_by_function_mapping(source_project_fcg, binary_fcg, binary_name_mapping,
                                           binary_function_to_source_function_dict_per_binary,
                                           binary2source_line_mapping):
    inlined_source_function_relations, all_source_functions = \
        extract_inlined_function_relations(binary_function_to_source_function_dict_per_binary)

    all_source_call_sites = get_all_call_sites(source_project_fcg)
    all_possible_mapping_call_sites = get_mapped_call_sites(all_source_call_sites, all_source_functions)
    if not inlined_source_function_relations:
        normal_call_site_per_binary = all_possible_mapping_call_sites
        inlined_call_site_per_binary = []
        reduced_inlined_call_site_per_binary = []
    else:
        inlined_call_site_per_binary = \
            traverse_all_inlined_function_pairs(all_possible_mapping_call_sites, inlined_source_function_relations)
        binary_call_sites = get_all_call_sites(binary_fcg)
        binary_mapped_source_call_sites = \
            get_binary_mapped_source_call_sites(binary_call_sites, binary2source_line_mapping, binary_name_mapping)
        reduced_inlined_call_site_per_binary = \
            remove_binary_mapped_call_sites(inlined_call_site_per_binary, binary_mapped_source_call_sites)
        normal_call_site_per_binary = get_difference(all_possible_mapping_call_sites,
                                                     reduced_inlined_call_site_per_binary)
    # print("debug")
    return normal_call_site_per_binary, reduced_inlined_call_site_per_binary


def combine_two_list(normal_call_site_per_binary, all_call_site):
    for item in normal_call_site_per_binary:
        if item not in all_call_site:
            all_call_site.append(item)
    return all_call_site


def read_all_composition_file(function_composition_folder):
    function_composition_all = {}
    for file_name in os.listdir(function_composition_folder):
        file_path = os.path.join(function_composition_folder, file_name)
        file_content = read_json(file_path)
        function_composition_all = {**function_composition_all, **file_content}
    return function_composition_all


def main():
    function_composition_folder = r"D:\binary2source_matching_under_function_inlining\code\binary2source_matching_under_inlining" \
                                  r"\1.inlining_ground_truth_labelining\function_composition"
    function_composition_all = read_all_composition_file(function_composition_folder)

    source_fcg_pickle_file = r"D:\binary2source_matching_under_function_inlining\code\binary2source_matching_under_inlining" \
                             r"\0.preprocessing-source_and_binary_FCG_construction\Source_FCG_extraction\source_fcgs.pkl"
    source_fcgs = read_pickle(source_fcg_pickle_file)

    binary_fcg_pickle_folder = r"D:\binary2source_matching_under_function_inlining\code\binary2source_matching_under_inlining\test_dataset\gnu_debug"
    # binary_fcgs_pickle_file = "binary_fcgs.pkl"
    # binary_fcgs = read_pickle(binary_fcg_pickle_file)

    # binary_address_name_to_function_name_mapping_file = "binary_name_mapping.json"
    # binary_address_name_to_function_name_mapping = read_json(binary_address_name_to_function_name_mapping_file)

    binary2source_mapping_folder = r"D:\binary2source_matching_under_function_inlining\code\binary2source_matching_under_inlining\test_dataset\mapping_results"

    record_all_call_sites = {}
    bar = tqdm(desc='running_on_projects', total=len(list(function_composition_all.keys())), leave=False)
    for binary_name_elf in function_composition_all:
        compiler, opt, arch, binary_name, binary_project_name = get_split_parts(binary_name_elf)
        project_name = "-".join(binary_project_name.split("-")[:-1])

        if project_name not in source_fcgs:
            if project_name != "gnu-pw-mgr":
                print(project_name)
            continue

        binary2source_line_mapping_file = \
            os.path.join(binary2source_mapping_folder, project_name, binary_name_elf + "_line_mapping.json")
        binary2source_line_mapping = read_json(binary2source_line_mapping_file)

        source_project_fcg = source_fcgs[project_name]
        binary_function_to_source_function_dict_per_binary = function_composition_all[binary_name_elf]

        binary_fcg_pickle_file = os.path.join(binary_fcg_pickle_folder, project_name, binary_name_elf + ".fcg_pkl")
        binary_fcg = read_pickle(binary_fcg_pickle_file)

        binary_name_mapping_file = os.path.join(binary_fcg_pickle_folder, project_name, binary_name_elf + ".mapping")
        binary_name_mapping = read_json(binary_name_mapping_file)
        binary_name_mapping = dict(zip(binary_name_mapping.values(), binary_name_mapping.keys()))

        normal_call_site_per_binary, inlined_call_site_per_binary = \
            classify_call_site_by_function_mapping(source_project_fcg, binary_fcg, binary_name_mapping,
                                                   binary_function_to_source_function_dict_per_binary,
                                                   binary2source_line_mapping)
        normal_call_site_per_binary = reformat_call_sites(normal_call_site_per_binary)
        inlined_call_site_per_binary = reformat_call_sites(inlined_call_site_per_binary)
        if compiler not in record_all_call_sites:
            record_all_call_sites[compiler] = {}
        if opt not in record_all_call_sites[compiler]:
            record_all_call_sites[compiler][opt] = {"normal_call_sites": [], "inlined_call_sites": []}
        record_all_call_sites[compiler][opt]["normal_call_sites"] += normal_call_site_per_binary
        record_all_call_sites[compiler][opt]["inlined_call_sites"] += inlined_call_site_per_binary
        # record_all_call_sites[compiler][opt]["normal_call_sites"] += \
        #     combine_two_list(normal_call_site_per_binary, record_all_call_sites[compiler][opt]["normal_call_sites"])
        # record_all_call_sites[compiler][opt]["inlined_call_sites"] += \
        #     combine_two_list(inlined_call_site_per_binary, record_all_call_sites[compiler][opt]["normal_call_sites"])
        bar.update()
    bar.close()

    record_all_call_sites = remove_redundant_call_sites_and_reformat(record_all_call_sites)
    record_all_call_pairs_file = "normal_and_inlined_call_sites_by_infer.json"
    write_json(record_all_call_pairs_file, record_all_call_sites)


if __name__ == '__main__':
    main()

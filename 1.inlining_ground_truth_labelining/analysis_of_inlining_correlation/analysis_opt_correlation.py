import csv
import json
import os

import matplotlib.pyplot as plt


def read_json(file_path):
    with open(file_path, "r") as f:
        file_content = json.load(f)
        return file_content


def write_json(file_path, obj):
    with open(file_path, "w") as f:
        json_str = json.dumps(obj, indent=2)
        f.write(json_str)


def main():
    call_sites_labels_file = "call_site_labels.json"
    call_site_labels = read_json(call_sites_labels_file)
    opt_correlation = {}
    for sf in call_site_labels:
        for compiler in compiler_list:
            if compiler not in opt_correlation:
                opt_correlation[compiler] = {"O0": [0] * 4, "O1": [0] * 4, "O2": [0] * 4, "O3": [0] * 4}
            if compiler in call_site_labels[sf]:
                for opt1 in opt_list:
                    for opt2 in opt_list:
                        if opt1 in call_site_labels[sf][compiler] and opt2 in call_site_labels[sf][compiler]:
                            if opt1 == opt2 and call_site_labels[sf][compiler][opt1] == "inlined_call_sites":
                                opt_correlation[compiler][opt1][opt_list.index(opt1)] += 1
                            if opt_list.index(opt1) < opt_list.index(opt2):
                                if call_site_labels[sf][compiler][opt1] == "inlined_call_sites" and \
                                        call_site_labels[sf][compiler][opt2] == "inlined_call_sites":
                                    opt_correlation[compiler][opt1][opt_list.index(opt2)] += 1

    for compiler in opt_correlation:
        for index, opt in enumerate(opt_list):
            if index >= 1:
                for value_index in range(len(opt_correlation[compiler][opt])):
                    if opt_correlation[compiler][opt][value_index] != 0:
                        opt_correlation[compiler][opt][value_index] -= opt_correlation[compiler][opt_list[index-1]][value_index]

    opt_correlation_file = "opt_correlation_file.json"
    write_json(opt_correlation_file, opt_correlation)


if __name__ == '__main__':
    clang_compiler_list = ["clang-4.0", "clang-5.0", "clang-6.0", "clang-7.0"]
    gcc_compiler_list = ["gcc-4.9.4", "gcc-5.5.0", "gcc-6.4.0", "gcc-7.3.0"]
    compiler_list = gcc_compiler_list + clang_compiler_list
    opt_list = ["O0", "O1", "O2", "O3"]
    main()

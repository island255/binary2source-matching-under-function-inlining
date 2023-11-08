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
    compiler_correlation = {}
    for sf in call_site_labels:
        for compiler1 in compiler_list:
            if compiler1 not in compiler_correlation:
                compiler_correlation[compiler1] = {}
            for compiler2 in compiler_list:
                if compiler2 not in compiler_correlation[compiler1]:
                    compiler_correlation[compiler1][compiler2] = {"same": 0, "different": 0}

                if compiler1 in call_site_labels[sf] and compiler2 in call_site_labels[sf]:
                    for opt in opt_list:
                        if opt in call_site_labels[sf][compiler1] and opt in call_site_labels[sf][compiler2]:
                            if call_site_labels[sf][compiler1][opt] == "normal_call_sites" and \
                                    call_site_labels[sf][compiler2][opt] == "normal_call_sites":
                                continue
                            if call_site_labels[sf][compiler1][opt] == \
                                    call_site_labels[sf][compiler2][opt]:
                                compiler_correlation[compiler1][compiler2]["same"] += 1
                            else:
                                compiler_correlation[compiler1][compiler2]["different"] += 1

    for compiler1 in compiler_correlation:
        for compiler2 in compiler_correlation[compiler1]:
            compiler_correlation[compiler1][compiler2] = \
                compiler_correlation[compiler1][compiler2]["same"] / \
                (compiler_correlation[compiler1][compiler2]["same"] + compiler_correlation[compiler1][compiler2]["different"])

    opt_correlation_file = "compiler_correlation_file.json"
    write_json(opt_correlation_file, compiler_correlation)


if __name__ == '__main__':
    clang_compiler_list = ["clang-4.0", "clang-5.0", "clang-6.0", "clang-7.0"]
    gcc_compiler_list = ["gcc-4.9.4", "gcc-5.5.0", "gcc-6.4.0", "gcc-7.3.0"]
    compiler_list = gcc_compiler_list + clang_compiler_list
    opt_list = ["O0", "O1", "O2", "O3"]
    main()

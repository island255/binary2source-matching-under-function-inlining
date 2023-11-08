import json


def read_json(file_path):
    with open(file_path, "r") as f:
        file_content = json.load(f)
        return file_content


def calculate_avg_sim(compiler_correlation, clang_compiler_list):
    avg_statistics = 0
    for compiler1 in clang_compiler_list:
        for compiler2 in clang_compiler_list:
            if compiler1 == compiler2:
                continue
            avg_statistics += compiler_correlation[compiler1][compiler2]
    avg_statistics = avg_statistics / 12
    return avg_statistics


def calculate_cross_compiler_sim(compiler_correlation, clang_compiler_list, gcc_compiler_list):
    cross_compiler_sim = 0
    for clang_compiler in clang_compiler_list:
        for gcc_compiler in gcc_compiler_list:
            cross_compiler_sim += compiler_correlation[clang_compiler][gcc_compiler]
    cross_compiler_sim = cross_compiler_sim / 16
    return cross_compiler_sim


def main():
    compiler_correlation_file = "compiler_correlation_file.json"
    compiler_correlation = read_json(compiler_correlation_file)
    clang_compiler_list = ["clang-4.0", "clang-5.0", "clang-6.0", "clang-7.0"]
    gcc_compiler_list = ["gcc-4.9.4", "gcc-5.5.0", "gcc-6.4.0", "gcc-7.3.0"]
    clang_avg_statistics = calculate_avg_sim(compiler_correlation, clang_compiler_list)
    print(clang_avg_statistics)
    gcc_avg_statistics = calculate_avg_sim(compiler_correlation, gcc_compiler_list)
    print(gcc_avg_statistics)
    cross_compiler_sim = calculate_cross_compiler_sim(compiler_correlation, clang_compiler_list, gcc_compiler_list)
    print(cross_compiler_sim)


if __name__ == '__main__':
    main()
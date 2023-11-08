import os
import json

from matplotlib import pyplot as plt, ticker


def read_json(file_path):
    with open(file_path, "r") as f:
        file_content = json.load(f)
        return file_content


def add_list(a, b):
    return [a[i] + b[i] for i in range(min(len(a), len(b)))]


def draw_figure(opt0, opt1, opt2, opt3):
    fig = plt.figure(figsize=(18, 8))
    ax = fig.add_subplot(111)
    # color = ['b', 'r', 'g', 'k']
    # line_format = ['*-', '>-', 's-']
    ax.set_xticks(range(32))
    index = list(range(32))
    ax.set_xticklabels(
        ['O0', 'O1\n      gcc-4.9.4', 'O2', 'O3', 'O0', 'O1\n     gcc-5.5.0', 'O2', 'O3', 'O0', 'O1\n     gcc-6.4.0',
         'O2', 'O3',
         'O0', 'O1\n     gcc-7.3.0', 'O2', 'O3', 'O0', 'O1\n     clang-4.0',
         'O2', 'O3',
         'O0', 'O1\n     clang-5.0', 'O2', 'O3', 'O0', 'O1\n     clang-6.0', 'O2', 'O3', 'O0', 'O1\n     clang-7.0',
         'O2', 'O3'],
        ha='center', fontsize=16)
    plt.yticks(fontsize=16)
    # ax.yaxis.set_major_formatter(ticker.PercentFormatter(xmax=1, decimals=1))

    node_size = 10
    line_size = 3

    line1 = ax.bar(index, opt0, width=0.5, label="O0", color="r")
    line2 = ax.bar(index, opt1, width=0.5, bottom=opt0, label="O1", color="b")
    line3 = ax.bar(index, opt2, width=0.5, bottom=add_list(opt0, opt1), label="O2", color="y")
    line4 = ax.bar(index, opt3, width=0.5, bottom=add_list(add_list(opt0, opt1), opt2), label="O3", color="g")


    plt.legend(fontsize=14)

    ax.set_ylabel("Number of call sites", fontsize=16)
    plt.xticks(fontsize=16)
    plt.yticks(fontsize=16)
    plt.subplots_adjust(bottom=0.18)
    plt.savefig("opt_correlation.png")
    plt.show()


def extract_opt_in(opt_correlation):
    opt0 = []
    opt1 = []
    opt2 = []
    opt3 = []
    for compiler in compiler_list:
        opt0 += opt_correlation[compiler]["O0"]
        opt1 += opt_correlation[compiler]["O1"]
        opt2 += opt_correlation[compiler]["O2"]
        opt3 += opt_correlation[compiler]["O3"]
    return opt0, opt1, opt2, opt3


def main():
    opt_correlation_file = "opt_correlation_file.json"
    opt_correlation = read_json(opt_correlation_file)
    opt0, opt1, opt2, opt3 = extract_opt_in(opt_correlation)
    draw_figure(opt0, opt1, opt2, opt3)


if __name__ == '__main__':
    clang_compiler_list = ["clang-4.0", "clang-5.0", "clang-6.0", "clang-7.0"]
    gcc_compiler_list = ["gcc-4.9.4", "gcc-5.5.0", "gcc-6.4.0", "gcc-7.3.0"]
    compiler_list = gcc_compiler_list + clang_compiler_list
    opt_list = ["O0", "O1", "O2", "O3"]
    main()

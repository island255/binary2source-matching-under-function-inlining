import json
import random
from matplotlib import pyplot as plt
from matplotlib import cm
from matplotlib import axes
from matplotlib.font_manager import FontProperties


def draw(sim_matrix):
    # 定义热图的横纵坐标
    xLabel = compiler_list
    yLabel = compiler_list[::-1]

    # 作图阶段
    fig = plt.figure()
    # 定义画布为1*1个划分，并在第1个位置上进行作图
    ax = fig.add_subplot(111)
    # 定义横纵坐标的刻度
    ax.set_yticks(range(len(yLabel)))
    ax.set_yticklabels(yLabel)
    ax.set_xticks(range(len(xLabel)))
    ax.set_xticklabels(xLabel, rotation=45)
    # 作图并选择热图的颜色填充风格，这里选择hot
    im = ax.imshow(sim_matrix, cmap=plt.cm.hot_r)
    # 增加右侧的颜色刻度条
    plt.colorbar(im)
    # 增加标题
    # plt.title("This is a title")
    # show
    plt.subplots_adjust(bottom=0.18)
    plt.savefig("compiler_correlation.png")
    plt.show()


def read_json(file_path):
    with open(file_path, "r") as f:
        file_content = json.load(f)
        return file_content


def main():
    compiler_correlation_file = "compiler_correlation_file.json"
    compiler_correlation = read_json(compiler_correlation_file)
    sim_matrix = []
    for compiler1 in compiler_list[::-1]:
        temp = []
        for compiler2 in compiler_list:
            temp.append(compiler_correlation[compiler1][compiler2])
        sim_matrix.append(temp)

    draw(sim_matrix)


if __name__ == '__main__':
    clang_compiler_list = ["clang-4.0", "clang-5.0", "clang-6.0", "clang-7.0"]
    gcc_compiler_list = ["gcc-4.9.4", "gcc-5.5.0", "gcc-6.4.0", "gcc-7.3.0"]
    compiler_list = gcc_compiler_list + clang_compiler_list
    opt_list = ["O0", "O1", "O2", "O3"]
    main()

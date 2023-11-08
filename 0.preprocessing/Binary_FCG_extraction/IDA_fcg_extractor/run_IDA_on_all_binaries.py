import os
from run_IDA import batch


def read_binary_list(projectdir):
    """
    get all binary file's path
    """
    binary_paths = []
    for root, dirs, files in os.walk(projectdir):
        for file_name in files:
            if file_name.endswith(".elf"):
                file_path = os.path.join(root, file_name)
                result_file_path = file_path + ".fcg"
                # if os.path.exists(result_file_path):
                #     continue
                binary_paths.append(file_path)
    return binary_paths


def main():
    binary_project_folder = "D:\\tencent_works\\classifier_for_inlinining_determintation\\" \
                            "designing_classifier_for_inlining\\test_dataset\\gnu_debug"
    project_name_list = os.listdir(binary_project_folder)
    binary_paths_list = []
    for project_name in project_name_list:
        binary_project_dir = os.path.join(binary_project_folder, project_name)
        binary_paths = read_binary_list(binary_project_dir)
        binary_paths_list += binary_paths
    cpu_num = 2
    binary_paths_list_file = "binary_paths_list.txt"
    print(len(binary_paths_list))
    with open(binary_paths_list_file, "w") as f:
        f.write("\n".join(binary_paths_list))
    batch(binary_paths_list_file, cpu_num)


if __name__ == '__main__':
    main()

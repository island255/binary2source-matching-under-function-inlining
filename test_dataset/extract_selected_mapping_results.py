import os
import shutil


def read_binary_list(projectdir):
    """
    get all binary file's path
    """
    binary_paths = []
    for root, dirs, files in os.walk(projectdir):
        for file_name in files:
            if "gcc-8.2.0_x86_64" in file_name or "clang-7.0_x86_64" in file_name:
                file_path = os.path.join(root, file_name)
                binary_paths.append(file_path)
    return binary_paths


def copy_files(binary_paths_list, dest_dir):
    for binary_path in binary_paths_list:
        print("processing {} of total {}".format(binary_paths_list.index(binary_path), len(binary_paths_list)))
        binary_name = os.path.basename(binary_path)
        project_name = os.path.basename(os.path.dirname(binary_path))
        dest_folder = os.path.join(dest_dir, project_name)
        if not os.path.exists(dest_folder):
            os.makedirs(dest_folder)
        dest_path = os.path.join(dest_dir, project_name, binary_name)
        shutil.copyfile(binary_path, dest_path)


def main():
    binary_project_folder = "D:\\tencent_works\\dataset_I\\mapping_results_for_gnu_debug"
    dest_dir = "D:\\tencent_works\\classifier_for_inlinining_determintation\\designing_classifier_for_inlining" \
               "\\test_dataset\\mapping_results"
    project_name_list = os.listdir(binary_project_folder)
    binary_paths_list = []
    for project_name in project_name_list:
        binary_project_dir = os.path.join(binary_project_folder, project_name)
        binary_paths = read_binary_list(binary_project_dir)
        binary_paths_list += binary_paths
    copy_files(binary_paths_list, dest_dir)


if __name__ == '__main__':
    main()

import os

from use_tree_sitter_get_function_ranges import get_functions_ranges


def main():
    project_path = "D:\\tencent_works\\dataset_I\\src"
    tree_sitter_lib_path = "C_Cpp.so"
    results_dir = "D:\\tencent_works\\function_inlining_prediction\\designing_classifier_for_inlining\\" \
                  "2.feature_extraction\\features_per_function\\function_contents"
    project_name_list = os.listdir(project_path)
    for project_name in project_name_list:
        print("processing project {} , {} of total {}".format(project_name, project_name_list.index(project_name),
                                                              len(project_name_list)))
        project_dir = os.path.join(project_path, project_name)
        for sub_name in os.listdir(project_dir):
            sub_path = os.path.join(project_dir, sub_name)
            if os.path.isdir(sub_path):
                get_functions_ranges(sub_path, results_dir, tree_sitter_lib_path)


if __name__ == '__main__':
    main()
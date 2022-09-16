import json
import subprocess
import os


def use_understand_extract_entities(understand_tool, source_dir, understand_python, understand_extract_script,
                                    understand_source_entities_file):
    source_project_und = os.path.join(source_dir, "project.und")

    cmd_understand_1 = "{} create -languages C++ {}".format(understand_tool, source_project_und)
    cmd_understand_2 = "{} add {} {}".format(understand_tool, source_dir, source_project_und)
    cmd_understand_3 = "{} analyze {}".format(understand_tool, source_project_und)
    cmd = " && ".join([cmd_understand_1, cmd_understand_2, cmd_understand_3])
    cmd = cmd_understand_3
    print(cmd)
    ex = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
    out, err = ex.communicate()
    status = ex.wait()
    # if status

    cmd_extract_understand = "{} {} --db_path {} --result_path {}".format(understand_python, understand_extract_script,
                                                                          source_project_und,
                                                                          understand_source_entities_file)
    ex = subprocess.Popen(cmd_extract_understand, shell=True, stdout=subprocess.PIPE)
    out, err = ex.communicate()
    status = ex.wait()


def run_understand_to_extract_entities(understand_tool, source_dir, understand_python,
                                       understand_extract_script, understand_source_entities_file):
    use_understand_extract_entities(understand_tool, source_dir, understand_python,
                                    understand_extract_script, understand_source_entities_file)


def get_all_source_porject_paths(dataset_base_dir):
    source_project_dir_list = []
    for project_name in os.listdir(dataset_base_dir):
        project_dir = os.path.join(dataset_base_dir, project_name)
        for sub_dir in os.listdir(project_dir):
            folder_path = os.path.join(project_dir, sub_dir)
            if os.path.isdir(folder_path):
                source_project_dir_list.append(folder_path)
    return source_project_dir_list


def run_script_for_all(dataset_base_dir, understand_tool, understand_python, understand_extract_script, entities_dir):
    source_project_dir_list = get_all_source_porject_paths(dataset_base_dir)
    if os.path.exists(entities_dir) is False:
        os.makedirs(entities_dir)
    for source_project_dir in source_project_dir_list:
        print("processing source project {} num {} of total {}".format(source_project_dir,
                                                                       str(source_project_dir_list.index(
                                                                           source_project_dir)),
                                                                       str(len(source_project_dir_list))))
        project_name = os.path.basename(os.path.dirname(source_project_dir))
        understand_source_entities_file = os.path.join(entities_dir, project_name + "_fcg.json")
        use_understand_extract_entities(understand_tool, source_project_dir, understand_python,
                                        understand_extract_script, understand_source_entities_file)


def main():
    dataset_base_dir = "D:\\tencent_works\\function_inlining_prediction\\designing_classifier_for_inlining\\src"
    understand_tool = "C:\\SciTools\\bin\\pc-win64\\und.exe"
    understand_python = "C:\\SciTools\\bin\\pc-win64\\upython.exe"
    entities_dir = "D:\\tencent_works\\function_inlining_prediction\\designing_classifier_for_inlining\\FCG_simple"
    understand_extract_script = "D:\\tencent_works\\function_inlining_prediction\\designing_classifier_for_inlining\\" \
                                "0.preprocessing-source_and_binary_FCG_construction\\Source_FCG_extraction" \
                                "\\use_understand_to_extract_fcgs_simple.py "
    run_script_for_all(dataset_base_dir, understand_tool, understand_python, understand_extract_script, entities_dir)


if __name__ == '__main__':
    main()

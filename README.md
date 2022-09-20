# TOSEM-binary2source-matching-under-function-inlining

This is the repository illustrate how we label the inlined call sites, train the classifier for ICS prediction and generate SFSs for binary2source matching.

This repository presents the code of our cross-project evaluation.

This is the architecture of this repository.

| dir | folder | function |
| :----  | :--- | :------- |
| 0.preprocessing-source_and_binary_FCG_construction  |  Binary_FCG_extraction | scripts to extract binary FCGs|
| | Source_FCG_extraction | scripts to extract source FCGs|
| 1.inlining_ground_truth_labelining  |  inlining_ground_truth_labelining_per_call_site | labeling call sites with inline or normal labels |
| 2.feature_extraction | features_per_function | extracted function contents using tree-sitter |
| | function_feature_extraction | scripts to extract function contents |
| | fuzzy_call_site_feature_extraction | scripts to extract call site feature |
| 3.classifier | | multi-label classifiers for ICS prediction |
| 4.apply_classifier_to_test_projects | | using multi-label classifiers to generate SFSs | 
| test_dataset | gnu_debug | the generated binaries | 
| | mapping_results | function-level mapping reuslt obtained using https://github.com/island255/TOSEM2022 |

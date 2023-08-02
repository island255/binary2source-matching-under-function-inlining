# binary2source-matching-under-function-inlining

This is the repository illustrating how we label the inlined call sites, train the classifier for ICS prediction, and generate SFSs for binary2source matching.

This repository presents the code and dataset for our cross-project evaluation.

This is the architecture of this repository.

| dir | folder | function |
| :----  | :--- | :------- |
| 0.preprocessing-source_and_binary_FCG_construction  |  Binary_FCG_extraction | scripts to extract binary FCGs|
| | Source_FCG_extraction | scripts to extract source FCGs|
| 1.inlining_ground_truth_labeling  |  inlining_ground_truth_ labelining_per_call_site | labeling call sites with inline or normal labels |
| 2.feature_extraction | features_per_function | extracted function contents using tree-sitter |
| | function_feature_extraction | scripts to extract function contents |
| | fuzzy_call_site_feature_extraction | scripts to extract call site feature |
| 3.classifier | | multi-label classifiers for ICS prediction |
| 4.apply_classifier_to_test_projects | | using multi-label classifiers to generate SFSs | 
| test_dataset | gnu_debug | the generated binaries | 
| | mapping_results | function-level mapping results obtained using function inlining identification tool in paper "1-to-1 or 1-to-n? Investigating the Effect of Function Inlining on Binary Similarity Analysis" |
| environment.yaml | | packages needed to be installed in Windows|

When running the code in this repository, paths must be set to their real paths.

Folder test_dataset only presents part of the dataset. The full dataset can be downloaded at https://zenodo.org/record/6675280

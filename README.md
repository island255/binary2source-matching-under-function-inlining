# binary2source-matching-under-function-inlining

This is the repository illustrating how we label the inlined call sites, train the classifier for ICS prediction, and generate SFSs for binary2source matching.

This repository presents the code and dataset for our cross-project evaluation.

This is the architecture of this repository.

| dir | folder | function |
| :----  | :--- | :------- |
| 0.preprocessing  |  Binary_FCG_extraction | scripts to extract binary FCGs|
| | Source_FCG_extraction | scripts to extract source FCGs|
| 1.inlining_ground_truth_labeling  |  inlining_ground_truth_ labeling_per_call_site | labeling call sites with inline or normal labels |
| 2.feature_extraction | features_per_function | extracted function contents using tree-sitter |
| | function_feature_extraction | scripts to extract function contents |
| | call_site_feature_extraction | scripts to extract call site feature |
| 3.classifier | | multi-label classifiers for ICS prediction |
| 4.apply_classifier_to_test_projects | | using multi-label classifiers to generate SFSs | 
| test_dataset | binaries_and_FCGs | binaries_and_their_FCGs | 
| | mapping_results | function-level mapping results obtained using function inlining identification tool in paper "1-to-1 or 1-to-n? Investigating the Effect of Function Inlining on Binary Similarity Analysis" |
| environment.yaml | | packages needed to be installed in Windows|

When running the code in this repository, paths must be set to their real paths.

Folder test_dataset only presents part of the dataset. The full dataset can be downloaded at https://zenodo.org/record/6675280

If you want to replicate the work, please run the following instructions:

### Processing and Labeling

1. run 0.preprocessing/Binary_FCG_extraction/IDA_fcg_extractor/run_IDA_on_all_binaries.py or 0.preprocessing/Binary_FCG_extraction/use_ghidra_extract_fcg/run_ghidra_on_all_binaries.py to extract FCG for binaries. Some paths in the above files should be changed to your destination. An example of extracted binary FCG can refer to test_dataset/gnu_debug/a2ps/a2ps-4.14_clang-7.0_x86_64_O0_a2ps.elf.fcg. It is stored in pickle format.

2. run 0.preprocessing/Source_FCG_extraction/run_understand_to_extract_fcgs.py to extract FCG for source projects. Paths of Understand and source projects should also be changed. An example of source FCG can refer to 0.preprocessing/Source_FCG_extraction/FCG/a2ps-4.14_fcg.json.

3. run 1.inlining_ground_truth_labelining/inlining_ground_truth_labeling_per_call_site/call_sites_labeling/summarize_binary2source_function_mappings.py to summary the binary2source function-level mapping of the dataset. Before running this script, please refer to https://github.com/island255/TOSEM2022 to construct the binary2source function-level mapping of the dataset.

4. run 1.inlining_ground_truth_labelining/inlining_ground_truth_labeling_per_call_site/call_sites_labeling/extract_mapped_call_site.py to identify the inlined call sites and the normal call sites.

### Feature Extraction

5. run 2.feature_extraction/function_feature_extraction/processing_projects.py to extract function contents for source projects.

6. run 2.feature_extraction/call_site_feature_extraction/call_site_feature_extraction.py to extract the call site features.

### Classifier Training

7. run 3.classifier/multi-label_classifier/find_best_para/find_best_parameters_for_models.py to find the best number of estimators for different MLC models.

### SFS Generation

8. run 4.apply_classifier_to_test_projects/multi-label_classifiers/using_multi-label_classifiers.py to generate SFSs for source projects.



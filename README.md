 # binary2source-matching-under-function-inlining

This is the repository illustrating how we label the inlined call sites, train the classifier for ICS prediction, and generate SFSs for binary2source matching.

## Dataset

The dataset can download from https://drive.google.com/file/d/1K9ef-OoRBr0X5u8g2mlnYqh9o1i6zFij/view and https://drive.google.com/file/d/1wt7GY-DDp8J_2zeBBVUrcfWIyerg_xLO/view. It is constructed using Binkit (https://github.com/SoftSec-KAIST/BinKit).

## Instructions

If you want to replicate the work, please run the following instructions:

### Processing and Labeling

1. run 0.preprocessing/Binary_FCG_extraction/IDA_fcg_extractor/run_IDA_on_all_binaries.py to extract FCG for binaries. Some paths in the above files should be changed to your destination. 

2. run 0.preprocessing/Source_FCG_extraction/run_understand_to_extract_fcgs.py to extract FCG for source projects. Paths of Understand and source projects should also be changed. An example of source FCG can refer to 0.preprocessing/Source_FCG_extraction/FCG/a2ps-4.14_fcg.json.

3. run 1.inlining_ground_truth_labelining/summarize_binary2source_function_mappings.py to summarize the binary2source function-level mapping of the dataset. Before running this script, please refer to https://github.com/island255/TOSEM2022 to construct the binary2source function-level mapping of the dataset.

4. run 1.inlining_ground_truth_labelining/extract_mapped_call_site.py to identify the inlined call sites and the normal call sites.

### Feature Extraction

5. run 2.feature_extraction/function_feature_extraction/processing_projects.py to extract function contents for source projects.

6. run 2.feature_extraction/call_site_feature_extraction/call_site_feature_extraction.py to extract the call site features.

### Classifier Training

7. run 3.classifier/multi-label_classifier/find_best_para/find_best_parameters_for_models.py to find the best number of estimators for different MLC models.

### SFS Generation

8. run 4.apply_classifier_to_test_projects/multi-label_classifiers/using_multi-label_classifiers.py to generate SFSs for source projects.



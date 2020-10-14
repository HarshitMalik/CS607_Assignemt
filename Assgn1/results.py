from utils.results import get_results

# Directory where text extraction outputs are saved
text_output_dir = 'Resourses/text_extraction_output/'
# Directory where topic modelling outputs are saved
tm_output_dir = 'Resourses/topic_modelling_output/'
# Directory to store final results
results_dir = 'Results/'

def main():
    get_results(tm_output_dir, results_dir,text_output_dir)

if __name__ == "__main__":
    main()

import os
import sys
import boto3
import tarfile

from utils.aws_s3 import create_bucket, delete_bucket, upload_file, download_file, get_bucket_list
from utils.aws_textract import aws_textract
from utils.aws_comprehend import topic_modelling
from utils.extract_text import extract_text
from utils.results import get_results

# Amazon Web Service Credentials
ACCESS_KEY = ''
SECRET_KEY = ''
SESSION_TOKEN = '' #if available
REGION = ''

# Amazon Resource Name (ARN) of the AWS Identity and Access Management (IAM) role that grants Amazon Comprehend read access to input data
data_access_role_arn = "arn:aws:iam::105741231021:role/ComprehendRole"

# S3 Buckets
textract_input_bucket = 'textractapiinputfiles'
comprehend_input_bucket = 'comprehendapiinputfiles'
comprehend_output_bucket = 'comprehendapioutputbucket'

# Directory where text extraction outputs are saved
text_output_dir = 'Resourses/text_extraction_output/'
# Directory where pdf of the books are stored
books_dir = 'Resourses/Books/'
# Directory where topic modelling outputs are saved
tm_output_dir = 'Resourses/topic_modelling_output/'
# Directory to store final results
results_dir = 'Results/'

# Books
books_name = ['Gita.pdf',
              'Quran.pdf',
              'Taoist.pdf',
              'GuruGranth.pdf',
              'Bible.pdf', ]

# To get a client instance for a particular service
def get_client(service_name):
    return boto3.client(
        service_name=service_name,
        aws_access_key_id=ACCESS_KEY,
        aws_secret_access_key=SECRET_KEY,
        aws_session_token=SESSION_TOKEN,
        region_name=REGION
    )

# To extract text from the PDFs
def extractText():
    for i in range(len(books_name)):
        extract_text(i)

# To create buckets to store data on aws S3 storage
def createBucketsOnS3(client):
    print('Creating buckets on S3 storage')
    buckets = get_bucket_list(client)
    if textract_input_bucket not in buckets:
        create_bucket(client, textract_input_bucket, REGION)
    if comprehend_input_bucket not in buckets:
        create_bucket(client, comprehend_input_bucket, REGION)
    if comprehend_output_bucket not in buckets:
        create_bucket(client, comprehend_output_bucket, REGION)
    print('Buckets created')

# To upload PDFs on aws S3 storage
def uploadFileForTextractAPI(client):
    print('Uploading PDF files on S3 for text extraction')
    files = os.listdir(books_dir)
    for file in files:
        print('.',end='')
        upload_file(client,textract_input_bucket, books_dir+file, file)
    print()
    print('PDF files uploaded')

# To upload text files on aws S3 storage
def uploadFileForComprehendAPI(client):
    print('Uploading text files on S3 for topic modelling')
    files = os.listdir(text_output_dir)
    for i,file in enumerate(files):
        if i%100 == 0:
            print('.',end='')
            sys.stdout.flush()
        upload_file(client,comprehend_input_bucket, text_output_dir+file, file)
    print()
    print('Text files uploaded')

# To run topic modelling on text files using aws comprehend API
def startTopicModelling(client_comprehend, client_s3):
    path_to_output = topic_modelling(client_comprehend, comprehend_input_bucket, comprehend_output_bucket, data_access_role_arn)
    if path_to_output == '':
        print('Topic Modelling failed')
        sys.exit()
    print('Downloading topic modelling output files')
    download_file(client_s3, comprehend_output_bucket, path_to_output[6+len(comprehend_output_bucket):],tm_output_dir+'output.tar.gz')
    print('Extracting files')
    file = tarfile.open(tm_output_dir+'output.tar.gz')
    file.extractall(tm_output_dir)
    file.close()

def main():
    s3 = get_client('s3')
    comprehend = get_client('comprehend')

    createBucketsOnS3(s3)
    uploadFileForTextractAPI(s3)
    extractText()
    uploadFileForComprehendAPI(s3)
    startTopicModelling(comprehend, s3)
    get_results(tm_output_dir, results_dir, text_output_dir)

if __name__ == "__main__":
    main()

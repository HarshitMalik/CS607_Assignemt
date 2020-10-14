import os
import boto3
import json
import sys
import time

# Directory where text extraction outputs are saved
text_output_dir = 'Resourses/text_extraction_output/'
# Directory where pdf of the books are stored
books_dir = 'Resourses/Books/'

# Books
books_name = [
              'Gita.pdf',
              'Quran.pdf',
              'Taoist.pdf',
              'GuruGranth .pdf',
              'Bible.pdf',
             ]

# First page where actual book text starts excluding cover page, about author, preface, contents, introduction,  etc
start_page = [20,4,0,0,12]

# Class to handle textract aws api
class DocumentProcessor:
    jobId = ''
    roleArn = ''
    bucket = ''
    document = ''
    sqsQueueUrl = ''
    snsTopicArn = ''

    def __init__(self, textract_client, sqs_client, sns_client, role, bucket, document):
        self.textract = textract_client
        self.sqs = sqs_client
        self.sns = sns_client
        self.roleArn = role
        self.bucket = bucket
        self.document = document

        # Check if books directory exists
        if not os.path.isdir(books_dir):
            raise 'Books directory' + '\''+ books_dir + '\''+'not found !'
            sys.exit()

        # Check if output directory exists otherwise create it
        if not os.path.isdir(text_output_dir):
            os.mkdir(text_output_dir)

    # Submit job on aws for text extraction from PDFs
    def ProcessDocument(self):
        jobFound = False

        response = self.textract.start_document_text_detection(
                        DocumentLocation={'S3Object': {'Bucket': self.bucket, 'Name': self.document}},
                        NotificationChannel={'RoleArn': self.roleArn, 'SNSTopicArn': self.snsTopicArn})
        print('Start Job Id: ' + response['JobId'])
        dotLine=0
        while jobFound == False:
            sqsResponse = self.sqs.receive_message(QueueUrl=self.sqsQueueUrl, MessageAttributeNames=['ALL'],MaxNumberOfMessages=10)

            if sqsResponse:
                if 'Messages' not in sqsResponse:
                    if dotLine<40:
                        print('.', end='')
                        dotLine=dotLine+1
                    else:
                        print()
                        dotLine=0
                    sys.stdout.flush()
                    time.sleep(7)
                    continue

                for message in sqsResponse['Messages']:
                    notification = json.loads(message['Body'])
                    textMessage = json.loads(notification['Message'])
                    print(textMessage['JobId'])
                    print(textMessage['Status'])
                    if str(textMessage['JobId']) == response['JobId']:
                        print('Matching Job Found:' + textMessage['JobId'])
                        jobFound = True
                        self.GetResults(textMessage['JobId'])
                        self.sqs.delete_message(QueueUrl=self.sqsQueueUrl,
                                       ReceiptHandle=message['ReceiptHandle'])
                    else:
                        print("Job didn't match:" +
                              str(textMessage['JobId']) + ' : ' + str(response['JobId']))
                    self.sqs.delete_message(QueueUrl=self.sqsQueueUrl,
                                   ReceiptHandle=message['ReceiptHandle'])
        print('Text extraction compeleted!')

    def CreateTopicandQueue(self):

        millis = str(int(round(time.time() * 1000)))

        #Create SNS topic
        snsTopicName="AmazonTextractTopic" + millis

        topicResponse=self.sns.create_topic(Name=snsTopicName)
        self.snsTopicArn = topicResponse['TopicArn']

        #create SQS queue
        sqsQueueName="AmazonTextractQueue" + millis
        self.sqs.create_queue(QueueName=sqsQueueName)
        self.sqsQueueUrl = self.sqs.get_queue_url(QueueName=sqsQueueName)['QueueUrl']

        attribs = self.sqs.get_queue_attributes(QueueUrl=self.sqsQueueUrl,
                                                    AttributeNames=['QueueArn'])['Attributes']

        sqsQueueArn = attribs['QueueArn']

        # Subscribe SQS queue to SNS topic
        self.sns.subscribe(
            TopicArn=self.snsTopicArn,
            Protocol='sqs',
            Endpoint=sqsQueueArn)

        #Authorize SNS to write SQS queue
        policy = """{{
  "Version":"2012-10-17",
  "Statement":[
    {{
      "Sid":"MyPolicy",
      "Effect":"Allow",
      "Principal" : {{"AWS" : "*"}},
      "Action":"SQS:SendMessage",
      "Resource": "{}",
      "Condition":{{
        "ArnEquals":{{
          "aws:SourceArn": "{}"
        }}
      }}
    }}
  ]
}}""".format(sqsQueueArn, self.snsTopicArn)

        response = self.sqs.set_queue_attributes(
            QueueUrl = self.sqsQueueUrl,
            Attributes = {
                'Policy' : policy
            })

    def DeleteTopicandQueue(self):
        self.sqs.delete_queue(QueueUrl=self.sqsQueueUrl)
        self.sns.delete_topic(TopicArn=self.snsTopicArn)

    # Get results from textract aws API and save the outputs
    def GetResults(self, jobId):
        maxResults = 1000
        paginationToken = None
        finished = False
        totalPages = 0
        currentPageNo = start_page[bookNumber]
        bookNumber = -1

        for i in range(len(books_name)):
            if self.document == books_name[i]:
                bookNumber = i
                break

        file = open(text_output_dir + books_name[bookNumber][:-4] + '_page_' + str(currentPageNo) + '.txt', "w")

        while finished == False:

            response=None
            if paginationToken==None:
                response = self.textract.get_document_text_detection(JobId=jobId,MaxResults=maxResults)
                totalPages = response['DocumentMetadata']['Pages']
            else:
                response = self.textract.get_document_text_detection(JobId=jobId,MaxResults=maxResults,NextToken=paginationToken)

            blocks=response['Blocks']
            for block in blocks:
                if block['BlockType'] == 'LINE' and block['Page'] >= start_page[bookNumber]:
                    if block['Page'] == currentPageNo:
                        file.write(block['Text']+"\n")
                    else:
                        currentPageNo = block['Page']
                        file.close()
                        file = open(text_output_dir + books_name[bookNumber][:-4] + '/page_' + str(currentPageNo) + '.txt', "w")
                        file.write(block['Text']+"\n")

            if 'NextToken' in response:
                paginationToken = response['NextToken']
            else:
                finished = True
        print('Total Pages detected : ', totalPages)
        file.close()

# Function extraction from PDFs using textract aws API
def aws_textract(textract_client, sqs_client, sns_client, roleArn, bucket_name, filename):
    analyzer=DocumentProcessor(textract_client, sqs_client, sns_client, roleArn, bucket_name, filename)
    analyzer.CreateTopicandQueue()
    analyzer.ProcessDocument()
    analyzer.DeleteTopicandQueue()

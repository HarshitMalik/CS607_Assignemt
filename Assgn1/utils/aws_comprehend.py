import boto3
import json
import time
import sys
from bson import json_util

def topic_modelling(client, input_bucket, output_bucket, data_access_role_arn, number_of_topics = 35):

    input_data_config = {"S3Uri": 's3://' + input_bucket, "InputFormat": "ONE_DOC_PER_FILE"}
    output_data_config = {"S3Uri": 's3://' + output_bucket}

    start_topics_detection_job_result = client.start_topics_detection_job(NumberOfTopics=number_of_topics,
                                                                              InputDataConfig=input_data_config,
                                                                              OutputDataConfig=output_data_config,
                                                                              DataAccessRoleArn=data_access_role_arn)

    job_id = start_topics_detection_job_result["JobId"]
    print('Started topic modelling with job_id: ' + job_id)
    
    response = client.describe_topics_detection_job(JobId=job_id)
    status = response['TopicsDetectionJobProperties']['JobStatus']

    dotLine=0
    while status == "IN_PROGRESS" or status == "SUBMITTED":
        if dotLine<40:
            print('.', end='')
            dotLine=dotLine+1
        else:
            print()
            dotLine=0
        sys.stdout.flush()
        time.sleep(45)
        response = client.describe_topics_detection_job(JobId=job_id)
        status = response['TopicsDetectionJobProperties']['JobStatus']
        continue


    print('Job finished')
    response = client.describe_topics_detection_job(JobId=job_id)
    status = response['TopicsDetectionJobProperties']['JobStatus']

    if status == 'COMPLETED':
        path_to_output = response['TopicsDetectionJobProperties']['OutputDataConfig']['S3Uri']
        return path_to_output
    else:
        print('Job status:',status)
        return ''

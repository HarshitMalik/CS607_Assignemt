import boto3

# To get existing bucket list
def get_bucket_list(client):
    response = client.list_buckets()
    buckets = [bucket['Name'] for bucket in response['Buckets']]
    return buckets

# To create a new bucket
def create_bucket(client,bucket_name, region):
    return client.create_bucket(
        Bucket=bucket_name,
        CreateBucketConfiguration={
            'LocationConstraint': region
        })

# To  delete a bucket
def delete_bucket(client,bucket_name):
    return client.delete_bucket(Bucket=bucket_name)

# To upload file on S3 storage
def upload_file(client,bucket_name, local_file_path, remote_file_name):
    client.upload_file(local_file_path, bucket_name, remote_file_name)

# To download file on S3 storage
def download_file(client,bucket_name, remote_file_name, local_file_path):
    client.download_file(bucket_name, remote_file_name, local_file_path)

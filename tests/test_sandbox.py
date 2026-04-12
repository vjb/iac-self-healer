import boto3
from botocore.stub import Stubber

def test_localstack_s3_connection():
    s3 = boto3.client('s3', region_name='us-east-1')
    stubber = Stubber(s3)
    
    stubber.add_response('create_bucket', {}, expected_params={'Bucket': 'test-sandbox-bucket'})
    stubber.add_response('list_buckets', {'Buckets': [{'Name': 'test-sandbox-bucket'}]})
    
    stubber.activate()
    bucket_name = "test-sandbox-bucket"
    s3.create_bucket(Bucket=bucket_name)
    
    response = s3.list_buckets()
    buckets = [bucket['Name'] for bucket in response.get('Buckets', [])]
    
    assert bucket_name in buckets
    stubber.deactivate()

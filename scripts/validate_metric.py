"""Quick validation: score a known-good CDK v2 stack through the metric pipeline."""
import os
import sys
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

from src.evaluators import _score_single_code
from src.compiler import run_cdk_synth

# A known-good CDK v2 stack (should score near 1.0)
GOOD_CODE = '''
from constructs import Construct
from aws_cdk import (
    Stack, RemovalPolicy, Duration,
    aws_dynamodb as dynamodb,
    aws_lambda as _lambda,
    aws_apigateway as apigateway,
)

class CdkTestingGroundStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        table = dynamodb.Table(self, "ItemsTable",
            partition_key=dynamodb.Attribute(
                name="id", type=dynamodb.AttributeType.STRING),
            removal_policy=RemovalPolicy.DESTROY)

        fn = _lambda.Function(self, "Handler",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="index.handler",
            code=_lambda.Code.from_inline(
                "def handler(event, context): return {\\'statusCode\\': 200, \\'body\\': \\'OK\\'}"),
            environment={"TABLE_NAME": table.table_name})

        table.grant_read_write_data(fn)

        api = apigateway.LambdaRestApi(self, "Api", handler=fn)
'''

# A known-bad stack (CDK v1 imports — should score low)
BAD_CODE = '''
from aws_cdk import core

class CdkTestingGroundStack(core.Stack):
    def __init__(self, scope: core.Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)
        pass
'''

# A stack with syntax error (should score 0.0)
SYNTAX_ERROR = '''
from aws_cdk import Stack
def this is not valid python {{{{
'''

def main():
    print("=== Testing Metric Pipeline ===\n")
    
    print("1. Testing known-good CDK v2 stack...")
    score = _score_single_code(GOOD_CODE)
    print(f"   Score: {score:.2f} (expected >= 0.80)\n")
    
    print("2. Testing known-bad CDK v1 stack...")
    score = _score_single_code(BAD_CODE)
    print(f"   Score: {score:.2f} (expected 0.20-0.30)\n")
    
    print("3. Testing syntax error code...")
    score = _score_single_code(SYNTAX_ERROR)
    print(f"   Score: {score:.2f} (expected 0.00)\n")
    
    print("=== Validation Complete ===")

if __name__ == "__main__":
    main()

# AWS CDK v2 Python — Correct Import Paths

## Core Imports (always from aws_cdk or constructs)
```python
from aws_cdk import App, Stack, RemovalPolicy, Duration, CfnOutput, Tags, Fn, Aws
from constructs import Construct
```

## Service Module Imports
```python
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_s3 as s3
from aws_cdk import aws_lambda as _lambda          # underscore prefix to avoid Python keyword
from aws_cdk import aws_dynamodb as dynamodb
from aws_cdk import aws_apigateway as apigateway
from aws_cdk import aws_iam as iam
from aws_cdk import aws_ecs as ecs
from aws_cdk import aws_ecs_patterns as ecs_patterns
from aws_cdk import aws_elasticloadbalancingv2 as elbv2
from aws_cdk import aws_elasticloadbalancingv2_targets as elbv2_targets
from aws_cdk import aws_rds as rds
from aws_cdk import aws_sqs as sqs
from aws_cdk import aws_sns as sns
from aws_cdk import aws_sns_subscriptions as sns_subs
from aws_cdk import aws_events as events
from aws_cdk import aws_events_targets as events_targets
from aws_cdk import aws_logs as logs
from aws_cdk import aws_cloudwatch as cw
from aws_cdk import aws_cloudwatch_actions as cw_actions
from aws_cdk import aws_stepfunctions as sfn
from aws_cdk import aws_stepfunctions_tasks as sfn_tasks
from aws_cdk import aws_cognito as cognito
from aws_cdk import aws_route53 as route53
from aws_cdk import aws_cloudfront as cloudfront
from aws_cdk import aws_cloudfront_origins as origins
from aws_cdk import aws_certificatemanager as acm
from aws_cdk import aws_wafv2 as wafv2
from aws_cdk import aws_kms as kms
from aws_cdk import aws_secretsmanager as secretsmanager
from aws_cdk import aws_ssm as ssm
from aws_cdk import aws_autoscaling as autoscaling
```

## Alternative Import Styles (both valid in CDK v2)
```python
# Style 1: Named imports from aws_cdk
from aws_cdk import (
    Stack,
    aws_ec2 as ec2,
    aws_lambda as _lambda,
    RemovalPolicy
)

# Style 2: Import submodules directly
import aws_cdk.aws_ec2 as ec2
import aws_cdk.aws_lambda as _lambda

# Style 3: Import specific classes
from aws_cdk.aws_ec2 import Vpc, SubnetType, SecurityGroup
from aws_cdk.aws_lambda import Function, Runtime, Code
```

## NEVER Use These (CDK v1 patterns):
```python
# WRONG — aws_cdk.core does not exist in v2
from aws_cdk import core
from aws_cdk.core import Stack, App

# WRONG — individual packages don't exist in v2
import aws_cdk.aws_s3  # This may work but is not idiomatic
from aws_cdk.aws_s3 import Bucket  # This works but prefer the alias pattern

# WRONG — cdk namespace
import cdk
from cdk import Stack
```

## Stack Class Template
```python
from aws_cdk import Stack, RemovalPolicy
from aws_cdk import aws_ec2 as ec2
from constructs import Construct

class MyStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        # Resources go here
```

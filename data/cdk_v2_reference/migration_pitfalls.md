# CDK v1 → v2 Migration Pitfalls (Python)

These are the exact patterns that LLMs hallucinate because their training data contains CDK v1 examples.

## Import Changes

### WRONG (CDK v1):
```python
from aws_cdk import core
from aws_cdk.core import App, Stack, RemovalPolicy
from aws_cdk import aws_s3 as s3
import aws_cdk.aws_ec2 as ec2
```

### CORRECT (CDK v2):
```python
from aws_cdk import App, Stack, RemovalPolicy
from aws_cdk import aws_s3 as s3
from aws_cdk import aws_ec2 as ec2
from constructs import Construct
```

Key difference: In v2, `core` module does not exist. All core types (App, Stack, RemovalPolicy, Duration, CfnOutput, Tags, Fn, Aws) are imported directly from `aws_cdk`. The `Construct` class is imported from the separate `constructs` package.

## Package Structure

### CDK v1: Multiple packages
```
aws-cdk.core
aws-cdk.aws-s3
aws-cdk.aws-ec2
aws-cdk.aws-lambda
```

### CDK v2: Single package
```
aws-cdk-lib  (contains everything)
constructs   (contains Construct base class)
```

All stable constructs are in `aws-cdk-lib`. Only experimental/alpha constructs are in separate packages.

## Common Hallucinations

1. `core.Construct` → Use `constructs.Construct`
2. `core.RemovalPolicy.DESTROY` → Use `aws_cdk.RemovalPolicy.DESTROY` or `RemovalPolicy.DESTROY`
3. `core.Duration.seconds(30)` → Use `aws_cdk.Duration.seconds(30)` or `Duration.seconds(30)`
4. `core.CfnOutput` → Use `aws_cdk.CfnOutput`
5. `core.Tags` → Use `aws_cdk.Tags`
6. `core.Stack.of(self)` → Use `aws_cdk.Stack.of(self)`
7. `cdk.RemovalPolicy` → Use `aws_cdk.RemovalPolicy`

## SubnetType Changes

### WRONG (deprecated):
```python
ec2.SubnetType.PRIVATE  # Removed in CDK v2
ec2.SubnetType.PRIVATE_WITH_NAT  # Deprecated alias
```

### CORRECT:
```python
ec2.SubnetType.PRIVATE_WITH_EGRESS  # Correct in CDK v2
ec2.SubnetType.PRIVATE_ISOLATED     # For subnets without internet
ec2.SubnetType.PUBLIC               # For public subnets
```

## Security Group Parameter

### WRONG:
```python
ec2.Instance(self, "Instance", security_group=my_sg)
```

### CORRECT:
```python
ec2.Instance(self, "Instance", security_group=my_sg)  # singular is OK for Instance
# BUT for Lambda:
_lambda.Function(self, "Fn", security_groups=[my_sg])  # must be a list
```

## ELBv2 Targets

### WRONG:
```python
from aws_cdk.aws_elasticloadbalancingv2 import InstanceTarget
```

### CORRECT:
```python
from aws_cdk.aws_elasticloadbalancingv2_targets import InstanceTarget
# Pass the Instance object, not instance_id string:
targets=[InstanceTarget(instance)]  # NOT InstanceTarget(instance.instance_id)
```

## S3 BlockPublicAccess

### WRONG:
```python
s3.Bucket(self, "Bucket", public_read_access=True, block_public_access=s3.BlockPublicAccess.BLOCK_ALL)
```
These conflict — you cannot enable public access and block it simultaneously.

### CORRECT:
```python
# For private bucket (default and recommended):
s3.Bucket(self, "Bucket", block_public_access=s3.BlockPublicAccess.BLOCK_ALL)

# For public bucket (if truly needed):
s3.Bucket(self, "Bucket", public_read_access=True)
```

## VPC Subnet Configuration

### WRONG (will crash at synth):
```python
vpc = ec2.Vpc(self, "VPC",
    subnet_configuration=[
        ec2.SubnetConfiguration(name="Private", subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS)
    ]
)
```
Error: PRIVATE subnets require PUBLIC subnets for NAT gateways.

### CORRECT:
```python
vpc = ec2.Vpc(self, "VPC",
    subnet_configuration=[
        ec2.SubnetConfiguration(name="Public", subnet_type=ec2.SubnetType.PUBLIC),
        ec2.SubnetConfiguration(name="Private", subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS)
    ]
)
```

## Lambda Code

### Valid CDK v2 patterns:
```python
# Inline code (simple handlers):
code=_lambda.Code.from_inline('def handler(event, context): return {"statusCode": 200}')

# From local directory:
code=_lambda.Code.from_asset('lambda/')

# InlineCode class (alternative):
code=_lambda.InlineCode('def handler(event, context): pass')
```

## DynamoDB Attribute

### WRONG:
```python
partition_key={'name': 'id', 'type': dynamodb.AttributeType.STRING}
```

### CORRECT:
```python
partition_key=dynamodb.Attribute(name='id', type=dynamodb.AttributeType.STRING)
```

## MachineImage for EC2

### Common patterns in CDK v2:
```python
# Latest Amazon Linux 2 (requires SSM access):
machine_image=ec2.MachineImage.latest_amazon_linux(
    generation=ec2.AmazonLinuxGeneration.AMAZON_LINUX_2
)

# Generic Linux with hardcoded AMI:
machine_image=ec2.MachineImage.generic_linux({'us-east-1': 'ami-0abcdef1234567890'})

# Latest Amazon Linux 2023:
machine_image=ec2.MachineImage.latest_amazon_linux_2023()
```
Note: `latestAmazonLinux()` is CDK v1 syntax. Use `latest_amazon_linux()` (snake_case) in Python CDK v2.

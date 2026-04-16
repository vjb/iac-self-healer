# Working CDK v2 Python Code Examples

These are verified, compilable AWS CDK v2 Python stacks from the aws-samples repository.

## 1. API Gateway + Lambda + CORS
Source: aws-samples/aws-cdk-examples/python/api-cors-lambda

```python
from constructs import Construct
from aws_cdk import (
    App, Stack,
    aws_lambda as _lambda,
    aws_apigateway as _apigw
)

class ApiCorsLambdaStack(Stack):
    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        base_lambda = _lambda.Function(self, 'ApiCorsLambda',
            handler='lambda-handler.handler',
            runtime=_lambda.Runtime.PYTHON_3_12,
            code=_lambda.Code.from_inline('def handler(event, context): return {"statusCode": 200, "body": "OK"}'))

        base_api = _apigw.RestApi(self, 'ApiGatewayWithCors',
            rest_api_name='ApiGatewayWithCors')

        example_entity = base_api.root.add_resource('example',
            default_cors_preflight_options=_apigw.CorsOptions(
                allow_methods=['GET', 'OPTIONS'],
                allow_origins=_apigw.Cors.ALL_ORIGINS))

        example_entity.add_method('GET',
            _apigw.LambdaIntegration(base_lambda, proxy=True))
```

## 2. EC2 Instance in VPC
Source: aws-samples/aws-cdk-examples/python/ec2/instance

```python
from aws_cdk import (
    aws_ec2 as ec2,
    aws_iam as iam,
    App, Stack
)
from constructs import Construct

class EC2InstanceStack(Stack):
    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        vpc = ec2.Vpc(self, "VPC",
            nat_gateways=0,
            subnet_configuration=[
                ec2.SubnetConfiguration(name="public", subnet_type=ec2.SubnetType.PUBLIC)
            ])

        amzn_linux = ec2.MachineImage.latest_amazon_linux(
            generation=ec2.AmazonLinuxGeneration.AMAZON_LINUX_2)

        role = iam.Role(self, "InstanceSSM",
            assumed_by=iam.ServicePrincipal("ec2.amazonaws.com"))
        role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("AmazonSSMManagedInstanceCore"))

        instance = ec2.Instance(self, "Instance",
            instance_type=ec2.InstanceType("t3.nano"),
            machine_image=amzn_linux,
            vpc=vpc,
            role=role)
```

## 3. Serverless Backend (API Gateway + Lambda + DynamoDB + S3 + Cognito)
Source: aws-samples/aws-cdk-examples/python/serverless-backend

```python
from aws_cdk import (
    Stack,
    aws_cognito as _cognito,
    aws_s3 as _s3,
    aws_dynamodb as _dynamodb,
    aws_lambda as _lambda,
    aws_apigateway as _apigateway,
    RemovalPolicy
)
from constructs import Construct

class ServerlessBackendStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        user_pool = _cognito.UserPool(self, "UserPool")
        user_pool.add_client("app-client",
            auth_flows=_cognito.AuthFlow(user_password=True))

        auth = _apigateway.CognitoUserPoolsAuthorizer(self, "Authorizer",
            cognito_user_pools=[user_pool])

        table = _dynamodb.Table(self, "Table",
            partition_key=_dynamodb.Attribute(
                name='id', type=_dynamodb.AttributeType.STRING),
            removal_policy=RemovalPolicy.DESTROY)

        bucket = _s3.Bucket(self, "Bucket",
            removal_policy=RemovalPolicy.DESTROY)

        fn = _lambda.Function(self, "Function",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler='index.handler',
            code=_lambda.Code.from_inline('def handler(event, context): return {"statusCode": 200, "body": "OK"}'),
            environment={
                'BUCKET': bucket.bucket_name,
                'TABLE': table.table_name
            })

        bucket.grant_read_write(fn)
        table.grant_read_write_data(fn)

        api = _apigateway.LambdaRestApi(self, "Api", handler=fn)
```

## 4. Fargate Load Balanced Service
Source: aws-samples/aws-cdk-examples/python/ecs/fargate-load-balanced-service

```python
from aws_cdk import (
    aws_ec2 as ec2,
    aws_ecs as ecs,
    aws_ecs_patterns as ecs_patterns,
    App, CfnOutput, Stack
)
from constructs import Construct

class FargateStack(Stack):
    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        vpc = ec2.Vpc(self, "MyVpc", max_azs=2)

        cluster = ecs.Cluster(self, 'Cluster', vpc=vpc)

        fargate_service = ecs_patterns.NetworkLoadBalancedFargateService(
            self, "FargateService",
            cluster=cluster,
            task_image_options=ecs_patterns.NetworkLoadBalancedTaskImageOptions(
                image=ecs.ContainerImage.from_registry("amazon/amazon-ecs-sample")))

        fargate_service.service.connections.security_groups[0].add_ingress_rule(
            peer=ec2.Peer.ipv4(vpc.vpc_cidr_block),
            connection=ec2.Port.tcp(80),
            description="Allow http inbound from VPC")

        CfnOutput(self, "LoadBalancerDNS",
            value=fargate_service.load_balancer.load_balancer_dns_name)
```

## 5. Lambda Cron (EventBridge + Lambda)
Source: aws-samples/aws-cdk-examples/python/lambda-cron

```python
from aws_cdk import (
    aws_events as events,
    aws_lambda as lambda_,
    aws_events_targets as targets,
    App, Duration, Stack
)
from constructs import Construct

class LambdaCronStack(Stack):
    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        fn = lambda_.Function(self, "Singleton",
            code=lambda_.InlineCode("def main(event, context): print('Hello')"),
            handler="index.main",
            timeout=Duration.seconds(300),
            runtime=lambda_.Runtime.PYTHON_3_12)

        rule = events.Rule(self, "Rule",
            schedule=events.Schedule.cron(
                minute='0', hour='18', month='*',
                week_day='MON-FRI', year='*'))

        rule.add_target(targets.LambdaFunction(fn))
```

## 6. S3 + CloudFront Static Website
```python
from aws_cdk import (
    Stack, RemovalPolicy, CfnOutput,
    aws_s3 as s3,
    aws_cloudfront as cloudfront,
    aws_cloudfront_origins as origins,
)
from constructs import Construct

class StaticSiteStack(Stack):
    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        bucket = s3.Bucket(self, "SiteBucket",
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True)

        distribution = cloudfront.Distribution(self, "Distribution",
            default_behavior=cloudfront.BehaviorOptions(
                origin=origins.S3BucketOrigin.with_origin_access_control(bucket)),
            default_root_object="index.html")

        CfnOutput(self, "DistributionDomain",
            value=distribution.distribution_domain_name)
```

## 7. SQS + SNS Event Processing
```python
from aws_cdk import (
    Stack, Duration,
    aws_sqs as sqs,
    aws_sns as sns,
    aws_sns_subscriptions as subs,
    aws_lambda as _lambda,
    aws_lambda_event_sources as lambda_events,
)
from constructs import Construct

class EventProcessingStack(Stack):
    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        queue = sqs.Queue(self, "Queue",
            visibility_timeout=Duration.seconds(300))

        topic = sns.Topic(self, "Topic")
        topic.add_subscription(subs.SqsSubscription(queue))

        fn = _lambda.Function(self, "Processor",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="index.handler",
            code=_lambda.Code.from_inline('def handler(event, context): print(event)'))

        fn.add_event_source(lambda_events.SqsEventSource(queue))
```

## 8. VPC with Public + Private Subnets + Security Groups
```python
from aws_cdk import (
    Stack,
    aws_ec2 as ec2,
)
from constructs import Construct

class NetworkStack(Stack):
    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        vpc = ec2.Vpc(self, "VPC",
            max_azs=2,
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    name="Public",
                    subnet_type=ec2.SubnetType.PUBLIC),
                ec2.SubnetConfiguration(
                    name="Private",
                    subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
            ])

        web_sg = ec2.SecurityGroup(self, "WebSG",
            vpc=vpc,
            description="Allow HTTP/HTTPS",
            allow_all_outbound=True)
        web_sg.add_ingress_rule(ec2.Peer.any_ipv4(), ec2.Port.tcp(80), "HTTP")
        web_sg.add_ingress_rule(ec2.Peer.any_ipv4(), ec2.Port.tcp(443), "HTTPS")

        app_sg = ec2.SecurityGroup(self, "AppSG",
            vpc=vpc,
            description="App tier",
            allow_all_outbound=True)
        app_sg.add_ingress_rule(web_sg, ec2.Port.tcp(8080), "From web tier")
```

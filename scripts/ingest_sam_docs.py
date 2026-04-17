import logging
import uuid
import chromadb
from chromadb.config import Settings

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

def ingest_sam_docs():
    """Populates ChromaDB with AWS SAM declarative architecture rules, cfn-lint definitions, and cfn-guard restrictions."""
    logger.info("Initializing ChromaDB connection for AWS SAM ingestion...")
    
    # Initialize the client in persistent mode targeting the local DB directory
    client = chromadb.PersistentClient(path="./chroma_db")
    
    # We maintain a specific collection for SAM-based documentation
    collection = client.get_or_create_collection(
        name="sam_declarative_reference",
        metadata={"hnsw:space": "cosine"}
    )
    
    # 1. Dynamic AWS SAM Resource Documentation 
    sam_docs = [
        "AWS SAM requires the Transform: AWS::Serverless-2016-10-31 declaration exactly at the root top level of the YAML template. Without it, AWS::Serverless objects will throw E1001 errors.",
        "AWS::Serverless::Function MemorySize must be an integer between 128 and 10240, in 1-MB increments.",
        "AWS::Serverless::Function Environment variables are mapped via the 'Environment: Variables:' property block. Values must be strings."
    ]
    try:
        import requests
        logger.info("Fetching real-time AWS CloudFormation Resource Specification schema...")
        r = requests.get('https://d1uauaxba7bl26.cloudfront.net/latest/gzip/CloudFormationResourceSpecification.json', timeout=30)
        data = r.json()
        scraped = 0
        for type_name, type_def in data.get('ResourceTypes', {}).items():
            if type_name.startswith("AWS::Serverless") or type_name.startswith("AWS::S3") or type_name.startswith("AWS::DynamoDB") or type_name.startswith("AWS::RDS") or type_name.startswith("AWS::Lambda") or type_name.startswith("AWS::ApiGateway"):
                desc = type_def.get('Documentation', "No explicit AWS doc link provided.")
                props = type_def.get('Properties', {})
                req_props = [k for k, v in props.items() if v.get('Required', False)]
                sam_docs.append(f"{type_name} declarative structural boundary. Official specification mapping: {desc}. Required Architecture Properties: {', '.join(req_props) if req_props else 'None strictly required.'}")
                scraped += 1
        logger.info(f"Successfully bridged {scraped} active dynamic AWS Schema bounds into working array.")
    except Exception as e:
        logger.error(f"Failed to fetch dynamic schema, falling back to basic bounds: {e}")
    
    # 2. cfn-lint Error Codes (Structural Bounds)
    cfn_lint_docs = [
        "[Lint E1001] Top level template section not valid. CloudFormation templates only support specific top-level blocks like AWSTemplateFormatVersion, Description, Metadata, Parameters, Mappings, Conditions, Transform, Resources, and Outputs.",
        "[Lint E2014] Property value must be a valid allowed value. Check the AWS specification. For DynamoDB AttributeType, allowed values are 'S', 'N', 'B'. For IAM effects, 'Allow' or 'Deny'.",
        "[Lint E3001] Invalid or unsupported Type. The 'Type' declaration points to an invalid AWS resource or a missing Transform prevents evaluation. Ensure Transform is defined for SAM objects.",
        "[Lint E3002] Resource properties are missing or invalid. Check the specific resource block and ensure all mandatory attributes are explicitly defined.",
        "[Lint E3012] Property value must be a string. Check your YAML typings and ensure boolean/number types are correctly quoted if the schema expects String (e.g. 'true' instead of true).",
        "[Lint E3030] You must specify a valid Node or runtime version for AWS::Serverless::Function runtimes (e.g. python3.11, python3.12, nodejs20.x).",
        "[Lint W2001] Parameter not used. You defined a Parameter block but it is never referenced using !Ref in the Resources or Outputs section.",
        "[Lint E1010] Invalid intrinsic function. Make sure you are using valid CloudFormation functions like !Sub, !Ref, !GetAtt, !Join, or !Select accurately.",
        "[Lint E1012] Ref to missing parameter or resource. Ensure that any !Ref references an explicit name present in the Resources or Parameters blocks.",
        "[Lint E3003] Property must be an array/list. You provided a primitive type but the schema explicitly expects a list of items (e.g. SecurityGroupIds or SubnetIds)."
    ]
    
    # 3. cfn-guard Security Constraints (HIPAA / Compliance bounds)
    cfn_guard_docs = [
        "[Guard aws-hipaa-conformance-pack] S3_BUCKET_SERVER_SIDE_ENCRYPTION_ENABLED: Ensure all AWS::S3::Bucket resources contain a BucketEncryption property utilizing AES256 or aws:kms. Plaintext buckets will cause immediate compliance failure.",
        "[Guard aws-hipaa-conformance-pack] IAM_NO_INLINE_POLICY_CHECK: You must avoid inline IAM policies. Use explicit AWS::IAM::ManagedPolicy bindings or exact AWS-provided SAM Policy Templates (e.g. DynamoDBCrudPolicy).",
        "[Guard aws-hipaa-conformance-pack] DYNAMODB_TABLE_ENCRYPTED_KMS: AWS::DynamoDB::Table and AWS::Serverless::SimpleTable must enable SSESpecification with SSEEnabled: true.",
        "[Guard security-baseline] LAMBDA_INSIDE_VPC: AWS::Serverless::Function must define VpcConfig referencing specific SubnetIds and SecurityGroupIds to prevent public execution exposure.",
        "[Guard security-baseline] API_GW_AUTHORIZER: AWS::Serverless::Api must strictly implement an Auth block configured with Cognito or a Custom Lambda Authorizer.",
        "[Guard security-baseline] API_GW_EXECUTION_LOGGING: All AWS::Serverless::Api and AWS::Serverless::HttpApi instances must define AccessLogSetting outlining a DestinationArn and correct LogFormat.",
        "[Guard security-baseline] LOG_GROUP_RETENTION: Every AWS::Logs::LogGroup must declare a explicitly limited RetentionInDays property. Infinite retention is a security vulnerability."
    ]
    
    docs_to_ingest = sam_docs + cfn_lint_docs + cfn_guard_docs
    ids = [str(uuid.uuid4()) for _ in docs_to_ingest]
    
    logger.info(f"Ingesting {len(docs_to_ingest)} structural and compliance reference vectors...")
    
    collection.add(
        documents=docs_to_ingest,
        ids=ids
    )
    
    logger.info("Phase 1: Knowledge Base Migration completed. ChromaDB populated with SAM definitions.")

if __name__ == "__main__":
    ingest_sam_docs()

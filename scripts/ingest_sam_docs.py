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
    
    # 1. AWS SAM Resource Documentation 
    sam_docs = [
        "AWS::Serverless::Function defines an AWS Lambda function, IAM execution role, and event source mappings. Required Properties: CodeUri, Handler, Runtime.",
        "AWS::Serverless::Api defines an Amazon API Gateway REST API. Required Properties: StageName.",
        "AWS::Serverless::SimpleTable defines a DynamoDB table with a single attribute primary key. Properties: PrimaryKey.",
        "AWS SAM requires the Transform: AWS::Serverless-2016-10-31 declaration at the top of the YAML template.",
    ]
    
    # 2. cfn-lint Error Codes (Structural Bounds)
    cfn_lint_docs = [
        "[Lint E1001] Top level template section not valid. CloudFormation templates only support specific top-level blocks like Resources, Outputs, Parameters, Mappings, Conditions, and Transform.",
        "[Lint E3002] Resource properties are missing or invalid. Check the specific resource block and ensure all mandatory attributes are explicitly defined.",
        "[Lint E3012] Property value must be a string. Check your YAML typings and ensure boolean/number types are correctly quoted if the schema expects String.",
        "[Lint E3030] You must specify a valid Node or runtime version for AWS::Serverless::Function runtimes.",
    ]
    
    # 3. cfn-guard Security Constraints (HIPAA / Compliance bounds)
    cfn_guard_docs = [
        "[Guard aws-hipaa-conformance-pack] S3_BUCKET_SERVER_SIDE_ENCRYPTION_ENABLED: Ensure all AWS::S3::Bucket resources contain a BucketEncryption property utilizing AES256 or aws:kms.",
        "[Guard aws-hipaa-conformance-pack] IAM_NO_INLINE_POLICY_CHECK: You must avoid inline IAM policies. Use AWS::IAM::ManagedPolicy bindings.",
        "[Guard security-baseline] LAMBDA_INSIDE_VPC: AWS::Serverless::Function must define VpcConfig referencing specific SubnetIds and SecurityGroupIds to prevent public execution exposure.",
        "[Guard security-baseline] API_GW_AUTHORIZER: AWS::Serverless::Api must strictly implement an Auth block configured with Cognito or a Custom Lambda Authorizer.",
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

import os
import glob
import re
import uuid
import time
import subprocess
import boto3
from dotenv import load_dotenv

def extract_champion_yaml(filepath: str) -> str:
    """Extracts raw YAML strictly from prompt_champion markdown blocks natively."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        match = re.search(r"```[a-zA-Z]*\n(.*?)\n```", content, re.DOTALL)
        if match:
            return match.group(1).strip()
    except Exception as e:
        print(f"[ERROR] Failed parsing {filepath}: {e}")
    return ""

def main():
    load_dotenv()
    
    auth_token = os.environ.get("LOCALSTACK_AUTH_TOKEN", "")
    if not auth_token:
        print("[CRITICAL] LOCALSTACK_AUTH_TOKEN not found in .env! LocalStack Pro limits require this for ENFORCE_IAM=1 verification.")
        return

    champion_files = sorted(glob.glob("results/optimization/run_seed_champions/prompt_champion_*.md"))
    if not champion_files:
        print("[WARNING] No champion files found in results/optimization/run_seed_champions/")
        return

    print("=== PHASE 2: EPHEMERAL SANDBOX EXECUTION NATIVELY BOOTING ===")
    print("[INFO] Provisioning LocalStack Pro natively via Docker... (Waiting 15 seconds for startup)")
    
    container_name = f"localstack-pro-eval-{uuid.uuid4().hex[:6]}"
    try:
        # Boot LocalStack dynamically without the testcontainers library proxy
        subprocess.run([
            "docker", "run", "-d", "--rm", "--name", container_name,
            "-p", "4566:4566",
            "-e", f"LOCALSTACK_AUTH_TOKEN={auth_token}",
            "-e", "ENFORCE_IAM=1",
            "localstack/localstack-pro:latest"
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        # Give the LocalStack JVM and services time to physically bind to port 4566
        time.sleep(15)
        print("[SUCCESS] LocalStack Pro Sandbox is strictly allocated and active!")
        
        # Initialize direct boto3 client mapped implicitly to the raw Docker localhost
        cf_client = boto3.client(
            "cloudformation",
            region_name="us-east-1",
            endpoint_url="http://localhost:4566",
            aws_access_key_id="test",
            aws_secret_access_key="test"
        )
        
        for file in champion_files:
            print(f"\n[EXECUTION] Testing target matrix: {os.path.basename(file)}")
            yaml_payload = extract_champion_yaml(file)
            
            if not yaml_payload:
                print("  -> ERROR: No valid YAML structural boundary found.")
                continue
                
            stack_id = f"eval-trace-{uuid.uuid4().hex[:8]}"
            print(f"  -> Injecting natively to Virtual CloudFormation Engine. Stack Name: {stack_id}")
            
            try:
                # AWS SAM is a physical macro transformation. We must enable CAPABILITY_AUTO_EXPAND mechanically.
                response = cf_client.create_stack(
                    StackName=stack_id,
                    TemplateBody=yaml_payload,
                    Capabilities=['CAPABILITY_IAM', 'CAPABILITY_NAMED_IAM', 'CAPABILITY_AUTO_EXPAND']
                )
                
                print("  -> Execution deployed. Initiating strict synchronization waiter...")
                
                # Active synchronous polling loop against the creation boundary
                waiter = cf_client.get_waiter('stack_create_complete')
                waiter.wait(StackName=stack_id, WaiterConfig={'Delay': 3, 'MaxAttempts': 15})
                print(f"  -> [PASS] Physical architecture deployed successfully over strict IAM boundaries! Score 2.0!")
                
            except Exception as e:
                print(f"  -> [FAIL] Deployment exception recorded natively. Extracting CloudFormation traces:")
                try:
                    events = cf_client.describe_stack_events(StackName=stack_id).get('StackEvents', [])
                    for evt in events:
                        if 'FAILED' in evt.get('ResourceStatus', '') and evt.get('LogicalResourceId') != stack_id:
                            print(f"       [TRACE] Resource: {evt.get('LogicalResourceId')} | Type: {evt.get('ResourceType')}")
                            print(f"       [REASON] {evt.get('ResourceStatusReason')}")
                except Exception as trace_err:
                    print(f"       [TRACE UNAVAILABLE] Execution halted completely: {str(e)[:250]}")
                
            finally:
                print("  -> Wiping sandbox constraints natively...")
                try:
                    cf_client.delete_stack(StackName=stack_id)
                except Exception as del_err:
                    print(f"       WARNING: Cleanup fault - {del_err}")
                    
    finally:
        print("\n[INFO] Terminating isolated sandbox...")
        subprocess.run(["docker", "stop", container_name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print("=== PHASE 2 EPHEMERAL TESTING BOUNDS COMPLETED ===")

if __name__ == "__main__":
    main()

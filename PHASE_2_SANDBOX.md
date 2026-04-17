# Phase 2: Physical Sandbox Execution Loop

## Executive Summary
The current `iac-self-healer` pipeline evaluates generative AWS Serverless Application Model (SAM) parameters entirely in local volatile RAM via static CLI analysis (`cfn-lint` and `cfn-guard`). While this mathematically seals syntactic and structural security patterns, it operates in a physical vacuum. It cannot explicitly prove that an IAM Execution Role possesses the correct deployment permissions for a specific Lambda configuration natively, nor that an API Gateway maps structural backend paths cleanly without yielding physical 403 authorization failures on deployment.

To achieve maximum institutional rigor for a hackathon boundary, the pipeline must transition exclusively to a **Phase 2 Execution**: dynamically triggering `sam deploy` parameters against physical ephemeral AWS environment constraints.

## Structural Execution Flow

### 1. Ephemeral Sandbox Initialization
The generative model must be permanently partitioned away from root physical resources. The evaluation loop must execute strictly under a dynamically isolated execution boundary:
- **Ephemeral Sandbox Constraint:** Target an isolated AWS Environment (e.g., via LocalStack running on massive RAM footprints, or explicit AWS Organizations sandbox policies). 
- **Strict Execution IAM Boundaries:** The Python orchestration thread assumes a tightly constrained IAM Execution Role possessing rights exclusively targeted for serverless provisioning bounds (Lambda, APIGW, S3, DynamoDB), strictly mapping back to a `PermissionsBoundary` to verify agents cannot break sandbox containment.

### 2. The Physical Execution Oracle (`sam deploy`)
The current static `evaluate_prompt_with_details` function routes the generated output string directly into physical cloud verification natively.

1. **Compilation & Synthesis:** The generative parameter writes a `template.yaml` to the volatile RAM disk node. The system mechanically executes `sam build --use-container`.
2. **Synchronous Deployment Trace:** The orchestration loop triggers continuous deployment boundaries utilizing randomized UUID hashing:
   ```bash
   sam deploy --stack-name eval-trace-[UUID] --resolve-s3 --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM --no-confirm-changeset
   ```
3. **Trace Extraction:** The Bayesian optimizer listens actively to the CloudFormation execution loop rather than local static syntax tests.
   - If `status == CREATE_COMPLETE`: The agent correctly mapped structural intent physically to the remote cloud. Reward limit multiplier bounds at `2.00`.
   - If `status == ROLLBACK_COMPLETE` or `CREATE_FAILED`: A physical parameter crash has occurred natively within the physical AWS system.

### 3. Dynamic Vectorized Feedback Injection
Static `cfn-guard` errors look like: `aws-wafr/S3_BLOCK FAIL`.
Physical `CloudFormation` deployment trace errors are essentially perfect. The Python script physically parses the exact failure stack vector directly from the deployment limits:
```bash
aws cloudformation describe-stack-events \
    --stack-name eval-trace-[UUID] \
    --query "StackEvents[?ResourceStatus=='CREATE_FAILED'].[LogicalResourceId, ResourceStatusReason]" \
    --output json
```

**Oracle Injection Pipeline:**
The pipeline natively parses the physical string failure payload (e.g., `LogicalID: MyDynamoDBTable, Reason: The conditional request failed because the BillingMode PROVISIONED is missing ReadCapacityUnits`). 
This exact physical deployment string boundary is recorded directly to ChromaDB using the `record_compiler_failure` Vector memory loop. The optimizer instantly dynamically shifts weights off the structural failure!

### 4. Zero-Budget Teardown Loop
Because AWS executes continuous billing parameters mapped to physical provisioned stack variables natively, the Python script executes deterministic resource eradication mechanically regardless of failure or success limits:
```python
try:
    stdout, stderr = run_sam_deploy()
    # Execute Deployment Grade Reward Evaluation...
finally:
    # Guaranteed Execution Wipe Bounds
    subprocess.run(["sam", "delete", "--stack-name", stack_name, "--no-prompts"], check=True)
```

## Institutional Advantages
By implementing this physical boundary evaluation execution loop natively, the `iac-self-healer` pipeline guarantees that its generated constraints are mathematically and physically deployable!
Any generated prompt strings exported dynamically by `generate.py` will carry the exact institutional assurance that the baseline architecture cleanly builds without limits against a live AWS environment. This effectively migrates the project completely from a "static constraint code generator" into a true Autonomous Physical Infrastructure Compiler.

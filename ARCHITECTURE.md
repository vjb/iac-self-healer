# Architecture: Compiler-in-the-Loop IaC Generation

This document describes the technical design of the IaC Self-Healer system, the problems it solves, and the engineering decisions behind its current implementation.

## Problem Statement

Standard LLM code generation for Infrastructure-as-Code fails at three distinct levels:

1. **API surface hallucination**: LLMs produce CDK v1 syntax (`core.RemovalPolicy`), reference non-existent class attributes (`BlockPublicAccess.BLOCK_NONE`), or pass arguments with incorrect types (`security_group=sg` instead of `security_groups=[sg]`).

2. **Environment-blind generation**: LLMs have no awareness of the target execution environment. They generate `aws_rds.DatabaseInstance` calls when the deployment target is LocalStack Community Edition (which does not support RDS). They use `MachineImage.latestAmazonLinux2()` which calls AWS SSM Parameter Store, a service that may not be running locally.

3. **Unactionable feedback loops**: Previous iterations of this system included an LLM-based "Static Critic" that reviewed generated code before compilation. This agent caused an infinite loop: it would reject valid code (false negatives) or approve invalid code (false positives), because it was predicting compiler behavior rather than observing it.

## Design Principles

### Physical compilation as the sole oracle

No LLM agent reviews or validates generated code. The only feedback the system trusts is the literal output of `npx cdk synth` (return code and stderr) and `npx cdklocal deploy` (CloudFormation stack status). This eliminates the hallucination loop described above.

### Separation of instruction and execution

The Teacher agent produces natural language instructions. The Student agent produces code. This separation prevents the Teacher's accumulated knowledge (constraints, environment rules) from being lost during code generation. If a single agent handled both, its constraint knowledge would compete with its code generation behavior in unpredictable ways.

### Dual-layer constraint injection

Environment rules must be enforced at both the instruction level (Teacher) and the execution level (Student). Early iterations only injected constraints into the Teacher's context. The Teacher would correctly write "use DynamoDB instead of RDS," but the Student, reading only the Teacher's prose, would still generate RDS code because the word "database" in the instructions triggered RDS in its training distribution. Hardcoding mandatory rules directly into the Student's system prompt resolved this.

## Component Design

### Teacher Agent (`generate.py`)

The Teacher is a DSPy `ChainOfThought` module with a custom `Signature` (`src/dspy_signatures.py`). It receives:

- The user's architectural intent (e.g., "three tier web app with security")
- AWS context from `src/data_loader.py`, which includes the contents of `learned_constraints.txt`
- ChromaDB query results for semantically relevant constraints

It outputs four fields: `prerequisites`, `use_case`, `core_instructions`, and `troubleshooting`. An Editor Agent (GPT-4o) reformats these into a clean markdown document (`FINAL_PROMPT.md`). The `generate.py` script then appends any unprocessed constraints from `learned_constraints.txt` verbatim to the bottom of the document under a `## Runtime Strict Constraints` header. This bypass ensures constraints survive the Editor's summarization step without information loss.

### Student Agent (`scripts/execute_prompt.py`)

The Student is a direct OpenAI API call (GPT-4o, temperature 0.0). It receives:

- A system prompt containing mandatory environment rules (hardcoded in `execute_prompt.py`)
- The Teacher's markdown prompt as user content

Three variants are generated concurrently. Each variant is validated with `ast.parse()` to confirm it defines a class inheriting from `Stack`, then checked with `flake8` for undefined names and import errors. The variant with the fewest errors is selected as the champion and injected into the CDK project directory.

The mandatory environment rules block includes:

```
- NEVER use aws_rds or DatabaseInstance. USE aws_dynamodb.Table.
- ALWAYS use Code.from_inline() for Lambda. NEVER use from_asset().
- ALWAYS use generic_linux() for EC2. NEVER use latestAmazonLinux or SSM lookups.
- ALWAYS use RemovalPolicy.DESTROY directly. NEVER use Stack.of(self).removal_policy.
- ALWAYS use SubnetType.PRIVATE_WITH_EGRESS. Never PRIVATE_WITH_NAT.
```

### Meta-Analyzer (`scripts/self_healing_optimizer.py`)

When `cdk synth` or `cdklocal deploy` fails, the orchestrator extracts the last 40 lines of stderr, filters out JSII `UserWarning` noise and `typeguard` protocol warnings, and sends the filtered trace to the Meta-Analyzer (GPT-4o).

The Meta-Analyzer's system prompt instructs it to produce exactly three outputs per failure:

1. A one-line description of what to change
2. A one-line description of the correct API usage
3. A code example block prefixed with `FIX FOR <construct>:`

These constraints are compared against existing entries in `learned_constraints.txt` using `difflib.SequenceMatcher`. If any new constraint has a similarity ratio above 0.98 with an existing line, it is discarded. Surviving constraints are appended to the file.

### ChromaDB Vector Store

ChromaDB (`chroma_db/`) stores static environment rules that persist across runs. It is seeded on first initialization with seven core constraints covering ALB imports, AMI lookups, subnet types, removal policies, Lambda asset paths, RDS keyword arguments, and the LocalStack RDS ban.

The Teacher queries ChromaDB for semantically similar documents based on the user's intent. Retrieved documents are injected into the DSPy context alongside `learned_constraints.txt` contents.

ChromaDB is not wiped between runs. `learned_constraints.txt` is wiped at the start of each run to prevent stale constraints from prior, unrelated intents.

### LocalStack Configuration

The LocalStack container must be running on port 4566 before the optimizer starts. The system verifies connectivity with a health check at startup.

The `cdklocal deploy` command sets the following environment variables:

```
AWS_ACCESS_KEY_ID=test
AWS_SECRET_ACCESS_KEY=test
AWS_DEFAULT_REGION=us-east-1
SERVICES=ec2,s3,dynamodb,lambda,apigateway,cloudformation,iam,ssm,sts,logs
```

The `SERVICES` variable is required because AWS CDK constructs trigger implicit service dependencies. For example, a VPC with `PRIVATE_WITH_EGRESS` subnets causes CloudFormation to look up NAT Gateway AMI IDs via SSM Parameter Store. Without `ssm` in the services list, this lookup fails even though the generated code never explicitly calls SSM.

## Convergence Behavior

In the most recent run (`run_1776108257`), the system produced the following score trajectory:

```
Iteration 0: 35/100 (synth failed, elbv2 import error)
Iteration 1: 35/100 (synth failed, SSM lookup in generated code)
Iteration 2: 70/100 (synth passed, deploy failed on implicit SSM)
Iteration 3: 70/100 (synth passed, deploy failed on implicit SSM)
Iteration 4: 70/100 (synth passed, deploy failed on implicit SSM)
Iteration 5: 70/100 (synth passed, deploy failed on implicit SSM)
Iteration 6: 70/100 (synth passed, deploy failed on implicit SSM)
Iteration 7: 35/100 (synth failed, InstanceTarget type error)
```

The 70/100 plateau from iterations 2 through 6 demonstrates that the code generation has converged on valid CDK v2 syntax. The generated code correctly uses DynamoDB (not RDS), inline Lambda (not from_asset), and standard RemovalPolicy imports. The remaining 30 points require the LocalStack `SERVICES` configuration to include `ssm`, which has been added to the deployment environment.

## Engineering Decisions

### Why not MIPROv2?

The codebase includes MIPROv2 imports and a `train()` function in `src/factory.py`. MIPROv2 is a Bayesian prompt optimizer that tests instruction variations against a metric function. It was not used in the active loop for two reasons:

1. MIPROv2 optimizes for a static dataset. The IaC problem has a dynamic feedback signal (compiler output) that changes every iteration.
2. The deterministic constraint injection approach (appending compiler-derived rules to the prompt) is more sample-efficient than probabilistic search over instruction space.

DSPy's `ChainOfThought` is used purely for its structured input/output signature, not for optimization.

### Why not a single agent?

A single agent that both reasons about constraints and generates code would conflate two competing objectives. When a single agent accumulates 15+ constraints in its context, its code generation quality degrades because the constraints compete for attention with the actual architectural instructions. The Teacher-Student split isolates constraint reasoning (Teacher) from code production (Student), and the hardcoded Student rules provide a guaranteed floor of environment compliance.

### Why was the Static Critic removed?

The Static Critic was an LLM agent positioned between code generation and compilation. It reviewed the generated code and rejected it if it "looked wrong." In practice, it caused three failure modes:

1. Rejecting valid code that used unfamiliar but correct CDK v2 APIs.
2. Approving code with subtle type errors that only the JSII runtime could catch.
3. Entering infinite loops where its suggestions contradicted the compiler's requirements.

Removing it and relying solely on physical compilation eliminated all three failure modes.

## Known Limitations

1. **No parallel compilation**: The working directory (`cdk-testing-ground/`) is shared across iterations. Parallel execution requires directory isolation per variant.
2. **Windows-specific process cleanup**: Orphaned `node.exe` processes are terminated via WMI queries. This logic does not work on Linux or macOS.
3. **Hardcoded Student rules are brittle**: If the target environment changes (e.g., switching to AWS CloudFormation instead of LocalStack), the Student's mandatory rules must be manually updated.
4. **No incremental learning across runs**: `learned_constraints.txt` is wiped per run. Constraints learned in one run do not carry over to the next. ChromaDB retains static rules but is not updated with runtime-learned constraints.
5. **Deduplication threshold sensitivity**: The 0.98 `SequenceMatcher` threshold was chosen empirically. At 0.80, semantically distinct constraints were incorrectly deduplicated. A production system should use embedding-based similarity rather than string matching.
6. **Temperature escalation is blunt**: When scores stagnate, the generation temperature increases by 0.1. This can cause the Student to produce more creative but less correct code. A more targeted response would be to modify the constraint set rather than the temperature.

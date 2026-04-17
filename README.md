# AWS SAM Evaluation Engine

This project defines a static evaluation pipeline for optimizing generated Infrastructure-as-Code schemas. The system utilizes DSPy MIPROv2 to Bayesian-search target parameter configurations capable of coercing language models to generate precise AWS Serverless Application Model architectures.

## Architecture Pipeline

1. The MIPROv2 optimizer selects a candidate instruction set.
2. The candidate instruction is parsed by a test language model (e.g. GPT-4o) to output a raw AWS SAM template.
3. The raw template is processed by a three-stage mechanical evaluation function.
    * `yaml.safe_load`: Confirms structure representation (+0.20).
    * `cfn-lint`: Parses against explicit AWS schemas to detect incorrect properties (+0.40).
    * `cfn-guard`: Validates against internal policy sets such as HIPAA configuration constraints (+0.40).
4. If an exception triggers during parsing, the exact error code queries the ChromaDB local storage base. Associated documentation snippets are mapped explicitly to the failure point and recursively passed to the generation model for a maximum of two automated retries.
5. Auto-correction executions incur an algorithmic subtraction mechanism (-0.10) penalizing prompt optimization efficiency parameters based directly on trial cost.
6. Instructions mapping to perfect 1.0 structural executions are exported natively as documentation schemas inside the `results/` block.

## Step 0: Environment Configuration

Before running any script logic, configure required system telemetry bounds. Duplicate the local configuration baseline into your primary execution route.

Ensure all variable data is assigned. 

```bash
cp .env.example .env
```

Review the `.env.example` structure directly:
* `OPENAI_API_KEY`: API authentication key required to power the primary verification model instance (e.g. sk-...).
* `OPENROUTER_API_KEY`: Optional fallback key utilized for dispatching test evaluation runs to distinct architectural platforms (e.g. sk-or-v1-...).

## Required Installation

Python 3.10 and explicitly bound target tools are required.

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

To function correctly, the native host system must include accessible system aliases pointing to the strict evaluation binaries.
* Execute `pip install cfn-lint` inside the virtual environment for linting coverage.
* Manually download or compile the `cfn-guard` execute object and attach it securely within `./venv/Scripts/cfn-guard.exe`.

## Execution Run Protocol

Populate the initial ruleset mappings via standard vector injection.

```bash
venv\Scripts\python.exe scripts/ingest_sam_docs.py
```

Begin standard parameter alignment:

```bash
venv\Scripts\python.exe scripts/optimize.py --auto medium
```

If previous evaluation data exists, initialize a stateful configuration recovery protocol by specifying the local resume parameter:

```bash
venv\Scripts\python.exe scripts/optimize.py --auto medium --resume
```

## Enterprise Security Compliance (`cfn-guard`)

This evaluation engine natively implements the [AWS Guard Rules Registry](https://github.com/aws-cloudformation/aws-guard-rules-registry) to enforce Tier-1 institutional compliance during the Bayesian generation loops.

By default, the engine provisions a core HIPAA boundary constraint checking S3 `BucketEncryption`. However, you can instantly replace this bound with any of the official AWS enterprise Conformance Packs by pulling their respective `.guard` files and pointing the `-r` flag natively inside `src/evaluators.py` to target them locally. 

The optimizer will natively evaluate tracebacks and punish/heal LLMs against:
* **PCI-DSS:** Mandates API Gateway TLS 1.2 minimums, strict RDS multi-AZ encryptions, and explicitly blocks public S3 ACLs.
* **NIST 800-53:** Government-grade strictness. Automatically bans wildcard `*` resource maps inside IAM Execution Roles.
* **CIS Foundations Benchmark:** General enterprise security baselines (e.g. CloudTrail regional orchestration requirements).
* **AWS Well-Architected Framework:** Automatically enforces Auto-Scaling, CloudFront edges, and X-Ray telemetry grid architectures on target topologies.

## Known Limitations & Future Work

1. Security Protocol Evasion: The evaluation script exclusively checks JSON syntax outputted by the generic lint binaries. A language model implicitly trained against the pipeline architecture could artificially generate output capable of tricking lint string pattern matching while fundamentally leaving the infrastructure fatally compromised.
2. Missing Physical Integration: The system validates code via `cfn-lint`. It explicitly does not invoke `sam deploy` against a target physical environment. Verification is inherently structural, not functional.
3. Dynamic Rule Injection: Currently, the pipeline maps explicit strings to predefined arrays inside the ingestion script. Production systems must execute automated web extraction processes directly indexing raw CloudFormation release patches to guarantee current reference validity.

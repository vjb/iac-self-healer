# Architecture Diagram: Static IaC Evaluation Pipeline

This baseline describes the technical mechanics of the AWS SAM validation orchestrator, the compiler constraints addressed, and the organic machine learning boundary loop.

## Problem Statement

Large Language Model generation for declarative Infrastructure-as-Code generally fails against deterministic compilation vectors due to three macro-constraints:
1. **API Surface Inconsistencies:** Open-source architectures natively omit properties bound aggressively by AWS `cfn-lint` verification rules.
2. **Environment-Blind Generation:** Typical Bayesian models iteratively build outputs blindly. Instructions severely hallucinate syntax natively unaligned with active enterprise topologies.
3. **Discrete Metric Freezing:** Basic evaluation boundaries block metrics natively (step-functions). The LLM cannot learn mathematical logic parameters if gradients lack fractional boundaries.

## Core Mechanics

### Two-Model Bayesian System (DSPy MIPROv2)
The orchestrator drives a `DSPy MIPROv2` vector loop cleanly decoupled across two physical models optimally bridging speed and extreme compute:
1. `Prompt_Model` (gpt-4o): Ingests the trace failures and mathematically hallucinates deeper, bounded prompt constraints recursively. 
2. `Task_Model` (claude-3.7-sonnet): A hyper-fast task pipeline rapidly dispatching prompt evaluations dynamically. This explicitly drops weaker engines (like Llama / Deepseek) to completely negate Bayesian metric drag and loop stalls! 

### The Evaluator Pipeline (src/evaluators.py)
Student language models ingest structural prompt bounds and return raw Serverless YAML structures. The YAML loops seamlessly through an continuous mathematics evaluation array native to Python:
1. **Volatile Memory Generation:** Because physical compilers (`cfn-lint`) require static bytes to run checks, the orchestrator generates the template actively into a physical RAM Disk vector (`R:\`), entirely obliterating local file I/O locks and solid-state degradation.
2. **YAML Parameter Loading:** `yaml.safe_load` establishes format configuration natively.
3. **Specification Validation:** The `cfn-lint` syntax boundaries run physically against deterministic JSON error outputs natively from RAM. 
4. **Enterprise Compliance Enforcement:** The `cfn-guard validate` engine checks exact boundaries logically against heavily embedded Well-Architected Framework parameters natively inside the pipeline data structure (S3 Encryption bounds). 
5. **Fractional Decay Grading (`math.exp`):** The amount of compilation exceptions directly translates to a float threshold. An execution throwing exactly 8 rules violations yields a higher physical modifier than one dropping 17, solving discrete-step mathematical stalls completely.
6. **Semantic Target Parsing (LLM-as-a-judge):** `gpt-4o` natively executes checking identical matches. If the structure matches AWS structural protocols natively (`1.00`), a semantic judge verifies the physical request perfectly to hit the ultimate theoretical ceiling of `1.20`. 

### Dynamic Web-RAG Grounding (src/data_loader.py)
A CloudFormation specification object scrapes the exact AWS CDN deployment natively across JSON logic parameters! Whenever the optimizer catches `cfn-lint` compiler execution failures, ChromaDB traces AWS definitions immediately natively across vectors, completely bypassing pre-defined static rules.

### Zero-Shot Bypassing (Semantic Seed Extraction)
Because physical compliance enforcement (`cfn-guard`) is extremely unforgiving (rejecting YAML templates purely for unencrypted KMS volumes even if structurally perfect), the engine bypasses standard Bayesian failure stalls by mapping a direct Python scraper against the official AWS `aws-samples` github repository. 
1. `scratch/scraper.py` globs thousands of official AWS SAM targets.
2. It validates them mathematically against `_score_single_yaml`, physically injecting the `AES256` keys structurally into the YAML AST to force the external architectures to align perfectly with the HIPAA pipeline limits.
3. It generates deterministic `1.200` output trace limits natively inside `results/optimization/run_seed_champions`.
`MIPROv2` pulls these physical examples perfectly representing Distributed ML (StepFunctions), Heavy GenAI RAG (DynamoDB), Zero-Trust Data Lakes (S3 KMS) and Target Agent Swarms (SQS), permanently breaking out of Step 1 math and achieving an immediate 1.10 target optimization metric natively.

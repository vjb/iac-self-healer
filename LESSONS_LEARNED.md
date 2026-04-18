# Institutional Learnings: SAM Declarative Migration
*Branch: `feature/sam-declarative-evaluation`*

This document tracks technical mechanics and structural engineering changes applied during the migration from the AWS CDK generator to a deterministic declarative SAM evaluation pipeline.

## 1. Post-Processing Middleware Over Prompt Constraint Enforcement
**The Problem:** The pipeline previously attempted to force generative models to output raw YAML payloads by writing strict string formats. Due to foundational RLHF training, the models frequently ignored syntax constraints, causing parsing loop failures.
**The Lesson:** A generative system is fundamentally unpredictable. Using prompt engineering to guarantee syntax stability is inefficient. 
**The Solution:** Deterministic middleware bounds were constructed outside the model logic. Mathematical validation was achieved by treating the output as raw data and parsing it via regex heuristic extraction (e.g., classifying all markdown blocks by byte length and extracting the largest chunk). 

## 2. Declarative Static Compilation Over Iterative Procedural Abstraction
**The Problem:** The legacy AWS CDK v2 generator utilized Python APIs relying on JSII Javascript mappings. The traceback errors from `cdk synth` were abstracted, creating invalid execution maps for subsequent retry bounds. 
**The Lesson:** Declarative structures (YAML/JSON) permit static inspection without allocating the dependency maps required for a fully instantiated computational tree. 
**The Solution:** By processing exclusively against AWS SAM templates, the output infrastructure configurations passed directly through `cfn-lint` and `cfn-guard`. This reduced validation latency and supplied the optimization models with deterministic resource properties.

## 3. Computational Fallbacks (YAML to JSON)
**The Problem:** Generative agents interchangeably output YAML format schemas and nested JSON strings when generating AWS target data. 
**The Lesson:** Forcing strict linguistic bounds wastes API cycles. YAML safely parses standard JSON objects natively. 
**The Solution:** The `evaluators.py` framework chains parsing exceptions. It captures outputs initially with `yaml.safe_load`. If sequence boundaries crash the interpreter, a `json.loads` fallback handles the string logic, then serialization converts the structure statically back to YAML for the SAM verification binaries.

## 4. Mechanical Checkpointing Over Static Storage
**The Problem:** Initial test executions overwrote active state parameters directly into the root directory. When optimization loops encountered unhandled exceptions, parameter loss occurred. 
**The Lesson:** Local filesystem memory within an execution boundary must be version-controlled, immutable, and partitioned from core logic. 
**The Solution:** Optimization checkpoints were securely isolated into sequential `results/optimization/run_[timestamp]/` directories. By establishing a `.optimizer_state.json` file synced to the `--resume` CLI parameter, the system maintains compounded execution runs without storing authentication tokens in execution paths.

## 5. Exposing Immutable Parameters Programmatically
**The Problem:** Generative models consistently failed `cfn-lint` validations on zero-shot executions because they omitted AWS configuration headers (e.g., `Transform: AWS::Serverless-2016-10-31`). 
**The Lesson:** Allocating parameter optimization cycles to generate standard boilerplate strings decreases efficiency. 
**The Solution:** By capturing the raw object natively inside the sanitization script, the process programmatically asserts that `AWSTemplateFormatVersion` applies recursively before compiler execution begins.

## 6. Flexible Heuristics Over Rigid Regex (Markdown Extraction)
**The Problem:** Generation models often append arbitrary text structures (e.g., formatting deployment guides physically preceding the actual architecture code). Extracting the primary logic block using absolute newline parameters (`\n`) failed against models injecting carriage returns (`\r\n`) and trailing whitespace.
**The Lesson:** Hardcoded regex boundaries exhibit high failure rates against unstructured language outputs. 
**The Solution:** A logical regex string (`r"```[a-zA-Z]*\s*(.*?)\s*```"`) utilizing wildcard whitespace (`\s*`) across the entire string length was applied. The process programmatically sorts the sequence array by byte-length descending, ensuring that the target object is systematically the largest declarative YAML payload extracted.

## 7. Compliance Rule Integration
**The Problem:** Generative agents failed strict AWS WAFR compliance bounds (such as `PublicAccessBlockConfiguration` on S3 resources) even when instructed to generate secure architectures because they lacked technical parameter bounds in context.
**The Lesson:** Enforcing enterprise compliance checks through generated instructions is unreliable against compiler verification.
**The Solution:** Mathematical `cfn-guard` scripts were physically mapped into the embedding vector context. Exposing the structural compiler boundaries directly inside the prompt payload ensures the models validate conditions dynamically prior to output generation.

## 8. Calibrating Execution Tiers for Declarative Synthesis
**The Problem:** The compilation loop operated against a 0.44 success threshold. Certain language models generated broken YAML topologies, logging continuous compilation exceptions into the Bayesian optimization vectors. 
**The Lesson:** Zero-shot autonomous configuration logic requires integration against optimized statistical inference weights.
**The Solution:** The pipeline execution parameters were modified to rely strictly on `anthropic/claude-3.7-sonnet` and `gpt-4o`. Removing underperforming processing engines eliminated wait states, scaling computation times and modifying the validation success metric boundary to `0.81`.

## 9. RAM Disk I/O Routing
**The Problem:** The pipeline design required creating thousands of recursive `template.yaml` files natively across the local SSD to pass schema payloads to external `cfn-lint` and `cfn-guard` processes, logging high I/O latency.
**The Lesson:** External compiled deterministic routines incur execution delays when bound against primary OS storage mediums. 
**The Solution:** The tempfile path generation script redirects execution templates directly into a RAM Disk partition (`R:\`). Because the entire evaluation sequence executes synchronously inside memory bounds, linter file-read latency dropped to near-zero margins.

## 10. Multi-Fidelity Oracle Execution (Phase 2 Integration)
**The Problem:** Structural prompt parameters successfully generated `cfn-lint` verified code, but physically crashed during dynamic validation due to open variable instantiations (e.g., `Parameters: VpcId` without default mappings). Static code evaluation fundamentally cannot verify physical execution targets dynamically.
**The Lesson:** A deterministic mathematical validation structure must execute both "static" rule checks and "physical" hardware compilation traces concurrently.
**The Solution:** A decoupled two-stage inference matrix handles validation logic. Phase 1 filters strictly against JSON/YAML schema definitions (fast loop). Phase 2 injects the surviving Champion parameters directly into an ephemeral LocalStack Pro Docker engine, logging native Boto3 target evaluation errors and mathematically recording them against the DSPy Vector database for deep hardware alignment bounds.

## 11. Unsupervised Semantic Fuzzing & Multi-Q Retrieval
**The Problem:** Standard Dense Vector architectures bias strictly toward lexical overlap. A dynamic query like `Target: Serverless Spec` would return core SAM specifications, but organically failed to retrieve strictly related hardware bounds (e.g., nested `WAFR Security Failures` or `cfn-lint Deprecation Violations`) absent within the query string syntax.
**The Lesson:** Unsupervised database analysis (`K-Means Silhouette Clustering`) mathematically confirmed that "Structural Specification constraints" geometrically deviate into entirely separate sub-clusters (`K=3`) from "Security Compiler Tracebacks". A standard `n_results=5` monolithic query natively suffers from topological blind spots.
**The Solution:** The RAG framework was structurally converted to a **Multi-Q Cross-Cluster Strategy**. Instead of running singular context limits, the optimizer dynamically forks the input intention array string into three explicit search modifiers (injecting explicit target labels like `CRITICAL COMPILER WARNING FAILED rules aws-wafr-conformance`). This forces standard AWS specs to seamlessly blend with strict compiler boundaries inside the vector extraction layer.

# Institutional Learnings: SAM Declarative Migration
*Branch: `feature/sam-declarative-evaluation`*

This document serves as an institutional knowledge base formalizing the critical mechanical, systemic, and structural engineering lessons learned during the migration from the AWS CDK orchestrator to a Tier-1 deterministic Declarative SAM evaluation pipeline.

---

## 1. Post-Processing Middleware > Prompt Constraint Enforcement
**The Problem:** We aggressively attempted to force stochastic LLMs (Claude, Llama-3, GPT-4o) to output pristine, raw YAML payloads by writing strict, verbose prompts (e.g., `"NEVER USE MARKDOWN CHUNKS"`). Because of foundational RLHF biases, the models frequently ignored this constraint, causing crippling `yaml.safe_load` loop failures.
**The Lesson:** A generative system is fundamentally unpredictable. Attempting to artificially guarantee stability purely through prompt engineering is fragile. 
**The Solution:** Build deterministic middle-ware bounds outside the model logic. We achieved mathematical validation guarantees by treating the output as raw noise and mathematically parsing it natively via Regex heuristic extraction (e.g., dynamically sorting all markdown blocks by byte length descending and extracting the largest chunk) and parsing the sequence actively. 

## 2. Declarative Static Compilation vs. Iterative Procedural Abstraction
**The Problem:** The legacy AWS CDK v2 generator utilized highly verbose Python APIs that relied on nested JSII Javascript mappings. The resulting traceback errors from `cdk synth` were wildly abstracted, misleading the optimizer models on subsequent retry bounds. 
**The Lesson:** Using declarative structures (YAML/JSON) allows native static inspection without building the dependency mapping of a fully instantiated computational tree. 
**The Solution:** By relying exclusively on AWS SAM templates, we securely piped the generated infrastructure graphs directly through `cfn-lint` and `cfn-guard`. This drastically reduced validation latency and supplied DSPy's semantic engine with deterministic, isolated resource properties immediately.

## 3. The Power of Computational Fallbacks (YAML to JSON)
**The Problem:** Generative agents interchangeably drift between generating pure conceptual YAML mappings and heavily fortified JSON strings when orchestrating AWS targets. 
**The Lesson:** Forcing specific linguistic bounds on an LLM wastes API cycles. YAML safely parses structural JSON bounds inherently. 
**The Solution:** Our `evaluators.py` framework chains exceptions safely, capturing raw outputs initially with `yaml.safe_load`. If sequence boundaries crash the interpreter, a `json.loads` fallback safely parses the JSON logic, then explicitly translates and serializes the state statically back to YAML for the SAM binaries, retaining complete architectural alignment safely.

## 4. Mechanical Checkpointing > Static Storage
**The Problem:** The initial iteration overwrote the active `optimized_factory.json` state aggressively into the root directory. When Bayesian optimization loops breached threshold variables or crashed natively, catastrophic parameter loss occurred. 
**The Lesson:** System memory within a generative execution boundary must be version-controlled, immutable, and strictly partitioned out of the codebase logic. 
**The Solution:** Optimization checkpoints were securely encapsulated directly into sequential `results/optimization/run_[timestamp]` storage. By establishing an automated `.optimizer_state.json` ledger mechanism synced natively to our `--resume` cli flags, the system achieves frictionless mathematical compounding without putting private secrets (such as `.env` mappings) natively at risk of truncation.

## 5. Exposing Immutable "Hidden" Parameters Programmatically
**The Problem:** LLMs consistently failed `cfn-lint` verification repeatedly on early zero-shot runs because they forget to prepend strict AWS-required headers (e.g., `Transform: AWS::Serverless-2016-10-31`). 
**The Lesson:** Never waste API training budget teaching an optimizer to add boilerplate strings. 
**The Solution:** By capturing the raw object natively inside our Sanitization Middleware, we execute constant mechanical checks ensuring `AWSTemplateFormatVersion` is applied recursively, completely bypassing unnecessary verification cycles for trivial syntax exclusions.

## 6. Flexible Heuristics vs. Rigid Regex (Markdown Extraction)
**The Problem:** Open-source models (like Llama 3.3) consistently hallucinate arbitrary multi-block structures (injecting ` ```bash ` deployment guides physically above the architecture configuration). Extracting just the "first" block fails. Our first attempt at extracting *all* blocks using rigid `\n` newline bounds crashed because RLHF models aggressively inject carriage returns (`\r\n`) and trailing spaces within their formatting boundaries.
**The Lesson:** Hardcoded regex boundaries instantly fracture against stochastic text generation. 
**The Solution:** We deployed a highly abstracted regex string (`r"```[a-zA-Z]*\s*(.*?)\s*```"`) utilizing wildcard whitespace (`\s*`) across the entire string length, extracted into an array. We then programmatically sorted the sequence array dynamically by byte-length descending, ensuring that the target extraction is systematically always the largest declarative YAML payload regardless of sequence position or hallucinated formatting constraints.

# Architecture: Compiler-in-the-Loop IaC Generation

This document describes the technical design of the target optimization system, the technical constraints it addresses, and the engineering details of the implementation.

## Problem Statement

Standard Large Language Model generation for Infrastructure-as-Code fails at three distinct levels:

1. API surface inconsistencies: Models produce CDK v1 syntax (e.g., core.RemovalPolicy), reference non-existent class attributes, or pass arguments with incorrect types (e.g., passing a string to a parameter requiring an array).
2. Environment-blind generation: Base instructions are often ambiguous regarding which imports or constructs to use. This results in the model relying on outdated training weights rather than specific framework documentation.
3. Unactionable feedback loops: Previous iterations of this architecture utilized a static LLM-based reviewer that analyzed the generated code prior to compilation. This resulted in an infinite loop where the reviewer would reject valid code or approve invalid code because it was predicting compiler behavior rather than evaluating a physical execution trace.

## Design Principles

### Physical Compilation as the Sole Validation Mechanism
No language model reviews or validates generated code. The feedback the system processes is the physical output of the `npx cdk synth` command (return code and stderr) alongside standard Python AST and linting tools (`ast.parse` and `flake8`). This removes recursive prediction errors and establishes a verifiable ground truth.

### Treating Prompts as Hyperparameters
Instead of fine-tuning model weights on specific infrastructure datasets, this system treats the instructional prompt templates as tunable hyperparameters. These hyperparameters are optimized using Bayesian search (MIPROv2) against a distinct physical compilation loss function.

## Component Design

### Prompt Generator Module (src/factory.py)
The orchestrator relies on a DSPy ChainOfThought module wrapped in a PromptFactory class. It ingests an architectural subset and corresponding CDK reference documentation to output a structured instructional document.

### Multi-Model Student Dispatcher (src/student.py)
To ensure the optimized prompt maintains robustness across different vendor architectures, the prompt is evaluated synchronously by multiple student evaluation models:
* Primary Evaluation: GPT-4o
* Secondary Evaluation: Claude 3.7 Sonnet, DeepSeek Chat, Llama 3.3 70B
Each evaluation model generates CDK Python code derived entirely from the candidate prompt.

### Physical Cost Function (src/evaluators.py)
Each student's generated output is processed through a sequential 5-stage pipeline:
1. `ast.parse()` check: Validates standard Python syntax (+0.10)
2. Stack class check: Verifies inheritance from the AWS CDK Stack base class (+0.10)
3. `flake8` execution: Evaluates undefined references and invalid imports (+0.10)
4. JSII Compilation Validation: The heavy `cdk synth` execution process (+0.50)
5. Resource validation: Counts CloudFormation resources to ensure structural completeness (+0.20)

### MIPROv2 Optimizer (scripts/optimize.py)
The system utilizes DSPy 3.1.3 native MIPROv2 functionality to bootstrap few-shot examples and conduct Bayesian optimization across candidate instructions. The mechanism evaluates the parameter space of system instructions and modifies prompts to produce structures that consistently output a 1.0 validation score.

### ChromaDB Reference Data (src/data_loader.py)
The system injects AWS CDK v2 documentation stored in a local ChromaDB instance to constrain generated instructions. Pre-populated data contains standard v1 to v2 migration structural changes, exact import paths, and AWS architectural specifications.

## Engineering Decisions

### Transitioning to Native DSPy 3.x
The project executes on Python 3.13 utilizing `dspy>=3.1.3`. This provides access to native module serialization (`.save()` and `.load()`), exact hyperparameter tuning controls (`num_trials`), and the standard Bayesian optimizer without requiring external workarounds or mock implementations.

### CloudFormation Synthesis Priority
Earlier iterations deployed infrastructure directly to an emulated environment. Testing implicit SDK calls and managing container timeouts degraded optimization efficiency. The `cdk synth` command performs exact dependency graph resolution, policy validation, and JSII transpilation. This yields a deterministic, zero-cost error signal at a significantly faster execution rate.

## Known Limitations & Future Work

1. Post-Deployment Execution Limitations: The system validates that code successfully compiles to a strict CloudFormation template. It does not deploy resources to AWS or monitor runtime operational status.
2. Environment Platform Dependencies: Orphaned `node.exe` processes originating from failed `cdk synth` execution runs are terminated using Windows Management Instrumentation (WMI) queries, limiting direct cross-platform execution of the evaluation scripts without modification.
3. Single-Tenant Concurrency Bottlenecks: The physical JSII compilation engine utilizes a shared `cdk.out` directory. This strictly prevents multi-threaded concurrent compilation checks within the same working directory. Production scaling requires dynamic isolated temporary directories for parallel evaluation.
4. Hardcoded Parameter Optimization: Currently, the pipeline assigns linear weights to the metric evaluation steps. Future iterations require dynamic gradient weighting where the evaluation pipeline heavily penalizes specific types of syntactic failures over linting anomalies.

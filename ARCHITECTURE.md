# Architecture: Compiler-in-the-Loop IaC Generation

This document describes the technical design of the IaC Self-Healer / Prompt Optimizer system, the problems it solves, and the engineering decisions behind its current implementation.

## Problem Statement

Standard LLM code generation for Infrastructure-as-Code fails at three distinct levels:

1. **API surface hallucination**: LLMs produce CDK v1 syntax (`core.RemovalPolicy`), reference non-existent class attributes, or pass arguments with incorrect types (`security_group=sg` instead of `security_groups=[sg]`).

2. **Environment-blind generation**: Instructions are often too vague on which imports or constructs to use, leading to assumptions based on outdated training data.

3. **Unactionable feedback loops**: Previous iterations of this system included an LLM-based "Static Critic" that reviewed generated code before compilation. This agent caused an infinite loop: it would reject valid code or approve invalid code because it was guessing compiler behavior rather than observing it.

## Design Principles

### Physical compilation as the sole oracle
No LLM agent reviews or validates generated code. The only feedback the system trusts is the literal output of `npx cdk synth` (return code and stderr) alongside standard Python tools (`ast.parse` and `flake8`). This eliminates hallucination loops and guarantees ground truth.

### Treating Prompts as Hyperparameters
Instead of fine-tuning models on code datasets, we treat the instructional prompts themselves as hyperparameters that can be optimized using Bayesian search (MIPROv2) against the physical compilation cost function. 

## Component Design

### Prompt Generator Module (`src/factory.py`)
The orchestrator is built purely around a DSPy `ChainOfThought` module wrapped in a `PromptFactory`. It takes an architectural intent and relevant CDK reference documentation to produce a highly structured instructional prompt.

### Multi-Model Student Dispatcher (`src/student.py`)
To ensure that an optimized prompt is robust across different foundation models, the prompt is evaluated by multiple "Student" LLMs:
- **Primary**: GPT-4o
- **Secondary**: Groq LLAMA 3.3 70B (free-tier, degrades gracefully)
Each student generates CDK code based on the candidate prompt.

### Physical Cost Function (`src/evaluators.py`)
Each student's generated code is passed through a 5-stage pipeline:
1. `ast.parse()` — syntax check (+0.10)
2. Stack class check — ensures correct inheritance (+0.10)
3. `flake8` — checks references and imports (+0.10)
4. `cdk synth` — the heavyweight physical JSII compilation oracle (+0.50)
5. Resource count — ensures structural richness (+0.20)

### MIPROv2 Optimizer (`scripts/optimize.py`)
We leverage DSPy 3.1.3's native `MIPROv2` to bootstrap few-shot examples and conduct Bayesian optimization over the instructions and selected demonstrations.
MIPROv2 probes the space of possible system instructions, pushing prompts towards producing CDK structures that consistently achieve a 1.0 score.

### ChromaDB Reference Data (`src/data_loader.py`)
The system grounds generated prompt instructions using actual CDK v2 documentation stored in ChromaDB. 
Pre-populated data includes common v1→v2 migration pitfalls, import paths, and official AWS architectural examples.

## Engineering Decisions

### Transitioning to DSPy 3.x
Earlier iterations relied on a mock/shim of DSPy or older versions. The project now explicitly runs on Python 3.13 with `dspy>=3.1.3` to access proper native object serialization (`.save()`/`.load()`), hyperparameter tuning parameters (`num_trials`), and the mature Bayesian optimizer under the hood without unstable workarounds.

### Deprecating LocalStack for Pure Synthesize
Earlier versions relied on `cdklocal deploy` to LocalStack. However, testing implicit SDK calls and dealing with container timeouts slowed down the optimizer. `cdk synth` already does full graph resolution, policy checking, and jsii transpilation—offering a highly robust zero-cost signal in far less time.

## Known Limitations

1. **CDK synth only**: We validate configuration but do not assert post-deployment runtime execution.
2. **Windows dependency**: Orphaned process cleanup is currently hard-coded using Windows `wmic`.
3. **Single-tenant execution**: The `cdk synth` process uses a shared `cdk.out` directory restricting safe multi-threaded concurrency of physical compilation checking itself.

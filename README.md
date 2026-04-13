# IaC Self-Healer

An autonomous multi-agent orchestration loop that generates, stress-tests, and self-heals AWS CDK infrastructure code using real-time reflection and syntax validation.

## The Concept

Generating Infrastructure-as-Code (IaC) with Large Language Models directly is notoriously brittle. Zero-shot prompting for AWS CDK frequently results in code that hallucinates outdated JSII imports, constructs invalid topological dependencies, or fails rigorous type-checking.

**IaC Self-Healer** flips this paradigm by shifting focus away from perfect generation and instead building a robust **Continuous Validation Gauntlet**.

### How it Works

The pipeline forces the AI to fight its way to a valid deployment:
1. **Generate**: A language model receives an intent (e.g., "three-tier web app") and generates a raw CDK string.
2. **Execute (The Gauntlet)**: The string is dynamically injected into an isolated scaffolding repository (`/cdk-testing-ground/`).
3. **Pummel**: The environment attempts to physically compile the infrastructure. It runs `flake8` for syntax, `npx cdk synth` to test JSII CloudFormation constraints, and deploys natively into a **LocalStack (Docker)** container using `cdklocal` to physically validate hardware allocation.
4. **Reflect**: If the local AWS environment crashes, the exact stack trace is extracted and verified against a **ChromaDB Lexicon RAG Engine**. A Meta-Analyzer agent deduces hyper-specific constraints based purely on the failure (e.g., `Never use aws_ec2.SubnetType.PRIVATE; you must use aws_ec2.SubnetType.PRIVATE_WITH_NAT instead.`).
5. **Score & Converge**: The orchestration loop scores fractional progress. It includes defensive ML traps:
    * **Kernel Kickstart Protocol:** If the score stagnates for 3 iterations, it physically overrides the LLM's `temperature` to shatter mathematical valleys.
    * **Topology Shrinkage Detection:** Using Python's `ast`, it tracks the total hardware component count. If the generator acts "lazy" by deleting infrastructure to bypass errors, it receives an instant -50pt penalty.

As a side-effect, the system natively aggregates this state transition trajectory (Prompt -> Crash Log -> Extracted Constraint -> Architecture Score) into an automatic RLHF (Reinforcement Learning from Human Feedback) dataset in `run_summary.json`.

## The DSPy "Inverse Prompt" Framework

IaC Self-Healer serves a dual purpose: rather than just synthesizing code, its root goal is utilizing the **Stanford DSPy Optimization framework** (`MIPROv2`) to mathematically compile the ultimate foundational prompts. 

Because Large Language Models interpret discrete English text (tokens) instead of continuous floating-point weights, you cannot natively perform a mathematical backward-pass "gradient descent" like in PyTorch. DSPy bridges this mathematical gap. Using Bayesian discrete optimization acting as a **simulated gradient**, the system intelligently bounces variations of multi-layered architectural templates through the Gauntlet until it structurally converges on the most mathematically optimal prompt configuration!

### Injecting Custom Prompt Libraries

The framework ships with an integration library bound to the `info/aws startup prompts/` directory. Rather than relying on rigid semantic constraints, you can seamlessly augment the Gauntlet by injecting your own internal architecture requirements!
1. Drop your complex structural Markdown architectures (e.g. `Serverless.md`, `EKS_Baseline.md`) directly into `info/aws startup prompts/`.
2. Run `venv\Scripts\python.exe -m src.factory` to re-execute the mathematical compiler.
3. The DSPy engine will mathematically assimilate the specific header definitions, context parameters, and topological constraints of your custom prompts and lock them into the static `optimized_factory.json` weights file for future zero-shot prompt generations!

## System Architecture

*   **Next.js Dashboard (`/ui/`):** A real-time visual interface bridging Server-Sent Events (SSE), allowing you to monitor the validation loop, trace compilation failures, and map LocalStack resources.
*   **Orchestration Engine (`scripts/self_healing_optimizer.py`):** The primary sub-process router that handles lockfiles, telemetry tracing, JSON logging, and API limit mechanics.
*   **Validation Gauntlet & LocalStack (`cdk-testing-ground/`):** The localized AWS Docker environment. Native execution of Python AWS CDK v2 and physical network graph simulations.

## Installation & Setup

**Prerequisites:**
*   Python 3.8+
*   Node.js (for AWS CDK `npx` execution)
*   An active `OPENAI_API_KEY` for the Meta-Analyzer reflection loop

**Backend Setup:**
```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```
*Create an `.env` file at the root repository containing your `OPENAI_API_KEY=...`*

**Frontend Dashboard Setup:**
```bash
cd ui
npm install
npm run dev
```

## Running the Engine

1. Boot the frontend using `npm run dev` and navigate to `localhost:3000`.
2. Input an architectural intent and initialize the factory.
3. The server will automatically spin up isolated directories under `results/learning_loop/run_<timestamp>/` for telemetry aggregation.
4. If you wish to terminate the search space early, tap "Halt Factory" to gracefully spin down the threading locks and save the existing trace constraints.

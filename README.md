# IaC Self-Healer

An autonomous multi-agent orchestration loop that generates, stress-tests, and self-heals AWS CDK infrastructure code using real-time reflection and syntax validation.

## The Concept

Generating Infrastructure-as-Code (IaC) with Large Language Models directly is notoriously brittle. Zero-shot prompting for AWS CDK frequently results in code that hallucinates outdated JSII imports, constructs invalid topological dependencies, or fails rigorous type-checking.

**IaC Self-Healer** flips this paradigm by shifting focus away from perfect generation and instead building a robust **Continuous Validation Gauntlet**.

### How it Works

The pipeline forces the AI to fight its way to a valid deployment:
1. **Generate**: A language model receives an intent (e.g., "three-tier web app") and generates a raw CDK string.
2. **Execute**: The string is dynamically injected into an isolated scaffolding repository (`/cdk-testing-ground/`).
3. **Pummel**: The environment attempts to physically compile the infrastructure. It runs `flake8` for syntax, `npx cdk synth` to test JSII CloudFormation constraints, and `pytest` paired with `moto` to mock live deployment.
4. **Reflect**: If the local AWS environment crashes, the exact stack trace is extracted and passed to a Meta-Analyzer agent. The agent deduces hyper-specific constraints based purely on the failure (e.g., `Never use aws_ec2.SubnetType.PRIVATE; you must use aws_ec2.SubnetType.PRIVATE_WITH_NAT instead.`).
5. **Converge**: The orchestration loop re-runs generation with the new accumulated constraints injected. This loops continuously, scoring fractional progress until the blueprint cleanly synthesizes a valid AST.

As a side-effect, the system natively aggregates this state transition trajectory (Prompt -> Crash Log -> Extracted Constraint -> Score Delta) into an automatic RLHF (Reinforcement Learning from Human Feedback) parameter dataset in the `run_summary.json` file.

## System Architecture

*   **Next.js Dashboard (`/ui/`):** A real-time visual interface bridging Server-Sent Events (SSE) from the orchestration engine, allowing you to monitor the validation loop, trace compilation failures, and safely halt the backend.
*   **Orchestration Engine (`scripts/self_healing_optimizer.py`):** The primary threaded sub-process router that handles lockfiles, telemetry tracing, JSON logging, and API execution logic.
*   **Validation Gauntlet (`cdk-testing-ground/`):** The localized AWS environment where Python execution, CDK JSII verification, and `moto` mock testing takes place.

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

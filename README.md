# IaC Self-Healer

An autonomous orchestration loop that generates, compiles, and reiterates AWS CDK infrastructure code using runtime validation.

## Architecture Concept

Generating Infrastructure-as-Code (IaC) via zero-shot Large Language Models frequently results in invalid dependency topological structures or outdated JSII constructs. 

**IaC Self-Healer** resolves this by executing a continuous validation pipeline. 

### Execution Workflow

The system enforces structural validity through the following discrete steps:
1. **Generate**: The system dynamically generates Python CDK code based on the user's architectural intent.
2. **Execute**: The artifact is injected into an isolated directory (`/cdk-testing-ground/`).
3. **Compile**: The directory triggers native dependencies to validate the code.
    * `flake8` executes static syntax checking.
    * `npx cdk synth` evaluates JSII constraints and generates CloudFormation.
    * The CDK stack deploys directly into a LocalStack Docker container to validate service provisioning.
4. **Reflect**: If compilation crashes, the literal stack trace is extracted and verified against a ChromaDB storage layer. A specialized DSPy script deduces strict constraints based entirely on the compiler failure.
5. **Evaluate**: The orchestrator scores progress. Current parameters include:
    * **Temperature Override Logic**: If generation scores stagnate over 3 consecutive iterations, the system adjusts the underlying temperature parameter to avoid local minima.
    * **AST Component Validation**: The system uses the Python `ast` module to tally deployed hardware elements. If the generator attempts to bypass syntax errors by omitting required infrastructural resources, it applies a -50 point adjustment.

The iteration states (Prompt, Crash Log, Constraint, and Score) are logged mathematically via JSON inside `run_summary.json` for potential reinforcement learning datasets.

## The DSPy "Inverse Prompt" Framework

Instead of merely generating execution code, this repository relies on the Stanford DSPy Optimization framework (`MIPROv2`) to mathematically compile foundational prompts. 

Because LLMs do not utilize continuous weight distributions for text generation, performing a traditional differentiable backward sweep is geometrically impossible. The framework circumvents this layout by using Bayesian discrete optimization. This acts as a simulated gradient, methodically testing architectural prompt variations against the compiler until it discovers stable patterns.

### Custom Prompt Ingestion

The repository supports mapping internal documentation directly into the generation layer.
1. Place standard markdown architectures (e.g., `Serverless.md`, `EKS_Baseline.md`) under `info/aws startup prompts/`.
2. Execute `venv\Scripts\python.exe -m src.factory` to re-compile the optimization layer.
3. DSPy will assimilate explicit constraint dependencies from the documents and lock them into `optimized_factory.json`.

## System Overview

*   **Next.js Dashboard (`/ui/`)**: A client-side web interface using Server-Sent Events to render compilation telemetry.
*   **Orchestration Logic (`scripts/self_healing_optimizer.py`)**: Sub-process logic orchestrating lockfiles and API rate limits.
*   **Testing Directory (`cdk-testing-ground/`)**: Windows native AWS execution environment hooked to the Docker daemon.

## Installation

### Step 0: Environment Configuration
Duplicate `.env.example` into a local `.env` file at the root repository. Populate all keys, notably defining your endpoint API structure and your LocalStack API token.

### Backend Requirements
*   Python 3.8+
*   Node.js (For the underlying V8 engine utilized by AWS CDK JSII wrappers)
*   Docker Desktop running natively

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### Dashboard Initialization
```bash
cd ui
npm install
npm run dev
```

## Running the Engine

1. Execute `npm run dev` and navigate to `localhost:3000`.
2. Provide standard text intent and instantiate the compiler logic.
3. System logs dynamically push to `results/learning_loop/run_<timestamp>/` folders.
4. If manual termination is required, invoke the cancellation flag on the UI to gracefully spin down the threading locks.

## Extensibility & Throughput Scaling

Because DSPy validation physically instruments dependent architecture binaries rather than purely virtual simulations, execution throughput is strictly bottlenecked by the compiler layer (`cdk synth` and Docker daemons) rather than LLM token streaming.

### Phase 1: Local Environment Constraints (Laptop)
*   **Docker Subsystem Overrides**: The default Docker Desktop resource allocations (used by LocalStack) constrain deployment IO. Increment allocated local memory limits to >=8GB and force allocation of all available CPU cores.
*   **Groq API Subsystem Replacement**: While current documentation points to `openai/gpt-4o`, migrating the native backend API target from OpenAI endpoints to internal Llama3 Groq LPU endpoints drastically reduces TTFT (Time-To-First-Token) bottlenecks on the generative execution phase. 

### Phase 2: High-Performance Infrastructure Deployment (Google Cloud)
*   **Avoid Serverless Topologies**: Cloud Run or Cloud Functions are insufficient due to ephemeral disk scaling limits when utilizing heavy NPM package caching alongside isolated Docker daemons.
*   **Compute Engine (IaaS)**: The most straightforward scale configuration employs dedicated high-CPU standard instances (e.g., GCP `c3` or `n2d-standard-32`). This allows for maximum parallel ThreadPool configuration. 
*   **GKE Batch Processing (Containerized Loop)**: For optimal scale, the `cdk-testing-ground` should be extracted from local runtime into standalone Kubernetes batch execution jobs. This isolates file-lock conflicts concurrently, allowing hundreds of architecture proposals to compile within horizontal nodes against dedicated Kubernetes LocalStack StatefulSets.

## Known Limitations & Future Work

1. **Child Daemon Locking**: The system currently terminates orphaned `node.exe` processes executing `cdk` wrappers using Windows native WMI logic to bypass directory access locking. Long-term production requires executing the testing loops in completely containerized sandbox instances rather than directly on the host machine.
2. **Ephemeral Hardware Storage**: LocalStack resets the infrastructure entirely between deployments (zero-state hygiene). There is no incremental caching.
3. **Sequential Processing**: Prompt variant linting and evaluation currently execute synchronously in specific execution loops, creating local CPU-bound bottlenecks on lower-spec machines.

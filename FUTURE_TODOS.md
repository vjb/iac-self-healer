# Future Architectural Roadmap

This document outlines structural limitations, technical debt, and required architectural expansions for future engineering cycles.

## 1. Immutable DSPy Weights State Management
**Current State:** 
The optimization pipeline outputs a single `optimized_factory.json` directly into the project root. Successive runs implicitly overwrite previous baseline logic, creating a volatile production state inherently vulnerable to catastrophic forgetting during deep Bayesian optimization loops.

**Required Action:** 
- Reroute the `compiled.save()` logic inside `src/factory.py` to deposit the parameters inside the isolated `results/optimization/run_[ID]` directories natively alongside their execution logs.
- Implement a physical configuration alias (e.g. symlinks, or a `CHAMPION_RUN_ID` constant within the `.env` mapping) inherently connected to the `--resume` execution parameter. This ensures the optimizer seamlessly extracts and compounds parameters from specific, versioned historical runs instead of blindly pulling from a single static root file.

## 2. Dynamic Policy Extraction Integration
**Current State:** 
AWS SAM rule topologies are populated statically during the ingestion script via offline markdown definitions (`scripts/ingest_sam_docs.py`). As native AWS schemas evolve, the compiler pipeline will enforce deprecated architectural bounds.

**Required Action:** 
- Engineer an automated web extraction process integrating natively directly into the AWS CloudFormation Resource Specification repositories.
- Automate vector refresh sequences dynamically on container boot to ensure semantic search queries are mathematically identical to active AWS release constraints.

## 3. Structural Binary Dependency Packaging
**Current State:** 
The pipeline requires manual `$PATH` configurations for physical lint executables (`cfn-lint`, `cfn-guard`), causing baseline synchronization anomalies and failing stage validations when executing across disparate host clusters.

**Required Action:** 
- Finalize the continuous integration environment by orchestrating an explicit `docker-compose.yml` baseline incorporating binary dependencies securely into an Alpine runtime envelope.

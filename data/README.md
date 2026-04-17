# IaC Data Directory

This directory contains the baseline JSON training intents and the AWS Well-Architected Framework Reliability rules utilized by the dynamic evaluation pipeline.

## Directory Contents

### 1. `training_intents.json`
This dataset maps the baseline architecture targets passed into DSPy. It includes configuration intents for cloud architectures such as Multi-Region RAG Backends and Data Lakes. These targets are parsed by the `cfn-lint` and `cfn-guard` evaluators to set prompt weights.

### 2. `aws-wafr-conformance-pack.guard`
This `.guard` file contains declarative boundary rules defined by the [AWS Well-Architected Framework Reliability (WAFR) Pillar](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/reliability.html).

The rules are injected into the pipeline context during inference via `src/data_loader.py` to enforce compliance constraints (e.g., `PublicAccessBlockConfiguration` for S3) prior to template generation.

---

## Expanding cfn-guard Integration

To extend compliance coverage to systems such as HIPAA, PCI-DSS, or NIST 800-53, standard AWS security patterns can be loaded into this directory.

**Reference Documentation:**
* **Official AWS cfn-guard Documentation:** [CloudFormation Guard User Guide](https://github.com/aws-cloudformation/cloudformation-guard)
* **AWS Guard Rule Registry:** [AWS Guard Rules Repository](https://github.com/aws-cloudformation/aws-guard-rules-registry)
* **Writing Custom Rules:** [Guard DSL Syntax](https://docs.aws.amazon.com/cfn-guard/latest/ug/writing-rules.html)

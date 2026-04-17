# 📂 Autonomous IaC Data Store

This directory acts as the structural baseline for your agentic DSPy framework. It physically provides the foundational **Training Intents** and **Zero-Trust Compliance Bounds** required to teach the agents how to generate valid, highly secure AWS SAM declarative infrastructure.

## Directory Contents

### 1. `training_intents.json`
This is the core training dataset ingested into DSPy. It maps 4 "Mega Intents" representing advanced cloud architectures (e.g., *Multi-Region RAG Backend*, *Zero-Trust Data Lake*) that the `cfn-lint` and `cfn-guard` evaluators use to optimize the RAG Prompt Weights.

### 2. `aws-wafr-conformance-pack.guard`
This is your **Physical WAFR Oracle**. Normally, LLMs passively hallucinate infrastructure designs without any concept of enterprise security. This `.guard` file contains absolute, natively compiled deterministic boundary rules driven by the [AWS Well-Architected Framework Reliability (WAFR) Pillar](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/reliability.html).

By injecting this directly into the vector RAG via `src/data_loader.py`, you force the student LLMs to mathematically "see" the exact boundary checks (like `PublicAccessBlockConfiguration` for S3) *before* they generate, entirely eliminating blind structural security traps.

---

## 🛡️ Expanding the `cfn-guard` Engine

The `aws-wafr-conformance-pack.guard` file here is just the beginning. 

If you want to seamlessly expand your autonomous agent's capabilities to natively handle compliance systems like **HIPAA**, **PCI-DSS**, or **NIST 800-53**, you can download official pre-written security `.guard` patterns directly from the Amazon Web Services registry!

**Helpful Links & Documentation:**
* **Official AWS cfn-guard Documentation:** [CloudFormation Guard User Guide](https://github.com/aws-cloudformation/cloudformation-guard)
* **AWS Guard Rule Registry:** [AWS Guard Rules Repository](https://github.com/aws-cloudformation/aws-guard-rules-registry) -> Contains hundreds of official enterprise-grade rules you can directly paste into this `data` folder to automatically harden your LLMs.
* **Writing Custom Rules:** [Guard DSL Syntax](https://docs.aws.amazon.com/cfn-guard/latest/ug/writing-rules.html)

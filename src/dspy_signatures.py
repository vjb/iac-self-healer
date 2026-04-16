import dspy


class CDKPromptGenerator(dspy.Signature):
    """Generate a detailed instructional prompt that guides any AI assistant
    to produce valid, production-ready AWS CDK v2 Python code."""
    
    architecture_intent = dspy.InputField(
        desc="High-level description of the desired AWS infrastructure."
    )
    cdk_reference = dspy.InputField(
        desc="Relevant AWS CDK v2 API documentation, import paths, and known pitfalls."
    )
    
    prompt = dspy.OutputField(
        desc="A complete, structural, single-shot instructional prompt in markdown format instructing an AI to build an AWS CDK v2 project. "
             "CRITICAL STRICT RULE: YOU MUST NEVER generate, write, or include actual raw Python/CDK code blocks (e.g. ````python ... ````) inside this prompt. "
             "Instead, you must describe what to do using structural requirements and strict constraints. "
             "The prompt MUST exactly follow this section layout: \n"
             "1. Title / Objective\n"
             "2. Requirements (Numbered list of architecture components)\n"
             "3. Critical Implementation Requirements / Constraints (Strict rules on what API classes or patterns the Agent MUST use or MUST avoid. Use your CDK reference knowledge here)\n"
             "4. Expected Deliverables (e.g. valid Python Stack class)\n"
             "5. Common Issues to Avoid (Address CDK v1 to v2 migration pitfalls)\n"
             "6. Success Criteria"
    )

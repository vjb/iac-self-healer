import dspy


class SAMPromptGenerator(dspy.Signature):
    """Generate a detailed instructional prompt that guides any AI assistant
    to produce valid, production-ready AWS SAM declarative architectures."""
    
    architecture_intent = dspy.InputField(
        desc="High-level description of the desired AWS infrastructure."
    )
    sam_reference = dspy.InputField(
        desc="Relevant AWS SAM documentation, CloudFormation properties, and known strict pitfalls."
    )
    
    prompt = dspy.OutputField(
        desc="A complete, structural, single-shot instructional prompt in markdown format instructing an AI to build an AWS SAM template. "
             "CRITICAL STRICT RULE: YOU MUST NEVER generate, write, or include actual raw YAML or JSON blocks (e.g. ````yaml ... ````) inside this prompt. "
             "Instead, you must describe what to do using structural requirements and strict constraints. "
             "The prompt MUST exactly follow this section layout: \\n"
             "1. Title / Objective\\n"
             "2. Requirements (Numbered list of architecture components)\\n"
             "3. Critical Implementation Requirements / Constraints (Strict rules on what API classes or patterns the Agent MUST use or MUST avoid. Use your SAM reference knowledge here)\\n"
             "4. Expected Deliverables (e.g. valid AWS SAM YAML template)\\n"
             "5. Common Issues to Avoid (Address explicit cfn-lint definitions)\\n"
             "6. Success Criteria"
    )

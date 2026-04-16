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
        desc="A complete, self-contained instructional prompt in markdown format. "
             "Must include: Prerequisites section listing required tools (Python 3.8+, "
             "Node.js 20+, AWS CDK v2); Architecture Overview describing each AWS service "
             "and how they connect; Step-by-Step Instructions referencing exact CDK v2 "
             "construct class names and their parameters; Import Statements section showing "
             "correct `from aws_cdk import ...` paths; Configuration Parameters with specific "
             "values for instance types, subnet masks, timeouts, etc.; Common Pitfalls section "
             "covering CDK v1 vs v2 differences; and Troubleshooting section with error messages "
             "and their fixes. The prompt must work with any AI assistant (ChatGPT, Claude, etc) "
             "to produce a single valid Python file defining a Stack class."
    )

import dspy

class AWSPromptGenerator(dspy.Signature):
    intent = dspy.InputField(desc="The core infrastructure requirement.")
    aws_strict_context = dspy.InputField(desc="Strict CDK v2 and Boto3 syntax rules to enforce.")
    
    prerequisites = dspy.OutputField(desc="A brief summary of tools required. Do NOT output any code here.")
    use_case = dspy.OutputField(desc="High level business use case. Do NOT output any code here.")
    core_instructions = dspy.OutputField(desc="Pure, functional AWS CDK v2 Python code implementation. MUST be 100% valid Python code without any markdown or conversational text.")
    troubleshooting = dspy.OutputField(desc="Common pitfalls and solutions in natural language. Do NOT output any code here.")

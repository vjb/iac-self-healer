import dspy

class AWSPromptGenerator(dspy.Signature):
    intent = dspy.InputField(desc="The core infrastructure requirement.")
    aws_strict_context = dspy.InputField(desc="Strict CDK v2 and Boto3 syntax rules to enforce.")
    
    prerequisites = dspy.OutputField()
    use_case = dspy.OutputField()
    core_instructions = dspy.OutputField(desc="Copy-paste ready prompt requesting explicit CDK code.")
    troubleshooting = dspy.OutputField()

import dspy

class AWSPromptGenerator(dspy.Signature):
    intent = dspy.InputField(desc="The core infrastructure requirement.")
    aws_strict_context = dspy.InputField(desc="Strict CDK v2 and Boto3 syntax rules to enforce.")
    
    prerequisites = dspy.OutputField(desc="A brief summary of tools required. Do NOT output any code here.")
    use_case = dspy.OutputField(desc="High level business use case. Do NOT output any code here.")
    master_prompt_instructions = dspy.OutputField(desc="A robust, natural language instructional prompt for a human developer. Describe the architecture, parameters, and layout. Absolutely NO full code scripts allowed. You may use small snippets to disambiguate complex attributes.")
    troubleshooting = dspy.OutputField(desc="Common pitfalls and solutions in natural language. Do NOT output any code here.")

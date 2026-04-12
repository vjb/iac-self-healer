import os
import dspy

def load_aws_reference_prompts():
    examples = []
    # Using absolute or reliable relative pathing based on execution dir being root
    prompts_dir = os.path.join(os.getcwd(), "info", "aws startup prompts")
    
    if not os.path.isdir(prompts_dir):
        return examples
        
    for filename in os.listdir(prompts_dir):
        if filename.endswith(".md"):
            filepath = os.path.join(prompts_dir, filename)
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            intent = filename.replace('.md', '')
            examples.append(dspy.Example(
                intent=intent,
                core_instructions=content,
                prerequisites="",
                use_case="",
                troubleshooting=""
            ).with_inputs('intent'))
    return examples

def get_aws_context():
    context = ""
    info_dir = os.path.join(os.getcwd(), "info")
    if not os.path.isdir(info_dir):
        return context
        
    for filename in os.listdir(info_dir):
        if filename.endswith(".txt"):
            filepath = os.path.join(info_dir, filename)
            with open(filepath, 'r', encoding='utf-8') as f:
                context += f"\n=== {filename} ===\n"
                context += f.read()
    return context

import argparse
import dspy
from src.factory import PromptFactory
from src.data_loader import get_aws_context

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--intent", type=str, required=True, help="The core infrastructure requirement.")
    parser.add_argument("--temperature", type=float, default=0.5, help="Temperature for generative randomness.")
    parser.add_argument("--output_file", type=str, default="", help="Specific filepath destination to write FINAL_PROMPT output to.")
    args = parser.parse_args()
    
    import os
    from dotenv import load_dotenv
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    lm = dspy.LM('openai/gpt-4o', api_key=api_key, temperature=args.temperature)
    dspy.configure(lm=lm)
    
    factory = PromptFactory()
    try:
        factory.load("optimized_factory.json")
    except Exception:
        pass
        
    context = get_aws_context()
    
    context = get_aws_context()
    topology_locked_intent = args.intent + "\\nCRITICAL TOPOLOGY LOCK: You must retain the underlying topological architecture defined within the user intent. Maintain the fundamental architecture intent.\\nCRITICAL SAM SYNTAX LOCK: You must strictly adhere to AWS SAM YAML syntax. Use Transform: AWS::Serverless-2016-10-31."
    prediction = factory(intent=topology_locked_intent, aws_strict_context=context)
    
    print("DEBUG PREDICTION FIELDS:", dir(prediction))
    raw_payload = f"""
    RAW_PREREQUISITES: {getattr(prediction, 'prerequisites', '')}
    RAW_USE_CASE: {getattr(prediction, 'use_case', '')}
    RAW_TROUBLESHOOTING: {getattr(prediction, 'troubleshooting', '')}
    RAW_MASTER_PROMPT: {getattr(prediction, 'master_prompt_instructions', getattr(prediction, 'core_instructions', ''))}
    """

    EDITOR_MEGA_PROMPT = """You are the "Strict Documentation & Formatting Editor" in an autonomous AWS SAM YAML optimization pipeline.
Your only job is to review the output of the "Generator Agent" and aggressively fix any formatting violations before the final Prompt is published. 

CRITICAL RULES OF ENGAGEMENT:
1. TEXT FIELDS MUST BE 100% ENGLISH: The Prerequisites, Use Case, and Troubleshooting fields MUST NOT contain any Python syntax.
2. NO MASSIVE CODE DUMPS: The `cleaned_master_prompt` field must be a robust, natural language instructional prompt. DO NOT output the full AWS SAM YAML template. Use bullet points to describe constraints and architecture layout. You may include tiny snippets (1-2 lines) to disambiguate complex attributes, but absolutely forbid massive code blocks.
3. FIX, DO NOT REJECT: Do not tell the user what is wrong; just fix it.

OUTPUT FORMAT:
You must output exclusively in valid JSON format matching the exact structure below. Do not include markdown formatting like ```json.
{
  "cleaned_prerequisites": "A comma-separated plain English list of tools required.",
  "cleaned_use_case": "A 2-sentence executive summary in plain text without any code.",
  "cleaned_troubleshooting": "A simple plain-text bulleted list of common pitfalls.",
  "cleaned_master_prompt": "Highly summarized natural language instructional guidelines. No big code blocks.", 
  "changes_made": "A brief internal note on what you fixed."
}"""

    import requests
    import json
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": EDITOR_MEGA_PROMPT},
            {"role": "user", "content": raw_payload}
        ],
        "response_format": { "type": "json_object" },
        "temperature": 0.1
    }
    
    try:
        resp = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
        resp.raise_for_status()
        cleaned_data = json.loads(resp.json()['choices'][0]['message']['content'])
    except Exception as e:
        cleaned_data = {
            "cleaned_prerequisites": getattr(prediction, 'prerequisites', ''),
            "cleaned_use_case": getattr(prediction, 'use_case', ''),
            "cleaned_troubleshooting": getattr(prediction, 'troubleshooting', ''),
            "cleaned_master_prompt": getattr(prediction, 'master_prompt_instructions', getattr(prediction, 'core_instructions', ''))
        }

    # Mechanically inject physical strict constraints to bypass LLM summarization.
    strict_constraints_block = ""
    try:
        import os
        pwd_constraints = os.path.join(os.getcwd(), "learned_constraints.txt")
        if os.path.exists(pwd_constraints):
            with open(pwd_constraints, "r", encoding="utf-8") as rf:
                strict_constraints_block = "\\n## Runtime Strict Constraints\\n" + rf.read()
    except Exception:
        pass

    output = f"""# AWS Prompt Output
## Prerequisites
{cleaned_data.get('cleaned_prerequisites', '')}

## Use Case
{cleaned_data.get('cleaned_use_case', '')}

## Instructions
{cleaned_data.get('cleaned_master_prompt', '')}

## Troubleshooting
{cleaned_data.get('cleaned_troubleshooting', '')}
{strict_constraints_block}
"""
    out_file = args.output_file if args.output_file else "FINAL_PROMPT.md"
    with open(out_file, "w", encoding='utf-8') as f:
        f.write(output)
        
    import logging
    logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(asctime)s - %(message)s')
    logger = logging.getLogger(__name__)
    logger.info("Generation complete. Output allocated to %s", out_file)

if __name__ == "__main__":
    main()

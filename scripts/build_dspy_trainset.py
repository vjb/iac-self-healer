import os
import glob
import json
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

PROMPTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "aws_official_prompts")
OUTPUT_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "bootstrap_trainset.json")

def build_trainset():
    if not os.path.exists(PROMPTS_DIR):
        logging.error(f"Prompts directory not found at: {PROMPTS_DIR}")
        return

    md_files = glob.glob(os.path.join(PROMPTS_DIR, "*.md"))
    logging.info(f"Found {len(md_files)} AWS Champion Prompts.")

    training_examples = []

    for file_path in md_files:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if not content:
                    continue
                
                # DSPy standardizes examples around dict structures that get mapped into `dspy.Example`
                training_examples.append({
                    "intent": content
                })
                logging.info(f"Ingested -> {os.path.basename(file_path)}")
        except Exception as e:
            logging.error(f"Failed to process {file_path}: {e}")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(training_examples, f, indent=4)

    logging.info(f"SUCCESS: Exported MiproV2 dataset ({len(training_examples)} entries) to {OUTPUT_FILE}")
    logging.info('You can map these records to DSPy in the optimizer using: [dspy.Example(**row).with_inputs("intent") for row in dataset]')

if __name__ == "__main__":
    build_trainset()

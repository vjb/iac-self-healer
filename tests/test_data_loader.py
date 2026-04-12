import pytest
from src.data_loader import load_aws_reference_prompts, get_aws_context

def test_load_aws_reference_prompts():
    examples = load_aws_reference_prompts()
    assert len(examples) > 0
    
    first = examples[0]
    assert hasattr(first, 'intent')
    assert hasattr(first, 'core_instructions')

def test_get_aws_context():
    context = get_aws_context()
    assert len(context) > 0
    assert "boto3-sns-deep.txt" in context

import pytest
from src.evaluators import continuous_aws_metric

class MockPrediction:
    def __init__(self, core_instructions="", prerequisites="", use_case="", troubleshooting=""):
        self.core_instructions = core_instructions
        self.prerequisites = prerequisites
        self.use_case = use_case
        self.troubleshooting = troubleshooting

def test_evaluator_broken_code():
    pred = MockPrediction(core_instructions="invalid code")
    score = continuous_aws_metric(None, pred)
    assert score < 0.3

def test_evaluator_valid_code():
    pred = MockPrediction(
        core_instructions="import aws_cdk as cdk",
        prerequisites="Prerequisites",
        use_case="Use Case",
        troubleshooting="Troubleshooting"
    )
    score = continuous_aws_metric(None, pred)
    assert score > 0.8

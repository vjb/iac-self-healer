import pytest
from unittest.mock import patch, MagicMock
from src.evaluators import _score_single_yaml

def test_yaml_structure_failure():
    # Pass bad YAML
    bad_yaml = "Resources:\\n  - Invalid: [\\n"
    score, rule_id, error = _score_single_yaml(bad_yaml)
    assert score == 0.0
    assert rule_id == "YAML_PARSE_ERROR"

@patch('subprocess.run')
def test_cfn_lint_failure(mock_run):
    # Mock successful run but cfn-lint JSON array output simulating E3002
    mock_result = MagicMock()
    mock_result.returncode = 1
    mock_result.stdout = '[{"Rule": {"Id": "E3002"}, "Message": "Resource properties are missing", "Location": {"Start": {"LineNumber": 12}}}]'
    mock_run.return_value = mock_result
    
    valid_yaml = "Resources: {}"
    score, rule_id, error = _score_single_yaml(valid_yaml)
    assert score == 0.20  # +0.20 for YAML parsing pass
    assert rule_id == "E3002"
    assert "E3002" in error

@patch('subprocess.run')
def test_cfn_guard_failure(mock_run):
    def side_effect(args, **kwargs):
        mock_result = MagicMock()
        if "cfn-lint" in str(args):
            mock_result.returncode = 0
            mock_result.stdout = "[]"
            return mock_result
            
        if "cfn-guard" in str(args):
            mock_result.returncode = 1
            mock_result.stdout = '{"not_compliant": [{"Rule": {"Name": "S3_BUCKET_SERVER_SIDE_ENCRYPTION_ENABLED"}}]}'
            return mock_result
            
    mock_run.side_effect = side_effect
    
    valid_yaml = "Resources: {}"
    score, rule_id, error = _score_single_yaml(valid_yaml)
    assert score == pytest.approx(0.60)  # 0.20 YAML + 0.40 Lint
    assert rule_id == "S3_BUCKET_SERVER_SIDE_ENCRYPTION_ENABLED"

@patch('subprocess.run')
def test_perfect_compilation(mock_run):
    def side_effect(args, **kwargs):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "[]"
        return mock_result
    mock_run.side_effect = side_effect
    
    valid_yaml = "Resources: {}"
    score, rule_id, error = _score_single_yaml(valid_yaml)
    assert score == 1.0  # Perfect Validation
    assert rule_id == "PASS"

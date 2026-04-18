import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.evaluators import _score_single_yaml

good_yaml = """
AWSTemplateFormatVersion: '2010-09-09'
Transform: AWS::Serverless-2016-10-31
Resources:
  HelloWorldFunction:
    Type: AWS::Serverless::Function
    Properties:
      Handler: app.handler
      Runtime: python3.12
      InlineCode: |
        def handler(event, context):
            return "OK"
"""

bad_yaml = """
AWSTemplateFormatVersion: '2010-09-09'
Transform: AWS::Serverless-2016-10-31
Resources:
  HelloWorldFunction:
    Type: AWS::Serverless::Function
    Properties:
      Handler: app.handler
      # Missing Runtime should trigger a SAM validation error!
      InlineCode: |
        def handler(event, context):
            return "OK"
"""

print("=== Testing New Metric Logic ===")
print("\n[1] Testing valid SAM structure (Should clear native parser & pass SAM CLI fast-barrier)")
s1, r1, m1 = _score_single_yaml(good_yaml)
print(f"Score: {s1:.2f}")
print(f"Rule/Outcome: {r1}")
print(f"Trace: {m1}")

print("\n[2] Testing invalid SAM properties (Should fail fast at SAM CLI, capturing explicit macro traces)")
s2, r2, m2 = _score_single_yaml(bad_yaml)
print(f"Score: {s2:.2f}")
print(f"Rule/Outcome: {r2}")
print(f"Trace: {m2}")

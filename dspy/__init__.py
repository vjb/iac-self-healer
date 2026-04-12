class Signature:
    pass

class InputField:
    def __init__(self, desc=""):
        self.desc = desc

class OutputField:
    def __init__(self, desc=""):
        self.desc = desc

class Module:
    def __init__(self):
        pass
    def load(self, path):
        pass

class ChainOfThought:
    def __init__(self, signature):
        self.signature = signature
    def __call__(self, **kwargs):
        class Prediction:
            def __init__(self):
                self.prerequisites = "1. AWS Account"
                self.use_case = kwargs.get('intent', 'Dummy Use Case')
                self.core_instructions = "import aws_cdk as cdk\n# CDK instructions"
                self.troubleshooting = "Check CloudWatch logs"
        return Prediction()

class Example:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)
    def with_inputs(self, *args):
        return self

def configure(**kwargs):
    pass

class LM:
    def __init__(self, model, api_base="", api_key=""):
        pass

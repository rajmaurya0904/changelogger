import sys

import yaml

try:
    with open('.github/workflows/ci.yml') as f:
        yaml.safe_load(f)
    print('YAML is valid')
    sys.exit(0)
except Exception as e:
    print(f'Invalid YAML: {e}')
    sys.exit(1)
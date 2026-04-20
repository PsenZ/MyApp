import sys

from veyraquant.config import AppConfig
from veyraquant.runner import run


def main() -> int:
    return run(AppConfig.from_env())


if __name__ == "__main__":
    sys.exit(main())

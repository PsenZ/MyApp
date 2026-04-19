import sys

from shortreport.config import AppConfig
from shortreport.runner import run


def main() -> int:
    return run(AppConfig.from_env())


if __name__ == "__main__":
    sys.exit(main())

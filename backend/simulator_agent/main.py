import json
import sys

from src.agent import run_simulation


def main():
    query = " ".join(sys.argv[1:]).strip()
    if not query:
        query = "Should we increase price by 10% for student segment next quarter?"
    result = run_simulation(query)
    print(json.dumps(result.get("response", result), indent=2))


if __name__ == "__main__":
    main()

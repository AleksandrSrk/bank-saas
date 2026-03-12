from pathlib import Path

from app.parsers.kl_to_1c_parser import parse_1c_client_bank


FIXTURES_DIR = Path(__file__).parent / "fixtures"


def main():
    files = list(FIXTURES_DIR.glob("*.txt"))

    if not files:
        print("No test files found in fixtures")
        return

    for file_path in files:
        print(f"\nParsing file: {file_path.name}")

        dtos = parse_1c_client_bank(str(file_path))

        for dto in dtos:
            print(dto)


if __name__ == "__main__":
    main()
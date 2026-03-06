from app.parsers.kl_to_1c_parser import parse_1c_client_bank


file_path = "app/kl_to_1c_40702810020000066887_044525104_01.02.2026-27.02.2026.txt"

dtos = parse_1c_client_bank(file_path)

for dto in dtos:
    print(dto)
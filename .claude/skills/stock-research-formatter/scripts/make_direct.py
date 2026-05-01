"""
MD 파일 없이 JSON 데이터를 직접 받아 Excel 파일 두 개를 생성.

사용법:
    python make_direct.py <json_path> <individual_xlsx_path> <portfolio_xlsx_path>
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from make_individual import make_individual_xlsx
from make_portfolio import add_to_portfolio


def main():
    if len(sys.argv) < 4:
        print("Usage: python make_direct.py <json_path> <individual_xlsx_path> <portfolio_xlsx_path>")
        sys.exit(1)

    json_path = Path(sys.argv[1])
    individual_path = sys.argv[2]
    portfolio_path = sys.argv[3]

    data = json.loads(json_path.read_text(encoding="utf-8"))

    saved_ind = make_individual_xlsx(data, individual_path)
    print(f"Individual: {saved_ind}")

    saved_port, action, cnt = add_to_portfolio(data, portfolio_path)
    print(f"Portfolio: {saved_port} ({action}, 평가 {cnt}건)")


if __name__ == "__main__":
    main()

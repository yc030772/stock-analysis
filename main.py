import argparse
import json

from stock_analysis import Orchestrator, convert_to_serializable


def main() -> None:
    parser = argparse.ArgumentParser(description="Dual-agent stock analysis orchestration")
    parser.add_argument("ticker", help="Stock ticker symbol")
    args = parser.parse_args()

    orchestrator = Orchestrator(args.ticker)
    final_report = orchestrator.run()
    print(json.dumps(final_report, ensure_ascii=False, indent=2, default=convert_to_serializable))


if __name__ == "__main__":
    main()

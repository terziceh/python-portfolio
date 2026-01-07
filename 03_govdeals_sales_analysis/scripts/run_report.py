from pathlib import Path
from govdeals_report.report import build_outputs

if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    csv_path = root / "data_sample" / "GovDeals_Data.csv"
    output_dir = root / "outputs"

    build_outputs(
        csv_path=csv_path,
        output_dir=output_dir,
        years_for_report=(2022, 2023, 2024),
        overhead=240_000.0,
    )

    print("Done. Check outputs/tables and outputs/figures")

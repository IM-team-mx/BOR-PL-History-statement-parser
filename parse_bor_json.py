import json
import csv
import pandas as pd
from pathlib import Path

INPUT_FILE = Path("input/BOR_statement_Historical_PL.json")
OUTPUT_BENEFICIAL_OWNER = Path("outputs/parsed_output_beneficial_owner_securities.csv")
OUTPUT_REALIZED_PL = Path("outputs/parsed_output_realized_pl.csv")
OUTPUT_HISTORICAL_PL = Path("outputs/historical_pl.csv")

COLUMNS_BENEFICIAL_OWNER = [
    "Portfolio", "Instrument", "Lot ID", "Contributor ID",
    "Event", "Date", "Quantity", "Unit"
]
COLUMNS_REALIZED_PL = [
    "Portfolio", "Instrument", "Lot ID", "Contributor ID", "Date", "Realized PL"
]


def parse_beneficial_owner_securities(data):
    rows = []
    records = data.get("balancesByAccountClass", {}).get("mandate.BeneficialOwnerSecurities", [])
    for record in records:
        try:
            lot_contract = record["balanceKey"]["account"]["lot"]["lotOpeningContract"]
            if lot_contract.get("externalSystemInstanceId") == "BOR.internal":
                continue
            portfolio = record["balanceKey"]["account"]["portfolio"]["name"]
            lot_id = lot_contract.get("representationId", "")

            instrument = ""
            for identifier in record["balanceKey"]["contract"].get("securityIdentifiers", []):
                if identifier.get("type") == "MX_DSPLABEL":
                    instrument = identifier.get("identifier", "")

            if record["balanceKey"].get("_type") == "DetailedBalanceKey":
                contributor_id = (
                    record["balanceKey"]["originBalanceKey"]["contract"]
                    ["externalRepresentation"].get("representationId", "")
                )
                date = record["balanceKey"].get("impactTimestamp", "").split("T")[0]
            else:
                contributor_id = ""
                date = ""

            unit = record["balanceKey"]["quantityUnit"].get("iso4217Alpha", "")
            quantity = float(record["balanceValue"].get("quantity", 0))

            event = "Purchase" if quantity > 0 else "Sale"
            quantity = abs(quantity)
            rows.append([
                portfolio, instrument, lot_id, contributor_id,
                event, date, quantity, unit
            ])
        except Exception as e:
            print(f"Error parsing beneficial owner securities record: {e}")
    return rows


def parse_realized_pl(data):
    rows = []
    records = data.get("balancesByAccountClass", {}).get("mandate.MonetaryRealizedPL", [])
    for record in records:
        try:
            portfolio = record["balanceKey"]["account"]["portfolio"]["name"]
            lot_id = record["balanceKey"]["account"]["lot"]["lotOpeningContract"]["representationId"]

            instrument = ""
            for identifier in record["balanceKey"]["originBalanceKey"]["contract"].get("securityIdentifiers", []):
                if identifier.get("type") == "MX_DSPLABEL":
                    instrument = identifier.get("identifier", "")

            if record["balanceKey"].get("_type") == "DetailedBalanceKey":
                contributor_id = (
                    record["balanceKey"]["originBalanceKey"]["originBalanceKey"]["contract"]
                    ["externalRepresentation"].get("representationId", "")
                )
                date = record["balanceKey"].get("impactTimestamp", "").split("T")[0]
            else:
                contributor_id = ""
                date = ""

            quantity = float(record["balanceValue"].get("quantity", 0))
            rows.append([
                portfolio, instrument, lot_id, contributor_id, date, quantity
            ])
        except Exception as e:
            print(f"Error parsing realized PL record: {e}")
    return rows


def write_csv(filepath, columns, rows):
    with open(filepath, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(columns)
        writer.writerows(rows)


def merge_and_save_historical_pl(rows_beneficial, rows_realized):
    df_beneficial = pd.DataFrame(rows_beneficial, columns=COLUMNS_BENEFICIAL_OWNER)
    df_realized = pd.DataFrame(rows_realized, columns=COLUMNS_REALIZED_PL)
    df_merged = pd.merge(
        df_beneficial, df_realized,
        on=["Portfolio", "Instrument", "Lot ID", "Contributor ID", "Date"],
        how="left"
    )
    df_sorted = df_merged.sort_values(by=["Portfolio", "Instrument", "Lot ID", "Date"])
    df_grouped = df_sorted.groupby(
        ["Portfolio", "Instrument", "Contributor ID", "Event", "Date", "Unit"]
    )[["Quantity", "Realized PL"]].sum().reset_index()
    df_filtered = df_grouped[df_grouped["Realized PL"] != 0]
    df_filtered.to_csv(OUTPUT_HISTORICAL_PL, index=False)


def main():
    try:
        with open(INPUT_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"Failed to read {INPUT_FILE}: {e}")
        return

    rows_beneficial = parse_beneficial_owner_securities(data)
    rows_realized = parse_realized_pl(data)

    write_csv(OUTPUT_BENEFICIAL_OWNER, COLUMNS_BENEFICIAL_OWNER, rows_beneficial)
    write_csv(OUTPUT_REALIZED_PL, COLUMNS_REALIZED_PL, rows_realized)

    merge_and_save_historical_pl(rows_beneficial, rows_realized)


if __name__ == "__main__":
    main()
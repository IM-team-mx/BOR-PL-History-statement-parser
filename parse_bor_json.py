import json
import csv
import pandas as pd
from pathlib import Path

INPUT_FILE = Path("input/BOR_statement_Historical_PL.json")
OUTPUT_BENEFICIAL_OWNER = Path("outputs/parsed_output_beneficial_owner_securities.csv")
OUTPUT_REALIZED_PL = Path("outputs/parsed_output_realized_pl.csv")
OUTPUT_CA_INCOME = Path("outputs/parsed_output_ca_income.csv")
OUTPUT_HISTORICAL_PL = Path("outputs/historical_pl.csv")

COLUMNS_BENEFICIAL_OWNER = [
    "Portfolio", "Instrument", "Lot ID", "Contributor ID",
    "Event", "Date", "Quantity", "Unit"
]
COLUMNS_REALIZED_PL = [
    "Portfolio", "Instrument", "Lot ID", "Contributor ID", "Date", "Realized PL"
]
COLUMNS_CA_INCOME = [
    "Portfolio", "Instrument", "Lot ID", "Contributor ID", "Event", "Date", "CA Income", "Unit"
]


def parse_beneficial_owner_securities(data):
    rows = []
    records = data["balancesByAccountClass"]["mandate.BeneficialOwnerSecurities"]
    for record in records:
        try:
            lot_contract = record["balanceKey"]["account"]["lot"]["lotOpeningContract"]
            if lot_contract["externalSystemInstanceId"] == "BOR.internal":  # ignores unallocated contracts
                continue

            portfolio = record["balanceKey"]["account"]["portfolio"]["name"]
            lot_id = lot_contract["representationId"]

            instrument = ""
            for identifier in record["balanceKey"]["contract"]["securityIdentifiers"]:
                if identifier["type"] == "MX_DSPLABEL":
                    instrument = identifier["identifier"]

            if record["balanceKey"]["_type"] == "DetailedBalanceKey":
                contributor_id = (
                    record["balanceKey"]["originBalanceKey"]["contract"]["externalRepresentation"]["representationId"]
                )
                date = record["balanceKey"]["impactTimestamp"].split("T")[0]
            else:
                contributor_id = ""
                date = ""

            unit = record["balanceKey"]["quantityUnit"]["iso4217Alpha"]
            quantity = float(record["balanceValue"]["quantity"])

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
    records = data["balancesByAccountClass"]["mandate.MonetaryRealizedPL"]
    for record in records:
        try:
            portfolio = record["balanceKey"]["account"]["portfolio"]["name"]
            lot_id = record["balanceKey"]["account"]["lot"]["lotOpeningContract"]["representationId"]

            instrument = ""
            for identifier in record["balanceKey"]["originBalanceKey"]["contract"]["securityIdentifiers"]:
                if identifier["type"] == "MX_DSPLABEL":
                    instrument = identifier["identifier"]

            if record["balanceKey"]["_type"] == "DetailedBalanceKey":
                contributor_id = (
                    record["balanceKey"]["originBalanceKey"]["originBalanceKey"]["contract"]["externalRepresentation"][
                        "representationId"]
                )
                date = record["balanceKey"]["impactTimestamp"].split("T")[0]
            else:
                contributor_id = ""
                date = ""

            quantity = float(record["balanceValue"]["quantity"])
            rows.append([
                portfolio, instrument, lot_id, contributor_id, date, quantity
            ])
        except Exception as e:
            print(f"Error parsing realized PL record: {e}")
    return rows


def parse_ca_income(data):
    rows = []
    records = data["balancesByAccountClass"]["mandate.MonetaryCAIncome"]
    for record in records:
        try:
            if record["balanceKey"]["_type"] == "BalanceKey":
                continue
            portfolio = record["balanceKey"]["account"]["portfolio"]["name"]
            lot_id = record["balanceKey"]["account"]["lot"]["lotOpeningContract"]["representationId"]
            instrument = ""
            for identifier in record["balanceKey"]["originBalanceKey"]["contract"]["securityIdentifiers"]:
                if identifier["type"] == "MX_DSPLABEL":
                    instrument = identifier["identifier"]

            contributor_id = (
                record["balanceKey"]["originBalanceKey"]["originBalanceKey"]["contract"]["identifier"][
                    "representationId"]
            )
            date = record["balanceKey"]["impactTimestamp"].split("T")[0]

            event = record["balanceKey"]["originBalanceKey"]["originBalanceKey"]["contract"]["borProductTaxonomy"]

            quantity = float(record["balanceValue"]["quantity"])

            unit = record["balanceKey"]["contract"]["iso4217Alpha"]

            rows.append([
                portfolio, instrument, lot_id, contributor_id,event, date, quantity, unit
            ])
        except Exception as e:
            print(f"Error parsing income record: {e}")
    return rows


def write_csv(filepath, columns, rows):
    with open(filepath, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(columns)
        writer.writerows(rows)


def merge_and_save_historical_pl(rows_beneficial, rows_realized, rows_income):
    df_beneficial = pd.DataFrame(rows_beneficial, columns=COLUMNS_BENEFICIAL_OWNER)
    df_realized = pd.DataFrame(rows_realized, columns=COLUMNS_REALIZED_PL)
    df_income = pd.DataFrame(rows_income, columns=COLUMNS_CA_INCOME)
    # df_merged = pd.merge(
    #     df_beneficial, df_realized,
    #     on=["Portfolio", "Instrument", "Lot ID", "Contributor ID", "Date"],
    #     how="left"
    # )

    df_merged = (
        df_beneficial.merge(df_realized, on=["Portfolio", "Instrument", "Lot ID", "Contributor ID", "Date"], how="left")
        .merge(df_income, on=["Portfolio", "Instrument", "Lot ID", "Contributor ID", "Event", "Date", "Unit"], how="outer")
    )

    df_sorted = df_merged.sort_values(by=["Portfolio", "Instrument", "Lot ID", "Date"])
    df_grouped = df_sorted.groupby(
        ["Portfolio", "Instrument", "Contributor ID", "Event", "Date", "Unit"]
    )[["Quantity", "Realized PL", "CA Income"]].sum().reset_index()
    print(df_grouped)
    # df_filtered = df_grouped[df_grouped["Realized PL"] != 0]
    df_filtered = df_grouped[
        (df_grouped["Realized PL"] != 0) | (df_grouped["CA Income"] != 0)
        ]
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
    rows_income = parse_ca_income(data)

    write_csv(OUTPUT_BENEFICIAL_OWNER, COLUMNS_BENEFICIAL_OWNER, rows_beneficial)
    write_csv(OUTPUT_REALIZED_PL, COLUMNS_REALIZED_PL, rows_realized)
    write_csv(OUTPUT_CA_INCOME, COLUMNS_CA_INCOME, rows_income)

    merge_and_save_historical_pl(rows_beneficial, rows_realized, rows_income)


if __name__ == "__main__":
    main()

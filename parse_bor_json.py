import json
import csv
import pandas as pd

# Input and output file paths
input_file = "input/BOR_statement_Historical_PL.json"
output_file_beneficial_owner_securities = "outputs/parsed_output_beneficial_owner_securities.csv"
output_file_realized_pl = "outputs/parsed_output_realized_pl.csv"
output_file_historical_pl = "outputs/historical_pl.csv"


# CSV columns
columns_beneficial_owner_securities = [
    "Portfolio",
    "Instrument",
    "Lot ID",
    "Contributor ID",
    "Event",
    "Date",
    "Quantity",
    "Unit"
]

columns_realized_pl = [
    "Portfolio",
    "Instrument",
    "Lot ID",
    "Contributor ID",
    "Date",
    "Realized PL"
]
# CSV rows
rows_beneficial_owner_securities = []
rows_realized_pl = []

# Open and parse the JSON file
with open(input_file, "r", encoding="utf-8") as f:
    data = json.load(f)

beneficial_owner_securities = data["balancesByAccountClass"]["mandate.BeneficialOwnerSecurities"]

for record in beneficial_owner_securities:
    if record["balanceKey"]["account"]["lot"]["lotOpeningContract"]["externalSystemInstanceId"] != "BOR.internal":

        portfolio = record["balanceKey"]["account"]["portfolio"]["name"]
        lot_id = record["balanceKey"]["account"]["lot"]["lotOpeningContract"]["representationId"]

        contract_identifiers = record["balanceKey"]["contract"]["securityIdentifiers"]
        for identifier in contract_identifiers:
            if identifier["type"] == "MX_DSPLABEL":
                instrument = identifier["identifier"]

        if record["balanceKey"]["_type"] == "DetailedBalanceKey":
            contributor_id = record["balanceKey"]["originBalanceKey"]["contract"]["externalRepresentation"]["representationId"]
            date = record["balanceKey"]["impactTimestamp"].split("T")[0]
        else:
            contributor_id = ""
            date = ""

        unit = record["balanceKey"]["quantityUnit"]["iso4217Alpha"]
        quantity = float(record["balanceValue"]["quantity"])

        if quantity > 0:
            event = "Purchase"
        else:
            event = "Sale"
            quantity = -quantity

        rows_beneficial_owner_securities.append([
            portfolio,
            instrument,
            lot_id,
            contributor_id,
            event,
            date,
            quantity,
            unit
        ])

# Write to CSV
with open(output_file_beneficial_owner_securities, "w", newline="", encoding="utf-8") as csvfile:
    writer = csv.writer(csvfile)
    writer.writerow(columns_beneficial_owner_securities)
    writer.writerows(rows_beneficial_owner_securities)


realized_pl = data["balancesByAccountClass"]["mandate.MonetaryRealizedPL"]

for record in realized_pl:
    portfolio = record["balanceKey"]["account"]["portfolio"]["name"]
    lot_id = record["balanceKey"]["account"]["lot"]["lotOpeningContract"]["representationId"]

    contract_identifiers = record["balanceKey"]["originBalanceKey"]["contract"]["securityIdentifiers"]
    for identifier in contract_identifiers:
        if identifier["type"] == "MX_DSPLABEL":
            instrument = identifier["identifier"]

    if record["balanceKey"]["_type"] == "DetailedBalanceKey":
        contributor_id = record["balanceKey"]["originBalanceKey"]["originBalanceKey"]["contract"]["externalRepresentation"]["representationId"]
        date = record["balanceKey"]["impactTimestamp"].split("T")[0]
    else:
        contributor_id = ""
        date = ""

    quantity = float(record["balanceValue"]["quantity"])

    rows_realized_pl.append([
        portfolio,
        instrument,
        lot_id,
        contributor_id,
        date,
        quantity
    ])

# Write to CSV
with open(output_file_realized_pl, "w", newline="", encoding="utf-8") as csvfile:
    writer = csv.writer(csvfile)
    writer.writerow(columns_realized_pl)
    writer.writerows(rows_realized_pl)


df_beneficial_owner_securities = pd.DataFrame(rows_beneficial_owner_securities, columns=columns_beneficial_owner_securities)
df_realized = pd.DataFrame(rows_realized_pl, columns=columns_realized_pl)

df_merged = pd.merge(df_beneficial_owner_securities, df_realized, on=["Portfolio", "Instrument", "Lot ID", "Contributor ID", "Date"], how="left")
df_sorted = df_merged.sort_values(by=["Portfolio", "Instrument", "Lot ID", "Date"])
df_grouped = df_sorted.groupby(["Portfolio", "Instrument", "Contributor ID", "Event", "Date", "Unit"])[["Quantity", "Realized PL"]].sum().reset_index()
df_filtered = df_grouped[df_grouped["Realized PL"] != 0]
df_filtered.to_csv(output_file_historical_pl, index=False)
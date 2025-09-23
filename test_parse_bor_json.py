import unittest
import pandas as pd
import csv
from pathlib import Path
import tempfile

# Import from your actual file
from parse_bor_json import (
    parse_beneficial_owner_securities,
    parse_realized_pl,
    parse_realized_amortization,
    parse_ca_income,
    write_csv,
    merge_and_save_historical_pl
)


class TestParseBORJson(unittest.TestCase):

    def setUp(self):
        self.rows_beneficial = [
            ["PortfolioA", "InstrumentX", "LOT123", "ContrID1", "Purchase", "2025-09-23", 100.0, "USD"]]
        self.rows_realized_pl = [["PortfolioA", "InstrumentX", "LOT123", "ContrID1", "2025-09-23", 50.0]]
        self.rows_realized_amortization = [["PortfolioA", "InstrumentX", "LOT123", "ContrID1", "2025-09-23", 10.0]]
        # Match Event to 'Purchase' so merge works
        self.rows_income = [["PortfolioA", "InstrumentX", "LOT123", "ContrID1", "Purchase", "2025-09-23", 5.0, "USD"]]

    def test_parse_beneficial_owner_securities(self):
        data = {
            "balancesByAccountClass": {
                "mandate.BeneficialOwnerSecurities": [
                    {
                        "balanceKey": {
                            "_type": "DetailedBalanceKey",
                            "account": {
                                "portfolio": {"name": "PortfolioA"},
                                "lot": {
                                    "lotOpeningContract": {
                                        "representationId": "LOT123",
                                        "externalSystemInstanceId": "BOR.external"
                                    }
                                }
                            },
                            "contract": {
                                "securityIdentifiers": [
                                    {"type": "MX_DSPLABEL", "identifier": "InstrumentX"}
                                ]
                            },
                            "originBalanceKey": {
                                "contract": {
                                    "externalRepresentation": {
                                        "representationId": "ContrID1"
                                    }
                                }
                            },
                            "impactTimestamp": "2025-09-23T12:00:00",
                            "quantityUnit": {"iso4217Alpha": "USD"}
                        },
                        "balanceValue": {"quantity": "100"}
                    }
                ]
            }
        }
        rows = parse_beneficial_owner_securities(data)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][4], "Purchase")
        self.assertEqual(rows[0][6], 100.0)

    def test_beneficial_owner_ignores_unallocated(self):
        data = {
            "balancesByAccountClass": {
                "mandate.BeneficialOwnerSecurities": [
                    {
                        "balanceKey": {
                            "account": {
                                "portfolio": {"name": "PortfolioA"},
                                "lot": {
                                    "lotOpeningContract": {
                                        "representationId": "LOT123",
                                        "externalSystemInstanceId": "BOR.internal"
                                    }
                                }
                            }
                        }
                    }
                ]
            }
        }
        rows = parse_beneficial_owner_securities(data)
        self.assertEqual(rows, [])

    def test_beneficial_owner_negative_quantity(self):
        data = {
            "balancesByAccountClass": {
                "mandate.BeneficialOwnerSecurities": [
                    {
                        "balanceKey": {
                            "_type": "DetailedBalanceKey",
                            "account": {
                                "portfolio": {"name": "PortfolioA"},
                                "lot": {
                                    "lotOpeningContract": {
                                        "representationId": "LOT123",
                                        "externalSystemInstanceId": "BOR.external"
                                    }
                                }
                            },
                            "contract": {
                                "securityIdentifiers": [
                                    {"type": "MX_DSPLABEL", "identifier": "InstrumentX"}
                                ]
                            },
                            "originBalanceKey": {
                                "contract": {
                                    "externalRepresentation": {
                                        "representationId": "ContrID1"
                                    }
                                }
                            },
                            "impactTimestamp": "2025-09-23T12:00:00",
                            "quantityUnit": {"iso4217Alpha": "USD"}
                        },
                        "balanceValue": {"quantity": "-200"}
                    }
                ]
            }
        }
        rows = parse_beneficial_owner_securities(data)
        self.assertEqual(rows[0][4], "Sale")
        self.assertEqual(rows[0][6], 200.0)

    def test_parse_functions_with_missing_keys(self):
        bad_data = {"balancesByAccountClass": {"mandate.BeneficialOwnerSecurities": [{}]}}
        self.assertEqual(parse_beneficial_owner_securities(bad_data), [])

        bad_data = {"balancesByAccountClass": {"mandate.MonetaryRealizedPL": [{}]}}
        self.assertEqual(parse_realized_pl(bad_data), [])

        bad_data = {"balancesByAccountClass": {"mandate.MonetaryRealizedAmortizationEIM": [{}]}}
        self.assertEqual(parse_realized_amortization(bad_data), [])

        bad_data = {"balancesByAccountClass": {"mandate.MonetaryCAIncome": [{}]}}
        self.assertEqual(parse_ca_income(bad_data), [])

    def test_ca_income_skips_balancekey_type_balancekey(self):
        data = {
            "balancesByAccountClass": {
                "mandate.MonetaryCAIncome": [
                    {"balanceKey": {"_type": "BalanceKey"}}
                ]
            }
        }
        self.assertEqual(parse_ca_income(data), [])

    def test_write_csv(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "test.csv"
            rows = [["A", "B"], ["C", "D"]]
            columns = ["col1", "col2"]
            write_csv(filepath, columns, rows)
            with open(filepath, newline="", encoding="utf-8") as f:
                reader = list(csv.reader(f))
            self.assertEqual(reader[0], columns)
            self.assertEqual(reader[1], ["A", "B"])

    def test_merge_and_save_historical_pl(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            out_file = Path(tmpdir) / "historical_pl.csv"
            import parse_bor_json
            parse_bor_json.OUTPUT_HISTORICAL_PL = out_file

            merge_and_save_historical_pl(
                self.rows_beneficial,
                self.rows_realized_pl,
                self.rows_realized_amortization,
                self.rows_income
            )

            df = pd.read_csv(out_file)
            self.assertIn("Clean Realized PL", df.columns)
            self.assertEqual(df.iloc[0]["Clean Realized PL"], 50.0)
            self.assertEqual(df.iloc[0]["Amortized Realized PL"], 40.0)
            self.assertEqual(df.iloc[0]["CA Income"], 5.0)

    def test_merge_and_save_with_empty_data(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            out_file = Path(tmpdir) / "empty.csv"
            import parse_bor_json
            parse_bor_json.OUTPUT_HISTORICAL_PL = out_file

            merge_and_save_historical_pl([], [], [], [])
            df = pd.read_csv(out_file)
            self.assertTrue(df.empty)


if __name__ == "__main__":
    unittest.main()

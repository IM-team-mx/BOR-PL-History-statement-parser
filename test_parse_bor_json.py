import unittest

from parse_bor_json import (
    parse_beneficial_owner_securities,
    parse_realized_pl,
)


class TestParseBorJson(unittest.TestCase):
    def setUp(self):
        self.sample_data = {
            "balancesByAccountClass": {
                "mandate.BeneficialOwnerSecurities": [
                    {
                        "balanceKey": {
                            "account": {
                                "portfolio": {"name": "TestPortfolio"},
                                "lot": {
                                    "lotOpeningContract": {
                                        "externalSystemInstanceId": "BOR.external",
                                        "representationId": "lot123"
                                    }
                                }
                            },
                            "contract": {
                                "securityIdentifiers": [
                                    {"type": "MX_DSPLABEL", "identifier": "InstrX"}
                                ]
                            },
                            "_type": "DetailedBalanceKey",
                            "originBalanceKey": {
                                "contract": {
                                    "externalRepresentation": {"representationId": "Contrib42"}
                                }
                            },
                            "impactTimestamp": "2024-01-01T12:00:00Z",
                            "quantityUnit": {"iso4217Alpha": "USD"}
                        },
                        "balanceValue": {"quantity": "150"}
                    },
                    # A Sale
                    {
                        "balanceKey": {
                            "account": {
                                "portfolio": {"name": "TestPortfolio"},
                                "lot": {
                                    "lotOpeningContract": {
                                        "externalSystemInstanceId": "BOR.external",
                                        "representationId": "lot124"
                                    }
                                }
                            },
                            "contract": {
                                "securityIdentifiers": [
                                    {"type": "MX_DSPLABEL", "identifier": "InstrY"}
                                ]
                            },
                            "_type": "DetailedBalanceKey",
                            "originBalanceKey": {
                                "contract": {
                                    "externalRepresentation": {"representationId": "Contrib43"}
                                }
                            },
                            "impactTimestamp": "2024-02-02T12:00:00Z",
                            "quantityUnit": {"iso4217Alpha": "USD"}
                        },
                        "balanceValue": {"quantity": "-70"}
                    },
                    # Should be skipped (BOR.internal)
                    {
                        "balanceKey": {
                            "account": {
                                "portfolio": {"name": "TestPortfolio"},
                                "lot": {
                                    "lotOpeningContract": {
                                        "externalSystemInstanceId": "BOR.internal",
                                        "representationId": "lot125"
                                    }
                                }
                            },
                            "contract": {
                                "securityIdentifiers": [
                                    {"type": "MX_DSPLABEL", "identifier": "InstrZ"}
                                ]
                            },
                            "_type": "DetailedBalanceKey",
                            "originBalanceKey": {
                                "contract": {
                                    "externalRepresentation": {"representationId": "Contrib44"}
                                }
                            },
                            "impactTimestamp": "2024-03-03T12:00:00Z",
                            "quantityUnit": {"iso4217Alpha": "USD"}
                        },
                        "balanceValue": {"quantity": "200"}
                    }
                ],
                "mandate.MonetaryRealizedPL": [
                    {
                        "balanceKey": {
                            "account": {
                                "portfolio": {"name": "TestPortfolio"},
                                "lot": {
                                    "lotOpeningContract": {"representationId": "lot123"}
                                }
                            },
                            "originBalanceKey": {
                                "contract": {
                                    "securityIdentifiers": [
                                        {"type": "MX_DSPLABEL", "identifier": "InstrX"}
                                    ],
                                    "externalRepresentation": {"representationId": "Contrib42"}
                                },
                                "originBalanceKey": {
                                    "contract": {
                                        "externalRepresentation": {"representationId": "Contrib42"}
                                    }
                                }
                            },
                            "_type": "DetailedBalanceKey",
                            "impactTimestamp": "2024-01-01T12:00:00Z"
                        },
                        "balanceValue": {"quantity": "333"}
                    }
                ]
            }
        }

    def test_parse_beneficial_owner_securities(self):
        rows = parse_beneficial_owner_securities(self.sample_data)
        self.assertEqual(len(rows), 2)  # Skips BOR.internal
        purchase = rows[0]
        self.assertEqual(purchase[0], "TestPortfolio")
        self.assertEqual(purchase[1], "InstrX")
        self.assertEqual(purchase[2], "lot123")
        self.assertEqual(purchase[3], "Contrib42")
        self.assertEqual(purchase[4], "Purchase")
        self.assertEqual(purchase[5], "2024-01-01")
        self.assertEqual(purchase[6], 150.0)
        self.assertEqual(purchase[7], "USD")
        sale = rows[1]
        self.assertEqual(sale[4], "Sale")
        self.assertEqual(sale[6], 70.0)

    def test_parse_realized_pl(self):
        rows = parse_realized_pl(self.sample_data)
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row[0], "TestPortfolio")
        self.assertEqual(row[1], "InstrX")
        self.assertEqual(row[2], "lot123")
        self.assertEqual(row[3], "Contrib42")
        self.assertEqual(row[4], "2024-01-01")
        self.assertEqual(row[5], 333.0)


if __name__ == "__main__":
    unittest.main()

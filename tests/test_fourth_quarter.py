from __future__ import annotations

import json
from datetime import date
from decimal import Decimal
from itertools import count
from typing import Any

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from financial_data_agent.api.tools import get_fourth_quarter as tool_module
from financial_data_agent.constants import METRIC_FIELDS
from financial_data_agent.db.DTO.company import CompanyDTO
from financial_data_agent.db.DTO.document import DocumentDTO
from financial_data_agent.db.DTO.financial_metric import FinancialMetricDTO
from financial_data_agent.db.models.base import Base
from financial_data_agent.db.repositories.company import CompanyRepository
from financial_data_agent.db.repositories.document import DocumentRepository
from financial_data_agent.db.repositories.financial_metric import FinancialMetricRepository
from financial_data_agent.services import fourth_quarter as service_module
from financial_data_agent.services.filing_import import CompanyNotFoundError, FilingNotFoundError
from financial_data_agent.services.fourth_quarter import (
    AnnualFilingNotFoundError,
    FourthQuarterService,
    IncompleteFiscalYearError,
    preceding_slot,
    subtract,
)

Filing = tuple[str, int, int, date, dict[str, Any]]

accessions = count(1)

NVDA_FILINGS: list[Filing] = [
    ("annual", 2020, 1, date(2020, 1, 26), {"revenue": 10918, "operating_cash_flow": 4000, "total_assets": 13292}),
    ("quarterly", 2019, 2, date(2019, 4, 28), {"revenue": 2220, "operating_cash_flow": 1000, "total_assets": 1}),
    ("quarterly", 2019, 3, date(2019, 7, 28), {"revenue": 2579, "operating_cash_flow": 2000, "total_assets": 2}),
    ("quarterly", 2019, 4, date(2019, 10, 27), {"revenue": 3014, "operating_cash_flow": 3000, "total_assets": 3}),
]
MSFT_FILINGS: list[Filing] = [
    ("annual", 2020, 3, date(2020, 6, 30), {"revenue": 143015, "operating_cash_flow": 60675}),
    ("quarterly", 2019, 4, date(2019, 9, 30), {"revenue": 33055, "operating_cash_flow": 15000}),
    ("quarterly", 2020, 1, date(2019, 12, 31), {"revenue": 36906, "operating_cash_flow": 30000}),
    ("quarterly", 2020, 2, date(2020, 3, 31), {"revenue": 35021, "operating_cash_flow": 45000}),
]
OLD_NVDA_FILINGS: list[Filing] = [
    ("annual", 2019, 1, date(2019, 1, 27), {"revenue": 1}),
    ("quarterly", 2018, 4, date(2018, 10, 28), {"revenue": 1}),
]


def make_session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)()


def store(session: Session, ticker: str, filings: list[Filing]) -> None:
    company = CompanyRepository(session).get_by_ticker(ticker) or CompanyRepository(session).create(
        CompanyDTO(ticker=ticker, name=ticker, cik=f"{ticker:0>10}")
    )
    for period_type, year, quarter, period_end, values in filings:
        document = DocumentRepository(session).create(
            DocumentDTO(
                company_id=company.id,
                accession_number=f"0000000000-00-{next(accessions):06d}",
                document_type="10-K" if period_type == "annual" else "10-Q",
                reporting_year=year,
                reporting_quarter=quarter,
                period_type=period_type,
                filing_date=period_end,
                period_of_report=period_end,
                raw_document_path="x",
            )
        )
        metric_values = {field: values.get(field) for field in METRIC_FIELDS}
        FinancialMetricRepository(session).create(
            FinancialMetricDTO(
                document_id=document.id, **metric_values, supplied_fields=frozenset({"document_id", *METRIC_FIELDS})
            )
        )


class FakeImports:
    """Stands in for both import services; importing a slot stores the filing registered for it."""

    imported: list[tuple[str, int, int]] = []
    pending: dict[tuple[int, int], Filing] = {}

    def __init__(self, session: Session, *args: Any) -> None:
        self.session = session

    def import_filings(self, ticker: str, year: int, quarter: int) -> None:
        if (year, quarter) not in self.pending:
            raise FilingNotFoundError(f"No filing for {ticker} {year} Q{quarter}")
        self.imported.append((ticker, year, quarter))
        store(self.session, ticker, [self.pending[(year, quarter)]])

    def import_metrics(self, ticker: str, year: int, quarter: int) -> None:
        pass


def use_import_fakes(monkeypatch: pytest.MonkeyPatch, pending: list[Filing]) -> list[tuple[str, int, int]]:
    imported: list[tuple[str, int, int]] = []
    fake = type("Imports", (FakeImports,), {"imported": imported, "pending": {(f[1], f[2]): f for f in pending}})
    monkeypatch.setattr(service_module, "FilingImportService", fake)
    monkeypatch.setattr(service_module, "FinancialMetricsImportService", fake)
    return imported


def test_nvda_fourth_quarter_is_the_10k_minus_the_three_10qs_and_ignores_other_years() -> None:
    session = make_session()
    store(session, "NVDA", [*OLD_NVDA_FILINGS, *NVDA_FILINGS])

    result = FourthQuarterService(session).derive("nvda", 2020, 1)

    assert result.fiscal_year_end == date(2020, 1, 26)
    assert result.previous_quarter_end == date(2019, 10, 27)
    assert result.fourth_quarter["revenue"] == Decimal(3105)
    assert result.previous_quarter["revenue"] == Decimal(3014)
    assert result.fourth_quarter["operating_cash_flow"] == Decimal(1000)
    assert result.previous_quarter["operating_cash_flow"] == Decimal(1000)
    assert result.fourth_quarter["total_assets"] == Decimal(13292)
    assert result.previous_quarter["total_assets"] == Decimal(3)
    assert [(s.reporting_year, s.reporting_quarter, s.period_type) for s in result.sources] == [
        (2020, 1, "annual"),
        (2019, 2, "quarterly"),
        (2019, 3, "quarterly"),
        (2019, 4, "quarterly"),
    ]


def test_msft_fourth_quarter_in_calendar_q3_slot() -> None:
    session = make_session()
    store(session, "MSFT", MSFT_FILINGS)

    result = FourthQuarterService(session).derive("MSFT", 2020, 3)

    assert result.fourth_quarter["revenue"] == Decimal(143015 - 33055 - 36906 - 35021)
    assert result.fourth_quarter["operating_cash_flow"] == Decimal(60675 - 45000)
    assert result.previous_quarter["revenue"] == Decimal(35021)
    assert result.previous_quarter["operating_cash_flow"] == Decimal(15000)


def test_share_counts_are_never_derived_and_missing_inputs_give_missing_outputs() -> None:
    session = make_session()
    filings = [(f[0], f[1], f[2], f[3], {**f[4], "shares_outstanding": 5}) for f in NVDA_FILINGS]
    filings[2][4]["revenue"] = None
    store(session, "NVDA", filings)

    result = FourthQuarterService(session).derive("NVDA", 2020, 1)

    assert result.fourth_quarter["revenue"] is None
    assert result.fourth_quarter["shares_outstanding"] is None
    assert result.previous_quarter["shares_outstanding"] is None
    assert result.fourth_quarter["operating_cash_flow"] == Decimal(1000)
    assert result.fourth_quarter["net_income"] is None


def test_missing_10qs_are_imported_from_the_three_slots_before_the_10k(monkeypatch: pytest.MonkeyPatch) -> None:
    session = make_session()
    store(session, "NVDA", NVDA_FILINGS[:2])
    imported = use_import_fakes(monkeypatch, NVDA_FILINGS[2:])

    result = FourthQuarterService(session).derive("NVDA", 2020, 1)

    assert imported == [("NVDA", 2019, 4), ("NVDA", 2019, 3)]
    assert result.fourth_quarter["revenue"] == Decimal(3105)


def test_import_failure_and_wrong_quarter_count_are_reported(monkeypatch: pytest.MonkeyPatch) -> None:
    session = make_session()
    store(session, "NVDA", NVDA_FILINGS[:1])
    use_import_fakes(monkeypatch, [])

    with pytest.raises(FilingNotFoundError):
        FourthQuarterService(session).derive("NVDA", 2020, 1)

    monkeypatch.setattr(FakeImports, "import_filings", lambda *args: None)
    with pytest.raises(IncompleteFiscalYearError):
        FourthQuarterService(session).derive("NVDA", 2020, 1)


def test_unknown_company_and_slot_without_10k_are_domain_errors() -> None:
    session = make_session()
    store(session, "NVDA", NVDA_FILINGS[1:])

    with pytest.raises(CompanyNotFoundError):
        FourthQuarterService(session).derive("ZZZZ", 2020, 1)
    with pytest.raises(AnnualFilingNotFoundError):
        FourthQuarterService(session).derive("NVDA", 2020, 1)


def test_quarter_arithmetic_helpers() -> None:
    assert preceding_slot(2020, 1, 1) == (2019, 4)
    assert preceding_slot(2020, 3, 3) == (2019, 4)
    assert subtract(Decimal(10), [Decimal(1), Decimal(2)]) == Decimal(7)
    assert subtract(Decimal(10), [Decimal(1), None]) is None
    assert subtract(None, []) is None


def test_get_fourth_quarter_tool_returns_json_result_and_error(monkeypatch: pytest.MonkeyPatch) -> None:
    session = make_session()
    store(session, "NVDA", NVDA_FILINGS)
    monkeypatch.setattr(tool_module, "get_session_factory", lambda: lambda: session)

    body = json.loads(tool_module.get_fourth_quarter("NVDA", 2020, 1))

    assert body["error"] is None
    assert Decimal(body["fourth_quarter"]["revenue"]) == Decimal(3105)
    assert Decimal(body["previous_quarter"]["revenue"]) == Decimal(3014)
    assert body["fiscal_year_end"] == "2020-01-26"
    assert len(body["sources"]) == 4

    error_body = json.loads(tool_module.get_fourth_quarter("NVDA", 2015, 1))
    assert "No 10-K" in error_body["error"]
    assert error_body["fourth_quarter"] is None

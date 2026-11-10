import os
import unittest
from unittest.mock import Mock, patch

os.environ.setdefault("TRUELAYER_CLIENT_ID", "test-client")
os.environ.setdefault("TRUELAYER_CLIENT_SECRET", "test-secret")
os.environ.setdefault("FIREFLY_URL", "http://firefly.test")
os.environ.setdefault("FIREFLY_TOKEN", "test-token")

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import ImportedTransaction, Provider, SyncState
from app.services.firefly import FireflyService
from app.services.truelayer import TrueLayerService


class SyncDeduplicationTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.db = sessionmaker(bind=self.engine)()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def test_main_module_imports_for_application_startup(self):
        from app.main import sync_provider_to_firefly

        self.assertTrue(callable(sync_provider_to_firefly))

    def test_same_true_layer_id_is_imported_only_once(self):
        service = FireflyService()
        service.get_or_create_account = Mock(return_value="42")
        response = Mock(status_code=201)
        response.json.return_value = {"data": {"id": "99"}}
        transaction = {
            "transaction_id": "stable-tx-id",
            "timestamp": "2026-07-01T10:00:00Z",
            "amount": -12.5,
            "transaction_type": "DEBIT",
            "currency": "GBP",
            "description": "Test purchase",
        }

        with patch("app.services.firefly.requests.post", return_value=response) as post:
            first = service.sync_truelayer_transactions(
                [transaction], "Current Account", "Bank", "tl-account-1", self.db
            )
            second = service.sync_truelayer_transactions(
                [transaction], "Current Account", "Bank", "tl-account-1", self.db
            )

        self.assertEqual(post.call_count, 1)
        self.assertEqual(first["created"], 1)
        self.assertEqual(second["duplicates"], 1)
        imported = self.db.query(ImportedTransaction).one()
        self.assertEqual(imported.status, "imported")

    def test_same_id_in_different_true_layer_accounts_is_not_suppressed(self):
        service = FireflyService()
        service.get_or_create_account = Mock(return_value="42")
        response = Mock(status_code=201)
        response.json.return_value = {"data": {"id": "99"}}
        transaction = {
            "transaction_id": "reused-provider-id",
            "timestamp": "2026-07-01T10:00:00Z",
            "amount": -12.5,
            "transaction_type": "DEBIT",
            "currency": "GBP",
            "description": "Test purchase",
        }

        with patch("app.services.firefly.requests.post", return_value=response) as post:
            service.sync_truelayer_transactions(
                [transaction], "First Account", "Bank", "account-1", self.db
            )
            service.sync_truelayer_transactions(
                [transaction], "Second Account", "Bank", "account-2", self.db
            )

        self.assertEqual(post.call_count, 2)
        self.assertEqual(self.db.query(ImportedTransaction).count(), 2)

    def test_validation_422_is_not_counted_as_a_duplicate(self):
        service = FireflyService()
        response = Mock(status_code=422, text="Invalid currency")
        response.json.return_value = {"message": "Validation error"}

        with patch("app.services.firefly.requests.post", return_value=response):
            result = service.import_transaction({"external_id": "tx"})

        self.assertEqual(result["status"], "error")
        self.assertEqual(result["status_code"], 422)

    def test_unresolved_import_is_not_submitted_again(self):
        self.db.add(ImportedTransaction(
            provider_name="Bank",
            account_id="account-1",
            external_id="uncertain-tx",
            status="processing",
        ))
        self.db.commit()
        service = FireflyService()
        service.get_or_create_account = Mock(return_value="42")
        transaction = {
            "transaction_id": "uncertain-tx",
            "timestamp": "2026-07-01T10:00:00Z",
            "amount": -12.5,
            "transaction_type": "DEBIT",
            "currency": "GBP",
            "description": "Test purchase",
        }

        with patch("app.services.firefly.requests.post") as post:
            result = service.sync_truelayer_transactions(
                [transaction], "Current Account", "Bank", "account-1", self.db
            )

        self.assertEqual(result["errors"], 1)
        self.assertEqual(result["unresolved"], 1)
        post.assert_not_called()

    def test_unresolved_import_list_contains_only_pending_records(self):
        from app.main import list_unresolved_transactions

        self.db.add_all([
            ImportedTransaction(
                provider_name="Bank",
                account_id="account-1",
                external_id="pending-tx",
                status="processing",
            ),
            ImportedTransaction(
                provider_name="Bank",
                account_id="account-1",
                external_id="done-tx",
                status="imported",
            ),
        ])
        self.db.commit()

        result = list_unresolved_transactions(self.db)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["external_id"], "pending-tx")

    def test_marking_unresolved_import_as_imported_preserves_deduplication(self):
        from app.main import mark_imported_transaction

        imported = ImportedTransaction(
            provider_name="Bank",
            account_id="account-1",
            external_id="uncertain-tx",
            status="processing",
        )
        self.db.add(imported)
        self.db.commit()

        result = mark_imported_transaction(imported.id, self.db)
        self.assertEqual(result["status"], "imported")

        service = FireflyService()
        service.get_or_create_account = Mock(return_value="42")
        with patch("app.services.firefly.requests.post") as post:
            summary = service.sync_truelayer_transactions(
                [{"transaction_id": "uncertain-tx"}],
                "Current Account",
                "Bank",
                "account-1",
                self.db,
            )

        self.assertEqual(summary["duplicates"], 1)
        post.assert_not_called()

    def test_releasing_unresolved_import_allows_next_sync_to_retry(self):
        from app.main import release_unresolved_transaction

        imported = ImportedTransaction(
            provider_name="Bank",
            account_id="account-1",
            external_id="uncertain-tx",
            status="processing",
        )
        self.db.add(imported)
        self.db.commit()

        result = release_unresolved_transaction(imported.id, self.db)
        self.assertEqual(result["status"], "retry_allowed")
        self.assertEqual(self.db.query(ImportedTransaction).count(), 0)

        service = FireflyService()
        service.get_or_create_account = Mock(return_value="42")
        response = Mock(status_code=201)
        response.json.return_value = {"data": {"id": "99"}}
        with patch("app.services.firefly.requests.post", return_value=response) as post:
            summary = service.sync_truelayer_transactions(
                [{"transaction_id": "uncertain-tx"}],
                "Current Account",
                "Bank",
                "account-1",
                self.db,
            )

        self.assertEqual(summary["created"], 1)
        post.assert_called_once()

    def test_unresolved_import_does_not_block_later_transactions(self):
        self.db.add(ImportedTransaction(
            provider_name="Bank",
            account_id="account-1",
            external_id="uncertain-tx",
            status="processing",
        ))
        self.db.commit()
        service = FireflyService()
        service.get_or_create_account = Mock(return_value="42")
        response = Mock(status_code=201)
        response.json.return_value = {"data": {"id": "99"}}
        transactions = [
            {"transaction_id": "uncertain-tx", "timestamp": "2026-07-01T10:00:00Z"},
            {"transaction_id": "later-tx", "timestamp": "2026-07-02T10:00:00Z"},
        ]

        with patch("app.services.firefly.requests.post", return_value=response) as post:
            result = service.sync_truelayer_transactions(
                transactions, "Current Account", "Bank", "account-1", self.db
            )

        self.assertEqual(result["errors"], 1)
        self.assertEqual(result["created"], 1)
        self.assertEqual(post.call_count, 1)
        later_import = self.db.query(ImportedTransaction).filter_by(
            external_id="later-tx"
        ).one()
        self.assertEqual(later_import.status, "imported")

    def test_sync_advances_cursor_only_after_firefly_import_succeeds(self):
        provider = Provider(
            name="Bank",
            provider_type="accounts",
            access_token="access",
            refresh_token="refresh",
        )
        self.db.add(provider)
        self.db.commit()

        service = TrueLayerService()
        transactions = [
            {"transaction_id": "old", "timestamp": "2026-07-01T10:00:00Z"},
            {"transaction_id": "new", "timestamp": "2026-07-02T10:00:00Z"},
        ]
        with (
            patch.object(service, "get_valid_token", return_value="access"),
            patch.object(service, "get_accounts", return_value=[
                {"account_id": "account-1", "display_name": "Current Account"}
            ]),
            patch.object(service, "get_transactions", return_value=transactions) as fetch,
        ):
            result = service.sync_provider(
                self.db,
                provider,
                lambda _account_id, _account_name, _transactions: {
                    "created": 1,
                    "duplicates": 1,
                    "errors": 0,
                },
            )

        fetch.assert_called_once()
        state = self.db.query(SyncState).one()
        self.assertEqual(state.last_sync_timestamp, "2026-07-02T10:00:00Z")
        self.assertEqual(state.transaction_count, 1)
        self.assertEqual(result["transactions_synced"], 1)

    def test_sync_does_not_advance_cursor_when_import_reports_errors(self):
        provider = Provider(
            name="Bank",
            provider_type="accounts",
            access_token="access",
            refresh_token="refresh",
        )
        self.db.add(provider)
        self.db.commit()

        service = TrueLayerService()
        with (
            patch.object(service, "get_valid_token", return_value="access"),
            patch.object(service, "get_accounts", return_value=[
                {"account_id": "account-1", "display_name": "Current Account"}
            ]),
            patch.object(
                service,
                "get_transactions",
                return_value=[{"transaction_id": "tx", "timestamp": "2026-07-02T10:00:00Z"}],
            ),
        ):
            with self.assertRaisesRegex(RuntimeError, "1 unresolved import"):
                service.sync_provider(
                    self.db,
                    provider,
                    lambda *_args: {"errors": 1, "unresolved": 1},
                )

        self.assertEqual(self.db.query(SyncState).count(), 0)


if __name__ == "__main__":
    unittest.main()

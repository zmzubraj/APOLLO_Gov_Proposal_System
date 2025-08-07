"""Tests for the Polkadot OpenGov governor interface."""
from types import SimpleNamespace

import src.execution.governor_interface as gi


def test_submit_preimage(monkeypatch):
    """Submitting a preimage composes the correct call and parses receipt."""
    class FakeSubstrate:
        def compose_call(self, call_module, call_function, call_params):
            assert call_module == "Preimage"
            assert call_function == "note_preimage"
            assert call_params["bytes"] == b"data"
            return "call"

        def create_signed_extrinsic(self, call, keypair):
            assert call == "call"
            assert keypair == "kp"
            return "xt"

        def submit_extrinsic(self, extrinsic, wait_for_inclusion):
            assert extrinsic == "xt"
            assert wait_for_inclusion is True
            return SimpleNamespace(
                extrinsic_hash="0xabc", block_hash="0xdef", is_success=True, error_message=None
            )

    monkeypatch.setattr(gi, "connect", lambda url: FakeSubstrate())
    monkeypatch.setattr(gi, "_create_keypair", lambda pk: "kp")
    receipt = gi.submit_preimage("ws://node", "priv", b"data")
    assert receipt == {
        "extrinsic_hash": "0xabc",
        "block_hash": "0xdef",
        "is_success": True,
        "error_message": None,
    }


def test_submit_proposal(monkeypatch):
    """Submitting a proposal references preimage hash and track."""
    class FakeSubstrate:
        def compose_call(self, call_module, call_function, call_params):
            assert call_module == "Referenda"
            assert call_function == "submit"
            assert call_params == {
                "proposal": "0x01",
                "track": 1,
                "value": 10,
            }
            return "call"

        def create_signed_extrinsic(self, call, keypair):
            assert call == "call"
            assert keypair == "kp"
            return "xt"

        def submit_extrinsic(self, extrinsic, wait_for_inclusion):
            assert extrinsic == "xt"
            return SimpleNamespace(
                extrinsic_hash="0x1", block_hash="0x2", is_success=False, error_message="fail"
            )

    monkeypatch.setattr(gi, "connect", lambda url: FakeSubstrate())
    monkeypatch.setattr(gi, "_create_keypair", lambda pk: "kp")
    receipt = gi.submit_proposal("ws://node", "priv", "0x01", 1, 10)
    assert receipt["extrinsic_hash"] == "0x1"
    assert receipt["is_success"] is False
    assert receipt["error_message"] == "fail"


def test_query_proposal_status(monkeypatch):
    """Status helper extracts state from storage query."""
    class FakeSubstrate:
        def query(self, module, storage_function, params):
            assert module == "Referenda"
            assert storage_function == "ReferendumInfoFor"
            assert params == [5]
            return SimpleNamespace(value={"Ongoing": {"status": "Deciding"}})

    monkeypatch.setattr(gi, "connect", lambda url: FakeSubstrate())
    status = gi.query_proposal_status("ws://node", 5)
    assert status == "Deciding"


def test_parse_receipt():
    """Receipt parser flattens receipt attributes."""
    receipt = SimpleNamespace(
        extrinsic_hash="0x3",
        block_hash="0x4",
        is_success=True,
        error_message=None,
    )
    assert gi.parse_receipt(receipt) == {
        "extrinsic_hash": "0x3",
        "block_hash": "0x4",
        "is_success": True,
        "error_message": None,
    }


def test_await_execution(monkeypatch):
    """Polling stops when a final status is observed."""

    statuses = iter(["Deciding", "Approved"])

    def fake_query(node_url, idx):
        return next(statuses)

    class FakeSubstrate:
        def get_block_hash(self):
            return "0xdead"

    monkeypatch.setattr(gi, "connect", lambda url: FakeSubstrate())
    monkeypatch.setattr(gi, "query_proposal_status", fake_query)
    monkeypatch.setattr(gi, "time", SimpleNamespace(sleep=lambda s: None))

    block_hash, outcome = gi.await_execution("ws://node", 1, "0xsub", poll_interval=0, max_attempts=5)
    assert block_hash == "0xdead"
    assert outcome == "Approved"

from agents.data_collector import DataCollector
from data_processing import evm_data_fetcher


def _dummy_web3():
    class DummyEth:
        block_number = 1

        def get_block(self, num, full_transactions=True):
            assert full_transactions is True
            return {
                "number": num,
                "hash": bytes.fromhex("11" * 32),
                "timestamp": 1000 + num,
                "transactions": [
                    {
                        "hash": bytes.fromhex("22" * 32),
                        "from": "0xabc",
                        "to": "0xdef",
                        "value": 123,
                    }
                ],
            }

    class DummyWeb3:
        class HTTPProvider:
            def __init__(self, url):
                self.url = url

        def __init__(self, provider):
            self.eth = DummyEth()

    return DummyWeb3


def test_fetch_evm_blocks_returns_data(monkeypatch):
    DummyWeb3 = _dummy_web3()
    monkeypatch.setattr(evm_data_fetcher, "Web3", DummyWeb3)
    blocks = evm_data_fetcher.fetch_evm_blocks("http://rpc", start_block=1, end_block=1)
    assert blocks[0]["number"] == 1
    assert blocks[0]["hash"].startswith("0x11")
    assert blocks[0]["transactions"][0]["hash"].startswith("0x22")


def test_data_collector_optional_evm(monkeypatch):
    called = {}

    def dummy_evm_fn():
        called["called"] = True
        return [{"timestamp": 0, "transactions": []}]

    monkeypatch.setenv("ENABLE_EVM_FETCH", "true")
    data = DataCollector.collect(
        msg_fn=lambda: {},
        news_fn=lambda: {},
        block_fn=lambda: [],
        evm_fn=dummy_evm_fn,
    )
    assert called["called"] is True
    assert "evm_daily_tx_count" in data["blocks"]

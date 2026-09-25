from types import SimpleNamespace

from creator_key_drill import CreatorIncidentRequest, CreatorKeyDrillService


class FakeKeys:
    def __init__(self):
        self.revoked_ids = []
        self.rotated_ids = []
        self.compromised_ids = []

    def list(self):
        return {
            "ok": True,
            "data": {
                "items": [
                    {"id": "key_123", "name": "production-download-worker"}
                ]
            },
            "error": None,
            "metadata": {},
        }

    def create(self, payload):
        assert payload["project_id"] == "creator-shop"
        assert payload["name"] == "drill-production-download-worker"
        return {
            "ok": True,
            "data": {"id": "key_456", "key": "store_this_now"},
            "error": None,
            "metadata": {},
        }

    def suspected_compromise(self, key_id, payload):
        self.compromised_ids.append((key_id, payload))
        return {"ok": True, "data": {"id": key_id}, "error": None, "metadata": {}}

    def rotate(self, key_id, payload):
        self.rotated_ids.append((key_id, payload))
        return {"ok": True, "data": {"id": key_id}, "error": None, "metadata": {}}

    def revoke(self, key_id):
        self.revoked_ids.append(key_id)
        return {"ok": True, "data": {"id": key_id}, "error": None, "metadata": {}}


class FakeLogs:
    def search(self, query):
        assert query["marker"] == "leaked-key-fragment"
        return {
            "ok": True,
            "data": {"items": [{"id": "log1"}, {"id": "log2"}]},
            "error": None,
            "metadata": {},
        }


class FakeInfrai:
    def __init__(self):
        self.account = SimpleNamespace(keys=FakeKeys())
        self.logs = FakeLogs()


def test_drill_pauses_delivery_and_marks_followup_when_logs_show_exposure():
    service = CreatorKeyDrillService(FakeInfrai())
    request = CreatorIncidentRequest(
        project_id="creator-shop",
        suspected_key_name="production-download-worker",
        leak_marker="leaked-key-fragment",
        asset_id="asset_042",
        subscriber_id="sub_123",
        content_id="post_77",
        grace_hours=2,
    )

    result = service.run(request)

    assert result.suspected_key_id == "key_123"
    assert result.temporary_key_id == "key_456"
    assert result.log_hits == 2
    assert result.blast_radius == "subscriber_and_asset_exposed"
    assert result.asset_delivery_status == "paused"
    assert result.subscriber_update_status == "pending_notice"
    assert result.content_processing_status == "reprocess_requested"

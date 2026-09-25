from __future__ import annotations

from typing import Any, Dict, List, Protocol
from uuid import uuid4

from pydantic import BaseModel, Field

from infrai_client import InfraiClient


class CreatorIncidentRequest(BaseModel):
    project_id: str
    suspected_key_name: str
    leak_marker: str
    asset_id: str
    subscriber_id: str
    content_id: str
    grace_hours: int = Field(default=1, ge=0)


class CreatorIncidentResult(BaseModel):
    incident_id: str
    suspected_key_id: str
    temporary_key_id: str
    temporary_key_plaintext: str
    log_hits: int
    blast_radius: str
    asset_delivery_status: str
    subscriber_update_status: str
    content_processing_status: str


class ClientProtocol(Protocol):
    account: Any
    logs: Any


class DigitalAssetDelivery:
    @staticmethod
    def pause(asset_id: str, reason: str) -> Dict[str, str]:
        return {"asset_id": asset_id, "status": "paused", "reason": reason}


class SubscriberUpdates:
    @staticmethod
    def queue_notice(subscriber_id: str, reason: str) -> Dict[str, str]:
        return {"subscriber_id": subscriber_id, "status": "pending_notice", "reason": reason}


class ContentProcessing:
    @staticmethod
    def request_reprocess(content_id: str, reason: str) -> Dict[str, str]:
        return {"content_id": content_id, "status": "reprocess_requested", "reason": reason}


class CreatorKeyDrillService:
    def __init__(self, infrai: ClientProtocol):
        self.infrai = infrai

    def run(self, request: CreatorIncidentRequest) -> CreatorIncidentResult:
        keys_env = self.infrai.account.keys.list()
        suspected_key_id = self._find_key_id(keys_env.get("data"), request.suspected_key_name)

        self.infrai.account.keys.suspected_compromise(
            suspected_key_id,
            {
                "confirmed_leak": True,
                "auto_rotate": False,
            },
        )

        create_env = self.infrai.account.keys.create(
            {
                "project_id": request.project_id,
                "name": f"drill-{request.suspected_key_name}",
                "scopes": ["logs.search"],
                "idempotency_key": f"create-{request.project_id}-{request.asset_id}-{request.subscriber_id}",
            }
        )
        temp_key = create_env.get("data") or {}
        temporary_key_id = str(temp_key.get("id"))
        temporary_key_plaintext = str(temp_key.get("key"))

        self.infrai.account.keys.rotate(
            temporary_key_id,
            {
                "grace_hours": request.grace_hours,
                "idempotency_key": f"rotate-{request.project_id}-{request.content_id}",
            },
        )

        logs_env = self.infrai.logs.search(
            {
                "marker": request.leak_marker,
                "project_id": request.project_id,
            }
        )
        log_hits = self._count_hits(logs_env.get("data"))

        if log_hits > 0:
            delivery = DigitalAssetDelivery.pause(request.asset_id, "key_exposure_drill")
            subscriber = SubscriberUpdates.queue_notice(request.subscriber_id, "key_exposure_drill")
            content = ContentProcessing.request_reprocess(request.content_id, "key_exposure_drill")
            blast_radius = "subscriber_and_asset_exposed"
        else:
            delivery = {"asset_id": request.asset_id, "status": "active"}
            subscriber = {"subscriber_id": request.subscriber_id, "status": "no_notice_needed"}
            content = {"content_id": request.content_id, "status": "no_reprocess_needed"}
            blast_radius = "no_matching_log_exposure"

        self.infrai.account.keys.revoke(temporary_key_id)

        return CreatorIncidentResult(
            incident_id=f"drill-{request.asset_id}-{request.subscriber_id}",
            suspected_key_id=suspected_key_id,
            temporary_key_id=temporary_key_id,
            temporary_key_plaintext=temporary_key_plaintext,
            log_hits=log_hits,
            blast_radius=blast_radius,
            asset_delivery_status=delivery["status"],
            subscriber_update_status=subscriber["status"],
            content_processing_status=content["status"],
        )

    @staticmethod
    def _find_key_id(data: Any, expected_name: str) -> str:
        if isinstance(data, dict):
            items = data.get("items") or data.get("keys") or []
        elif isinstance(data, list):
            items = data
        else:
            items = []
        for item in items:
            if item.get("name") == expected_name:
                return str(item.get("id"))
        raise ValueError(f"Key named '{expected_name}' was not found")

    @staticmethod
    def _count_hits(data: Any) -> int:
        if isinstance(data, dict):
            if isinstance(data.get("items"), list):
                return len(data["items"])
            if isinstance(data.get("results"), list):
                return len(data["results"])
            if isinstance(data.get("total"), int):
                return data["total"]
        if isinstance(data, list):
            return len(data)
        return 0


def run_creator_key_drill(request: CreatorIncidentRequest) -> CreatorIncidentResult:
    infrai = InfraiClient()
    service = CreatorKeyDrillService(infrai)
    return service.run(request)

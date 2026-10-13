"""TOBB user operations, wired to existing persistence/execution/audit adapters."""
from uuid import UUID

from app.modules.fairs.domain.exceptions import TobbReviewConflict


class TobbWorkflowService:
    def __init__(self, reviews, runs, runner, schedule, audit):
        self.reviews, self.runs, self.runner, self.schedule, self.audit = reviews, runs, runner, schedule, audit

    def start_preview(self, year: int, *, user_id: UUID, user_label: str) -> dict:
        run, created = self.runs.start([year], requested_by=user_id, requested_by_label=user_label)
        return self._dispatch(run, created)

    def _dispatch(self, run, created: bool) -> dict:
        if created:
            self.schedule(self.runner.run, run.id)
        return {"run": self.runs.view(run), "started": created}

    def apply_preview(self, run_id: UUID) -> dict:
        return self._dispatch(*self.runs.queue_apply(run_id))

    def retry(self, run_id: UUID, *, user_id: UUID, user_label: str) -> dict:
        return self._dispatch(*self.runs.queue_retry(run_id, user_id=user_id, user_label=user_label))

    def cancel(self, run_id: UUID, *, user_id: UUID) -> dict:
        return self.runs.request_cancel(run_id, user_id=user_id)

    def retry_notification(self, run_id: UUID) -> dict:
        self.runs.queue_notification_retry(run_id)
        self.schedule(self.runner.retry_notification, run_id)
        return self.runs.get_view(run_id)

    def get_run(self, run_id: UUID) -> dict:
        return self.runs.get_view(run_id)

    def history(self, *, offset: int = 0) -> dict:
        return {"items": self.runs.list_runs(offset=offset)}

    def pending(self, *, search: str = "", kind: str | None = None) -> dict:
        all_items = self.reviews.list_pending()
        counts: dict[str, int] = {}
        for item in all_items:
            counts[item["kind"]] = counts.get(item["kind"], 0) + 1
        return {"items": self.reviews.list_pending(search=search, kind=kind), "counts": counts, "pending_count": len(all_items)}

    def mappings(self) -> dict:
        return {"items": self.reviews.list_mappings()}

    def change_mapping(self, mapping_id: UUID, *, fair_id: UUID, auth, access_token: str) -> dict:
        self.reviews.change_mapping(mapping_id, fair_id=fair_id, user_id=auth.user_id)
        self.audit.record_event(organization_id=auth.organization_id, access_token=access_token,
            action="fair_crm.tobb.mapping_changed", resource_type="tobb_mapping", resource_id=str(mapping_id),
            metadata={"user_id": str(auth.user_id), "fair_id": str(fair_id), "job_scope": "system"})
        return {"id": str(mapping_id), "fair_id": str(fair_id)}

    def decide(self, body: dict, *, auth, access_token: str) -> dict:
        result = self.reviews.decide(body["id"], version=body["version"], decision=body["decision"],
            user_id=auth.user_id, target_fair_id=body.get("target_fair_id"), source_external_id=body.get("source_external_id"))
        if body["decision"] != "defer":
            self.audit.record_event(organization_id=auth.organization_id, access_token=access_token,
                action="fair_crm.tobb.review_decided", resource_type="tobb_review", resource_id=str(body["id"]),
                metadata={"user_id": str(auth.user_id), "decision": body["decision"], "kind": result["kind"],
                          "fair_id": result["fair_id"], "stored_values": result["stored_values"],
                          "proposed_values": result["proposed_values"], "job_scope": "system",
                          "target_fair_id": str(body["target_fair_id"]) if body.get("target_fair_id") else None,
                          "source_external_id": body.get("source_external_id")})
        return result

    def bulk_dates(self, items: list[dict], *, auth, access_token: str) -> dict:
        results = []
        for item in items:
            try:
                with self.reviews.decision_transaction():
                    current = next((row for row in self.reviews.list_pending() if row["id"] == str(item["id"])), None)
                    if current is None or current["kind"] != "dates" or item["decision"] not in {"apply", "keep"}:
                        raise ValueError("Toplu işlem yalnız bekleyen tarih önerilerinde Uygula/Koru destekler")
                    result = self.decide(item, auth=auth, access_token=access_token)
                results.append({"id": str(item["id"]), "success": True, "current": result})
            except ValueError as exc:
                results.append({"id": str(item["id"]), "success": False, "error": str(exc),
                                "current": exc.current if isinstance(exc, TobbReviewConflict) else None})
        return {"items": results}

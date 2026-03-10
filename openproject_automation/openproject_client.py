from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any
import base64
import json
from urllib.parse import quote

import httpx

from openproject_automation.config import AppConfig


def _compact_text(value: object, max_chars: int) -> str:
    text = "" if value is None else str(value)
    text = text.strip()
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 3].rstrip() + "..."


def _match_text(candidate: str, query: str) -> bool:
    if not query:
        return True
    return query.casefold() in candidate.casefold()


def _link_title(entity: dict[str, Any], link_name: str) -> str:
    links = entity.get("_links")
    if not isinstance(links, dict):
        return ""
    link = links.get(link_name)
    if not isinstance(link, dict):
        return ""
    return str(link.get("title") or "")


def _description_raw(entity: dict[str, Any]) -> str:
    description = entity.get("description")
    if isinstance(description, dict):
        raw = description.get("raw")
        if raw is not None:
            return str(raw)
    if description is None:
        return ""
    return str(description)


@dataclass
class OpenProjectApiError(RuntimeError):
    message: str
    status_code: int | None = None
    response_body: str = ""

    def __str__(self) -> str:
        if self.status_code is None:
            return self.message
        return f"{self.message} (HTTP {self.status_code})"


class OpenProjectClient:
    def __init__(self, config: AppConfig) -> None:
        token = base64.b64encode(f"apikey:{config.openproject_api_key}".encode("utf-8")).decode("ascii")
        self._base_url = config.openproject_base_url.rstrip("/")
        self._max_items = config.max_items_per_tool_call
        self._max_text_chars = config.max_text_chars
        self._client = httpx.Client(
            base_url=self._base_url,
            headers={
                "Accept": "application/hal+json",
                "Content-Type": "application/json",
                "Authorization": f"Basic {token}",
                "User-Agent": "openproject-automation/0.1.0",
            },
            timeout=config.openproject_timeout_seconds,
        )

    def close(self) -> None:
        self._client.close()

    def _request(
        self,
        method: str,
        path: str,
        *,
        expected: Iterable[int] = (200,),
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        response = self._client.request(method, path, params=params, json=json_body)
        if response.status_code not in set(expected):
            raise OpenProjectApiError(
                message=f"OpenProject request failed for {method} {path}",
                status_code=response.status_code,
                response_body=response.text,
            )
        if not response.content:
            return {}
        return response.json()

    def _request_first_success(
        self,
        method: str,
        paths: list[str],
        *,
        expected: Iterable[int] = (200,),
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        last_error: OpenProjectApiError | None = None
        for path in paths:
            try:
                return self._request(method, path, expected=expected, params=params, json_body=json_body)
            except OpenProjectApiError as exc:
                if exc.status_code == 404:
                    last_error = exc
                    continue
                raise
        if last_error is not None:
            raise last_error
        raise OpenProjectApiError(f"No compatible endpoint succeeded for {method}: {paths}")

    def _paginate(
        self,
        path: str,
        *,
        page_size: int = 100,
        query: str = "",
        fields_for_search: tuple[str, ...] = ("name",),
        params: dict[str, Any] | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        current_page = 1
        items: list[dict[str, Any]] = []
        safe_limit = limit if limit is not None else self._max_items

        while len(items) < safe_limit:
            merged_params = {"offset": current_page, "pageSize": page_size}
            if params:
                merged_params.update(params)
            payload = self._request("GET", path, params=merged_params)
            elements = payload.get("_embedded", {}).get("elements", [])
            if not isinstance(elements, list):
                break

            for element in elements:
                haystacks = [str(element.get(field, "")) for field in fields_for_search]
                if query and not any(_match_text(text, query) for text in haystacks):
                    continue
                items.append(element)
                if len(items) >= safe_limit:
                    break

            count = payload.get("count")
            total = payload.get("total")
            if not isinstance(count, int) or not isinstance(total, int) or current_page + count > total or not elements:
                break
            current_page += count

        return items

    def _normalize_project(self, project: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": project.get("id"),
            "identifier": project.get("identifier"),
            "name": project.get("name"),
            "type": project.get("_type"),
            "active": project.get("active"),
            "description": _compact_text(_description_raw(project), self._max_text_chars),
            "href": project.get("_links", {}).get("self", {}).get("href"),
        }

    def _normalize_work_package(self, work_package: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": work_package.get("id"),
            "subject": work_package.get("subject"),
            "type": _link_title(work_package, "type"),
            "status": _link_title(work_package, "status"),
            "priority": _link_title(work_package, "priority"),
            "assignee": _link_title(work_package, "assignee"),
            "project": _link_title(work_package, "project"),
            "updatedAt": work_package.get("updatedAt"),
            "createdAt": work_package.get("createdAt"),
            "startDate": work_package.get("startDate"),
            "dueDate": work_package.get("dueDate"),
            "lockVersion": work_package.get("lockVersion"),
            "description": _compact_text(_description_raw(work_package), self._max_text_chars),
            "href": work_package.get("_links", {}).get("self", {}).get("href"),
        }

    def _normalize_member(self, member: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": member.get("id"),
            "name": member.get("name") or member.get("title"),
            "type": member.get("_type"),
            "href": member.get("_links", {}).get("self", {}).get("href"),
        }

    def _normalize_activity(self, activity: dict[str, Any]) -> dict[str, Any]:
        comment = activity.get("comment", {})
        comment_raw = comment.get("raw") if isinstance(comment, dict) else comment
        return {
            "id": activity.get("id"),
            "createdAt": activity.get("createdAt"),
            "user": _link_title(activity, "user"),
            "comment": _compact_text(comment_raw, self._max_text_chars),
        }

    def list_projects(self, name_contains: str = "", limit: int | None = None) -> dict[str, Any]:
        projects = self._paginate(
            "/api/v3/projects",
            query=name_contains,
            fields_for_search=("name", "identifier"),
            limit=limit,
        )
        normalized = [self._normalize_project(project) for project in projects]
        return {"items": normalized, "count": len(normalized)}

    def get_project_raw(self, project_ref: str) -> dict[str, Any]:
        encoded = quote(str(project_ref), safe="")
        try:
            return self._request("GET", f"/api/v3/projects/{encoded}")
        except OpenProjectApiError as exc:
            if exc.status_code != 404:
                raise

        projects = self._paginate("/api/v3/projects", page_size=100, limit=100, query=str(project_ref), fields_for_search=("name", "identifier"))
        for project in projects:
            if str(project.get("identifier", "")).casefold() == str(project_ref).casefold():
                return project
            if str(project.get("name", "")).casefold() == str(project_ref).casefold():
                return project
        raise OpenProjectApiError(f"Could not resolve project: {project_ref}")

    def get_project(self, project_ref: str) -> dict[str, Any]:
        return self._normalize_project(self.get_project_raw(project_ref))

    def _project_collection_paths(self, project_id: int, suffix: str) -> list[str]:
        return [
            f"/api/v3/workspaces/{project_id}/{suffix}",
            f"/api/v3/projects/{project_id}/{suffix}",
        ]

    def _project_collection(
        self,
        project_ref: str,
        suffix: str,
        *,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        project = self.get_project_raw(project_ref)
        last_error: OpenProjectApiError | None = None
        for path in self._project_collection_paths(int(project["id"]), suffix):
            try:
                return self._paginate(path, limit=limit)
            except OpenProjectApiError as exc:
                if exc.status_code == 404:
                    last_error = exc
                    continue
                raise
        if last_error is not None:
            raise last_error
        raise OpenProjectApiError(f"Could not load collection '{suffix}' for project: {project_ref}")

    def list_project_types(self, project_ref: str, limit: int | None = None) -> dict[str, Any]:
        items = self._project_collection(project_ref, "types", limit=limit)
        normalized = [
            {
                "id": item.get("id"),
                "name": item.get("name"),
                "isDefault": item.get("isDefault"),
                "href": item.get("_links", {}).get("self", {}).get("href"),
            }
            for item in items
        ]
        return {"items": normalized, "count": len(normalized)}

    def list_available_assignees(self, project_ref: str, limit: int | None = None) -> dict[str, Any]:
        items = self._project_collection(project_ref, "available_assignees", limit=limit)
        normalized = [self._normalize_member(item) for item in items]
        return {"items": normalized, "count": len(normalized)}

    def list_statuses(self, limit: int | None = None) -> dict[str, Any]:
        items = self._paginate("/api/v3/statuses", limit=limit)
        normalized = [
            {
                "id": item.get("id"),
                "name": item.get("name"),
                "isClosed": item.get("isClosed"),
                "href": item.get("_links", {}).get("self", {}).get("href"),
            }
            for item in items
        ]
        return {"items": normalized, "count": len(normalized)}

    def list_priorities(self, limit: int | None = None) -> dict[str, Any]:
        items = self._paginate("/api/v3/priorities", limit=limit)
        normalized = [
            {
                "id": item.get("id"),
                "name": item.get("name"),
                "href": item.get("_links", {}).get("self", {}).get("href"),
            }
            for item in items
        ]
        return {"items": normalized, "count": len(normalized)}

    def list_work_packages(
        self,
        *,
        project: str | None = None,
        search: str = "",
        limit: int | None = None,
        filters_json: str = "",
    ) -> dict[str, Any]:
        params: dict[str, Any] = {}
        if filters_json:
            params["filters"] = filters_json

        if project:
            project_payload = self.get_project_raw(project)
            items = self._request_first_success(
                "GET",
                self._project_collection_paths(int(project_payload["id"]), "work_packages"),
                params={"offset": 1, "pageSize": max(25, min(limit or self._max_items, 100)), **params},
            ).get("_embedded", {}).get("elements", [])
            if not isinstance(items, list):
                items = []
        else:
            items = self._paginate("/api/v3/work_packages", limit=limit, params=params)

        normalized: list[dict[str, Any]] = []
        for work_package in items:
            normalized_item = self._normalize_work_package(work_package)
            candidate = f"{normalized_item['subject']} {normalized_item['description']}"
            if not _match_text(candidate, search):
                continue
            normalized.append(normalized_item)
            if len(normalized) >= (limit or self._max_items):
                break

        return {"items": normalized, "count": len(normalized)}

    def get_work_package_raw(self, work_package_id: int | str) -> dict[str, Any]:
        return self._request("GET", f"/api/v3/work_packages/{int(work_package_id)}")

    def list_work_package_activities(self, work_package_id: int | str, limit: int | None = None) -> dict[str, Any]:
        payload = self._request(
            "GET",
            f"/api/v3/work_packages/{int(work_package_id)}/activities",
            params={"offset": 1, "pageSize": limit or self._max_items},
        )
        items = payload.get("_embedded", {}).get("elements", [])
        if not isinstance(items, list):
            items = []
        normalized = [self._normalize_activity(item) for item in items[: (limit or self._max_items)]]
        return {"items": normalized, "count": len(normalized)}

    def get_work_package(self, work_package_id: int | str, *, include_activities: bool = True, activity_limit: int = 5) -> dict[str, Any]:
        payload = self.get_work_package_raw(work_package_id)
        normalized = self._normalize_work_package(payload)
        if include_activities:
            normalized["activities"] = self.list_work_package_activities(work_package_id, limit=activity_limit)["items"]
        return normalized

    def _resolve_from_items(self, ref: str | int, items: list[dict[str, Any]], *, label: str, keys: tuple[str, ...]) -> dict[str, Any]:
        text_ref = str(ref).strip()
        for item in items:
            if str(item.get("id", "")) == text_ref:
                return item
        for item in items:
            for key in keys:
                if str(item.get(key, "")).casefold() == text_ref.casefold():
                    return item
        raise OpenProjectApiError(f"Could not resolve {label}: {ref}")

    def _resolve_type_href(self, project_ref: str, type_ref: str | int | None) -> str:
        types_payload = self.list_project_types(project_ref, limit=100)["items"]
        if not types_payload:
            raise OpenProjectApiError(f"No types available for project: {project_ref}")
        if not type_ref:
            for item in types_payload:
                if item.get("isDefault"):
                    return str(item["href"])
            return str(types_payload[0]["href"])
        resolved = self._resolve_from_items(type_ref, types_payload, label="type", keys=("name",))
        return str(resolved["href"])

    def _resolve_priority_href(self, priority_ref: str | int) -> str:
        priorities = self.list_priorities(limit=100)["items"]
        resolved = self._resolve_from_items(priority_ref, priorities, label="priority", keys=("name",))
        return str(resolved["href"])

    def _resolve_status_href(self, status_ref: str | int) -> str:
        statuses = self.list_statuses(limit=100)["items"]
        resolved = self._resolve_from_items(status_ref, statuses, label="status", keys=("name",))
        return str(resolved["href"])

    def _resolve_assignee_href(self, project_ref: str, assignee_ref: str | int) -> str:
        assignees = self.list_available_assignees(project_ref, limit=100)["items"]
        resolved = self._resolve_from_items(assignee_ref, assignees, label="assignee", keys=("name",))
        return str(resolved["href"])

    def create_work_package(
        self,
        *,
        project: str,
        subject: str,
        description: str | None = None,
        type_ref: str | int | None = None,
        priority_ref: str | int | None = None,
        assignee_ref: str | int | None = None,
        start_date: str | None = None,
        due_date: str | None = None,
        notify: bool = False,
    ) -> dict[str, Any]:
        project_payload = self.get_project_raw(project)
        project_id = int(project_payload["id"])

        links: dict[str, Any] = {"type": {"href": self._resolve_type_href(project, type_ref)}}
        if priority_ref:
            links["priority"] = {"href": self._resolve_priority_href(priority_ref)}
        if assignee_ref:
            links["assignee"] = {"href": self._resolve_assignee_href(project, assignee_ref)}

        body: dict[str, Any] = {"subject": subject, "_links": links}
        if description is not None:
            body["description"] = {"format": "markdown", "raw": description}
        if start_date:
            body["startDate"] = start_date
        if due_date:
            body["dueDate"] = due_date

        payload = self._request_first_success(
            "POST",
            self._project_collection_paths(project_id, "work_packages"),
            expected=(200, 201),
            params={"notify": json.dumps(notify)},
            json_body=body,
        )
        return self._normalize_work_package(payload)

    def update_work_package(
        self,
        *,
        work_package_id: int | str,
        subject: str | None = None,
        description: str | None = None,
        status_ref: str | int | None = None,
        priority_ref: str | int | None = None,
        assignee_ref: str | int | None = None,
        start_date: str | None = None,
        due_date: str | None = None,
        notify: bool = False,
    ) -> dict[str, Any]:
        current = self.get_work_package_raw(work_package_id)
        project_href = current.get("_links", {}).get("project", {}).get("href", "")
        project_id = str(project_href).rstrip("/").split("/")[-1]

        body: dict[str, Any] = {"lockVersion": current.get("lockVersion")}
        links: dict[str, Any] = {}

        if subject is not None:
            body["subject"] = subject
        if description is not None:
            body["description"] = {"format": "markdown", "raw": description}
        if status_ref:
            links["status"] = {"href": self._resolve_status_href(status_ref)}
        if priority_ref:
            links["priority"] = {"href": self._resolve_priority_href(priority_ref)}
        if assignee_ref:
            links["assignee"] = {"href": self._resolve_assignee_href(project_id, assignee_ref)}
        if start_date:
            body["startDate"] = start_date
        if due_date:
            body["dueDate"] = due_date
        if links:
            body["_links"] = links

        payload = self._request(
            "PATCH",
            f"/api/v3/work_packages/{int(work_package_id)}",
            expected=(200,),
            params={"notify": json.dumps(notify)},
            json_body=body,
        )
        return self._normalize_work_package(payload)

    def add_comment(
        self,
        *,
        work_package_id: int | str,
        comment: str,
        internal: bool = False,
        notify: bool = False,
    ) -> dict[str, Any]:
        payload = self._request(
            "POST",
            f"/api/v3/work_packages/{int(work_package_id)}/activities",
            expected=(200, 201),
            params={"notify": json.dumps(notify)},
            json_body={"comment": {"raw": comment}, "internal": internal},
        )
        return self._normalize_activity(payload)

from __future__ import annotations

from langchain_core.tools import tool

from openproject_automation.config import AppConfig
from openproject_automation.openproject_client import OpenProjectClient


def _none_if_blank(value: str) -> str | None:
    return value.strip() or None


def build_openproject_tools(config: AppConfig) -> list[object]:
    if not config.has_openproject:
        return []
    client = OpenProjectClient(config)

    @tool
    def openproject_list_projects(name_contains: str = "", limit: int = 20) -> dict:
        """List OpenProject projects/workspaces. Use this first when you need project IDs or identifiers."""
        return client.list_projects(name_contains=name_contains, limit=limit)

    @tool
    def openproject_get_project(project: str) -> dict:
        """Get one project by numeric ID, identifier, or exact name."""
        return client.get_project(project)

    @tool
    def openproject_list_project_types(project: str, limit: int = 50) -> dict:
        """List available work package types for a project. Use before creating work packages if type is unclear."""
        return client.list_project_types(project, limit=limit)

    @tool
    def openproject_list_available_assignees(project: str, limit: int = 50) -> dict:
        """List assignees that can be assigned inside a project."""
        return client.list_available_assignees(project, limit=limit)

    @tool
    def openproject_list_statuses(limit: int = 50) -> dict:
        """List available global work package statuses."""
        return client.list_statuses(limit=limit)

    @tool
    def openproject_list_priorities(limit: int = 50) -> dict:
        """List available global work package priorities."""
        return client.list_priorities(limit=limit)

    @tool
    def openproject_list_work_packages(project: str = "", search: str = "", limit: int = 20, filters_json: str = "") -> dict:
        """List work packages globally or inside one project. Keep limit small to control context size."""
        return client.list_work_packages(
            project=_none_if_blank(project),
            search=search,
            limit=limit,
            filters_json=filters_json,
        )

    @tool
    def openproject_get_work_package(work_package_id: int, include_activities: bool = True, activity_limit: int = 5) -> dict:
        """Get one work package and optionally include recent comments/activities."""
        return client.get_work_package(
            work_package_id,
            include_activities=include_activities,
            activity_limit=activity_limit,
        )

    @tool
    def openproject_list_work_package_activities(work_package_id: int, limit: int = 10) -> dict:
        """List recent comments/activities for one work package."""
        return client.list_work_package_activities(work_package_id, limit=limit)

    @tool
    def openproject_create_work_package(
        project: str,
        subject: str,
        description: str = "",
        type: str = "",
        priority: str = "",
        assignee: str = "",
        start_date: str = "",
        due_date: str = "",
        notify: bool = False,
    ) -> dict:
        """Create a work package. Only call this after the user clearly asked to create a task."""
        return client.create_work_package(
            project=project,
            subject=subject,
            description=_none_if_blank(description),
            type_ref=_none_if_blank(type),
            priority_ref=_none_if_blank(priority),
            assignee_ref=_none_if_blank(assignee),
            start_date=_none_if_blank(start_date),
            due_date=_none_if_blank(due_date),
            notify=notify,
        )

    @tool
    def openproject_update_work_package(
        work_package_id: int,
        subject: str = "",
        description: str = "",
        status: str = "",
        priority: str = "",
        assignee: str = "",
        start_date: str = "",
        due_date: str = "",
        notify: bool = False,
    ) -> dict:
        """Update a work package. Only call this after the user clearly asked to edit the task."""
        return client.update_work_package(
            work_package_id=work_package_id,
            subject=_none_if_blank(subject),
            description=_none_if_blank(description),
            status_ref=_none_if_blank(status),
            priority_ref=_none_if_blank(priority),
            assignee_ref=_none_if_blank(assignee),
            start_date=_none_if_blank(start_date),
            due_date=_none_if_blank(due_date),
            notify=notify,
        )

    @tool
    def openproject_add_comment(work_package_id: int, comment: str, internal: bool = False, notify: bool = False) -> dict:
        """Add a comment to a work package. Only call this after the user clearly asked to comment."""
        return client.add_comment(
            work_package_id=work_package_id,
            comment=comment,
            internal=internal,
            notify=notify,
        )

    return [
        openproject_list_projects,
        openproject_get_project,
        openproject_list_project_types,
        openproject_list_available_assignees,
        openproject_list_statuses,
        openproject_list_priorities,
        openproject_list_work_packages,
        openproject_get_work_package,
        openproject_list_work_package_activities,
        openproject_create_work_package,
        openproject_update_work_package,
        openproject_add_comment,
    ]

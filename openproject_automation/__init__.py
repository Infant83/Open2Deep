"""OpenProject automation package."""

__all__ = ["AgentBundle", "build_agent_bundle"]


def __getattr__(name: str):
    if name in {"AgentBundle", "build_agent_bundle"}:
        from openproject_automation.agent import AgentBundle, build_agent_bundle

        return {"AgentBundle": AgentBundle, "build_agent_bundle": build_agent_bundle}[name]
    raise AttributeError(name)

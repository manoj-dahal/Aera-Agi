"""Memory Notes — example AERA plugin (docs/17-PLUGIN-SYSTEM.md).

Demonstrates the plugin contract:
    setup(api)    — called on enable; register event handlers, do setup
    teardown(api) — called on disable/reload/remove

The `api` object is a PluginAPI facade gated by the permissions the user
approved (memory_graph + notifications here).
"""


async def setup(api) -> None:
    # Documented Event System: plugins receive events from the bus.
    async def on_automation(event) -> None:
        workflow = event.data.get("workflow", "unknown")
        status = event.data.get("status", "unknown")
        api.memory_store(f"noted automation run: {workflow} -> {status}", importance=0.4)

    api.on_event("automation.executed", on_automation)
    api.memory_store("memory-notes plugin enabled", importance=0.2)
    await api.notify("Memory Notes plugin is now active")


async def teardown(api) -> None:
    await api.notify("Memory Notes plugin deactivated")

import importlib
from typing import Any, Callable, Dict, List

plugins_to_create: Dict[str, Callable[..., Any]] = {}


def register_plugin(plugin: str, call: Callable[..., Any]) -> None:
    plugins_to_create[plugin] = call


def create_plugin(arguments: Dict[str, Any]) -> Any:
    args_copy = arguments.copy()
    plugin_type = args_copy.pop("type")
    try:
        creator_call = plugins_to_create[plugin_type]
    except KeyError as exc:
        raise ValueError(f"Unknown plugin {plugin_type!r}") from exc
    return creator_call(**args_copy)


def load_plugins(plugin_path: str, plugin_name: List[str]) -> None:
    for plugin_file in plugin_name:
        plugin = importlib.import_module(plugin_path + plugin_file)
        plugin.register()

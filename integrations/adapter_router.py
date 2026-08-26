"""
Routes a golden dataset example to the correct adapter based on its
target_system field. This is the ONLY place that needs to know the mapping
between target_system strings and adapter modules - everything else just
calls route_to_adapter().
"""

from integrations import rag_adapter, coach_agent_adapter, multiagent_adapter

ADAPTER_MAP = {
    "rag": rag_adapter.get_answer,
    "coach_agent": coach_agent_adapter.get_answer,
    "multiagent_pipeline": multiagent_adapter.get_answer,
}


def route_to_adapter(example: dict) -> tuple:
    """
    Returns (context_used, answer) by calling the adapter matching
    example["target_system"]. Raises a clear error for an unknown
    target_system rather than silently returning empty results.
    """
    target_system = example["target_system"]
    adapter_fn = ADAPTER_MAP.get(target_system)

    if adapter_fn is None:
        raise ValueError(
            f"No adapter registered for target_system='{target_system}' "
            f"(example id={example['id']}). Known systems: {list(ADAPTER_MAP.keys())}"
        )

    return adapter_fn(example["query"])
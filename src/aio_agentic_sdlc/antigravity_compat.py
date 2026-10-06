import warnings

from google.antigravity import CapabilitiesConfig, LocalAgentConfig

# google-antigravity 0.1.17 reads its own deprecated
# CapabilitiesConfig.compaction_threshold field during validation, so building
# an agent config warns even though we never set that field.
_COMPACTION_DEPRECATION = "CapabilitiesConfig.compaction_threshold is deprecated"


def local_agent_config(system_instructions: str) -> LocalAgentConfig:
    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore", message=_COMPACTION_DEPRECATION, category=DeprecationWarning
        )
        return LocalAgentConfig(
            system_instructions=system_instructions,
            capabilities=CapabilitiesConfig(),
        )

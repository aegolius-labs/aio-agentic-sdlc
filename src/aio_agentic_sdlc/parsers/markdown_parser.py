import os

import yaml

from aio_agentic_sdlc.dag_models import EdgeType, NodeType

from .base import BaseFileParser


# aio-sdlc-mapping-approval: {"candidate_reality_id":"a4114ac7-09b1-5a58-ae83-45acdaff1884","identity_approval":{"approved_at":"2026-11-08T19:08:23+00:00","approved_by":"Felix","candidate_reality_id":"a4114ac7-09b1-5a58-ae83-45acdaff1884","evidence_digest":"26b71cb95a38245614b5184811d5ef6b0a0e5f19d39198298d338c98a8c5ebd8","intent_id":"a937dc0f-c261-461a-975f-03950289be88","rationale":"Felix approved the 2026-11-08 mapping and triage packet on its decision card: MarkdownAgentParser is the implementation identity of 'Markdown Parser'. Evidence digest unchanged since the packet. Identity only; it does not approve intent or prove acceptance.","schema_version":1,"source_path":"src/aio_agentic_sdlc/parsers/markdown_parser.py","source_sha256":"57b1e6742d70dc10cdc9443f2ed0d3d1c00fe23dfbdad3e5f56b3868eda7f9ed","symbol_kind":"class","symbol_name":"MarkdownAgentParser"},"intent_id":"a937dc0f-c261-461a-975f-03950289be88","maintenance_approval":{"approved_at":"2026-11-10T12:17:12+00:00","approved_by":"Felix","evidence_digest":"594f65248050c1a540683219b912d83927a26ec3b92830bc717fe2e45a31ff22","rationale":"Felix approved the batch refresh of the 15 older mapping receipts on the 2026-11-10 decision card, at the review digests listed in .aio-agentic-sdlc/changes/symbol-receipts-2026-11-09/refresh-batch.json. Rebinds the receipt to its symbol; the approved identity is unchanged and no behavior or acceptance is claimed.","supersedes_receipt_sha256":"3a44ae08a9d8890a68fad4934f419611d2a797e993242cbb235bcf42b3050c84"},"schema_version":2,"source_path":"src/aio_agentic_sdlc/parsers/markdown_parser.py","source_sha256":"57b1e6742d70dc10cdc9443f2ed0d3d1c00fe23dfbdad3e5f56b3868eda7f9ed","symbol_kind":"class","symbol_name":"MarkdownAgentParser","symbol_sha256":"e066030e02c493b2f5cdfda53475b2310007a3b76b150bdd659f9a1712767d8f"}
# aio-sdlc-node: a937dc0f-c261-461a-975f-03950289be88
class MarkdownAgentParser(BaseFileParser):
    def parse(self, generator, file_path: str):
        rel_path = os.path.relpath(file_path, generator.root_dir)
        normalized_rel = rel_path.replace(os.sep, "/")
        if not normalized_rel.startswith(".agents/agents/"):
            return

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except UnicodeDecodeError:
            return

        if not content.startswith("---"):
            return

        parts = content.split("---", 2)
        if len(parts) >= 3:
            frontmatter = parts[1]
            try:
                data = yaml.safe_load(frontmatter)
                if data and isinstance(data, dict):
                    name = data.get("name")
                    obj_type = data.get("type")
                    tools = data.get("tools")
                    desc = data.get("description", f"Agent {name}")

                    is_agent = False
                    if obj_type == "agent":
                        is_agent = True
                    elif obj_type is None and (name or tools is not None):
                        is_agent = True

                    if name and is_agent:
                        agent_id = name

                        # Extract Node ID from metadata (if present)
                        if "metadata" in data and isinstance(data["metadata"], dict):
                            node_id = data["metadata"].get("node_id")
                            if node_id:
                                agent_id = node_id

                        generator._add_node(
                            id=agent_id,
                            node_type=NodeType.AGENT,
                            name=name,
                            description=desc,
                        )
                        generator._add_edge("system_root", agent_id, EdgeType.CONTAINS)
            except yaml.YAMLError:
                pass

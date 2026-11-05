from .base import BaseFileParser
from .markdown_parser import MarkdownAgentParser
from .python_parser import PYTHON_LANGUAGE, TreeSitterParser
from .visitors import TreeSitterVisitor


# aio-sdlc-mapping-approval: {"candidate_reality_id":"a7278b66-0ac6-5e6b-91d7-0604d42cc40f","identity_approval":{"approved_at":"2026-08-13T19:29:14.286017-04:00","approved_by":"Felix","candidate_reality_id":"a7278b66-0ac6-5e6b-91d7-0604d42cc40f","evidence_digest":"1c322789fdfb8510307391326e0f9c8b16eb36833922846aaaf460b2c857b854","intent_id":"d0307d83-371e-4bb6-925d-84a4b70beb6b","rationale":"Approved the ParserFactory source identity; extension-based parser selection responsibility and public API match.","schema_version":1,"source_path":"src/aio_agentic_sdlc/parsers/factory.py","source_sha256":"532714443f9a88c178c6e666de53447ca1c017f0525941802b4bdbe2ef088b03","symbol_kind":"class","symbol_name":"ParserFactory"},"intent_id":"d0307d83-371e-4bb6-925d-84a4b70beb6b","maintenance_approval":{"approved_at":"2026-11-05T19:00:00+00:00","approved_by":"Felix","evidence_digest":"ced9a77eb02ab1a2d28f734b90082364179bdbae64d3bbdc3ebf34af41a0e640","rationale":"Source changed since the receipt was approved; the marker still names the same symbol. Refreshed by Claude under Felix's standing approval of 2026-11-05 for work waiting on him. Identity only; acceptance criteria stay separately reviewable.","supersedes_receipt_sha256":"6c6ad9ad8a77176a25f6d1db8d98665eb63b574f7c77c0971f77e8ef1e04ae30"},"schema_version":2,"source_path":"src/aio_agentic_sdlc/parsers/factory.py","source_sha256":"84c81ddd69d71b4de629ceab40ccd8cec81f592e028bb57a222e9bd2d5c13a2a","symbol_kind":"class","symbol_name":"ParserFactory"}
# aio-sdlc-node: d0307d83-371e-4bb6-925d-84a4b70beb6b
class ParserFactory:
    def __init__(self):
        self.parsers = {
            ".py": TreeSitterParser(PYTHON_LANGUAGE, TreeSitterVisitor),
            ".md": MarkdownAgentParser(),
        }

    def get_parser(self, ext: str) -> BaseFileParser | None:
        return self.parsers.get(ext)

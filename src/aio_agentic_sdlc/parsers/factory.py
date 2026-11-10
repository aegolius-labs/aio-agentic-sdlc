from .base import BaseFileParser
from .markdown_parser import MarkdownAgentParser
from .python_parser import PYTHON_LANGUAGE, TreeSitterParser
from .typescript_parser import TypeScriptParser
from .visitors import TreeSitterVisitor


# aio-sdlc-mapping-approval: {"candidate_reality_id":"a7278b66-0ac6-5e6b-91d7-0604d42cc40f","identity_approval":{"approved_at":"2026-08-13T19:29:14.286017-04:00","approved_by":"Felix","candidate_reality_id":"a7278b66-0ac6-5e6b-91d7-0604d42cc40f","evidence_digest":"1c322789fdfb8510307391326e0f9c8b16eb36833922846aaaf460b2c857b854","intent_id":"d0307d83-371e-4bb6-925d-84a4b70beb6b","rationale":"Approved the ParserFactory source identity; extension-based parser selection responsibility and public API match.","schema_version":1,"source_path":"src/aio_agentic_sdlc/parsers/factory.py","source_sha256":"532714443f9a88c178c6e666de53447ca1c017f0525941802b4bdbe2ef088b03","symbol_kind":"class","symbol_name":"ParserFactory"},"intent_id":"d0307d83-371e-4bb6-925d-84a4b70beb6b","maintenance_approval":{"approved_at":"2026-11-10T12:17:12+00:00","approved_by":"Felix","evidence_digest":"0382b410a7e1286b1cb864e7de7bd85e52274374f6b06e06c6ca87a54a52ca07","rationale":"Felix approved the batch refresh of the 15 older mapping receipts on the 2026-11-10 decision card, at the review digests listed in .aio-agentic-sdlc/changes/symbol-receipts-2026-11-09/refresh-batch.json. Rebinds the receipt to its symbol; the approved identity is unchanged and no behavior or acceptance is claimed.","supersedes_receipt_sha256":"811164f7b55216a051a5f4dd33dcddbab514e078792793c9b73d8ae4738538be"},"schema_version":2,"source_path":"src/aio_agentic_sdlc/parsers/factory.py","source_sha256":"84c81ddd69d71b4de629ceab40ccd8cec81f592e028bb57a222e9bd2d5c13a2a","symbol_kind":"class","symbol_name":"ParserFactory","symbol_sha256":"ba0d2fef63b25bb114e4a8465cc307c7e3134386092b70b54fd9f41adea78dde"}
# aio-sdlc-node: d0307d83-371e-4bb6-925d-84a4b70beb6b
class ParserFactory:
    def __init__(self):
        self.parsers = {
            ".py": TreeSitterParser(PYTHON_LANGUAGE, TreeSitterVisitor),
            ".md": MarkdownAgentParser(),
        }
        typescript = TypeScriptParser()
        self.parsers[".ts"] = typescript
        self.parsers[".tsx"] = typescript

    def get_parser(self, ext: str) -> BaseFileParser | None:
        return self.parsers.get(ext)

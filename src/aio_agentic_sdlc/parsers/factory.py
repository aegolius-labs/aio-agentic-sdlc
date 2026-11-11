from .base import BaseFileParser
from .markdown_parser import MarkdownAgentParser
from .python_parser import PYTHON_LANGUAGE, TreeSitterParser
from .typescript_parser import TypeScriptParser
from .visitors import TreeSitterVisitor


# aio-sdlc-mapping-approval: {"candidate_reality_id":"a7278b66-0ac6-5e6b-91d7-0604d42cc40f","identity_approval":{"approved_at":"2026-08-13T19:29:14.286017-04:00","approved_by":"Felix","candidate_reality_id":"a7278b66-0ac6-5e6b-91d7-0604d42cc40f","evidence_digest":"1c322789fdfb8510307391326e0f9c8b16eb36833922846aaaf460b2c857b854","intent_id":"d0307d83-371e-4bb6-925d-84a4b70beb6b","rationale":"Approved the ParserFactory source identity; extension-based parser selection responsibility and public API match.","schema_version":1,"source_path":"src/aio_agentic_sdlc/parsers/factory.py","source_sha256":"532714443f9a88c178c6e666de53447ca1c017f0525941802b4bdbe2ef088b03","symbol_kind":"class","symbol_name":"ParserFactory"},"intent_id":"d0307d83-371e-4bb6-925d-84a4b70beb6b","maintenance_approval":{"approved_at":"2026-11-11T12:35:24+00:00","approved_by":"Felix","evidence_digest":"a47911c0fdbf706c00d2035bc4641b0e5f804a1b92432558896f514ef777c707","rationale":"Felix approved refreshing the ParserFactory receipt on the 2026-11-11 decision card, at the review digest in .aio-agentic-sdlc/changes/typescript-parser-2026-11-10/refresh-batch.json. The class still selects a parser by file extension; it gains the TypeScript entries. The approved identity is unchanged and no behavior or acceptance is claimed.","supersedes_receipt_sha256":"880d50a4a4de7f70f2aacd58faa9aa580fe16e5e48aebf36c0cfdf598e6a643c"},"schema_version":2,"source_path":"src/aio_agentic_sdlc/parsers/factory.py","source_sha256":"2313617cf1c776889f25d0e3e4020e43f3b209e2f56afbb89d9b759859f21d08","symbol_kind":"class","symbol_name":"ParserFactory","symbol_sha256":"420c5714c7ebc3bc0d99aef60a218fa55a9c028ba4e75a371d494fb566aa61a2"}
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

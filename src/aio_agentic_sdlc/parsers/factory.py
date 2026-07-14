from .python_parser import TreeSitterParser, PYTHON_LANGUAGE
from .markdown_parser import MarkdownAgentParser
from .visitors import TreeSitterVisitor
from .base import BaseFileParser

class ParserFactory:
    def __init__(self):
        self.parsers = {
            '.py': TreeSitterParser(PYTHON_LANGUAGE, TreeSitterVisitor),
            '.md': MarkdownAgentParser()
        }

    def get_parser(self, ext: str) -> BaseFileParser | None:
        return self.parsers.get(ext)

"""
Parser that accepts text/plain and parses body as JSON.
Telegram Mini App / some clients send JSON with Content-Type: text/plain.
"""
import json
from rest_framework.parsers import BaseParser


class PlainTextJSONParser(BaseParser):
    """Accept text/plain and parse body as JSON (for Telegram Mini App and similar clients)."""
    media_type = 'text/plain'

    def parse(self, stream, media_type=None, parser_context=None):
        body = stream.read().decode('utf-8')
        if not body.strip():
            return {}
        return json.loads(body)

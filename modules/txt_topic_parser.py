"""
TXT Topic Parser
================
Parses txt files to extract topic headings and their content.

File format:
    # Batch Name                          ← file title, skipped
    Heading Name | 12345                  ← heading with topic ID already set
    Heading Name                          ← heading without topic ID yet
    Content Name : URL                    ← content item under current heading
    Content Name://URL                    ← also valid

    Inline topic prefix format (topic embedded in each content line):
    [Topic Name] Content Name: URL        ← topic extracted from [...]
    [Topic Name] Content Name://URL       ← also valid

The pipe + number at the end of a heading line is the Telegram topic ID.
Add it after manually creating the topic in your group.
"""

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class TxtTopic:
    raw_line: str       # original line from file
    heading: str        # clean heading text (no topic ID, no trailing hints)
    topic_id: Optional[int]   # Telegram topic ID if written in file, else None
    topic_key: str      # safe dict key
    contents: List[dict] = field(default_factory=list)


def _parse_heading_line(line: str):
    """
    Parse a heading line. Returns (heading_text, topic_id_or_None).
    Heading format:  Some Heading Name | 12345
    The '| number' at the end is optional.
    """
    line = line.strip()

    # Strip leading [bracket] prefix → use content inside as topic name
    # e.g. "[Arithmetic]" → "Arithmetic", "[12345] Topic" → "Topic" with topic_id=12345
    _bracket = re.match(r'^\[([^\]]+)\]\s*(.*)', line)
    if _bracket:
        _inner = _bracket.group(1).strip()
        _rest  = _bracket.group(2).strip()
        if _inner.lstrip('-').isdigit():
            line = _rest or _inner
            return line, int(_inner)
        else:
            line = (_inner + ' ' + _rest).strip() if _rest else _inner

    # Check for pipe-separated topic ID at the end: "Heading | 12345"
    topic_id = None
    pipe_match = re.search(r'\|\s*(-?\d+)\s*$', line)
    if pipe_match:
        topic_id = int(pipe_match.group(1))
        line = line[:pipe_match.start()].strip()

    # Clean up display separators
    heading = line.replace('||', ' ')
    heading = re.sub(r'\s+', ' ', heading).strip()

    return heading, topic_id


def _make_topic_key(heading: str) -> str:
    """Safe dict/file key from heading text."""
    key = re.sub(r'[^a-z0-9]+', '_', heading.lower().strip())
    return key.strip('_')[:60]


def _is_heading_line(line: str) -> bool:
    """Any non-empty line that has no URL pattern and doesn't start with # is a heading."""
    line = line.strip()
    has_url = '://' in line or ': //' in line
    return bool(line) and not has_url and not line.startswith('#')


def _parse_inline_topic_line(line: str) -> Optional[tuple]:
    """
    Detect lines with an inline [Topic Name] prefix before the content + URL.
    Returns (topic_name, content_name, url) or None if not this format.

    Examples:
        [Arithmetic] Class-01 | Ratio & Proportion: https://example.com
        [12345] Batch Demo Videos videos
        Content Name://url
    """
    line = line.strip()
    match = re.match(r'^\[([^\]]+)\]\s*(.*)', line)
    if not match:
        return None
    topic_name = match.group(1).strip()
    rest = match.group(2).strip()
    if not rest:
        return None
    # Only treat as inline topic if the rest has a URL
    if '://' not in rest and ': //' not in rest:
        return None
    content = _parse_content_line(rest)
    if not content:
        return None
    return (topic_name, content['name'], content['url'])


def _parse_content_line(line: str) -> Optional[dict]:
    """Parse a content line (Name : URL or Name://URL or Name: //URL) into a dict."""
    if '://' not in line and ': //' not in line:
        return None
    match = re.match(r'^(.*?)\s*:\s*(https?://.*|//.*)', line.strip())
    if match:
        name = match.group(1).strip()
        url = match.group(2).strip()
        if not url.startswith('http'):
            url = 'https:' + url
        return {'name': name, 'url': url}
    return None


def parse_txt_file(file_path: str) -> Dict[str, TxtTopic]:
    """
    Parse a txt file. Returns dict of topic_key → TxtTopic.
    Every non-URL, non-comment line is treated as a heading.
    Content lines (with ://) are assigned to the current heading.
    """
    topics: Dict[str, TxtTopic] = {}
    current_topic: Optional[TxtTopic] = None

    try:
        with open(file_path, 'r', encoding='utf-8-sig') as f:
            lines = f.readlines()
    except Exception as e:
        print(f"[TxtParser] Error reading file: {e}")
        return {}

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue

        if line.startswith('#'):
            continue

        # Check for inline [Topic] prefix format: [Topic Name] Content: URL
        inline = _parse_inline_topic_line(line)
        if inline:
            topic_name, content_name, url = inline
            topic_key = _make_topic_key(topic_name)
            if topic_key not in topics:
                topics[topic_key] = TxtTopic(
                    raw_line=line,
                    heading=topic_name,
                    topic_id=None,
                    topic_key=topic_key,
                )
            current_topic = topics[topic_key]
            current_topic.contents.append({'name': content_name, 'url': url})
            continue

        if _is_heading_line(line):
            heading, topic_id = _parse_heading_line(line)
            if not heading:
                continue

            topic_key = _make_topic_key(heading)

            if topic_key in topics:
                # Update topic_id if it was added
                if topic_id is not None:
                    topics[topic_key].topic_id = topic_id
                current_topic = topics[topic_key]
            else:
                current_topic = TxtTopic(
                    raw_line=line,
                    heading=heading,
                    topic_id=topic_id,
                    topic_key=topic_key,
                )
                topics[topic_key] = current_topic
            continue

        # Content line
        if current_topic and ('://' in line or ': //' in line):
            content = _parse_content_line(line)
            if content:
                current_topic.contents.append(content)

    return topics


def get_topics_from_txt(file_path: str) -> List[TxtTopic]:
    """Return list of TxtTopic objects from a file."""
    return list(parse_txt_file(file_path).values())

import json
import sys
from pathlib import Path
import yaml

ACT_SCHEMA_PATH = Path('frontmatter.act.schema.json')
DOCS_ROOT = Path('docs/math/acts')


def load_act(path: Path):
    """Load a single act markdown frontmatter."""
    text = path.read_text().split('---')
    if len(text) < 3:
        raise ValueError(f"No frontmatter in {path}")
    frontmatter = yaml.safe_load(text[1])
    if frontmatter.get('role') != 'act':
        raise ValueError(f"Non-act in acts folder: {path}")
    return frontmatter


def build_act_graph(root: Path):
    nodes = {}
    edges = []
    for md in root.glob('*.md'):
        act = load_act(md)
        act_id = act['id']
        nodes[act_id] = {
            'id': act_id,
            'title': act.get('title', ''),
            'status': act.get('status', ''),
            'top': act.get('top'),
            'bottom': act.get('bottom'),
        }
        # typed edges: act -> top, act -> bottom
        if act.get('top'):
            edges.append({'from': act_id, 'to': act['top'], 'type': 'top'})
        if act.get('bottom'):
            edges.append({'from': act_id, 'to': act['bottom'], 'type': 'bottom'})
    return {'nodes': nodes, 'edges': edges}


def main():
    graph = build_act_graph(DOCS_ROOT)
    json.dump(graph, sys.stdout, indent=2)


if __name__ == '__main__':
    main()

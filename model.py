"""CrosshairLab v0.2.1 profile, backward compatibility, and testable geometry.

The rendering/UI layer depends on PySide6; this module uses only the stdlib.
"""
from dataclasses import asdict, dataclass, fields
import json
from pathlib import Path


@dataclass
class CrosshairProfile:
    version: int = 2
    name: str = 'Default'

    horizontal: bool = True
    horizontal_length: int = 12
    horizontal_gap: int = 5
    horizontal_thickness: int = 3

    vertical: bool = True
    vertical_length: int = 12
    vertical_gap: int = 5
    vertical_thickness: int = 3

    circle: bool = False
    circle_radius_x: int = 22
    circle_radius_y: int = 22
    circle_thickness: int = 3
    circle_offset_x: int = 0
    circle_offset_y: int = 0

    dot: bool = True
    dot_size: int = 3
    outline: int = 1
    color: str = '#00FF80'
    outline_color: str = '#111111'
    opacity: int = 255

    offset_x: int = 0
    offset_y: int = 0
    monitor: int = 0
    visible: bool = True

    def validated(self):
        ranges = {
            'horizontal_length': (0, 130),
            'horizontal_gap': (0, 55),
            'horizontal_thickness': (1, 24),
            'vertical_length': (0, 130),
            'vertical_gap': (0, 55),
            'vertical_thickness': (1, 24),
            'circle_radius_x': (1, 125),
            'circle_radius_y': (1, 125),
            'circle_thickness': (1, 24),
            'circle_offset_x': (-50, 50),
            'circle_offset_y': (-50, 50),
            'dot_size': (1, 30),
            'outline': (0, 10),
            'opacity': (0, 255),
            'offset_x': (-500, 500),
            'offset_y': (-500, 500),
            'monitor': (0, 99),
        }
        for key, (low, high) in ranges.items():
            value = getattr(self, key)
            if type(value) is not int or not low <= value <= high:
                raise ValueError(f'{key} must be an integer in {low}..{high}')
        for key in ('color', 'outline_color'):
            value = getattr(self, key)
            if not (isinstance(value, str) and len(value) == 7
                    and value.startswith('#')
                    and all(c in '0123456789abcdefABCDEF' for c in value[1:])):
                raise ValueError(f'{key} must be a #RRGGBB color')
        for key in ('horizontal', 'vertical', 'circle', 'dot',
                    'visible'):
            if type(getattr(self, key)) is not bool:
                raise ValueError(f'{key} must be boolean')
        if type(self.version) is not int or self.version != 2:
            raise ValueError('Unsupported profile version')
        if not isinstance(self.name, str) or len(self.name) > 100:
            raise ValueError('Profile name must be a string of at most 100 chars')
        return self

    @classmethod
    def from_dict(cls, data):
        if not isinstance(data, dict):
            raise ValueError('Profile must be a JSON object')
        data = dict(data)
        if 'version' in data and type(data['version']) is not int:
            raise ValueError('Profile version must be an integer')
        # v0.1 had one shared length/gap/thickness for both axes.
        if data.get('version', 1) == 1:
            for previous_key, new_keys in (
                ('arm_length', ('horizontal_length', 'vertical_length')),
                ('gap', ('horizontal_gap', 'vertical_gap')),
                ('thickness', ('horizontal_thickness', 'vertical_thickness')),
            ):
                if previous_key in data:
                    for key in new_keys:
                        data.setdefault(key, data[previous_key])
                    del data[previous_key]
            data['version'] = 2
        allowed = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in data.items() if k in allowed}).validated()

    @classmethod
    def load(cls, path):
        with open(path, 'r', encoding='utf-8') as stream:
            return cls.from_dict(json.load(stream))

    def save(self, path):
        self.validated()
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(self), indent=2, ensure_ascii=False) + '\n',
                        encoding='utf-8')


def arm_rectangles(profile, center_x=220.0, center_y=220.0):
    """Pure arm geometry. Returns list of (x, y, width, height)."""
    p = profile.validated()
    items = []
    if p.vertical and p.vertical_length:
        t, g, length = p.vertical_thickness, p.vertical_gap, p.vertical_length
        items.extend(((center_x - t / 2, center_y - g - length, t, length),
                      (center_x - t / 2, center_y + g, t, length)))
    if p.horizontal and p.horizontal_length:
        t, g, length = p.horizontal_thickness, p.horizontal_gap, p.horizontal_length
        items.extend(((center_x - g - length, center_y - t / 2, length, t),
                      (center_x + g, center_y - t / 2, length, t)))
    return items


def circle_geometry(profile, center_x=220.0, center_y=220.0):
    """Return circle center/radii/stroke for an optional ring, or None."""
    p = profile.validated()
    if not p.circle:
        return None
    return (center_x + p.circle_offset_x, center_y + p.circle_offset_y,
            p.circle_radius_x, p.circle_radius_y, p.circle_thickness)


def dot_rectangle(profile, center_x=220.0, center_y=220.0):
    p = profile.validated()
    if not p.dot:
        return None
    return (center_x - p.dot_size / 2, center_y - p.dot_size / 2,
            p.dot_size, p.dot_size)


def shapes(profile, center_x=220.0, center_y=220.0):
    """Legacy-compatible rectangle list (arms + optional center dot)."""
    result = arm_rectangles(profile, center_x, center_y)
    dot = dot_rectangle(profile, center_x, center_y)
    if dot:
        result.append(dot)
    return result

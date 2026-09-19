"""Canonical Catalog Preview markup and metadata. CSS lives in catalog_preview_css."""

from __future__ import annotations

from app.modules.fair_stand.infrastructure.catalog_preview_css import CATALOG_PREVIEW_SILHOUETTE_CSS


def _simple(class_name: str) -> str:
    return f'<div class="{class_name}"></div>'


def _width(class_name: str, extra: str = "", min_width: int | None = None) -> str:
    attrs = f'class="{class_name}{extra}" data-preview-width'
    if min_width is not None:
        attrs += f' data-preview-min-width="{min_width}"'
    return f"<div {attrs}></div>"


def _parts(root: str, prefix: str, parts: tuple[str, ...]) -> str:
    inner = "".join(f'<i class="{prefix}-{part}"></i>' for part in parts)
    return f'<div class="{root}">{inner}</div>'


PREVIEW_KIND_DEFINITIONS: tuple[dict[str, object], ...] = (
    {"preview_key": "bar-stool", "display_name": "Bar taburesi", "sort_index": 1, "markup": _simple("module-drag-bar-stool")},
    {"preview_key": "base", "display_name": "Baza", "sort_index": 2, "markup": _width("module-drag-base", min_width=34)},
    {
        "preview_key": "base-wall",
        "display_name": "Baza duvar",
        "sort_index": 3,
        "markup": '<div class="module-drag-base-wall" data-preview-width data-preview-min-width="34" data-auto-spans="7"></div>',
    },
    {"preview_key": "chair", "display_name": "Sandalye", "sort_index": 4, "markup": _simple("module-drag-eames-chair")},
    {"preview_key": "coat-rack", "display_name": "Askılık", "sort_index": 5, "markup": _simple("module-drag-coat-rack")},
    {"preview_key": "coffee-table", "display_name": "Sehpa", "sort_index": 6, "markup": _simple("module-drag-coffee-table")},
    {"preview_key": "counter", "display_name": "Banko", "sort_index": 7, "markup": _width("module-drag-counter", min_width=34)},
    {"preview_key": "door", "display_name": "Kapı", "sort_index": 8, "markup": _width("module-drag-door")},
    {
        "preview_key": "flat-panel",
        "display_name": "Düz panel",
        "sort_index": 9,
        "markup": '<div class="module-drag-panel" data-preview-width data-flat-panel></div>',
    },
    {"preview_key": "floodlight", "display_name": "Projektör", "sort_index": 10, "markup": _simple("module-drag-floodlight")},
    {"preview_key": "glass-table", "display_name": "Cam masa", "sort_index": 11, "markup": _simple("module-drag-glass-table")},
    {
        "preview_key": "indoor-plant",
        "display_name": "İç mekan bitkisi",
        "sort_index": 12,
        "markup": (
            '<div class="module-drag-plant module-drag-plant-1">'
            '<i class="module-drag-plant-pot"></i>'
            '<i class="module-drag-plant-stem"></i>'
            '<i class="module-drag-plant-leaf leaf-a"></i>'
            '<i class="module-drag-plant-leaf leaf-b"></i>'
            "</div>"
        ),
    },
    {
        "preview_key": "kettle",
        "display_name": "Kettle",
        "sort_index": 13,
        "markup": _parts(
            "module-drag-kettle",
            "module-drag-kettle",
            ("body", "handle", "spout", "lid", "knob"),
        ),
    },
    {
        "preview_key": "long-planter",
        "display_name": "Uzun saksı",
        "sort_index": 14,
        "markup": _parts("module-drag-long-planter", "module-drag-long-planter", ("pot", "soil", "leaves")),
    },
    {"preview_key": "mini-fridge", "display_name": "Mini buzdolabı", "sort_index": 15, "markup": _simple("module-drag-mini-fridge")},
    {
        "preview_key": "plastic-trash-bin",
        "display_name": "Plastik çöp kutusu",
        "sort_index": 16,
        "markup": _parts("module-drag-trash-bin", "module-drag-trash-bin", ("handle", "lid", "body")),
    },
    {"preview_key": "profile", "display_name": "Profil", "sort_index": 17, "markup": _width("module-drag-profile")},
    {"preview_key": "separator", "display_name": "Ayırıcı", "sort_index": 18, "markup": _width("module-drag-separator")},
    {
        "preview_key": "separator-vine",
        "display_name": "Sarmaşıklı ayırıcı",
        "sort_index": 19,
        "markup": _width("module-drag-separator", extra=" is-vine"),
    },
    {"preview_key": "shelf", "display_name": "Raf", "sort_index": 20, "markup": _width("module-drag-shelf")},
    {
        "preview_key": "showcase",
        "display_name": "Vitrin",
        "sort_index": 21,
        "markup": '<div class="module-drag-showcase" data-preview-width data-eyes></div>',
    },
    {"preview_key": "sofa-double", "display_name": "İkili kanepe", "sort_index": 22, "markup": _simple("module-drag-sofa-double")},
    {"preview_key": "sofa-set", "display_name": "Kanepe takımı", "sort_index": 23, "markup": _simple("module-drag-sofa")},
    {"preview_key": "sofa-single", "display_name": "Tekli kanepe", "sort_index": 24, "markup": _simple("module-drag-sofa-single")},
    {
        "preview_key": "table-chair-set",
        "display_name": "Masa sandalye takımı",
        "sort_index": 25,
        "markup": _simple("module-drag-table-chair"),
    },
    {"preview_key": "tv", "display_name": "TV", "sort_index": 26, "markup": _simple("module-drag-tv")},
    {"preview_key": "upright", "display_name": "Dikme", "sort_index": 27, "markup": _simple("module-drag-upright")},
    {
        "preview_key": "video-wall",
        "display_name": "Video wall",
        "sort_index": 28,
        "markup": '<div class="module-drag-tv is-video-wall" data-video-wall></div>',
    },
)


def all_preview_kind_rows() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for row in PREVIEW_KIND_DEFINITIONS:
        payload = dict(row)
        payload["css_code"] = CATALOG_PREVIEW_SILHOUETTE_CSS
        payload["is_active"] = True
        rows.append(payload)
    return rows

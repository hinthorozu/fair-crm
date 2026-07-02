from app.modules.imports.domain.services.merge_preview import build_merge_preview


class MergeStrategy:
    build_preview = staticmethod(build_merge_preview)

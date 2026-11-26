"""Run from repository root: python examples/at246_scope_draft.py"""

import json
import sys
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from estimate_api.domain.scope_capture import (
    AssetAvailability,
    AssetValidation,
    ClientAsset,
    ScopeIntake,
    build_scope_draft,
)

draft = build_scope_draft(
    ScopeIntake(
        description="Install a client-supplied cabinet at a fictional workshop.",
        client_assets=(
            ClientAsset("cabinet", AssetAvailability.AVAILABLE, AssetValidation.UNVALIDATED),
        ),
    )
)
print(json.dumps(asdict(draft), indent=2, ensure_ascii=False))

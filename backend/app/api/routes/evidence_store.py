"""Admin endpoints for evidence store management."""

from fastapi import APIRouter, Depends

from app.auth.admin import require_admin_token
from app.auth.actor import AdminActor
from app.core.config import get_settings
from app.services.evidence_store_validation import validate_evidence_store_root

router = APIRouter(prefix="/api/admin/evidence-store", tags=["admin"])


@router.get("/status")
def get_evidence_store_status(_: AdminActor = Depends(require_admin_token)) -> dict:
    """Get evidence store configuration and validation status.
    
    Response does not include full filesystem path for security.
    """
    settings = get_settings()
    
    if not settings.evidence_store_root:
        return {
            "enabled": False,
            "root_configured": False,
            "storage_layout": None,
            "probe_ok": None,
        }
    
    try:
        result = validate_evidence_store_root(
            settings.evidence_store_root,
            required=False,
            probe_write=False,  # Do not probe on every status check
        )
        return {
            "enabled": result["enabled"],
            "root_configured": True,
            "storage_layout": "snapshots/sha256/AA/BB/hash.bin",
            "probe_ok": result.get("reason") is None,
        }
    except RuntimeError as e:
        return {
            "enabled": False,
            "root_configured": True,
            "storage_layout": "snapshots/sha256/AA/BB/hash.bin",
            "probe_ok": False,
            "error": str(e),
        }

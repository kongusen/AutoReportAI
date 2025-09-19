"""
Template Path Resolver

Resolves a template_id to a local docx template path by downloading from MinIO (via HybridStorageService)
or reading from local storage, depending on configuration.
"""

import os
import tempfile
import logging
from typing import Optional, Dict, Any

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def resolve_docx_template_path(db: Session, template_id: str) -> Dict[str, Any]:
    """Resolve template_id to a local docx path.

    Returns dict with keys: path, source, original_filename, storage_path
    """
    from app import crud as crud_template
    from app.services.infrastructure.storage.hybrid_storage_service import get_hybrid_storage_service

    tpl = crud_template.template.get(db=db, id=template_id)
    if not tpl:
        raise ValueError(f"Template {template_id} not found")

    storage_path: Optional[str] = getattr(tpl, 'file_path', None)
    original_filename: Optional[str] = getattr(tpl, 'original_filename', None)
    if not storage_path:
        raise ValueError("Template has no associated file_path")

    # Download from storage to temp file
    storage = get_hybrid_storage_service()
    data, backend = storage.download_file(storage_path)

    # Ensure docx
    ext = os.path.splitext(original_filename or '')[1].lower()
    if ext not in ('.docx', '.doc'):
        logger.warning(f"Template file is not docx/doc: {original_filename}")

    tmp_dir = tempfile.mkdtemp(prefix=f"tpl_{template_id}_")
    local_path = os.path.join(tmp_dir, original_filename or 'template.docx')
    with open(local_path, 'wb') as f:
        f.write(data)

    return {
        'path': local_path,
        'source': backend,
        'original_filename': original_filename,
        'storage_path': storage_path,
    }


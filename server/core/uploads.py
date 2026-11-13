"""Bounded reads for multipart uploads."""

from fastapi import HTTPException, UploadFile

DEFAULT_MAX_UPLOAD_BYTES = 20 * 1024 * 1024


async def read_upload_capped(file: UploadFile, max_bytes: int = DEFAULT_MAX_UPLOAD_BYTES) -> bytes:
    """Read at most ``max_bytes``; a larger upload is rejected with 413 instead of loaded into memory."""
    content = await file.read(max_bytes + 1)
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds the {max_bytes // (1024 * 1024)}MB limit",
        )
    return content

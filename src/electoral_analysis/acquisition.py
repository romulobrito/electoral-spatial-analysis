"""Bounded official downloads with reproducibility manifests and ZIP inspection."""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener
from zipfile import ZipFile

from .sources import OfficialResource, validated_download_url


class OfficialOnlyRedirects(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        candidate = urlsplit(newurl)
        if candidate.scheme != "https" or candidate.hostname != "cdn.tse.jus.br":
            raise ValueError("Redirect outside approved official TSE host")
        return super().redirect_request(request, fp, code, msg, headers, newurl)


def inventory_zip(path: Path, *, max_members: int = 100, max_uncompressed: int = 8_000_000_000) -> list[dict]:
    """Inspect without extraction; reject suspicious paths and excessive archive expansion."""
    with ZipFile(path) as archive:
        members = archive.infolist()
        if len(members) > max_members:
            raise ValueError("Archive contains unexpectedly many entries")
        if sum(member.file_size for member in members) > max_uncompressed:
            raise ValueError("Archive's declared expanded size exceeds safety limit")
        result = []
        for member in members:
            name = member.filename
            parts = Path(name.replace("\\", "/")).parts
            if (name.startswith(("/", "\\")) or ".." in parts or ":" in name or not parts):
                raise ValueError(f"Unsafe archive member: {name}")
            result.append({"name": name, "uncompressed_bytes": member.file_size,
                           "compressed_bytes": member.compress_size, "crc32": format(member.CRC, "08x")})
        return result


def download_official(resource: OfficialResource, directory: str | Path,
                      *, max_bytes: int = 2_000_000_000, timeout: int = 120) -> dict:
    """Download once, compute SHA256, inspect ZIP, and write a JSON manifest.

    An existing destination is never silently overwritten. No outside redirects accepted.
    """
    url = validated_download_url(resource)
    destination_dir = Path(directory)
    destination_dir.mkdir(parents=True, exist_ok=True)
    destination = destination_dir / f"{resource.key}.zip"
    manifest_path = destination_dir / f"{resource.key}.manifest.json"
    if destination.exists() or manifest_path.exists():
        raise FileExistsError("Existing artifact: use a new directory/version to preserve provenance")
    request = Request(url, headers={"User-Agent": "electoral-spatial-analysis/0.1 (research)"})
    digest = hashlib.sha256()
    count = 0
    fd, tmp_name = tempfile.mkstemp(dir=destination_dir, prefix=f".{resource.key}-", suffix=".part")
    os.close(fd)
    temp = Path(tmp_name)
    try:
        opener = build_opener(OfficialOnlyRedirects())
        with opener.open(request, timeout=timeout) as response, temp.open("wb") as handle:
            for chunk in iter(lambda: response.read(1024 * 1024), b""):
                count += len(chunk)
                if count > max_bytes:
                    raise ValueError("Archive download exceeds configured size limit")
                handle.write(chunk)
                digest.update(chunk)
            final_url = response.geturl()
            if urlsplit(final_url).hostname != "cdn.tse.jus.br":
                raise ValueError("Unexpected final download host")
        if not count:
            raise ValueError("Empty archive")
        members = inventory_zip(temp)
        metadata = {"key": resource.key, "year": resource.year, "kind": resource.kind,
                    "source_dataset": resource.dataset, "resource_id": resource.resource_id,
                    "requested_url": url, "resolved_url": final_url,
                    "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
                    "sha256": digest.hexdigest(), "bytes": count, "zip_members": members,
                    "audit_status": "downloaded_not_validated"}
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=destination_dir,
                                         prefix=".manifest-", suffix=".tmp", delete=False) as mf:
            json.dump(metadata, mf, ensure_ascii=False, indent=2)
            manifest_temp = Path(mf.name)
        try:
            os.replace(temp, destination)
            os.replace(manifest_temp, manifest_path)
        finally:
            manifest_temp.unlink(missing_ok=True)
        return metadata
    finally:
        temp.unlink(missing_ok=True)

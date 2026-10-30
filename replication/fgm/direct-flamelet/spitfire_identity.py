"""Record the actual compiled extension and any explicitly declared source patch."""
import json
from pathlib import Path
from common import sha256
from spitfire_patch import UPSTREAM, PATCH_ID, ORIGINAL_SHA256, PATCHED_SHA256


def runtime_identity(settings, patch_path=None, cold_patch_path=None):
    from spitfire.sqa import gitinfo
    from spitfire.griffon import griffon
    if gitinfo.current_hexsha != settings["upstream_revision"] or gitinfo.current_hexsha != UPSTREAM:
        raise ValueError("Loaded Spitfire base revision differs from pinned settings")
    dirty = str(gitinfo.is_dirty).lower() == "true"
    result = {"upstream_revision": gitinfo.current_hexsha, "upstream_dirty": dirty,
              "extension_path": str(griffon.__file__), "extension_sha256": sha256(griffon.__file__)}
    if patch_path is None:
        if cold_patch_path is not None:
            raise ValueError("Cold candidate requires the separately recorded energy patch")
        if dirty:
            raise ValueError("Dirty Spitfire build requires --upstream-patch-receipt")
        result["source_patch"] = None
        return result
    patch = json.loads(Path(patch_path).read_text())
    if (patch.get("schema") != "spitfire-source-patch/v1" or patch.get("patch_id") != PATCH_ID or
            patch.get("upstream_revision") != UPSTREAM or patch.get("original_sha256") != ORIGINAL_SHA256 or
            patch.get("patched_sha256") != PATCHED_SHA256 or
            patch.get("replacements") != 8 or patch.get("applied") is not True or not dirty):
        raise ValueError("Patch receipt and installed dirty-source identity are inconsistent")
    result.update(source_patch=patch, source_patch_receipt_sha256=sha256(patch_path))
    if cold_patch_path is not None:
        from prepare_cold_patch import CANDIDATE_PATCH_SHA256, DIRECTORY, FILES, HEADER_NAME
        cold = json.loads(Path(cold_patch_path).read_text())
        if (cold.get("schema") != "spitfire-cold-patch/v1" or cold.get("applied") is not True or
                cold.get("upstream_revision") != UPSTREAM or cold.get("patch_sha256") != CANDIDATE_PATCH_SHA256 or
                cold.get("energy_patch_receipt_sha256") != sha256(patch_path) or
                not cold.get("applied_files")):
            raise ValueError("Cold patch receipt is incomplete or not bound to this energy patch")
        expected = {DIRECTORY + name for name in [*FILES, HEADER_NAME]}
        if set(cold["applied_files"]) != expected or set(cold["candidate_manifest"]["files"]) != expected:
            raise ValueError("Cold receipt must cover all four kernels and the helper header exactly")
        for relative, digest in cold["applied_files"].items():
            if digest != cold["candidate_manifest"]["files"][relative]["candidate_sha256"]:
                raise ValueError("Cold applied-file hash differs from frozen candidate")
        result.update(cold_source_patch=cold, cold_patch_receipt_sha256=sha256(cold_patch_path))
    return result

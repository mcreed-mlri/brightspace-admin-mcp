"""Data Hub tools: Brightspace Data Sets (BDS) and Advanced Data Sets exports.

These are org-wide bulk CSV/zip exports for analytics. Listing is cheap; downloads can be
large and may contain PII — they are saved to ./exports/ (gitignored) by default.
"""

from __future__ import annotations

import asyncio

from mcp.types import ToolAnnotations

from ..config import PROJECT_ROOT
from ..context import get_client

_READ_ONLY = ToolAnnotations(readOnlyHint=True)

# Cap on Next-link pages when listing BDS (each page is ~100 data set descriptors).
_MAX_LIST_PAGES = 20

_JOB_STATUS = {0: "Queued", 1: "Processing", 2: "Complete", 3: "Error", 4: "Deleted"}

_PII_WARNING = (
    "WARNING: this export may contain student PII; it is stored unencrypted under "
    "./exports/ — handle per your data policy and delete when no longer needed."
)


def register(mcp) -> None:
    @mcp.tool(annotations=_READ_ONLY)
    async def list_brightspace_data_sets() -> list[dict]:
        """List available Brightspace Data Sets (BDS) — the standard bulk exports.

        Each entry includes a name, PluginId, and download link(s) for full/differential CSVs.
        """
        client = get_client()
        result = await client.get("lp", "/dataExport/bds")
        if not isinstance(result, dict):
            return result or []
        # Newer LP versions page this list via a Next URL.
        objects = result.get("Objects", result.get("Items", []))
        for _ in range(_MAX_LIST_PAGES):
            next_url = result.get("Next")
            if not next_url:
                break
            result = await client.get_raw(next_url)
            if not isinstance(result, dict):
                break
            objects.extend(result.get("Objects", result.get("Items", [])))
        return objects

    @mcp.tool(annotations=_READ_ONLY)
    async def list_advanced_data_sets() -> list[dict]:
        """List Advanced Data Sets available to export (custom/on-demand data exports)."""
        result = await get_client().get("lp", "/dataExport/list")
        if isinstance(result, dict):
            return result.get("Objects", result.get("Items", []))
        return result or []

    @mcp.tool()
    async def run_advanced_data_set(
        data_set_id: str,
        filters: dict[str, str] | None = None,
        filename: str | None = None,
        poll_interval: int = 10,
        timeout: int = 600,
    ) -> str:
        """Create an Advanced Data Set export job on the Brightspace server, wait for
        completion, and download the result. This is the only tool that writes anything
        (the export job) on the server side.

        data_set_id: the DataSetId from list_advanced_data_sets() (e.g. 'c195aa85-...').
        filters: optional dict of filter name → value (e.g. {"startDate": "2025-01-01",
                 "endDate": "2025-12-31", "parentOrgUnitId": "6606"}).
        Returns the local file path. WARNING: output may contain PII.
        """
        client = get_client()
        body: dict = {"DataSetId": data_set_id}
        if filters:
            body["Filters"] = [{"Name": k, "Value": v} for k, v in filters.items()]

        job = await client.post("lp", "/dataExport/create", body)
        job_id = job.get("ExportJobId") or job.get("JobId") or job.get("Identifier")
        if not job_id:
            raise RuntimeError(f"No job ID in create response: {job}")

        loop = asyncio.get_running_loop()
        deadline = loop.time() + timeout
        while True:
            status_obj = await client.get("lp", f"/dataExport/jobs/{job_id}")
            status = status_obj.get("Status")
            status_name = _JOB_STATUS.get(int(status), str(status)) if str(status).isdigit() else str(status)
            if status_name.lower() == "complete":
                break
            if status_name.lower() in ("error", "deleted"):
                raise RuntimeError(f"Export job ended as {status_name}: {status_obj}")
            if loop.time() > deadline:
                raise TimeoutError(f"Export job {job_id} did not complete within {timeout}s")
            await asyncio.sleep(poll_interval)

        # Some payloads include a link; the documented route is /dataExport/download/{jobId}.
        download_link = status_obj.get("DownloadLink") or status_obj.get("DownloadUrl")
        if not download_link:
            version = await client.version_for("lp")
            download_link = f"/lp/{version}/dataExport/download/{job_id}"

        dest_dir = PROJECT_ROOT / "exports"
        dest_dir.mkdir(exist_ok=True)
        name = filename or f"{data_set_id}.zip"
        dest = dest_dir / name
        await client.download(download_link, dest)
        return f"Saved to {dest}. {_PII_WARNING}"

    @mcp.tool()
    async def download_data_set(download_url: str, filename: str | None = None) -> str:
        """Download a data set export to ./exports/ given its download link.

        Pass a download link from list_brightspace_data_sets()/list_advanced_data_sets().
        Returns the local file path. WARNING: these files can be large and contain PII.
        """
        dest_dir = PROJECT_ROOT / "exports"
        dest_dir.mkdir(exist_ok=True)
        name = filename or download_url.rstrip("/").split("/")[-1] or "dataset.zip"
        dest = dest_dir / name
        await get_client().download(download_url, dest)
        return f"Saved to {dest}. {_PII_WARNING}"

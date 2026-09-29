"""Minimal YouCam API V2 client: upload a photo, run AI Skin Analysis, read the scores.

Standard library only. The API key is read from YOUCAM_API_KEY or ~/.config/youcam.key and is
never printed.
"""
import io
import json
import os
import pathlib
import time
import urllib.request
import zipfile

API = "https://yce-api-01.makeupar.com"


def api_key():
    key = os.environ.get("YOUCAM_API_KEY")
    if key:
        return key.strip()
    return (pathlib.Path.home() / ".config" / "youcam.key").read_text().strip()


def _call(method, path, body=None, key=None):
    data = json.dumps(body).encode() if body is not None else None
    request = urllib.request.Request(API + path, data=data, method=method)
    request.add_header("Authorization", "Bearer " + (key or api_key()))
    if data is not None:
        request.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.load(response)


def balance():
    return sum(r.get("amount", 0) for r in _call("GET", "/s2s/v1.0/client/credit")["results"])


def upload(image_bytes, name="photo.jpg", content_type="image/jpeg"):
    """Two steps: ask for an upload slot, then PUT the bytes there. Returns the file_id."""
    slot = _call("POST", "/s2s/v2.1/file/skin-analysis", {"files": [
        {"content_type": content_type, "file_name": name, "file_size": len(image_bytes)}]})
    entry = slot["data"]["files"][0]
    put = entry["requests"][0]
    request = urllib.request.Request(put["url"], data=image_bytes, method=put.get("method", "PUT"))
    for header, value in (put.get("headers") or {}).items():
        request.add_header(header, value)
    urllib.request.urlopen(request, timeout=120).read()
    return entry["file_id"]


def delete_task(task_id):
    """Remove the task, its results and the uploaded photo from YouCam's servers."""
    try:
        _call("POST", "/s2s/v2.0/task/delete", {"task_id": task_id})
    except Exception:  # best effort: files expire on their own after 24 hours
        pass


def analyse(concerns, file_id=None, url=None, poll=3.0, timeout=180, forget=False,
            overlay=False):
    """Run one analysis and return the parsed score_info.json plus the result zip bytes.

    With `forget`, the task and the uploaded photo are deleted from YouCam once read.
    """
    body = {"dst_actions": list(concerns)}
    body["src_file_id" if file_id else "src_file_url"] = file_id or url
    if overlay:
        body["miniserver_args"] = {"enable_mask_overlay": True}
    task = _call("POST", "/s2s/v2.1/task/skin-analysis", body)["data"]["task_id"]
    deadline = time.time() + timeout
    while True:
        data = _call("GET", "/s2s/v2.1/task/skin-analysis/" + task)["data"]
        if data["task_status"] == "success":
            break
        if data["task_status"] == "error":
            raise RuntimeError(f"{data.get('error')}: {data.get('error_message')}")
        if time.time() > deadline:
            raise TimeoutError(task)
        time.sleep(poll)
    results = data["results"]
    try:
        if "url" in results:
            raw = urllib.request.urlopen(results["url"], timeout=120).read()
            with zipfile.ZipFile(io.BytesIO(raw)) as archive:
                name = next(n for n in archive.namelist() if n.endswith("score_info.json"))
                return json.loads(archive.read(name)), raw
        return results.get("output"), None
    finally:
        if forget:
            delete_task(task)

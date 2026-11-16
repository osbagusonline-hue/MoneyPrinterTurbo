"""Small image-to-video client for the repository's supported Ark Seedance API.

Submit once, persist the task id, and resume polling on rerun. No paid POST retry.
"""
import base64
import hashlib
import json
import mimetypes
import os
from pathlib import Path
import time
from urllib.parse import quote, urlparse

import requests

TASKS_URL = "https://ark.cn-beijing.volces.com/api/v3/contents/generations/tasks"
MODEL = "doubao-seedance-1-0-pro-250528"
PROMPT = (
    "Cinematic food commercial. Slow smooth camera push toward this exact meal: "
    "plain white rice, fresh raw ulam and crispy fried fish, sambal in a bowl. "
    "Subtle natural steam, warm side lighting, realistic textures. Preserve food "
    "arrangement. No eggs, no people, no text, no logos, no bottle."
)


def _generate_meal(image: Path, cache: Path, *, timeout=600, session=None):
    """Return a cached 10s clip, or submit one paid 720p image-to-video task.

    An unresolved submission is intentionally blocked on rerun: reconcile it in
    the provider console before deleting its receipt and submitting again.
    """
    key = os.getenv("VOLCENGINE_ARK_API_KEY", "").strip()
    if not key:
        raise RuntimeError("Seedance needs VOLCENGINE_ARK_API_KEY and funded Ark credits.")
    model = (os.getenv("FOOD_AD_SEEDANCE_MODEL", "").strip() or MODEL)
    identity = hashlib.sha256(image.read_bytes() + model.encode() + PROMPT.encode()).hexdigest()
    cache.mkdir(parents=True, exist_ok=True)
    receipt = cache / f"{identity}.json"
    clip = cache / f"{identity}.mp4"
    state = json.loads(receipt.read_text()) if receipt.exists() else {}
    if clip.exists() and clip.stat().st_size and state.get("status") == "downloaded":
        return clip
    http = session or requests.Session()
    headers = {"Authorization": f"Bearer {key}"}
    if not state:
        # Write before POST so even a process interruption cannot duplicate billing.
        state = {"status": "submission_unconfirmed", "model": model}
        receipt.write_text(json.dumps(state))
        mime = mimetypes.guess_type(image.name)[0] or "image/png"
        ref = f"data:{mime};base64," + base64.b64encode(image.read_bytes()).decode()
        payload = {
            "model": model,
            "content": [{"type": "text", "text": PROMPT},
                        {"type": "image_url", "image_url": {"url": ref}, "role": "first_frame"}],
            "ratio": "9:16", "duration": 10, "resolution": "720p", "watermark": False,
        }
        try:
            response = http.post(TASKS_URL, headers=headers, json=payload,
                                 timeout=(15, 45), allow_redirects=False)
        except requests.RequestException:
            raise RuntimeError("Seedance submission unconfirmed; inspect saved receipt/provider console. Do not resubmit.") from None
        if not 200 <= response.status_code < 300:
            if response.status_code in (400, 401, 403, 404, 422):
                receipt.unlink()  # explicit rejection, no accepted task
            raise RuntimeError(f"Seedance submission HTTP {response.status_code}; check provider console/credits.")
        try:
            task_id = response.json().get("id")
        except (ValueError, AttributeError):
            task_id = None
        if not task_id:
            raise RuntimeError("Seedance accepted without task id; reconcile in provider console.")
        state.update(id=task_id, status="queued")
        receipt.write_text(json.dumps(state))
    task_id = state.get("id")
    if not task_id:
        raise RuntimeError("Unconfirmed paid submission receipt exists; reconcile in provider console before retrying.")
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            response = http.get(f"{TASKS_URL}/{quote(task_id, safe='')}", headers=headers,
                                timeout=(10, 20), allow_redirects=False)
            if response.status_code in (429, 500, 502, 503, 504):
                time.sleep(5)
                continue
            if response.status_code != 200:
                raise RuntimeError(f"Seedance polling HTTP {response.status_code}; task saved for resume.")
            body = response.json()
        except requests.RequestException:
            time.sleep(5)
            continue
        status = body.get("status")
        state["status"] = status
        receipt.write_text(json.dumps(state))
        if status in ("failed", "cancelled", "canceled", "expired"):
            raise RuntimeError(f"Seedance task {task_id} {status}; inspect provider console.")
        if status == "succeeded":
            url = body.get("content", {}).get("video_url", "")
            if urlparse(url).scheme != "https":
                raise RuntimeError("Seedance did not return an HTTPS video URL.")
            # Signed CDN download deliberately receives no provider Authorization.
            with http.get(url, stream=True, timeout=(15, 60)) as download:
                download.raise_for_status()
                temp = clip.with_suffix(".part")
                with temp.open("wb") as target:
                    for chunk in download.iter_content(1024 * 1024):
                        target.write(chunk)
                temp.replace(clip)
            state["status"] = "downloaded"
            receipt.write_text(json.dumps(state))
            return clip
        if status not in ("queued", "running"):
            raise RuntimeError(f"Seedance returned unknown task status; task {task_id} saved.")
        time.sleep(5)
    raise RuntimeError(f"Seedance still pending; rerun to resume task {task_id}, without another charge.")


def generate_meal(image: Path, cache: Path, *, timeout=600, session=None):
    # A second WebUI session must not race the receipt check and duplicate a POST.
    from filelock import FileLock, Timeout
    cache.mkdir(parents=True, exist_ok=True)
    try:
        with FileLock(str(cache / ".generation.lock"), timeout=0):
            return _generate_meal(image, cache, timeout=timeout, session=session)
    except Timeout:
        raise RuntimeError("Another food video task is using this cache; wait for it to finish.") from None

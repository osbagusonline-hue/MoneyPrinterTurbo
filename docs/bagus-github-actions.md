# Bagus commercial: render, workflow diagnosis and credentials

## Delivered commercial

`deliverables/bagus/bagus_sambal_belacan_10s.mp4` is a 10.000-second, 1080 × 1920, 30 fps H.264/yuv420p video with 48 kHz AAC audio. It uses:

- The user-selected uploaded packshot (`assets/food_ads/bsb.png`, 1122 × 1402 RGBA), composited directly. This is the prepared AI cutout uploaded by the user; it differs from the original camera photograph in some label details.
- A newly generated, cinematic serving illustration of **plain white rice, ulam, fried fish and sambal**. The old photo contains herb-mixed rice and egg and is not used.
- A continuous drifting camera pullback on the food image, overlapping scene dissolves, an eased bottle entrance, and a continuous product shot through the Bagusmart CTA.
- Malay female `ms-MY-YasminNeural` narration, cached with its actual word timing.
- An original locally synthesized pluck/pad/pulse music bed, ducked under narration.
- Burned-in Malay captions, plus a separate SRT. CTA: `bagusmart.sg`.

**This delivered edition uses animated stills, not generated moving food footage.** The user has no funded video provider. No paid video task was submitted. The optional Seedance path is implemented and tested against mocked API responses; live provider acceptance, quality and billing remain unverified.

## Why the existing render appeared unfinished

Inspected the repository at `52b9a96c48379a7692902da603ea2d76c0310787` and the existing Actions runs on 16 November 2026.

[Run 43788024271](https://github.com/osbagusonline-hue/MoneyPrinterTurbo/actions/runs/43788024271) was dispatched at **09:44:40 Singapore time**. Its hosted runner started at **10:01:50**, roughly 17 minutes later. The actual render ran from **10:02:25 to 10:02:33**, about 8 seconds, and the artifact uploaded successfully at **10:02:34**. Job `133039947114` concluded **success**; artifact ID `14191688372`.

The observed delay was runner queueing, not an FFmpeg failure. Another run (`43788069466`) was also queued when inspected. Logs do not establish why GitHub delayed allocating the runner; do not infer a billing or concurrency failure without account evidence.

The old script could render, but only concatenated three static image scenes and added Edge TTS. It never called an AI video provider, created music or synchronized subtitles. The old UI only exported a storyboard JSON. Its push trigger initially watched asset/project folders but omitted script/workflow edits (the latest main commit partially changed its triggers).

The revised workflow tests the generator, watches its source, uses an explicit Ubuntu image, avoids cancelling an active paid task, validates/decode-checks the MP4 and uploads MP4/SRT/probe/manifest files. Cached narration eliminates a network TTS dependency from the normal Actions run. Manual dispatch is the only workflow route to paid generation; pushes and PRs use animated stills.

## Run locally (Linux with FFmpeg, libass and DejaVu fonts)

```sh
python -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-food-ad.txt
python scripts/render_bagus_food_ad.py \
  --voice-audio assets/food_ads/bagus_ms_Yasmin.mp3 \
  --subtitles assets/food_ads/bagus_ms_Yasmin.words.srt \
  --output dist/bagus_sambal_belacan_10s.mp4
ffmpeg -v error -i dist/bagus_sambal_belacan_10s.mp4 -f null -
```

Open the existing MoneyPrinterTurbo Streamlit WebUI, select **Food Advertisement Generator**, then use **Generate MP4**. The upper form remains the general storyboard builder; the lower renderer is a fixed ten-second Bagus commercial with replaceable bottle/meal/music inputs at the CLI. It does not synthesize arbitrary products or languages from the storyboard form.

CLI options include `--bottle`, `--meal`, `--music`, `--cta`, `--footage` (a supplied video of at least 10 seconds), and `--provider stills|seedance`. Omit both cached audio/subtitle arguments to regenerate the fixed Malay script via Edge TTS. Supply both to use recorded speech and matching timed captions. Custom narration must fit inside 10 seconds. The on-screen Bagus branding is fixed; changing only the URL does not change the spoken Bagusmart CTA.

## API keys and credits

| Component | Key/credit requirement |
| --- | --- |
| Delivered animated-still MP4 | No API key or video credits. Bundled reference, cached narration and local original music. |
| Regenerate Malay narration | Edge TTS network access; no API key. This unofficial public endpoint can be unavailable or change; use the bundled audio or licensed recorded narration if necessary. |
| Generate moving meal footage | Funded Volcengine Ark account with video generation enabled, supported model access, and `VOLCENGINE_ARK_API_KEY`. |
| Food reference regeneration | Created once using ChatGPT image generation for this delivery. No image API integration or key is required to rerender the supplied reference. |

The supported protocol matches the repository's `app/services/volcengine_seedance.py`: Ark `/api/v3/contents/generations/tasks`. The small food-ad adapter adds a **first-frame image reference**, while leaving the actual bottle outside the model and compositing it afterward. Default model: `doubao-seedance-1-0-pro-250528`; override using `FOOD_AD_SEEDANCE_MODEL` if your Ark account requires a different available image-to-video model/endpoint ID with the same request contract. Model availability and regional account eligibility must be checked in your provider console.

Set the key through the server secret environment, or GitHub **Settings → Secrets and variables → Actions → New repository secret** named `VOLCENGINE_ARK_API_KEY`. An optional repository variable `FOOD_AD_SEEDANCE_MODEL` overrides the default. Do not commit credentials or enter them in source files.

Select **Actions → Bagus Food Advertisement MP4 → Run workflow → provider: seedance**. This submits **one 10-second, 720p, 9:16 meal clip**, using the supplied food image as its first frame. The local final encode remains 1080 × 1920; this is an upscale of provider footage. The bottle never goes to Ark. A generated clip still needs visual inspection; generation may distort food, and success is not guaranteed.

Pricing varies by model/account/region. Check the provider's current console quote and credit balance before choosing Seedance. No exact price or free-credit allowance has been verified here. The script does not purchase credits or bypass access restrictions.

## Paid-task recovery

Task receipts in `storage/food_ad_provider/` are hashed by food reference/model/prompt and contain task IDs, never credentials. A cross-process file lock prevents duplicate concurrent submissions. A receipt is written before the single POST. Timeouts, redirects, 5xx and unreadable responses do **not** trigger a new POST. If a task ID is known, rerunning resumes GET polling and downloads; if the POST outcome is unknown, inspect the Ark console before clearing its receipt. Do not blindly delete receipts or rerun with a fresh cache: a paid task may already exist.

Actions restores/saves these receipts for manual Seedance runs and uploads them for recovery even on render failure. If an Actions runner is terminated before saving cache/artifacts, reconcile the provider console before another paid attempt. GitHub cache expiry/eviction also requires this check. Download URLs are fetched without the Ark Authorization header. Provider response bodies and API keys are not shown in the WebUI.

## Validation performed

- Streamlit AppTest: real Generate MP4 flow, video/subtitle download data, and missing-key guard passed.
- Ruff checks and Python compilation passed for changed Python files.
- Five offline unit tests: missing key, referenced generation payload/download/cache, ambiguous submission without duplicate POST, task resumption, and real caption timing.
- Native FFmpeg rendering with the actual references, bundled narration, generated music, overlays and captions.
- ffprobe: 10 seconds, 1080 × 1920, H.264/yuv420p, 30 fps, AAC 48 kHz.
- Complete video/audio decode; 300 video frames.
- Extracted opening, product and CTA frames inspected for content and caption placement.
- Audio analysis: approximately −19.8 LUFS integrated and −5.2 dBTP on the inspected encode; audible samples present with headroom.

The full MoneyPrinterTurbo application suite was not run. Live Seedance generation was not run because no key/credits were provided. See the accompanying PR checks for validation of the revised GitHub workflow.

## Motion revision

After feedback that the first edit felt rigid, the renderer now keeps the food visible throughout, dissolves overlapping scene layers, glides the actual bottle into place, and carries it continuously into the closing CTA. The ten-second format, Malay voice and subtitles remain. This is still image-based motion design; real moving steam, food handling or pouring requires generated/supplied footage. The revised native render, full decode, frame inspection, five unit tests and Ruff checks passed.

## Selected bottle update

The user uploaded `assets/food_ads/bsb.png` on main and requested an immediate render. CLI, WebUI and Actions defaults now select that uploaded file. The MP4 has been rerendered with this packshot; narration, music, captions and motion timing remain unchanged.

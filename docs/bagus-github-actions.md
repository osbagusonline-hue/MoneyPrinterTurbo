# Bagus Sambal Belacan GitHub Actions commercial

## Required assets
Upload these two real photographs to the repository using GitHub **Add file → Upload files**:
- `assets/food_ads/bagus_bottle.png`: the original Bagus Sambal Belacan Traditional bottle, label unchanged.
- `assets/food_ads/nasi_ulam_fried_fish.jpg`: **white rice with fresh ulam and fried fish**, not nasi lemak.

The workflow deliberately fails when either file is absent. Do not substitute generated packaging for the actual bottle.

## Running
1. Merge the feature branch into `main` after reviewing and testing the code.
2. Open **Actions → Bagus Food Advertisement MP4 → Run workflow**.
3. Keep the default asset paths, or enter the correct paths in the workflow inputs.
4. After the run succeeds, download the `bagus-sambal-belacan-commercial` artifact.

GitHub requires a manually dispatched workflow file to exist on the default branch before the **Run workflow** control appears.

## Output and limitations
Produces a 10-second, 1080×1920 H.264 MP4 with three still-image scenes, text overlays, and a Malay female Edge TTS voiceover. It does **not** yet invoke MoneyPrinterTurbo's AI image-to-video providers or produce moving food footage, music or synchronized subtitles. The voiceover uses an external network TTS service and may fail when that service is unavailable. No secret keys are required for this basic render. The workflow must be tested on a GitHub runner before production use.

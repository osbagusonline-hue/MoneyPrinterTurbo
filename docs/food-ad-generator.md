# AI Food Advertisement Generator

The MoneyPrinterTurbo Streamlit **Food Advertisement Generator** page has two sections:

1. A general storyboard builder: product details, language, format, duration and style generate a downloadable JSON production plan. Its reference upload remains a browser-only visual aid.
2. A working ten-second **Bagus commercial renderer**: actual bottle, nasi putih/ulam/fried-fish illustration, Malay female narration, music, timed subtitles and Bagusmart CTA. It previews and downloads an MP4 and SRT.

The Bagus renderer defaults to animated stills and cached narration, requiring no paid API. Its optional Seedance image-to-video mode uses the food reference, a secret `VOLCENGINE_ARK_API_KEY` and funded Ark credits. It preserves the supplied bottle by compositing it after footage generation. Generic storyboard settings do not change the fixed Bagus renderer.

See [rendering, credentials, testing and workflow diagnosis](bagus-github-actions.md) for commands, limitations and paid-task recovery.

---
name: glm-image
description: AI image generation using Zhipu AI's GLM-Image model via OpenAI-compatible API. Use when user wants to generate images with Chinese-friendly output, especially for text-intensive tasks like posters, PPTs, and infographics.
version: 2.0.0
---

# GLM Image Generator

Image generation using Zhipu AI's GLM-Image model via OpenAI-compatible API.

**Documentation:** https://docs.z.ai/guides/image/glm-image

## Key Features

- **Text-intensive generation**: Excellent at posters, PPTs, infographics with accurate text rendering
- **Chinese prompts**: Native Chinese language support
- **Multiple aspect ratios**: 1:1, 3:4, 4:3, 16:9, etc.
- **High quality**: Open-source SOTA in text rendering benchmarks

## Setup

Requires Zhipu AI credentials in `.baoyu-skills/.env`:

```env
OPENAI_API_KEY=<your-zhipu-api-key>
OPENAI_BASE_URL=https://open.bigmodel.cn/api/paas/v4/
```

## API Endpoint

```
POST https://api.z.ai/api/paas/v4/images/generations
```

## Usage

The agent should call baoyu-image-gen with OpenAI provider pointing to Zhipu AI:

```bash
npx -y bun <baoyu-image-gen-path>/scripts/main.ts \
  --provider openai \
  --model glm-image \
  --prompt "<prompt>" \
  --image <output.png> \
  --ar 3:4 \
  --quality 2k
```

Or via curl:

```bash
curl --request POST \
  --url https://api.z.ai/api/paas/v4/images/generations \
  --header 'Authorization: Bearer <token>' \
  --header 'Content-Type: application/json' \
  --data '{
    "model": "glm-image",
    "prompt": "A cute little kitten sitting on a sunny windowsill",
    "size": "1280x1280"
  }'
```

## Available Models

| Model | Description | Price |
|-------|-------------|-------|
| `glm-image` | Flagship model with autoregressive + diffusion decoder architecture | $0.015/image |
| `cogview-4` | Alternative image generation model | - |

## Supported Resolutions

Common resolutions (width x height must be 512-2048px, multiples of 32):

| Aspect Ratio | Resolution |
|--------------|------------|
| 1:1 | 1280×1280 |
| 3:4 | 1056×1408 |
| 4:3 | 1408×1056 |
| 16:9 | 1728×960 |
| 9:16 | 960×1728 |

## Notes

- Uses Zhipu AI's OpenAI-compatible endpoint
- Supports Chinese prompts natively
- Output is an image URL that needs to be downloaded
- No reference image support (Zhipu API limitation)
- Default aspect ratio: 3:4 (Xiaohongshu optimized)
- Excellent for text rendering in images (posters, infographics, etc.)

# API Configuration Guide

## Overview

The backend requires API keys for two main functions:
1. **Speech-to-Text** (语音转文字): Convert voice commands to text
2. **Vision Analysis** (图片理解): Analyze camera images for navigation

## Quick Setup

```bash
cd backend
cp .env.example .env
nano .env  # Edit and add your API keys
```

## Configuration Options

### 1. Speech-to-Text (Required for voice commands)

**Option A: OpenAI Whisper (Recommended)**
```bash
SPEECH_TO_TEXT_PROVIDER=openai
SPEECH_TO_TEXT_API_KEY=sk-...
SPEECH_TO_TEXT_BASE_URL=https://api.openai.com/v1
SPEECH_TO_TEXT_MODEL=whisper-1
```

**Option B: OpenAI-compatible API (国内中转)**
```bash
SPEECH_TO_TEXT_PROVIDER=openai
SPEECH_TO_TEXT_API_KEY=your_key
SPEECH_TO_TEXT_BASE_URL=https://your-proxy.com/v1
SPEECH_TO_TEXT_MODEL=whisper-1
```

### 2. Vision Analysis (Required for navigation)

**Option A: Google Gemini (Recommended - cheapest)**
```bash
VISION_PROVIDER=gemini
GEMINI_API_KEY=your_gemini_key
GEMINI_MODEL=gemini-2.0-flash-exp
```

Get Gemini API key: https://aistudio.google.com/app/apikey

**Option B: OpenAI GPT-4o**
```bash
VISION_PROVIDER=openai
OPENAI_API_KEY=sk-...
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_VISION_MODEL=gpt-4o-mini
```

**Option C: OpenAI-compatible API (国内中转)**
```bash
VISION_PROVIDER=openai
OPENAI_API_KEY=your_key
OPENAI_BASE_URL=https://your-proxy.com/v1
OPENAI_VISION_MODEL=gpt-4o-mini
```

### 3. Text-to-Speech (Optional)

By default, the app uses **browser's free speechSynthesis**. No API needed.

If you want higher quality cloud TTS:
```bash
TTS_PROVIDER=openai
TTS_API_KEY=sk-...
TTS_BASE_URL=https://api.openai.com/v1
TTS_MODEL=tts-1
TTS_VOICE=alloy
```

## Minimal Configuration (Recommended for Testing)

For the cheapest setup, use:
- **Speech**: OpenAI Whisper
- **Vision**: Google Gemini
- **TTS**: Browser (free)

```bash
# .env file
SPEECH_TO_TEXT_API_KEY=sk-...
GEMINI_API_KEY=your_gemini_key
VISION_PROVIDER=gemini
```

## Testing Without API Keys

The system works without API keys using mock responses:
- Speech transcription: always returns "go to the podium"
- Vision analysis: returns generic navigation instructions

This is perfect for testing the UI and flow.

## Cost Estimates (100 captures/day)

| Service | Provider | Monthly Cost |
|---------|----------|--------------|
| Speech-to-Text | OpenAI Whisper | ~¥3 (100 commands × ~1 min) |
| Vision | Gemini 2.5 Flash | ~¥5 (3000 images) |
| Vision | GPT-4o-mini | ~¥10 (3000 images) |
| TTS | Browser | Free |
| TTS | OpenAI | ~¥2 (optional) |
| **Total (Gemini)** | | **~¥8/month** |
| **Total (OpenAI)** | | **~¥15/month** |

## Troubleshooting

### "No API key, using mock transcription"
- Check `SPEECH_TO_TEXT_API_KEY` or `OPENAI_API_KEY` is set in `.env`
- Restart backend after editing `.env`

### "No API key, using mock response" (vision)
- Check `GEMINI_API_KEY` or `OPENAI_API_KEY` is set
- Check `VISION_PROVIDER` matches your key (gemini/openai)

### API errors with custom base_url
- Verify the base URL is correct (should end with `/v1`)
- Test with curl: `curl https://your-proxy.com/v1/models -H "Authorization: Bearer YOUR_KEY"`
- Check the proxy supports the required endpoints

### Rate limit errors
- Gemini free tier: 15 requests/minute
- OpenAI: depends on your plan
- Add delays between requests or upgrade your plan

## Security Best Practices

1. **Never commit `.env` to git** - it's already in `.gitignore`
2. **Use environment variables in production**:
   ```bash
   export SPEECH_TO_TEXT_API_KEY=...
   export GEMINI_API_KEY=...
   ```
3. **Rotate keys regularly**
4. **Set spending limits** in API provider dashboards
5. **Monitor usage** to detect abuse

## Advanced: Multiple Providers

You can use different providers for different functions:
```bash
# Speech: OpenAI
SPEECH_TO_TEXT_API_KEY=sk-...

# Vision: Gemini (cheaper)
VISION_PROVIDER=gemini
GEMINI_API_KEY=...

# TTS: Browser (free)
TTS_PROVIDER=browser
```

## Getting API Keys

### OpenAI
1. Go to https://platform.openai.com/api-keys
2. Create new secret key
3. Copy and save it (shown only once)

### Google Gemini
1. Go to https://aistudio.google.com/app/apikey
2. Create API key
3. Copy and save it

### 国内中转服务
Search for "OpenAI API 中转" or "OpenAI API 代理" for domestic proxy services.

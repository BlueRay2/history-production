# CLAUDE.md — Shorts Production (Multi-Agent)

This file provides guidance to Claude Code when working with YouTube Shorts production.

## Project Overview

YouTube Shorts production pipeline for the Cities Evolution channel. Vertical (9:16) videos up to 60 seconds. Shorts are built on realistic transitions between keyframe images: static frames are generated, then Kling AI / Veo creates smooth transitions (I2V Start/End Frame mode). No voiceover, no text narration — pure visual storytelling with music/sound.

## Multi-Agent Architecture

### Token Economy Principle

**Claude Code (Opus 4.6) is a DELEGATOR, not a worker.** Claude's tokens are expensive and should be spent ONLY on:
- Receiving user requests from Telegram
- Parsing intent and routing to the right agent
- Delegating tasks to Codex and Gemini
- Reviewing agent outputs before sending to users
- Coordinating multi-step workflows

**All heavy lifting is delegated to Codex and Gemini.**

### Agent Roles

| Agent | Role | Tasks | Delegation Method |
|-------|------|-------|-------------------|
| **Claude Code** (Opus 4.6) | Orchestrator & Telegram interface | Route requests, delegate, review, send results | Direct |
| **Codex CLI** (GPT-5.4) | Primary prompt engineer & storyboard writer | Generate image prompts, Kling/Veo video prompts, write storyboards, cost estimates | `codex-tracked-exec.sh` or MCP |
| **Gemini CLI** (3.1 Pro) | Researcher & quality checker | Historical research, reference gathering, fact-checking, competitor analysis | `gemini-agent.sh` |

### Delegation Rules

1. **User sends a Shorts request via Telegram** → Claude receives it
2. **Claude identifies the task type:**
   - Prompt generation → **delegate to Codex**
   - Historical research → **delegate to Gemini**
   - Storyboard creation → **Gemini research first** → **then Codex storyboard**
   - Video analysis/review → **delegate to Codex** (GPT-5.4 Vision)
   - Competitor analysis → **delegate to Gemini**
3. **Claude reviews the output** → sends to user via Telegram
4. **Claude does NOT write prompts itself** — only reviews and relays

### Delegation Prompt Templates

**Codex (prompt generation):**
```
You are Codex, the primary prompt engineer for Cities Evolution YouTube Shorts.
Channel: Cities Evolution. Style: wabi-sabi, documentary, warm palette (jade, cedar, amber, moss).
Format: 9:16 vertical, ≤60 seconds. Pipeline: Keyframes → Kling AI/Veo transitions → montage + music.
No voiceover, no text — pure visual storytelling.
Task: [specific task]
```

**Gemini (research):**
```
You are Gemini, the researcher for Cities Evolution YouTube Shorts.
Task: [specific research task]
Focus: historical accuracy, visual references, competitor analysis, trending formats.
Output: structured findings for Codex to use in prompt generation.
```

### Workflow Example

```
User (Telegram): "Сделай шортс про эволюцию одежды в Стамбуле"

Claude: [receives, parses intent, ~100 tokens]
  → Gemini: "Research Istanbul clothing by era" [~3000 tokens]
  → Codex: "Create 30s storyboard with 8 eras using research" [~5000 tokens]
  → Claude reviews and sends to user [~400 tokens]

Claude total: ~500 tokens. Work done: ~8000 tokens by agents.
```

## Skills

Nine project-level skills configured in `.claude/skills/`:

### User-invocable

| Skill | Invocation | Purpose |
|---|---|---|
| `shorts-storyboard` | `/shorts-storyboard` | Main: generate storyboard with Kling prompts |
| `kling-video-prompting` | `/kling-video-prompting` | Kling AI prompt reference (9:16) |
| `setup-channel` | `/setup-channel` | Channel profile setup |
| `setup-video` | `/setup-video` | Per-Short visual concept |
| `article-extractor` | `/article-extractor <url>` | Extract article text |
| `video-analyzer` | `/video-analyzer <path>` | Analyze video frames |
| `youtube-transcript` | `/youtube-transcript <url>` | Download YT transcripts |

### Background knowledge

| Skill | Purpose |
|---|---|
| `shorts-music-audio` | Music/sound design for Shorts |
| `shorts-cost-calculator` | Kling credit costs and budget |

## Video Generation Pipeline

1. **Research** (Gemini): historical context, visual references
2. **Storyboard** (Codex): scene breakdown, keyframe descriptions, transitions
3. **Image Prompts** (Codex): per-keyframe prompts for Nano Banana/GPT/Midjourney
4. **Video Prompts** (Codex): Kling AI / Veo transition prompts
5. **Review** (Claude): quality + accuracy check
6. **Delivery** (Claude): send to user via Telegram

## Video Generation Services

- **Image generation:** Nano Banana, GPT, Midjourney (9:16 keyframes)
- **Video transitions:** Kling AI (I2V Start/End Frame) or Google Veo/Flow
- **Models:** Kling 2.5 Turbo (simple), Kling 3.0 (complex), Veo 3.1 (atmospheric)
- **Format:** 9:16 vertical, ≤60 seconds

## Contributors

- **protasartem2010-sudo** (Артём) — original Shorts repo, Shorts producer
- **BlueRay2** (Дима) — footage generation, montage
- **EvanderLatine** (Ярослав) — project creator, ideator

## Language

Users communicate in Russian via Telegram. Prompts in English. Documentation bilingual.

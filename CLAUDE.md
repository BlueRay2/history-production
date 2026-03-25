# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This repository is a collection of Claude Code skills, prompt templates, and reference documentation for content production workflows — specifically YouTube script production with AI-generated video footage. There is no build system, package manager, or test suite — the project consists entirely of markdown files and shell scripts.

## Repository Structure

- `.claude/skills/` — Installed Claude Code skills (each skill is a directory with `SKILL.md` as entrypoint)
- `docs/TEAM_LEAD_PROMPT.md` — Multi-agent Team Lead prompt for YouTube script production (~80KB, detailed orchestration protocol with Phase 5.5 cost estimation)
- `docs/NICHE_STYLE_GUIDE_TEMPLATE.md` — Шаблон адаптации под конкретный канал и нишу (заполнить и сохранить как `docs/ref/NICHE_STYLE_GUIDE.md` в проекте скрипта)
- `docs/ref/` — Reference documents required by Team Lead prompt (retention strategy, ElevenLabs guide, niche style guide)

## Skills

Thirteen project-level skills are configured in `.claude/skills/`:

### User-invocable skills

| Skill | Invocation | Key Tools | Purpose |
|---|---|---|---|
| `article-extractor` | `/article-extractor <url>` | Bash, Write | Extract clean article text from URLs |
| `content-research-writer` | `/content-research-writer` | (default) | Research and writing assistant |
| `editor` | `/editor` | (default) | Professional editing and proofreading |
| `video-analyzer` | `/video-analyzer <video_path>` | Bash (ffmpeg) | Analyze video by extracting frames |
| `youtube-transcript` | `/youtube-transcript <url>` | Bash, Read, Write | Download YouTube transcripts |
| `sora-2-pro-prompting` | `/sora-2-pro-prompting` | Read | Sora 2 Pro video generation prompts |
| `kling-video-prompting` | `/kling-video-prompting` | Read | Kling AI video generation prompts |
| `google-flow-prompting` | `/google-flow-prompting` | Read | Google Flow (Veo 3.1) video generation prompts |
| `setup-channel` | `/setup-channel` | AskUserQuestion, Write | Interactive fork setup — channel profile (sections 1-8, 10) |
| `setup-video` | `/setup-video` | AskUserQuestion, Edit | Fill video topic (section 9) before each new script |

### Background knowledge skills (non-invocable)

| Skill | Purpose |
|---|---|
| `video-gen-prompts` | Cross-service comparison and prompt adaptation guide (Sora 2, Kling, Flow) |
| `ai-service-selector` | Decision matrix for choosing video generation service per clip (with scene-level temporal rules) |
| `production-cost-estimator` | Production cost calculation methodology and pricing tables |

### Skill details

- `video-analyzer` bundles a helper script at `scripts/extract_frames.sh` — reference it via `${CLAUDE_SKILL_DIR}/scripts/extract_frames.sh`.
- Video generation prompting skills (`sora-2-pro-prompting`, `kling-video-prompting`, `google-flow-prompting`) each contain `references/` subdirectories with detailed pricing, prompt architecture, and camera reference documents.
- `ai-service-selector` includes "Premium Start" temporal quality strategy: premium models for first ~3 minutes, economy models (Flow Veo 3.1 Fast = free) after.
- `production-cost-estimator` covers Sora 2, Kling, Flow, and ElevenLabs pricing; outputs `COST_ESTIMATE.md`.

## Video Generation Services

This project works exclusively with three AI video generation services:
- **Sora 2 Pro** (OpenAI) — cinematic quality, human subjects, complex motion
- **Kling AI** — stylized content, camera movements, abstract visuals, budget-friendly
- **Google Flow / Veo 3.1** — atmospheric shots, establishing footage, free iteration on Ultra

No other video generation services (Runway, Hailuo, Midjourney, Flux, etc.) are used.

## Hooks

A `SessionStart` hook (`.claude/hooks/session-start.sh`) runs automatically at session start with three modes:

1. **FORK_SETUP_NEEDED** — `docs/ref/NICHE_STYLE_GUIDE.md` not found. Suggests `/setup-channel`.
2. **VIDEO_SETUP_NEEDED** — Guide exists but section 9 has `{{...}}` placeholders. Suggests `/setup-video`.
3. **PRICING_CHECK** — Everything configured. Triggers WebSearch to verify AI service pricing is up to date.

## Fork Workflow

1. Fork this repository
2. `/setup-channel` — interactive channel profile setup (sections 1-8, 10)
3. `/setup-video` — fill video topic and parameters (section 9) before each new script
4. Run Team Lead prompt for script production

## Permissions

`.claude/settings.json` runs in `bypassPermissions` mode with sandbox enabled. Bash is auto-allowed when sandboxed. Hooks, permissions, and sandbox config are all in this single file (no `settings.local.json`).

## Language

User communicates in Russian. Documentation and prompts are a mix of Russian and English.

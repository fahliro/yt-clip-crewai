# yt-clip-crewai

YouTube Shorts clipping pipeline yang dijalankan oleh **tim multi-agent CrewAI** —
bukan satu bash script lagi. Arsitektur memisahkan *orchestration deterministik*
(CrewAI Flow) dari *pekerjaan kreatif berbasis keputusan* (CrewAI Crew hierarchical).

> Stack LLM **persis sama** dengan repo [`yt-clip-automation`](https://github.com/fahliro/yt-clip-automation) lama:
> **Groq Whisper** (transkripsi) + **endpoint OpenAI-compatible** (`LLM_API_KEY`/`LLM_BASE_URL`/`LLM_MODEL`) untuk agen.

## Tim (Crew)

| Agent | Peran |
|---|---|
| **Director** | Orchestrator & quality gate (go/no-go) |
| **Content Scout** | Pilih 3–8 momen ber-virality tertinggi |
| **Transcript Engineer** | Transkripsi + timestamp kata (Groq Whisper) |
| **Clip Cutter** | Potong video (buang filler + silence, portrait) |
| **Caption Designer** | Caption typographic ala Opus Clip |
| **YouTube Publisher** | Upload ke YouTube (Upload API) |
| **QA Reviewer** | Validasi sebelum publish |

## Alur (Flow)

```
trigger → resolve_video → analyze (Crew) → upload → mark_done
```

1. **resolve_video** — terima `VIDEO_ID` (WebSub dispatch / manual / poll cron)
2. **analyze** — transkripsi, lalu Crew memilih segmen + mendesain caption + review
3. **upload** — Publisher upload clip yang lolos QA
4. **mark_done** — simpan `state.json` (anti double-clip)

## Setup lokal

```bash
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env   # isi semua secret (sama dengan repo lama)
python -m src.flow <VIDEO_ID>
```

## CI (GitHub Actions)

`.github/workflows/crew.yml` memicu lewat `repository_dispatch` (WebSub),
cron tiap jam, atau `workflow_dispatch`. Public repo = menit Actions unlimited.

Secret yang dibutuhkan (Environment `YT_CHANNEL_ID`): `YT_CHANNEL_ID`,
`YT_COOKIES_TXT`, `YT_UPLOAD_CLIENT`, `YT_UPLOAD_SECRET`, `YT_UPLOAD_TOKEN`,
`YT_READ_TOKEN` (opsional), `GROQ_API_KEY`, `LLM_API_KEY`, `LLM_BASE_URL`;
serta `vars.LLM_MODEL`.

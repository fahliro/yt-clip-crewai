"""The clipping crew: a hierarchical multi-agent team. The Director delegates
creative/decision work to specialist agents, exactly like the team described in
the project brief. Each agent is bound to the OpenAI-compatible LLM endpoint."""
from __future__ import annotations

from crewai import Agent, Crew, Process

from ..config import build_llm
from ..tools import (
    DownloadRawTool, TranscribeTool, PickSegmentsTool, BuildCaptionTool,
    CutClipTool, UploadTool, PollLatestTool,
)


def build_clipping_crew() -> Crew:
    llm = build_llm()

    director = Agent(
        role="Director & Quality Gate",
        goal="Koordinasi tim dan memutuskan clip mana yang layak publish (go/no-go).",
        backstory=(
            "Kamu adalah sutradara pipeline clipping. Kamu membagi tugas ke agen "
            "spesialis, lalu menyetujui hasil akhir sebelum upload."
        ),
        llm=llm,
        tools=[DownloadRawTool(), PollLatestTool()],
        allow_delegation=True,
        verbose=True,
    )

    scout = Agent(
        role="Content Scout (trend & moment analyst)",
        goal="Pilih 3-8 momen ber-virality tertinggi dari transcript untuk Shorts 30-60s.",
        backstory=(
            "Kamu jago membaca transcript dan mengenali momen yang akan engagement "
            "tinggi di YouTube Shorts. Kamu memberi skor dan alasan per momen."
        ),
        llm=llm,
        tools=[PickSegmentsTool()],
        allow_delegation=False,
        verbose=True,
    )

    transcriber = Agent(
        role="Transcript Engineer",
        goal="Ekstrak transcript + timestamp kata akurat via Groq Whisper.",
        backstory="Kamu ahli transkripsi; timestamp per kata harus presisi supaya cut rapi.",
        llm=llm,
        tools=[TranscribeTool()],
        allow_delegation=False,
        verbose=True,
    )

    cutter = Agent(
        role="Clip Cutter",
        goal="Potong video sesuai timestamp (buang filler + silence), portrait 1080x1920.",
        backstory="Kamu editor mekanis yang rapi; output selalu vertikal dan sinambung.",
        llm=llm,
        tools=[CutClipTool()],
        allow_delegation=False,
        verbose=True,
    )

    captioner = Agent(
        role="Caption Designer (Opus-style typographic captions)",
        goal="Bakar caption tebal, highlight, bottom-center seperti Opus Clip.",
        backstory="Kamu desainer caption; teks mudah dibaca, kontras tinggi, animasi kata.",
        llm=llm,
        tools=[BuildCaptionTool()],
        allow_delegation=False,
        verbose=True,
    )

    uploader = Agent(
        role="YouTube Publisher",
        goal="Upload clip ke YouTube (public) dengan title/desc yang menarik.",
        backstory="Kamu publisher andal; handle OAuth, retry, dan metadata SEO.",
        llm=llm,
        tools=[UploadTool()],
        allow_delegation=False,
        verbose=True,
    )

    qa = Agent(
        role="QA Reviewer",
        goal="Validasi durasi, audio, caption kebakar, dan kepatuhan policy sebelum publish.",
        backstory="Kamu pengawas kualitas yang teliti; tidak lolos kalau ada cacat.",
        llm=llm,
        tools=[],
        allow_delegation=False,
        verbose=True,
    )

    return Crew(
        agents=[director, scout, transcriber, cutter, captioner, uploader, qa],
        process=Process.hierarchical,
        manager_agent=director,
        verbose=True,
    )

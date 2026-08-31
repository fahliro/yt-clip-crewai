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

    # ---- Tasks (hierarchical: director delegates, agents execute) ----
    from crewai import Task

    transcribe_task = Task(
        description="Transkripsi video {raw_path} via Groq Whisper. Kembalikan dict "
                    "berisi 'duration' dan 'words' (list {word,start,end}).",
        expected_output="Dict {duration:float, words:[{word,start,end}]}",
        agent=transcriber,
    )

    analyze_task = Task(
        description="Dari transcript, pilih 3-8 segmen Shorts terbaik (30-60s) lengkap "
                    "dengan start, end, score virality (1-10), reason, dan fillers. "
                    "Urutkan by score menurun.",
        expected_output="JSON list [{start,end,score,reason,fillers}] (3-8 item)",
        agent=scout,
        context=[transcribe_task],
    )

    cut_task = Task(
        description="Untuk TIAP segmen terpilih, potong raw video (buang filler + silence) "
                    "dan bakar caption Opus-style. Hasilkan list clip .mp4 + title + description.",
        expected_output="List objek {clip_path, title, description, approved:true}",
        agent=cutter,
        context=[analyze_task],
    )

    caption_task = Task(
        description="Review caption tiap clip: pastikan teks kontras, bottom-center, "
                    "mudah dibaca (Opus-style). Laporkan jika ada yang perlu di-tweak.",
        expected_output="QA notes per clip (atau 'OK')",
        agent=captioner,
        context=[cut_task],
    )

    review_task = Task(
        description="Validasi tiap clip: durasi 30-60s, audio ada, caption kebakar, "
                    "tidak melanggar policy. Set 'approved' tiap clip.",
        expected_output="List {clip_path, approved:bool, reason}",
        agent=qa,
        context=[cut_task, caption_task],
    )

    upload_task = Task(
        description="Upload semua clip ber-approved=true ke YouTube (public) via Upload API. "
                    "Gunakan title/description dari cut_task. Kembalikan list URL.",
        expected_output="List URL youtu.be/* yang berhasil diupload",
        agent=uploader,
        context=[review_task],
    )

    return Crew(
        agents=[director, scout, transcriber, cutter, captioner, uploader, qa],
        tasks=[transcribe_task, analyze_task, cut_task, caption_task, review_task, upload_task],
        process=Process.hierarchical,
        manager_agent=director,
        verbose=True,
    )

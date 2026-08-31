"""CrewAI Flow: orchestrates the clipping pipeline end-to-end.

Flow = deterministic pipeline (trigger -> analyze -> cut -> caption -> review ->
upload). The creative/decision steps are delegated to the hierarchical Crew.

Usage:
    python -m src.flow                       # uses VIDEO_ID env or polls latest
    python -m src.flow <video_id>            # explicit video
"""
from __future__ import annotations

import sys

from crewai.flow import Flow, listen, start

from .config import TEST_VIDEO_ID, MAX_CLIPS
from .crew import build_clipping_crew
from .tools import DownloadRawTool, TranscribeTool, PollLatestTool
from .utils import already_done, mark_done, log, WORKDIR


class ClipPipelineFlow(Flow):
    def __init__(self):
        super().__init__()
        self.video_id: str = ""
        self.raw_path: str = ""
        self.transcript: dict = {}
        self.uploaded: list[str] = []

    @start()
    def resolve_video(self):
        """Determine which video to clip (env -> arg -> poll)."""
        self.video_id = (
            (sys.argv[1] if len(sys.argv) > 1 else "")
            or TEST_VIDEO_ID
        )
        if not self.video_id:
            poll = PollLatestTool()
            self.video_id = poll._run() or TEST_VIDEO_ID
        log(f"target video_id={self.video_id}")
        if already_done(self.video_id):
            log("sudah di-clip, skip"); return
        self.raw_path = DownloadRawTool()._run(self.video_id)

    @listen(resolve_video)
    def analyze(self):
        if already_done(self.video_id):
            return
        self.transcript = TranscribeTool()._run(self.raw_path)
        # Hand decision-making (segment selection + caption design + review) to the Crew
        crew = build_clipping_crew()
        result = crew.kickoff(inputs={
            "video_id": self.video_id,
            "raw_path": self.raw_path,
            "transcript": self.transcript,
            "max_clips": MAX_CLIPS,
        })
        # Crew returns a list of {clip_path, title, description, approved}
        self._clips = getattr(result, "raw", result) if not isinstance(result, list) else result

    @listen(analyze)
    def upload(self):
        if already_done(self.video_id):
            return
        clips = getattr(self, "_clips", [])
        from .tools import UploadTool
        uploader = UploadTool()
        for c in clips:
            if not c.get("approved", True):
                log(f"clip ditolak QA: {c.get('title')}"); continue
            url = uploader._run(c["clip_path"], c["title"], c.get("description", ""))
            self.uploaded.append(url)
        mark_done(self.video_id)
        log(f"SELESAI: {len(self.uploaded)} clip diupload -> {self.uploaded}")


def main():
    ClipPipelineFlow().kickoff()


if __name__ == "__main__":
    main()

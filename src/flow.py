"""CrewAI Flow: orchestrates the clipping pipeline end-to-end.

Flow = deterministic pipeline (resolve video -> run crew -> mark done).
The crew itself handles transcribe -> analyze -> cut -> caption -> review -> upload
(the creative/decision + publishing steps), exactly like the team brief.

Usage:
    python -m src.flow                       # uses VIDEO_ID env or polls latest
    python -m src.flow <video_id>            # explicit video
"""
from __future__ import annotations

import sys

from crewai.flow import Flow, listen, start

from .config import TEST_VIDEO_ID
from .crew import build_clipping_crew
from .tools import DownloadRawTool, PollLatestTool
from .utils import already_done, mark_done, log


class ClipPipelineFlow(Flow):
    def __init__(self):
        super().__init__()
        self.video_id: str = ""
        self.raw_path: str = ""

    @start()
    def resolve_video(self):
        """Determine which video to clip (env -> arg -> poll)."""
        self.video_id = (
            (sys.argv[1] if len(sys.argv) > 1 else "")
            or TEST_VIDEO_ID
        )
        if not self.video_id:
            self.video_id = PollLatestTool()._run() or TEST_VIDEO_ID
        log(f"target video_id={self.video_id}")
        if already_done(self.video_id):
            log("sudah di-clip, skip"); return
        self.raw_path = DownloadRawTool()._run(self.video_id)

    @listen(resolve_video)
    def run_crew(self):
        """Delegate all creative + publishing steps to the Crew. The crew's
        upload_task publishes clips; we just record completion here."""
        if already_done(self.video_id):
            return
        crew = build_clipping_crew()
        result = crew.kickoff(inputs={
            "video_id": self.video_id,
            "raw_path": self.raw_path,
        })
        log(f"crew selesai: {getattr(result, 'raw', result)}")
        mark_done(self.video_id)
        log("SELESAI (clip diupload oleh crew.upload_task)")


def main():
    ClipPipelineFlow().kickoff()


if __name__ == "__main__":
    main()

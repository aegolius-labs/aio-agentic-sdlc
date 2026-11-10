import datetime
import os

from .workspace import ARCHIVE_DIR


# aio-sdlc-mapping-approval: {"candidate_reality_id":"ac41eaca-b3f9-55fc-850a-a633ffc6b723","identity_approval":{"approved_at":"2026-08-10T10:12:30.970663-04:00","approved_by":"Felix","candidate_reality_id":"ac41eaca-b3f9-55fc-850a-a633ffc6b723","evidence_digest":"b822c46ff78c9fac9717f904f769a80af67e265b243ac951d72673e78c20bca9","intent_id":"6506870b-b262-4f54-b6e9-43de4a873a55","rationale":"Felix approved PRDArchiver as the implementation identity of the PRD Archiver component; behavioral completeness remains separately reviewable.","schema_version":1,"source_path":"src/aio_agentic_sdlc/archiver.py","source_sha256":"cdd5b44b21809aa5c94f6577b7302f2455e131ae8d9c9c3853c7f30487e90022","symbol_kind":"class","symbol_name":"PRDArchiver"},"intent_id":"6506870b-b262-4f54-b6e9-43de4a873a55","maintenance_approval":{"approved_at":"2026-11-10T12:17:12+00:00","approved_by":"Felix","evidence_digest":"0db8d49e418b8c9d162182f727165e56e8202cdca6fab25c69211d89971f8620","rationale":"Felix approved the batch refresh of the 15 older mapping receipts on the 2026-11-10 decision card, at the review digests listed in .aio-agentic-sdlc/changes/symbol-receipts-2026-11-09/refresh-batch.json. Rebinds the receipt to its symbol; the approved identity is unchanged and no behavior or acceptance is claimed.","supersedes_receipt_sha256":"a78b4202cf5474f5d86d38ef2cb48f33f34694425cc263524efd879a913ed02b"},"schema_version":2,"source_path":"src/aio_agentic_sdlc/archiver.py","source_sha256":"cf08847b54aeebd06ab110ea6447196dc7b4b686a68b096d999966a624207b40","symbol_kind":"class","symbol_name":"PRDArchiver","symbol_sha256":"de983f14d0f7240fb03799285085f121a215ca0c8a32943d016c7ca4a8834303"}
# aio-sdlc-node: 6506870b-b262-4f54-b6e9-43de4a873a55
class PRDArchiver:
    def __init__(self, archive_dir: str = ARCHIVE_DIR):
        self.archive_dir = archive_dir

    def archive(self, file_path: str) -> str:
        """
        Moves a file to the archive directory.
        If a file with the same name exists, it appends a timestamp to prevent overwriting.
        Returns the new path of the archived file.
        """
        if not os.path.lexists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        if not os.path.lexists(self.archive_dir):
            os.makedirs(self.archive_dir)
        elif not os.path.isdir(self.archive_dir):
            raise NotADirectoryError(
                f"Archive destination exists but is not a directory: {self.archive_dir}"
            )

        filename = os.path.basename(file_path)
        dest_path = os.path.join(self.archive_dir, filename)

        if os.path.lexists(dest_path):
            name, ext = os.path.splitext(filename)
            timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
            new_filename = f"{name}_{timestamp}{ext}"
            dest_path = os.path.join(self.archive_dir, new_filename)

        os.replace(file_path, dest_path)
        return dest_path

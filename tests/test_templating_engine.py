import os

import pytest

from aio_agentic_sdlc import templating_engine
from aio_agentic_sdlc.templating_engine import (
    TemplateValidationError,
    generate_document,
)
from aio_agentic_sdlc.workspace import WORKSPACE_DIR


def _document_recovery_bytes(project) -> list[bytes]:
    recovery = project / WORKSPACE_DIR / "backups" / "document-transitions"
    return [path.read_bytes() for path in recovery.iterdir()]


def test_generate_document(tmp_path):
    # Use tmp_path to create a dummy template directory
    templates_dir = tmp_path / "templates"
    templates_dir.mkdir()

    template_content = (
        "Title: {{ title }}\nAuthor: {{ author }}\nContent: {{ content }}"
    )
    template_file = templates_dir / "test-template.md"
    template_file.write_text(template_content, encoding="utf-8")

    data = {"title": "Test Title", "author": "Alice", "content": "This is a test."}
    output_file = tmp_path / "output.md"

    result = generate_document(
        "test-template.md",
        data,
        str(output_file),
        templates_dir=str(templates_dir),
    )

    assert "Title: Test Title" in result
    assert "Author: Alice" in result
    assert "Content: This is a test." in result

    assert output_file.exists()
    assert output_file.read_text(encoding="utf-8") == result


def test_template_not_found(tmp_path):
    templates_dir = tmp_path / "templates"
    templates_dir.mkdir()

    with pytest.raises(FileNotFoundError, match="Template 'missing.md' not found"):
        generate_document("missing.md", {}, "out.md", templates_dir=str(templates_dir))


def test_generate_document_preserves_template_trailing_newline(tmp_path):
    templates_dir = tmp_path / "templates"
    templates_dir.mkdir()
    (templates_dir / "report.md").write_text(
        "# {{ title }}\n",
        encoding="utf-8",
    )

    rendered = generate_document(
        "report.md",
        {"title": "Evidence"},
        str(tmp_path / "report.md"),
        templates_dir=str(templates_dir),
    )

    assert rendered == "# Evidence\n"
    assert (tmp_path / "report.md").read_bytes().endswith(b"\n")


def test_generate_document_overwrite_retains_old_content_in_private_recovery(tmp_path):
    templates_dir = tmp_path / "templates"
    templates_dir.mkdir()
    (templates_dir / "report.md").write_text("# {{ title }}\n", encoding="utf-8")
    output = tmp_path / "report.md"
    old = b"# Previous\n"
    output.write_bytes(old)

    rendered = generate_document(
        "report.md",
        {"title": "Current"},
        str(output),
        templates_dir=str(templates_dir),
        project_path=str(tmp_path),
    )

    assert output.read_text(encoding="utf-8") == rendered == "# Current\n"
    assert old in _document_recovery_bytes(tmp_path)
    assert list(tmp_path.glob(".report.md.*")) == [tmp_path / ".report.md.lock"]


def test_generate_document_preserves_swap_at_output_retire_boundary(
    tmp_path,
    monkeypatch,
):
    templates_dir = tmp_path / "templates"
    templates_dir.mkdir()
    (templates_dir / "report.md").write_text("# {{ title }}\n", encoding="utf-8")
    output = tmp_path / "report.md"
    old = b"# Previous\n"
    foreign = b"FOREIGN-OUTPUT\n"
    output.write_bytes(old)
    adversary_saved = tmp_path / "adversary-saved.md"
    real_move = templating_engine._move_output_no_replace
    swapped = False

    def swap_before_retire(source, destination):
        nonlocal swapped
        if source == output and str(destination).endswith(".document-backup"):
            output.rename(adversary_saved)
            output.write_bytes(foreign)
            swapped = True
        return real_move(source, destination)

    monkeypatch.setattr(
        templating_engine, "_move_output_no_replace", swap_before_retire
    )
    with pytest.raises(TemplateValidationError, match="changed during write"):
        generate_document(
            "report.md",
            {"title": "Current"},
            str(output),
            templates_dir=str(templates_dir),
            project_path=str(tmp_path),
        )

    assert swapped is True
    assert output.read_bytes() == foreign
    assert adversary_saved.read_bytes() == old
    assert b"# Current\n" in _document_recovery_bytes(tmp_path)


def test_generate_document_never_overwrites_new_install_occupant(
    tmp_path,
    monkeypatch,
):
    templates_dir = tmp_path / "templates"
    templates_dir.mkdir()
    (templates_dir / "report.md").write_text("# {{ title }}\n", encoding="utf-8")
    output = tmp_path / "report.md"
    old = b"# Previous\n"
    foreign = b"FOREIGN-INSTALL-OCCUPANT\n"
    output.write_bytes(old)
    real_move = templating_engine._move_output_no_replace
    occupied = False

    def occupy_install_target(source, destination):
        nonlocal occupied
        if source.name.endswith(".tmp") and destination == output:
            output.write_bytes(foreign)
            occupied = True
        return real_move(source, destination)

    monkeypatch.setattr(
        templating_engine,
        "_move_output_no_replace",
        occupy_install_target,
    )
    with pytest.raises(TemplateValidationError, match="changed during write"):
        generate_document(
            "report.md",
            {"title": "Current"},
            str(output),
            templates_dir=str(templates_dir),
            project_path=str(tmp_path),
        )

    assert occupied is True
    assert output.read_bytes() == foreign
    recovery_bytes = _document_recovery_bytes(tmp_path)
    assert old in recovery_bytes
    assert b"# Current\n" in recovery_bytes


def test_generate_document_rejects_symlinked_output_without_external_write(tmp_path):
    templates_dir = tmp_path / "templates"
    templates_dir.mkdir()
    (templates_dir / "report.md").write_text("# {{ title }}\n", encoding="utf-8")
    external = tmp_path / "external.md"
    external.write_text("preserve", encoding="utf-8")
    output = tmp_path / "output.md"
    try:
        os.symlink(external, output)
    except OSError as error:
        pytest.skip(f"Symlink creation unavailable: {error}")

    with pytest.raises(ValueError, match="regular file"):
        generate_document(
            "report.md",
            {"title": "escaped"},
            str(output),
            templates_dir=str(templates_dir),
        )

    assert external.read_text(encoding="utf-8") == "preserve"

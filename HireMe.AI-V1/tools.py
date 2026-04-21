import re


_PLACEHOLDER_RE = re.compile(r"\[[^\]]+\]")


def _has_substantive_content(section_lines: list[str]) -> bool:
    for line in section_lines:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("## "):
            continue
        candidate = _PLACEHOLDER_RE.sub("", stripped).strip(" -|:")
        if candidate:
            return True
    return False


def format_resume_markdown(resume_content: str) -> str:
    """Normalize resume markdown output and remove empty template sections."""
    lines = str(resume_content).strip().splitlines()
    if not lines:
        return ""

    output_lines: list[str] = []
    current_section: list[str] = []
    in_section = False

    for line in lines:
        if line.startswith("## "):
            if in_section and _has_substantive_content(current_section):
                if output_lines and output_lines[-1] != "":
                    output_lines.append("")
                output_lines.extend(current_section)
            current_section = [line]
            in_section = True
            continue

        if in_section:
            current_section.append(line)
        else:
            output_lines.append(line)

    if in_section and _has_substantive_content(current_section):
        if output_lines and output_lines[-1] != "":
            output_lines.append("")
        output_lines.extend(current_section)

    return "\n".join(output_lines).strip()


def format_cover_letter_markdown(cover_letter_content: str) -> str:
    """Normalize cover letter markdown output."""
    return str(cover_letter_content).strip()

from privacyradar.hashing import changed_sections, doc_hash, normalize_markdown, section_hashes


def test_normalize_markdown_collapses_whitespace_and_blank_lines() -> None:
    raw = "Title  \r\n\r\n\r\nA   sentence\twith spaces.  \r\n"

    assert normalize_markdown(raw) == "Title\n\nA sentence with spaces.\n"


def test_doc_hash_ignores_cosmetic_whitespace() -> None:
    assert doc_hash("# Privacy\nWe collect email.") == doc_hash(
        "# Privacy  \r\nWe   collect   email.\r\n"
    )


def test_section_hashes_split_headings_and_uppercase_labels() -> None:
    hashes = section_hashes(
        "Intro text\n\n# Collection\nEmail address\n\nYOUR CONTROLS\nDelete your account"
    )

    assert set(hashes) == {"_preamble", "Collection", "YOUR CONTROLS"}


def test_changed_sections_includes_added_removed_and_modified_sections() -> None:
    old = {"same": "1", "changed": "old", "removed": "x"}
    new = {"same": "1", "changed": "new", "added": "y"}

    assert changed_sections(old, new) == ["added", "changed", "removed"]

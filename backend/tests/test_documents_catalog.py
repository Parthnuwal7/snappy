from app.case.documents import (
    DOC_TYPES, DOC_TYPE_KEYS, DEFAULT_DOC_TYPE, MAX_DOCUMENT_BYTES,
    ALLOWED_EXTENSIONS, is_valid_doc_type, is_allowed_filename, extension_of,
)


def test_doc_types_include_legal_vocabulary():
    assert {"pleading", "wakalatnama", "evidence", "order",
            "correspondence", "draft", "other"} <= DOC_TYPE_KEYS
    assert all("label" in d for d in DOC_TYPES)


def test_defaults_and_limits():
    assert DEFAULT_DOC_TYPE == "other"
    assert MAX_DOCUMENT_BYTES == 25 * 1024 * 1024


def test_doc_type_validation():
    assert is_valid_doc_type("evidence")
    assert not is_valid_doc_type("smoke")


def test_filename_rules():
    assert is_allowed_filename("petition.pdf")
    assert is_allowed_filename("Scan.JPG")
    assert not is_allowed_filename("malware.exe")
    assert not is_allowed_filename("noext")
    assert extension_of("Scan.JPG") == "jpg"

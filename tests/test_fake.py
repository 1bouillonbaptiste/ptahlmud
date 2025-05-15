from ptahlmud.fake import get_ptahlmud


def test_get_ptahlmud():
    assert get_ptahlmud() == "ptahlmud"

from scripts.check_policy import check_branch, check_title


def test_valid_metadata() -> None:
    assert check_title("feat(api): initialize bootstrap (AT-207)", "AT-207")
    assert check_branch("feature/AT-207-api-bootstrap", "AT-207")


def test_rejects_wrong_issue_and_merge_style() -> None:
    assert not check_title("feat(api): initialize bootstrap (AT-208)", "AT-207")
    assert not check_title("Merge pull request #1", "AT-207")
    assert not check_branch("feature/AT-208-api-bootstrap", "AT-207")


def test_other_issue_can_use_same_policy() -> None:
    assert check_title("feat(auth): add login (AT-209)", "AT-209")
    assert check_branch("feature/AT-209-login", "AT-209")

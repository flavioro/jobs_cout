from bs4 import BeautifulSoup
import pytest


@pytest.mark.parametrize(
    "selector",
    [
        "[data-testid='expandable-text-box']",
        "a[href*='/company/']",
        "a[href*='currentJobId=']",
    ],
)
def test_regression_contract_selectors_exist_in_all_real_pages(selector, linkedin_case):
    soup = BeautifulSoup(linkedin_case["html"], "lxml")
    assert soup.select_one(selector) is not None

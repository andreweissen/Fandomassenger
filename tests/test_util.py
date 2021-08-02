from fandomassenger import util


def test_is_fandom_wiki_base_url():
    test_cases = [
        {
            "url": "https://eizen.fandom.com/",
            "result": False
        },
        {
            "url": "http://eizen.fandom.com",
            "result": True
        },
        {
            "url": "https://eizen.wikia.com",
            "result": False
        },
        {
            "url": "http://google.com",
            "result": False
        },
        {
            "url": "fandom.com",
            "result": False
        },
        {
            "url": "https://wikia.org",
            "result": False
        },
        {
            "url": "malformed input",
            "result": False
        }
    ]

    for test_case in test_cases:
        print(f'Test case: {test_case["url"]}')
        print(f'\tExpected result: {test_case["result"]}')
        outcome = util.is_fandom_wiki_base_url(test_case["url"])
        print(f"\tObserved result: {outcome}")
        print(f'\t{("Failed", "Passed")[outcome == test_case["result"]]}')

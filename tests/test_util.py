import fandomassenger.api as api
import fandomassenger.util as util
import requests
import unittest


class TestUtil(unittest.TestCase):
    def test_is_fandom_wiki_base_url(self):
        for test_case in [
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
        ]:
            self.assertEqual(util.is_fandom_wiki_base_url(test_case["url"]),
                             test_case["result"])

    def test_JsonModelHTMLParser(self):
        test_case = '{"type":"doc","content":[{"type":"paragraph","content":[{"type":"text","text":"Test "},{"type":"text","marks":[{"type":"link","attrs":{"href":"https://eizen.fandom.com/wiki/Message_Wall:Eizen","title":null}}],"text":"link here"},{"type":"text","text":" text "},{"type":"text","marks":[{"type":"link","attrs":{"href":"https://eizen.fandom.com/wiki/User:Eizen","title":null}}],"text":"another link"},{"type":"text","text":"."}]}]}'
        wikitext = "Test [[Message Wall:Eizen|link here]] text [[User:Eizen|another link]]."
        api_php = "https://eizen.fandom.com/api.php"
        parsed_message_body = api.parse_wikitext(wikitext, api_php,
                                                 requests.Session())
        (parser := util.JsonModelHTMLParser()).feed(parsed_message_body)

        print(test_case)
        print(json_model := parser.get_json_model_as_string())

        self.assertEqual(json_model, test_case)


if __name__ == "__main__":
    unittest.main()

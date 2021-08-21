"""
The ``test_util`` module serves to encapsulate all the code used to test the
various helper functions and classes that together constitute the
``fandomassenger.util``. Its primary content takes the form of a instantiating
subclass of ``unittest.TestCase`` that is tacitly instantiated by the
``runner.py`` file's ``unittest.TextTestRunner`` as part of a test suite.
"""

__author__ = "Andrew Eissen"
__version__ = "0.1"

import fandomassenger.api as api
import fandomassenger.util as util
import json
import unittest


class TestUtil(unittest.TestCase):
    """
    The ``TestUtil`` class extends the base ``unittest.TestCase`` class and
    contains functionality that tests the various disparate helper functions and
    classes present in the ``fandomassenger.util`` module. It is tacitly
    instantiated by the ``runner.py`` file's ``unittest.TextTestRunner`` as part
    of a test suite.
    """

    def test_is_fandom_wiki_base_url(self):
        """
        The ``test_is_fandom_wiki_base_url`` tests the function of the same name
        present in ``fandomassenger.util`` to ensure all passed URLs provided by
        the user are validated and improper URLs that aren't on the Wikia/Fandom
        domain are caught successfully. As such, a list of dictionaries is
        provided as test data, containing a possible URL and a boolean denoting
        whether the case should pass of fail.
            :return: None
        """

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
        """
        The ``test_JsonModelHTMLParser`` tests the ``JsonModelHTMLParser`` class
        that constitutes the parser responsible for converting HTML content into
        the "jsonModel" used by Fandom's ``wikia.php`` endpoint as the means by
        which message content is expressed. This test ensures that the parser
        generates permissible jsonModels that the appropriate endpoint would
        consider correct, well-formed input.

        The function loads an example JSON file from ``/data`` constituting a
        cases of well-formed input. This was obtained by posting a message via
        the endpoint and grabbing the resultant jsonModel from the developer
        console's Network tab in the browser.
            :return: None
        """

        # Grab test JSON
        test_file = util.get_json_file("../data/testJsonModel.json")
        test_case = json.dumps(test_file, separators=(',', ':'))

        # Wikitext that generated example JSON above
        wikitext = "Test [[Message Wall:Eizen|link here]] text " \
                   + "[[User:Eizen|another link]]."

        # Use test wiki
        api_php = "https://eizen.fandom.com/api.php"

        # Grab parsed HTML generated from wikitext
        parsed_message_body = api.parse_wikitext(wikitext, api_php)

        # Pass HTML to the parser for... well, parsing
        (parser := util.JsonModelHTMLParser()).feed(parsed_message_body)

        print(test_case)
        print(json_model := parser.get_json_model_as_string())

        # Check if equal (may be too long?)
        self.assertEqual(json_model, test_case)

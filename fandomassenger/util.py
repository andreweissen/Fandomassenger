"""
The ``util`` module is used to contain utility functions and classes that have
practical utility within the context of this application but which could
conceivably be co-opted to serve in a different context for a different
application if needed. As such, there are no hardcoded magic numbers or any such
application-specific logic that might hinder their porting to a different
package or program.
"""

__all__ = [
    "JsonModelHTMLParser",
    "determine_system_language",
    "get_json_file",
    "has_rights",
    "is_fandom_wiki_base_url",
    "log_msg",
    "log_prompt",
    "pretty_print",
    "split_delimited_string_into_list"
]
__author__ = "Andrew Eissen"
__version__ = "0.1"

import ctypes
import html.parser
import json
import locale
import os
import re
import sys
import urllib.parse


class JsonModelHTMLParser(html.parser.HTMLParser):
    def __init__(self):
        """
        The ``JsonModelHTMLParser`` class is a subclass extending the base
        ``html.parser`` ``HTMLParser`` class that is used for parsing HTML
        strings into ProseMirror-style ``jsonModel`` JSON objects used by
        Fandom's UCP Message Walls to represent user input.

        At present, the class only looks for ``<p>`` and ``<a>`` elements,
        though support is planned for bold, underline, and italic elements in
        future as this sort of text formatting is permissible in Message Wall
        thread content.
        """
        html.parser.HTMLParser.__init__(self)

        # Temporary holding stacks for <p> and <a> HTML elements
        self.paragraphs_stack = []
        self.links_stack = []

        # Base jsonModel object
        self.json_model = {
            "type": "doc",
            "content": []
        }

    def handle_starttag(self, tag, attrs):
        """
        The ``handle_starttag`` function overrides its parent class's default
        implementation and accepts a pair of arguments, namely a string named
        ``tag`` representing the plaintext name of the HTML tag encountered
        (p, a, div, span, etc.) and a list named ``attrs`` containing key/value
        tuples that represent the element's attributes (href, title, etc.)

        The function checks for ``<p>`` and ``<a>`` elements. If the present tag
        is of the former, it adds a new paragraph node to the class instance's
        ``paragraphs_stack`` storage stack. If the present tag is a link, the
        function creates a new link node, populates its ``mark`` list with the
        link's ``href`` and ``title`` attributes, pushes the new node onto the
        class instance's ``links_stack`` storage stack, and likewise pushes the
        node onto the closest paragraph node's ``content`` list.
            :param tag: The plaintext string representation of the currently
                viewed tag (p, a, div, span, etc.) without the ``<>`` brackets
            :param attrs: A list of key/value tuples containing the attributes
                of the current HTML element
            :return: None
        """
        if tag == "p":
            self.paragraphs_stack.append({
                "type": "paragraph",
                "content": []
            })
        elif tag == "a":
            new_link = {
                "type": "text",
                "marks": [
                    {
                        "type": "link",
                        "attrs": {}
                    }
                ]
            }

            # jsonModel only cares for href and title link attributes
            for attr in attrs:
                if attr[0] == "href":
                    new_link["marks"][0]["attrs"]["href"] = attr[1]
                elif attr[0] == "title":
                    new_link["marks"][0]["attrs"]["title"] = attr[1]

            self.links_stack.append(new_link)
            self.paragraphs_stack[-1]["content"].append(new_link)

    def handle_endtag(self, tag):
        """
        The ``handle_endtag`` function overrides its parent class's default
        implementation and accepts a single argument, namely a string named
        ``tag`` representing the plaintext name of the HTML tag encountered
        (p, a, div, span, etc.).

        The function serves to indicate that the end of the current element has
        been reached. Within the context of the class and its intended use, this
        indicates that the "current" elements sitting at the end of the class's
        two helper stacks, ``paragraphs_stack`` and ``links_stack``, can be
        popped off. In the event of encountered ``</p>`` tags, the popped
        paragraph JSON object node is then added to and preserved int the master
        ``json_model`` object as part of the essential representational
        structure.
            :param tag: The plaintext string representation of the currently
                viewed tag (p, a, div, span, etc.) without the ``<>`` brackets
            :return: None
        """
        if tag == "p":
            self.json_model["content"].append(self.paragraphs_stack.pop())
            return
        elif tag == "a":
            self.links_stack.pop()

    def handle_data(self, data):
        """
        The ``handle_data`` function overrides its parent class's default
        implementation and accepts a single argument, namely a string named
        ``data`` that represents the contents of the HTML element currently
        under inspection by the parser.

        If there is a link node on the appropriate ``links_stack``, the data
        belongs to that link, so it is added to that link object as the value of
        a key titled "text." However, if there are no extant link nodes and
        there is a paragraph node on the ``paragraphs_stack``, the data lies
        between ``<p>`` tags, so a new text object is created and added to
        current paragraph object's ``content`` list.
            :param data: A string constituting the plaintext contents of the
                currently inspected HTML tag
            :return: None
        """
        if len(self.links_stack):
            self.links_stack[-1]["text"] = data
        elif len(self.paragraphs_stack):
            self.paragraphs_stack[-1]["content"].append({
                "type": "text",
                "text": data
            })

    def error(self, message):
        """
        The ``handle_data`` function overrides its parent class's default
        implementation and accepts a single argument, namely a string named
        ``message`` describing the nature of the error encountered in the course
        of parsing the HTML. This method is not used in the class's usual use
        cases, and simply logs the parameter message in the console.
            :param message: A string describing the specific error encountered
                in the course of parsing the input HTML
            :return: None
        """
        log_msg(message, True)

    def get_json_model_as_string(self):
        """
        The ``get_json_model_as_string`` function is the only custom class
        method included in the ``JsonModelHTMLParser`` class. It serves simply
        to return the value of the class instance's ``json_model`` field, a JSON
        object representing the HTML input and layout, as a string. The purpose
        of this operation is related to the intended use of the string jsonModel
        within the context of the ``wikia.php`` endpoints as a required POST
        parameter.
            :return: The method returns the jsonModel existing as a member field
                of the class instance as a string for inclusion in POST requests
                made to the appropriate ``wikia.php`` endpoints
        """
        return json.dumps(self.json_model)


def determine_system_language():
    """
    The (admittedly janky) ``determine_system_language`` function is used to
    detect and determine the system language being used on the computer running
    the application. As this differs for Windows and UNIX-based operating
    systems, two approaches are used, though if the operating system is not
    "nt" (Windows) or "posix" (Linux/Mac OS), the language code "en" is returned
    by default for English.
        :return: A two-character string representing the abbreviation of the
            detected system language ("en" for "en_US" and "en_UK", etc.)
    """
    if os.name == "nt":
        windll = ctypes.windll.kernel32.GetUserDefaultUILanguage()
        return locale.windows_locale[windll].split("_")[0]
    elif os.name == "posix":
        return locale.getdefaultlocale()[0].split("_")[0]
    else:
        return "en"


def get_json_file(filename):
    """
    The ``get_json_file`` function is a simple helper function that serves to
    open, load, and return the contents of the JSON file indicated in the input
    ``filename`` formal parameter.
        :param filename: A string indicating the location and name of the
            desired JSON file to open
        :return: The contents of the indicated JSON file are returned for
            subsequent usage
    """
    return json.load(open(filename, "r"))


def has_rights(groups, permissible):
    """
    The ``has_rights`` function is used to determine whether the user whose list
    of user rights is passed as the ``groups`` formal parameter possesses the
    required permissions necessary to undertake whatever restricted operation is
    intended. The list produced by ``re.findall`` is coerced into a boolean and
    returned as the returned status of the function.
        :param groups: A list of strings denoting the specific user rights
            groups to which the currently queried user belongs according to the
            MediaWiki API's ``list=users`` endpoint
        :param permissible: A list of strings denoting the target user rights
            against which to compare the user's usergroups for membership
        :return: A boolean denoting whether the user has the permissions
            necessary to undertake whatever operation is intended
    """
    return bool(re.findall(rf'(?=({"|".join(permissible)}))', "|".join(groups)))


def is_fandom_wiki_base_url(url):
    """
    The ``is_fandom_wiki_base_url`` helper function is used to determine whether
    a given URL has a base URL address corresponding to one of the permissible
    Wikia/Fandom domains, namely, ``wikia.org`` and ``fandom.com``. The formal
    parameter, ``url``, is expected to be a base URL, and its subdomain (if any)
    is popped off prior to comparison. A boolean is returned as the return value
    indicating whether the domain of the parameter matches one of the
    Wikia/Fandom default domains.
        :param url: A string representing the desired URL for which the function
            will check its base address for compliance with a ``wikia.org`` or
            ``fandom.com`` domain.
        :return: A boolean representing whether the parameter url's base address
            is ``wikia.org`` or ``fandom.com`` is returned
    """
    parsed = urllib.parse.urlparse(url.strip(" "))

    # Only scheme and netloc should be present in base URL
    if (not parsed.scheme or not parsed.netloc or parsed.path or parsed.params
            or parsed.query or parsed.fragment):
        return False

    # "eizen.fandom.com" -> ["eizen", "fandom", "com"]
    domain = parsed.netloc.split(".")

    # ["eizen", "fandom", "com"] -> ["fandom", "com"]
    domain.pop(0)

    # ["fandom", "com"] -> "fandom.com"
    domain = ".".join(domain)

    return domain in ["fandom.com", "wikia.org"]


def log_msg(message_text, is_error=False):
    """
    The ``log_msg`` function is simply used to log a message in the console
    (expected) using either the ``sys.stdout`` or ``sys.stderr`` text IOs. It
    was intended to behavior much alike to the default ``print`` function but
    with a little more stylistic control.
        :param message_text: A string representing the intended message to print
            to the text IO
        :param is_error: An optional boolean denoting whether the message being
            logged is an error necessitating the use of ``sys.stderr``
        :return: None
    """
    (text_io := (sys.stdout, sys.stderr)[is_error]).write(f"{message_text}\n")
    text_io.flush()


def log_prompt(message_text):
    """
    The ``log_prompt`` function is used to prompt the user for input, strip that
    input of whitespace, and return the value passed by the user to the calling
    function. It can be conceived of as a substitute for the default ``input``
    function that permits a bit more stylistic control.
        :param message_text: A string representing the intended message to print
            to the text IO as the prompt
        :return: The user input value, obtained from ``sys.stdin.readline`` and
            stripped of whitespace
    """
    sys.stdout.write(f"{message_text}: ")
    sys.stdout.flush()
    return sys.stdin.readline().rstrip()


def pretty_print(json_data):
    """
    The ``pretty_print`` function is used simply to "pretty print" JSON response
    data in the console in a readable, understandable manner, similar to the
    "pretty print" functionality available in most browser consoles. This
    particular implementation of such functionality uses the ``json`` module's
    ``dump`` function to print the data, setting the indent to the author's
    preferred two-space indent and keeping keys unsorted and listed in the order
    in which they were generated.
        :param json_data: A JSON object for display in the console. The data is
            rendered unordered with two-space indent
        :return: None
    """
    log_msg(json.dumps(json_data, indent=2, sort_keys=False))


def split_delimited_string_into_list(string, delimiter):
    """
    The ``split_delimited_string_into_list`` function, as its name implies, is
    used to split the string passed in the ``string`` formal parameter into a
    list of data elements. The ``delimiter`` formal parameter indicates the
    delimiter used to separate data elements in the ``string`` parameter.

    After splitting the string into a list at the input delimiter, the function
    makes use of list comprehension to strip whitespace from each item before
    filtering out empty entries and recasting the resultant filter object as a
    list. This list is then returned from the function as the return value.
        :param string: The string containing the data to be split into list
            elements and returned to the caller
        :param delimiter: A string representing the delimiter being used in the
            ``string`` parameter to separate data elements
        :return: A list of elements constituting the data elements formerly
            included in the ``string`` formal parameter
    """
    return list(filter(None, [e.strip(" ") for e in string.split(delimiter)]))

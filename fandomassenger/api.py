"""
The `api` module contains a number of general functions that permit external
scripts to interact and interface with the MediaWiki Action API (typically found
at `api.php`) and/or the Fandom Nirvana/Services API without having to make
`GET` and `POST` requests directly. Likewise, the module's functions all handle
the validation and collation of data from query responses themselves, either
raising exceptions or performing computer member access to return the necessary
values for calling functions.
"""

__version__ = "0.1"
__author__ = "Andrew Eissen"
__all__ = [
    "QueryException",
    "InputException",
    "get_category_members",
    "get_csrf_token",
    "get_login_token",
    "get_rate_limit_interval",
    "get_user_data",
    "has_message_walls",
    "login",
    "parse_wikitext",
    "post_message_wall_thread",
    "post_user_talk_message"
]

import json.decoder
import re
import requests
import time


class QueryException(Exception):
    """
    The ``QueryException`` class is a subclass extending the base ``Exception``
    class that serves as a helper exception indicating that a problem was
    encountered while the raising function was attempting to consume or submit
    data to the MediaWiki or Wikia/Fandom APIs via ``GET`` or ``POST`` request.
    This exception is raised in cases of API failure; successful operations that
    return malformed data on account of faulty input should throw
    ``InputException``.
    """


class InputException(Exception):
    """
    The ``InputException`` class is a subclass extending the base ``Exception``
    class that serves as a helper exception indicating that a problem was
    encountered with the input passed to the raising function for inclusion in
    the ``GET`` or ``POST`` request. This exception is raised in cases in which
    the attempted query succeeded but the data returned is malformed on account
    of faulty input; failed operations that can be attributed to API error
    should throw ``QueryException``.
    """


def get_category_members(categories, interval, api_php, session=None):
    """
    This function is the public-facing method that handles external requests
    for category members. The function collates a master listing of all
    members belonging to the list of categories specified in the
    "categories" formal parameter list. The function makes use of a pair of
    recursive private helper functions that work around maximum return
    limits imposed by the MediaWiki API to ensure all members pages are
    retrieved together. Prior to return, the function removes any duplicate
    entries found in the listing (constituting pages that exist in several
    of the desired categories), and returns the rest as a list of strings.
        :param categories: A list of strings denoting the categories from
            which to retrieve member page titles. A single string for one
            category is also valid, as it will be coerced into a single-element
            list.
        :param interval: The edit interval ensuring operations abide by the
            required rate limit value
        :param api_php: The full URL pointing to the MediaWiki Action API
            `api.php` resource
        :param session: An optional `requests.Session` object. If no session is
            passed, a new `requests.Session` is instantiated for the function.
        :return: Though the use of recursive private helper functions, the
            function returns a master list of category members derived from
            all the categories passed in ``categories``, bereft of
            duplicates and properly sorted in "human readable" form.
    """

    # Coerce string to list if single category name is passed
    if isinstance(categories, str):
        categories = [categories]

    # If something other than list is passed, raise InputException
    if not isinstance(categories, list):
        raise InputException()

    # wgFormattedNamespaces[14]
    prefix = "Category:"

    # Ensure each category string is prefixed with "Category:"
    categories = list(map(lambda c: (c, prefix + c)[c[:len(prefix)] != prefix],
                          categories))

    # Remove duplicate entries via set, then coerce back to list
    members = list(set(_get_category_members_process(interval, 0, categories,
                                                     api_php, session)))

    if len(members):
        # Employ human sort (i.e. "Page 2" before "Page 10", not vice versa)
        regex = r"[+-]?([0-9]+(?:[.][0-9]*)?|[.][0-9]+)"
        members.sort(key=lambda m: [float(c) if c.isdigit() else c.lower()
                                    for c in re.split(regex, m)])

    return members


def _get_category_members(interval, api_php, session=None, config=None,
                          members=None):
    """
    This function is one of the private helper functions employed in the
    category member acquisition process. It is responsible for returning the
    category member pages (articles, templates, other categories, etc.) that
    exist in the given category, the name of which is passed along in the
    ``config`` formal parameter as the value of a key named ``cmtitle``. If
    the maximum number of returned member pages is reached in a given
    ``GET`` request to the ``categorymembers`` endpoint, the function will
    recursively call itself so as to acquire all the pages, eventually
    returning a master list of all members in the parameter category.
        :param interval: The edit interval ensuring operations abide by the
            required rate limit value
        :param api_php: The full URL pointing to the MediaWiki Action API
            `api.php` resource
        :param session: An optional `requests.Session` object. If no session is
            passed, a new `requests.Session` is instantiated for the function.
        :param config: Depending on the circumstances of the invocation,
            this dictionary may contain the name of the desired category as
            the value of a key titled ``cmtitle`` and/or the value of a key
            titled ``cmcontinue`` indicating where querying should pick up
            should the maximum number of member pages be returned in one
            request.
        :param members: A list of previously collated member pages to be
            returned from the function as the return value
        :return: Though multiple recursive calls may be made if there exist
            more pages in a category than can be retrieved in a single
            ``GET`` request, the function will ultimately return a master
            list of all members in the given category.
    """

    # Set defaults for optional parameters
    session = session or requests.Session()
    config = config or {}
    members = members or []

    try:
        # Join config parameter dictionary to params prior to query to pass name
        request = session.get(url=api_php, params={**{
            "action": "query",
            "list": "categorymembers",
            "cmnamespace": "*",
            "cmprop": "title",
            "cmdir": "desc",
            "cmlimit": "max",
            "rawcontinue": True,
            "format": "json",
        }, **config})
        request.raise_for_status()

        data = request.json()
    except (requests.exceptions.HTTPError, json.decoder.JSONDecodeError):
        raise QueryException()

    # Successful query with errors mediated by means of faulty input
    if "errors" in data:
        raise InputException()

    try:
        # Add page title to master members list
        for member in data["query"]["categorymembers"]:
            members.append(member["title"])

        # If there are more members than can be retrieved in one call...
        if "query-continue" in data:

            # Sleep to avoid rate limiting...
            time.sleep(interval)

            # ...and recursively call self until all pages are acquired
            _get_category_members(interval, api_php, session, {**config, **{
                "cmcontinue":
                    data["query-continue"]["categorymembers"]["cmcontinue"]
            }}, members)
    except KeyError:
        # Missing success-condition key/value pairs indicate input was faulty
        raise InputException()

    return members


def _get_category_members_process(interval, counter, categories, api_php,
                                  session=None, members=None):
    """
    This function is a private helper function employed in the category
    member acquisition process to coordinate the retrieval of all category
    members from all input categories and the collation of a complete list
    for returning from the function. The function will recursively call
    itself if there are multiple categories from which member pages are to
    be extracted, only returning a complete list once all categories have
    been handled.
        :param interval: The edit interval ensuring operations abide by the
            required rate limit value
        :param counter: Counter to keep track of number of recursive calls
            needed to process requested categories
        :param categories: A list of categories from which to extract all
            member pages
        :param api_php: The full URL pointing to the MediaWiki Action API
            `api.php` resource
        :param session: An optional `requests.Session` object. If no session is
            passed, a new `requests.Session` is instantiated for the function.
        :param members: A list of previously collated member pages to be
            returned from the function as the return value
        :return: The function ultimately returns a master list of all member
            pages belong to all the categories included in the
            ``categories`` formal parameter list. This list may be acquired
            over the course of multiple recursive calls.
    """

    if isinstance(members, type(None)):
        members = []

    # Recursive end condition, return master list once all cats queried
    if counter == len(categories):
        return members

    session = session or requests.Session()

    # Attempt to acquire member pages of given category
    pages = _get_category_members(interval, api_php, session, {
        "cmtitle": categories[counter]
    })
    counter = counter + 1

    # Add retrieved member pages to master list if applicable
    if len(pages):
        members = members + pages

    # Recursively call self while there remain categories to query
    return _get_category_members_process(interval, counter, categories, api_php,
                                         session, members)


def get_csrf_token(api_php, session=None):
    """
    This formerly private function is responsible for acquiring a Cross-Site
    Request Forgery (CSRF) token from the "``tokens``" MediaWiki API
    endpoint as one of the required parameters for all ``POST`` requests
    made by the application. In JavaScript, this token may be acquired
    simply from ``mw.user.tokens.get("editToken")``, but a separate query
    must be made by off-site applications like this one for the purposes of
    token acquisition.
        :param api_php: The full URL pointing to the MediaWiki Action API
            `api.php` resource
        :param session: An optional `requests.Session` object. If no session is
            passed, a new `requests.Session` is instantiated for the function.
        :return: A string login token retrieved from the API for use in the
            class's ``POST``ing methods if successful.
    """
    try:
        request = (session or requests.Session()).get(url=api_php, params={
            "action": "query",
            "meta": "tokens",
            "format": "json"
        })
        request.raise_for_status()

        data = request.json()
    except (requests.exceptions.HTTPError, json.decoder.JSONDecodeError):
        raise QueryException()

    try:
        token = data["query"]["tokens"]["csrftoken"]
    except KeyError:
        # Missing success-condition key/value pairs indicate input was faulty
        raise InputException()

    # Successful query with errors mediated by means of faulty input
    if "errors" in data:
        raise InputException()

    return token


def get_login_token(api_php, session=None):
    """
    This formerly private function is used to retrieve a login token from the
    MediaWiki API for use in external, offsite editing/querying. It is used
    in the initial login process by the ``login`` method in conjunction with
    a bot username and password to authenticate the application.
        :param api_php: The full URL pointing to the MediaWiki Action API
            `api.php` resource
        :param session: An optional `requests.Session` object. If no session is
            passed, a new `requests.Session` is instantiated for the function.
        :return: A string login token retrieved from the API for use in the
            ``login`` method if successful.
    """

    try:
        request = (session or requests.Session()).get(url=api_php, params={
            "action": "query",
            "meta": "tokens",
            "type": "login",
            "format": "json"
        })
        request.raise_for_status()

        data = request.json()
    except (requests.exceptions.HTTPError, json.decoder.JSONDecodeError):
        raise QueryException()

    try:
        token = data["query"]["tokens"]["logintoken"]
    except KeyError:
        # Missing success-condition key/value pairs indicate input was faulty
        raise InputException()

    # Successful query with errors mediated by means of faulty input
    if "errors" in data:
        raise InputException()

    return token


def get_rate_limit_interval(api_php, session=None):
    """
    This function is responsible for calculating an appropriate edit
    interval that respects the rate limit imposed on the logged-in user. For
    bots and accounts with the bot flag, the limit is 80 edits/minute. For
    standard user accounts, the limit is 40 edits/minute. When calculated,
    these give rise to the edit intervals of .75 seconds and 1.5 seconds,
    respectively.
        :param api_php: The full URL pointing to the MediaWiki Action API
            `api.php` resource
        :param session: An optional `requests.Session` object. If no session is
            passed, a new `requests.Session` is instantiated for the function.
        :return: An appropriate rate limit edit interval is returned, as
            calculated from the values passed by the MediaWiki API request
    """

    try:
        request = (session or requests.Session()).get(url=api_php, params={
            "action": "query",
            "meta": "userinfo",
            "uiprop": "ratelimits",
            "format": "json"
        })
        request.raise_for_status()

        data = request.json()
    except(requests.exceptions.HTTPError, json.decoder.JSONDecodeError):
        raise QueryException()

    # Successful query with errors mediated by means of faulty input
    if "errors" in data:
        raise InputException()

    try:
        limits = data["query"]["userinfo"]["ratelimits"]["edit"]["user"]
        interval = limits["seconds"] / limits["hits"]
    except KeyError:
        # Missing success-condition key/value pairs indicate input was faulty
        raise InputException()

    return interval


def get_user_data(usernames, api_php, retrieve_groups=False, session=None):
    """
    The ``get_user_data`` function is used both to retrieve information about
    a list of users input in the ``usernames`` formal parameter and to
    simultaneously validate those usernames. Input usernames which do not abide
    by MediaWiki's internal naming conventions are omitted from the returned
    ``user_objects`` list. If the return list is empty, an ``InputException`` is
    raised rather than an empty list returned.

    Assuming some input was well-formed and provided usernames pointed to extant
    accounts, the returned ``user_objects`` list contains a number of member
    dictionaries that each have a ``name`` attribute containing a string
    representing the username and a ``userid`` containing an int constituting
    the user's internal account id, in addition to other information if needed.
        :param usernames: A list of strings denoting the usernames to be queried
            by the function. A single string for one name is also valid, as it
            will be coerced into a single-element list.
        :param api_php: The full URL pointing to the MediaWiki Action API
            `api.php` resource
        :param retrieve_groups: An optional boolean indicating whether the
            function should require information pertaining to the user's user
            rights groups in the request. ``False`` by default.
        :param session: An optional `requests.Session` object. If no session is
            passed, a new `requests.Session` is instantiated for the function.
        :return user_objects: A list of dictionaries with at least two key/value
            pairs in each, namely, a ``name`` attribute containing a string
            representing the username and a ``userid`` containing an int
            constituting the user's internal account id.
    """

    # Coerce string to list if single username name is passed
    if isinstance(usernames, str):
        usernames = [usernames]

    # If something other than list is passed, raise InputException
    if not isinstance(usernames, list):
        raise InputException()

    user_objects = []
    params = {
        "action": "query",
        "list": "users",
        "ususers": "|".join(usernames),
        "format": "json"
    }

    if retrieve_groups:
        params["usprop"] = "groups"

    try:
        request = (session or requests.Session()).get(url=api_php,
                                                      params=params)
        request.raise_for_status()
        data = request.json()
    except (requests.exceptions.HTTPError, json.decoder.JSONDecodeError):
        raise QueryException()

    try:
        users = data["query"]["users"]
    except KeyError:
        # Missing success-condition key/value pairs indicate input was faulty
        raise InputException()

    # Successful query with errors mediated by means of faulty input
    if "errors" in data or not len(users):
        raise InputException()

    for user in users:
        if "userid" in user and "missing" not in user:
            # Format: user = {name: "Eizen", userid: 123456}
            user_objects.append(user)

    # Returning empty list is pointless; indicate no valid user data was found
    if not len(user_objects):
        raise InputException()

    return user_objects


def has_message_walls(wikia_php, session=None):
    """
    The ``has_message_walls`` function is used to determine whether the
    specified wiki to which the ``wikia_php`` formal parameter belongs has the
    Wikia/Fandom Message Wall extension installed in lieu of vanilla MediaWiki
    user talk pages. As this extension is not built on the standard MediaWiki
    engine, a different mass-messaging approach will need to be used for wikis
    using the extension, so the return boolean indicating Message Wall status is
    essential to the core operations of the application.
        :param wikia_php: The full URL pointing to the Wikia/Fandom
            Nirvana/Services `wikia.php` resource
        :param session: An optional `requests.Session` object. If no session is
            passed, a new `requests.Session` is instantiated for the function.
        :return: A boolean denoting whether the specified wiki to which the
            ``wikia_php`` resource belongs has the Wikia/Fandom Message Wall
            extension installed in lieu of standard MediaWiki user talk pages.
    """
    try:
        request = (session or requests.Session()).get(url=wikia_php, params={
            "controller": "UserProfile",
            "method": "getUserData",
            "userId": 4403388,
            "format": "json",
        })
        request.raise_for_status()

        data = request.json()
    except (requests.exceptions.HTTPError, json.decoder.JSONDecodeError):
        raise QueryException()

    # Successful query with errors mediated by means of faulty input
    if "errors" in data:
        raise InputException()

    try:
        return "userData" in data and "messageWallUrl" in data["userData"]
    except KeyError:
        # Missing success-condition key/value pairs indicate input was faulty
        raise InputException()


def login(username, password, api_php, session=None):
    """
    The ``login`` function, as the name implies, is used as the primary means by
    which the user logs into the wiki to which the ``api_php`` formal parameter
    belongs. This function will not return a ``True`` status boolean if the user
    attempts to pass his own user account password as the value of the formal
    parameter of the same name; a bot password retrieved from the wiki's
    ``Special:BotPasswords`` generator will need to be used for login attempts
    to succeed.
        :param username: A string representing the username of the user
            employing the application
        :param password: The bot password of the user employing the application,
            obtained from the wiki's ``Special:BotPasswords`` generator
        :param api_php: The full URL pointing to the MediaWiki Action API
            `api.php` resource
        :param session: An optional `requests.Session` object. If no session is
            passed, a new `requests.Session` is instantiated for the function.
        :return: A status boolean indicating whether the login attempt was
            successful is returned as the return value
    """
    session = session or requests.Session()

    try:
        request = session.post(api_php, data={
            "action": "login",
            "lgname": username,
            "lgpassword": password,
            "lgtoken": get_login_token(api_php, session),
            "format": "json"
        })
        request.raise_for_status()

        data = request.json()
    except (requests.exceptions.HTTPError, json.decoder.JSONDecodeError):
        raise QueryException()

    # Successful query with errors mediated by means of faulty input
    if "errors" in data:
        raise InputException()

    try:
        is_successful = data["login"]["result"] == "Success"
        is_right_user = data["login"]["lgusername"] == username
    except KeyError:
        # Missing success-condition key/value pairs indicate input was faulty
        raise InputException()

    # Successful login only occurs if the request succeeds and username matches
    return is_successful and is_right_user


def parse_wikitext(wikitext, api_php, session=None):
    """
    As the name implies, the ``parse_wikitext`` function is used to translate
    the string-based wikitext markup passed in the ``wikitext`` formal parameter
    to wellformed string HTML using the default MediaWiki parser engine found at
    the ``action=parse`` endpoint. This HTML may then be used in other functions
    that require HTML in lieu of wikitext, such as those that engage with the
    Wikia/Fandom Nirvana/Services API.
        :param wikitext: A string containing the wikitext to be parsed by the
            function into a wellformed HTML string
        :param api_php: The full URL pointing to the MediaWiki Action API
            `api.php` resource
        :param session: An optional `requests.Session` object. If no session is
            passed, a new `requests.Session` is instantiated for the function.
        :return: A string containing wellformed HTML generated by the default
            MediaWiki parser is returned from the function
    """
    try:
        request = (session or requests.Session()).get(url=api_php, params={
            "action": "parse",
            "disablelimitreport": True,
            "prop": "text",
            "wrapoutputclass": None,
            "text": wikitext,
            "contentmodel": "wikitext",
            "format": "json",
        })
        request.raise_for_status()

        data = request.json()
    except (requests.exceptions.HTTPError, json.decoder.JSONDecodeError):
        raise QueryException()

    # Successful query with errors mediated by means of faulty input
    if "errors" in data:
        raise InputException()

    try:
        return data["parse"]["text"]["*"]
    except KeyError:
        # Missing success-condition key/value pairs indicate input was faulty
        raise InputException()


def post_message_wall_thread(userid, title, json_model, wikia_php, api_php,
                             session=None):
    """
    Perhaps the most troublesome function of the ``api`` module, the
    ``post_message_wall_thread`` function is used to post new Message Wall
    threads to the wall of the intended recipient denoted by the ``userid``
    formal parameter. As the ``wikia.php`` Nirvana/Services API run by
    Wikia/Fandom operates differently than the MediaWiki Action API, different
    input is required than is generally required for MW ``POST`` requests. The
    most notable difference is the required inclusion of message text in the
    form of a ``jsonModel``, a type of structured JSON object for use in
    representing HTML data that was developed for the ProseMirror rich text
    editor (upon which the author suspects the on-wiki Message Wall editor is
    built).

    Despite being properly formulated as a posting method, the function is
    presently unable to post new Message Wall threads on account of outstanding
    CORS issues that forbid external, off-site applications from ``POST``ing
    data to the ``wikia.php`` API. The API can be accessed via JavaScript code
    run in the browser console once logged in to the wiki, but the requisite
    ``access-control-allow-origin`` header is absent for external, off-wiki
    applications that employ the same code. 403 Client Error status codes are
    returned in all such cases.

    The author was formerly under the impression that the Wikia/Fandom
    Services API could be accessed by authenticated applications logged in via
    bot passwords generated by ``Special:BotPasswords``, but this is not the
    case. The author has since reached out to Fandom Staff in support ticket
    #1072954 to see if the permissions of bot passwords can be augmented to
    include access to the ``wikia.php`` API, but will likely explore the
    possibility of using a CORS proxy as an alternative means of adding the
    required ``access-control-allow-origin`` header.
        :param userid: The ``userid`` attribute retrieved from ``list=users``
            MediaWiki queries representing the internal id of the intended
            message thread recipient
        :param title: The plaintext string representation of the intended title
            of the message
        :param json_model: A stringified JSON object representing the content
            of the message in ProseMirror syntax-compliant jsonModel form
        :param wikia_php: The full URL pointing to the Wikia/Fandom
            Nirvana/Services `wikia.php` resource
        :param api_php: The full URL pointing to the MediaWiki Action API
            `api.php` resource
        :param session: An optional `requests.Session` object. If no session is
            passed, a new `requests.Session` is instantiated for the function.
        :return: A status boolean indicating whether the message thread was
            successfully posted to the user's Message Wall
    """
    try:
        new_wikia_php = requests.models.PreparedRequest()
        new_wikia_php.prepare_url(wikia_php, {
            "controller": "Fandom\\MessageWall\\MessageWall",
            "method": "createThread",
            "format": "json",
        })

        request = (session or requests.Session()).post(new_wikia_php.url, data={
            "title": title,
            "wallOwnerId": userid,
            "token": get_csrf_token(api_php, session),
            # "rawcontent": "",
            "jsonModel": json_model,
            "attachments":
                "{\"contentImages\":[],\"openGraphs\":[],\"atMentions\":[]}"
        })
        request.raise_for_status()

        data = request.json()
    except (requests.exceptions.HTTPError, json.decoder.JSONDecodeError):
        raise QueryException()

    try:
        # No clean way to determine if operation was successful
        return "id" in data and int(data["createdBy"]["id"]) == userid
    except (KeyError, ValueError):
        # Missing success-condition key/value pairs indicate input was faulty
        raise InputException()


def post_user_talk_message(page, title, body, api_php, session=None):
    """
    The more manageable analogue of ``post_message_wall_thread``, the
    ``post_user_talk_message`` function is the primary message-posting handler
    of wikis that do not have the Wikia/Fandom Message Wall extension installed
    and which use MediaWiki's default user talk pages. The function is capable
    of posting raw wikitext markup as the content of the intended message
    without the need to first parse it as HTML and then render it in
    representational form as a jsonModel.
        :param page: The name of the page to which the message will be appended;
            should be formulated as "User talk:Eizen" or some such
        :param title: The plaintext string representation of the intended title
            of the message
        :param body: The intended content of the message represented in standard
            wikitext markup form
        :param api_php: The full URL pointing to the MediaWiki Action API
            `api.php` resource
        :param session: An optional `requests.Session` object. If no session is
            passed, a new `requests.Session` is instantiated for the function.
        :return: A status boolean indicating whether the user talk section was
            successfully posted to the user's user talk page as a message
    """

    try:
        request = (session or requests.Session()).post(api_php, data={
            "action": "edit",
            "section": "new",
            "format": "json",
            "sectiontitle": title,
            "token": get_csrf_token(api_php, session),
            "text": body,
            "title": page
        })
        request.raise_for_status()

        data = request.json()
    except (requests.exceptions.HTTPError, json.decoder.JSONDecodeError):
        raise QueryException()

    # Successful query with errors mediated by means of faulty input
    if "errors" in data:
        raise InputException()

    try:
        return data["edit"]["result"] == "Success"
    except KeyError:
        # Missing success-condition key/value pairs indicate input was faulty
        raise InputException()

"""
The ``main`` module contains the central coordinating functions that are
responsible for undertaking the main application logic of the Fandomassenger
application and overseeing the performing of all the attendant operations.
"""

__all__ = []
__author__ = "Andrew Eissen"
__version__ = "0.1"

import api
import requests
import time
import util


def main():
    """
    The ``main`` function serves as the central node of the application,
    responsible for accepting and validating user input used for the purposes of
    undertaking the mass-messaging operations and undertaking those operations
    for all valid intended recipients. The outcome is an interactive,
    console-based interface that prompts the user for all requisite information
    and validates on the fly.
        :return: None
    """

    # Grab i18n file for console message text
    try:
        i18n_file = util.get_json_file("../data/i18n.json")
    except FileNotFoundError:
        return

    try:
        i18n = i18n_file[util.determine_system_language()]
    except KeyError:
        # If requested language doesn't exist in i18n, default to English
        i18n = i18n_file["en"]

    # Default definitions
    is_logged_in = False
    wiki = {}
    session = requests.Session()

    # Print welcome message
    util.log_msg(i18n["consoleWelcome"])

    # Login loop; runs until successful login
    while not is_logged_in:

        # Continue to prompt while input URL is malformed
        while not len(wiki):
            util.log_msg(i18n["consoleWikiLocation"])
            util.log_msg(i18n["consoleWikiLocationExample"])

            input_url = input(i18n["consoleWikiLocationPrompt"])

            # Check if fandom.com or wikia.org is base URL, loop again if not
            if not util.is_fandom_wiki_base_url(input_url):
                util.log_msg(i18n["errorWikiLocation"], True)
                continue

            # Store URLs for querying purposes
            wiki = {
                "base_url": input_url,
                "api_php": input_url + "/api.php",
                "wikia_php": input_url + "/wikia.php"
            }

        # Sign in using bot password
        util.log_msg(i18n["consoleSignin"])

        # Acquire potential credentials
        username = input(i18n["consoleSigninUsernamePrompt"])
        password = input(i18n["consoleSigninPasswordPrompt"])

        try:
            # Test credentials using login method
            is_logged_in = api.login(username, password, wiki["api_php"],
                                     session)

        # Catch queries made to nonexistent wikis
        except api.QueryException:
            util.log_msg(i18n["errorNonexistentWiki"], True)
            continue

        # Catch improper credentials used to login
        except api.InputException:
            util.log_msg(i18n["errorLogin"], True)
            continue

        # Prompt reentry of credentials if still not logged in
        if not is_logged_in:
            util.log_msg(i18n["errorLogin"], True)
            continue

        # Check user groups to ensure only privileged users can mass-message
        try:
            # Get name, userid, and groups properties
            data = api.get_user_data(username, wiki["api_php"], session)

            # Groups in which the user exists
            my_usergroups = data[0]["groups"]

            # On Fandom wikis, admins & Discussion moderators can moderate posts
            required_usergroups = ["threadmoderator", "sysop"]

            # Hard exit if user is not in the right group to prevent spamming
            if not util.has_rights(my_usergroups, required_usergroups):
                util.log_msg(i18n["errorInsufficientPermissions"], True)
                return

        # Catch API errors and input errors generated server-side
        except (api.QueryException, api.InputException, KeyError):
            util.log_msg(i18n["errorAPI"], True)
            continue

    # Acquire edit interval that prevents POST request rate limiting
    try:
        interval = api.get_rate_limit_interval(wiki["api_php"], session)

    # Set one and half second default if error is encountered
    except (api.QueryException, api.InputException):
        util.log_msg(i18n["errorEditInterval"], True)
        interval = 1.5

    # Main functionality loop; runs to user exit
    while True:

        # Initial definitions
        selected_index = None
        indices = []
        members = []
        input_entries = []

        # Create de facto menu with indices derived from enumerate
        util.log_msg(i18n["consoleType"])
        for index, option in enumerate([
            i18n["consoleTypeCategories"],
            i18n["consoleTypeLoose"],
            i18n["consoleTypeExit"]
        ]):
            indices.append(index + 1)
            util.log_msg(f"{index + 1}: {option}")

        # Ensure users cannot enter indices not provided as menu options
        while selected_index not in indices:
            try:
                selected_index = int(input(i18n["consoleTypePrompt"]))

            # Ensure plaintext cannot be entered, ony menu option indices
            except ValueError:
                util.log_msg(i18n["errorTypeInvalid"], True)
                continue

            # Ensure plaintext cannot be entered, ony menu option indices
            if selected_index not in indices:
                util.log_msg(i18n["errorTypeInvalid"], True)
                continue

        # Exit out of loop and function
        if selected_index == 3:
            util.log_msg(i18n["consoleExit"])
            break

        # Acquire recipient or category list, separated by comma delimiters
        util.log_msg(i18n["consoleEntries"])
        while not len(input_entries):
            input_entries = input(i18n["consoleEntriesPrompt"])
            input_entries = util.split_delimited_string_into_list(input_entries,
                                                                  ",")

        # If the user wants to edit members of a user category...
        if is_categories := (selected_index == 1):
            try:
                members = api.get_category_members(input_entries, interval,
                                                   wiki["api_php"], session)
            except api.QueryException:
                util.log_msg(i18n["errorAPI"], True)

            # Only thrown if there are no members in the given category
            except api.InputException:
                util.log_msg(i18n["errorNoCategoryMembers"], True)

            # Reprompt if the given categories are empty
            if not len(members):
                util.log_msg(i18n["errorNoCategoryMembers"], True)
                continue

        try:
            # Evaluate either category members or loose input usernames
            users = members if is_categories else input_entries
            user_dicts = api.get_user_data(users, wiki["api_php"], False,
                                           session)
        except api.QueryException:
            util.log_msg(i18n["errorAPI"], True)
            time.sleep(interval)
            continue

        # Reset if no valid usernames are retrieved from relevant query
        except api.InputException:
            util.log_msg(i18n["errorNoValidUsernames"], True)
            time.sleep(interval)
            continue

        util.log_msg(i18n["consoleMessage"])
        while True:
            message_title = input(i18n["consoleMessageTitlePrompt"])

            # Unlike message body, message title is required in all cases
            if not len(message_title):
                util.log_msg("errorMessageTitleMissing", True)
            else:
                break

        message_body = input(i18n["consoleMessageBodyPrompt"])

        # Determine if wiki has Message Wall extension installed locally
        # As the MW extension is not built on MW, two-phase parsing is needed
        if has_walls := api.has_message_walls(wiki["wikia_php"], session):

            # First, convert input wikitext to well-formed HTML string
            parsed_message_body = api.parse_wikitext(message_body,
                                                     wiki["api_php"], session)

            # Instantiate HTML parser to convert HTML to ProseMirror jsonModel
            (parser := util.JsonModelHTMLParser()).feed(parsed_message_body)

            # Convert JSON jsonModel to string for inclusion as query parameter
            json_model = parser.get_json_model_as_string()

            # Set custom query function and default params prior to invocation
            func = api.post_message_wall_thread
            params = [message_title, json_model, wiki["wikia_php"],
                      wiki["api_php"], session]

        # Normal MediaWiki-standard user talk pages are much simpler
        else:
            # Talk page handler accepts wikitext, so no need for 2-phase parsing
            func = api.post_user_talk_message
            params = [message_title, message_body, wiki["api_php"], session]

        for index, user_dict in enumerate(user_dicts):
            try:
                # Set loop iteration-specific param immediately prior to call
                first_param = (f'User talk:{user_dict["name"]}',
                               user_dict["userid"])[has_walls]
                if index == 0:
                    params.insert(index, first_param)
                else:
                    params[0] = first_param

                # Print differing messages depending on status and include name
                util.log_msg(
                    i18n[
                        ("errorMessageStd", "successMessage")[func(*params)]
                    ].replace("$1", user_dict["name"]), True)

            except (api.QueryException, api.InputException):
                util.log_msg(
                    i18n["errorMessageAPI"].replace("$1", user_dict["name"]),
                    True)

            # Sleep for set edit interval to ensure rate limiting is prevented
            finally:
                time.sleep(interval)

        util.log_msg(i18n["successComplete"])
        time.sleep(interval)


if __name__ == "__main__":
    main()

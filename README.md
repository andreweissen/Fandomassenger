## Fandomassenger ##

__Fandomassenger__, a [portmanteau](https://en.wikipedia.org/wiki/Portmanteau) of "__Fandom Mass Messenger__," is a command-line application/script written in [Python 3](https://en.wikipedia.org/wiki/History_of_Python#Version_3) for use in mass-messaging groups of users on [Fandom](https://en.wikipedia.org/wiki/Fandom_(website)) [MediaWiki](https://en.wikipedia.org/wiki/MediaWiki) [wikis](https://en.wikipedia.org/wiki/Wiki).

It was developed in response to the fact that per an archived discussion previously held [here](https://dev.fandom.com/wiki/MediaWiki_talk:MassMessage.js), Wikia/Fandom Staff no longer look favorably upon [Dev wiki](https://dev.fandom.com/wiki/Fandom_Developers_Wiki) [JavaScript userscripts](https://dev.fandom.com/wiki/List_of_JavaScript_enhancements) that provide mass-messaging functionality, despite the [ongoing need for such automated functionality](https://dev.fandom.com/wiki/Special:Diff/153216) and the prior approval of longstanding scripts like [MassEdit](https://dev.fandom.com/wiki/MassEdit) and [Message](https://dev.fandom.com/wiki/Message) that have historically provided such functionality.

### Outstanding issues ###
* The application is presently unable to post new threads to Message Walls on wikis that employ that extension on account of an unresolved [CORS](https://en.wikipedia.org/wiki/Cross-origin_resource_sharing) issue. The author was previously under the impression that authenticated external applications logged in via a [bot password](https://www.mediawiki.org/wiki/Manual:Bot_passwords) generated by the designated wiki's `Special:BotPasswords` page were able to `POST` to the `wikia.php` API, given that such actions are possible using JavaScript in the browser console.
* The author has since reached out to Fandom Staff in support ticket #1072954 to see if the standard `Special:BotPasswords` permissions can be augmented and extended to include external access to the Nirvana/Services API. If no such Fandom-supported option is possible, the author will explore the possibility of CORS proxies as a means of circumventing the aforementioned CORS issue.
* Update 11 August 2021: Per support ticket #1072954, Fandom engineers are exploring the possibility of expanding the default `Special:BotPasswords` permissions to include external access to the `wikia.php` resource for authorized applications like Fandomassenger.

### To-do ###
* At present, the application can only be run via interaction with the dynamic console interface rather than via the command line directly. A command-line input-based alternative approach will be developed to allow fast interaction with the application via the inclusion of command-line arguments.
* Additionally, in addition to a command line-driven approach, the author will also permit the inclusion of a `settings.ini` file for the configuration of certain universal properties like bot password and username.  
* The included `setup.py` file may not properly invoke the `setuptools.setup` function. Further research into the function's required formal parameters may be required in future, with particular emphasis on the `entry_points` parameter dictionary.
* A complete test suite for the `api.py` and `util.py` modules is needed to ensure all operations operate as intended in a variety of well-formed and malformed cases.
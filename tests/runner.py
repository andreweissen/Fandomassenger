"""
The ``runner.py`` module serves to coordinate the various test cases associated
with each of the helper modules employed in the Fandomassenger application to
undertake the various operations that together constitute the complete program.
The runner file is a central coordinating module that takes the form of a
``TestSuite`` of the ``unittest`` module.
"""

__author__ = "Andrew Eissen"
__version__ = "0.1"

import unittest
import test_util


def suite():
    """
    The ``suite`` function serves as the central coordinating function of the
    ``runner`` module, adding each of the test modules in the ``/tests`` folder
    to the new ``unittest.TestSuite`` instance that is subsequently returned
    from the function for running by ``unittest.TextTestRunner``.
        :return test_suite: A new ``unittest.TestSuite`` object created by the
            function is returned
    """
    loader = unittest.TestLoader()
    test_suite = unittest.TestSuite()

    test_suite.addTests(loader.loadTestsFromModule(test_util))
    return test_suite


if __name__ == "__main__":
    unittest.TextTestRunner(verbosity=3).run(suite())

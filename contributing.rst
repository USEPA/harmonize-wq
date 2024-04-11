.. _contributing:

Contributing to harmonize_wq
============================

We’re so glad you’re thinking about contributing to an EPA open source project!
If you’re unsure about anything, just ask — or submit your issue or pull request anyway.
The worst that can happen is we’ll politely ask you to change something. We appreciate all friendly contributions.

We encourage you to read this project’s CONTRIBUTING policy (you are here), its
`LICENSE <https://github.com/USEPA/harmonize-wq/blob/81b172afc3b72bec0a9f5624bade59eb2527510f/LICENSE>`_,
and its `README <https://github.com/USEPA/harmonize-wq/blob/main/README.md>`_.

All contributions to this project will be released under the MIT dedication.
By submitting a pull request or issue, you are agreeing to comply with this waiver of copyright interest.

harmonize_wq uses:

- `GitHub <https://github.com/USEPA/harmonize-wq>`_ to host the code.
- `GitHub actions <https://docs.github.com/en/actions>`_ to test all commits and PRs.
- `pytest <https://docs.pytest.org/en/stable/>`_ to write tests.
- `sphinx <https://www.sphinx-doc.org/en/master/>`_ to write docs.

You can contribute in different ways:

Report issues
-------------

You can report any issues with the package or the documentation to the `issue tracker`_.
Also feel free to submit feature requests, comments, or questions.


Contribute code
---------------

To contribute fixes, code, tests, or documentation, fork harmonize_wq in GitHub_
and submit the changes using a pull request against the **main** branch.

- If you are submitting new code, add tests (see below) and documentation.
- Write "Closes #<bug number>" in the PR description or a comment, as described in the `GitHub docs`_.
- Check tests and resolve any issues.

In any case, feel free to use the `issue tracker`_ to discuss ideas for new features or improvements.

Notice that we will not merge a PR if tests are failing.
In certain cases tests pass in your machine but not in GitHub actions.
There might be multiple reasons for this but these are some of the most common:

- Your new code does not work for other operating systems or Python versions.
- The documentation is not being built properly or the examples in the docs are not working.

Development environment setup
-----------------------------

- pip install the latest development version of the package from `GitHub <https://github.com/USEPA/harmonize-wq>`_
- Install the requirements for the development environment by pip installing the additional requirements-dev.txt file.

docs are built using sphinx
tests are run using pytest

There are workflows using GitHub actions for both docs and tests to help avoid 'it worked on my machine' type development issues.

.. _`issue tracker`: https://github.com/USEPA/harmonize-wq/issues
.. _`GitHub docs`: https://help.github.com/articles/closing-issues-via-commit-messages/

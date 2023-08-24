.. _contributing:

Contributing to harmonize_wq
============================

We’re so glad you’re thinking about contributing to an EPA open source project! If you’re unsure about anything, just ask — or submit your issue or pull request anyway. The worst that can happen is we’ll politely ask you to change something. We appreciate all friendly contributions.

We encourage you to read this project’s CONTRIBUTING policy (you are here), its
LICENSE, and its `README <https://github.com/USEPA/harmonize-wq/blob/main/README.md>`_.

All contributions to this project will be released under the MIT dedication. By submitting a pull request or issue, you are agreeing to comply with this waiver of copyright interest.

harmonize_wq uses:

- `github <https://github.com/USEPA/harmonize-wq>`_ to host the code.
- `github actions <https://docs.github.com/en/actions>`_ to test all commits and PRs.
- `pytest <https://docs.pytest.org/en/stable/>`_ to write tests.
- `sphinx <https://www.sphinx-doc.org/en/master/>`_ to write docs.

You can contribute in different ways:

Report issues
-------------

You can report any issues with the package, the documentation to the `issue tracker`_.
Also feel free to submit feature requests, comments or questions.


Contribute code
---------------

To contribute fixes, code or documentation, fork harmonize_wq in github_ and submit
the changes using a pull request against the **main** branch.

- If you are submitting new code, add tests (see below) and documentation.
- Write "Closes #<bug number>" in the PR description or a comment, as described in the
  `github docs`_.
- Check tests and resolve any issues.

In any case, feel free to use the `issue tracker`_ to discuss ideas for new features or improvements.

Notice that we will not merge a PR if tests are failing. In certain cases tests pass in your
machine but not in github actions. There might be multiple reasons for this but these are some of
the most common

- Your new code does not work for other operating systems or Python versions.
- The documentation is not being built properly or the examples in the docs are
  not working.


.. _`issue tracker`: https://github.com/USEPA/harmonize-wq/issues
.. _`github docs`: https://help.github.com/articles/closing-issues-via-commit-messages/
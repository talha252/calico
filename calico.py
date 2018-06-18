# Copyright (C) 2016-2018 H. Turgut Uyar <uyar@itu.edu.tr>
#
# Calico is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Calico is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Calico.  If not, see <http://www.gnu.org/licenses/>.

"""Calico is a utility for checking command-line programs.

For documentation, please refer to: https://calico.readthedocs.io/
"""

import logging
import os
import shutil
import sys
from argparse import ArgumentParser
from collections import OrderedDict
from enum import Enum

import pexpect
from ruamel import yaml
from ruamel.yaml import comments


# sigalias: SpecNode = comments.CommentedMap


MAX_LEN = 40
SUPPORTS_JAIL = shutil.which("fakechroot") is not None

_logger = logging.getLogger(__name__)


class ActionType(Enum):
    """Type of an action."""

    EXPECT = ("e", "expect")
    SEND = ("s", "send")


class Suite(OrderedDict):
    """A suite containing multiple, ordered test cases."""

    def __init__(self, spec):
        """Initialize this test suite from a given specification.

        :sig: (str) -> None
        :param spec: Specification to parse.
        """
        super().__init__()

        self.points = 0  # sig: int
        """Total points in this test suite."""

        self.parse(spec)

    def parse(self, source):
        """Parse a test specification.

        :sig: (str) -> None
        :param source: Specification to parse.
        :raise AssertionError: When given spec is invalid.
        """
        try:
            config = yaml.round_trip_load(source)
        except yaml.YAMLError as e:
            raise AssertionError(str(e))

        if config is None:
            raise AssertionError("No configuration")

        if not isinstance(config, comments.CommentedSeq):
            raise AssertionError("Invalid configuration")

        action_types = {i: m for m in ActionType for i in m.value}

        tests = [(k, v) for c in config for k, v in c.items()]
        for name, test in tests:
            run = test.get("run")
            assert run is not None, f"{name}: no run command"
            assert isinstance(run, str), f"{name}: run command must be a string"

            kwargs = {}

            ret = test.get("return")
            if ret is not None:
                assert isinstance(ret, int), f"{name}: return value must be integer"
                kwargs["returns"] = ret

            timeout = get_comment_value(test, name="run", field="timeout")
            if timeout is not None:
                assert timeout.isdigit(), f"{name}: timeout value must be integer"
                kwargs["timeout"] = int(timeout)

            points = test.get("points")
            if points is not None:
                assert isinstance(points, int), f"{name}: points value must be integer"
                kwargs["points"] = points

            blocker = test.get("blocker")
            if blocker is not None:
                assert isinstance(
                    blocker, bool
                ), f"{name}: blocker must be true or false"
                kwargs["blocker"] = blocker

            vis = test.get("visible")
            if vis is not None:
                assert isinstance(vis, bool), f"{name}: visible must be true or false"
                kwargs["visible"] = vis

            case = TestCase(name, command=run, **kwargs)

            script = test.get("script")
            if script is None:
                # If there's no script, just expect EOF.
                action = Action(ActionType.EXPECT, "_EOF_")
                case.add_action(action)
            else:
                for step in script:
                    action_type, data = [(k, v) for k, v in step.items()][0]
                    assert action_type in action_types, f"{name}: unknown action type"
                    assert isinstance(data, str), f"{name}: action data must be string"

                    kwargs = {}

                    timeout = get_comment_value(step, name=action_type, field="timeout")
                    if timeout is not None:
                        assert (
                            timeout.isdigit()
                        ), f"{name}: timeout value must be integer"
                        kwargs["timeout"] = int(timeout)

                    action = Action(action_types[action_type], data, **kwargs)
                    case.add_action(action)

            self.add_case(case)

    def add_case(self, case):
        """Add a test case to this suite.

        :sig: (TestCase) -> None
        :param case: Test case to add.
        """
        super().__setitem__(case.name, case)
        self.points += case.points

    def run(self, *, quiet=False):
        """Run this test suite.

        :sig: (Optional[bool]) -> Mapping[str, Any]
        :param quiet: Whether to suppress progress messages.
        :return: A report containing the results.
        """
        report = OrderedDict()
        earned_points = 0

        os.environ["TERM"] = "dumb"  # disable color output in terminal

        for test_name, test in self.items():
            _logger.debug("starting test %s", test_name)
            if (not quiet) and test.visible:
                dots = "." * (MAX_LEN - len(test_name) + 1)
                print(f"{test_name} {dots}", end=" ")

            jailed = SUPPORTS_JAIL and test_name.startswith("case_")
            report[test_name] = test.run(jailed=jailed)
            passed = len(report[test_name]["errors"]) == 0

            if test.points > 0:
                if (not quiet) and test.visible:
                    print("PASSED" if passed else "FAILED")
            else:
                report[test_name]["points"] = test.points if passed else 0
                earned_points += report[test_name]["points"]
                if (not quiet) and test.visible:
                    scored = report[test_name]["points"]
                    print(f"{scored} / {test.points}")

            if test.blocker and (not passed):
                break

        report["points"] = earned_points
        return report


class TestCase:
    """A test case in a specification."""

    def __init__(
        self,
        name,
        *,
        command,
        timeout=0,
        returns=0,
        points=0,
        blocker=False,
        visible=True,
    ):
        """Initialize this test case.

        :sig:
            (
                str,
                str,
                Optional[int],
                Optional[int],
                Optional[int],
                Optional[bool],
                Optional[bool]
            ) -> None
        :param name: Name of the case.
        :param command: Command to run.
        :param timeout: Timeout duration, in seconds.
        :param returns: Expected return value.
        :param points: Contribution to overall points.
        :param blocker: Whether failure blocks subsequent cases.
        :param visible: Whether the test will be visible during the run.
        """
        self.name = name  # sig: str
        """Name of this test case."""

        self.command = command  # sig: str
        """Command to run in this test case."""

        self.script = []  # sig: List[Action]
        """Sequence of actions to run in this test case."""

        self.timeout = timeout  # sig: int
        """Timeout duration of this test case, in seconds. 0 means no timeout."""

        self.returns = returns  # sig: int
        """Expected return value of this test case."""

        self.points = points  # sig: int
        """How much this test case contributes to the total points."""

        self.blocker = blocker  # sig: bool
        """Whether failure in this case will block subsequent cases or not."""

        self.visible = visible  # sig: bool
        """Whether this test will be visible during the run or not."""

    def add_action(self, action):
        """Append an action to the script of this test case.

        :sig: (Action) -> None
        :param action: Action to append to the script.
        """
        self.script.append(action)

    def run(self, *, jailed=False):
        """Run this test and produce a report.

        :sig: (Optional[bool]) -> Mapping[str, Union[str, List[str]]]
        :param jailed: Whether to jail the command to the current directory.
        :return: Result report of the test.
        """
        report = {"errors": []}

        jail_prefix = f"fakechroot chroot {os.getcwd()} " if jailed else ""
        command = f"{jail_prefix}{self.command}"
        _logger.debug("running command: %s", command)

        exit_status, errors = self.run_script(command)
        report["errors"].extend(errors)

        if exit_status != self.returns:
            report["errors"].append("Incorrect exit status.")

        return report

    def run_script(self, command):
        """Run the command of this test case and check whether it follows the script.

        :sig: (str) -> Tuple[int, List[str]]
        :return: Exit status and errors.
        """
        process = pexpect.spawn(command)
        process.setecho(False)
        errors = []
        for action in self.script:
            if action == ActionType.EXPECT:
                try:
                    _logger.debug(
                        "  expecting%s: %s",
                        " (%ss)" % action.timeout if action.timeout > 0 else "",
                        action.data,
                    )
                    process.expect(action.data, timeout=action.timeout)
                    received = (
                        "_EOF_" if ".EOF" in repr(process.after) else process.after
                    )
                    _logger.debug("  received: %s", received)
                except pexpect.EOF:
                    received = (
                        "_EOF_" if ".EOF" in repr(process.before) else process.before
                    )
                    _logger.debug("  received: %s", received)
                    process.close(force=True)
                    _logger.debug("FAILED: Expected output not received.")
                    errors.append("Expected output not received.")
                    break
                except pexpect.TIMEOUT:
                    received = (
                        "_EOF_" if ".EOF" in repr(process.before) else process.before
                    )
                    _logger.debug("  received: %s", received)
                    process.close(force=True)
                    _logger.debug("FAILED: Timeout exceeded.")
                    errors.append("Timeout exceeded.")
                    break
            elif action == ActionType.SEND:
                _logger.debug("  sending: %s", action.data)
                process.sendline(action.data)
        else:
            process.close(force=True)
        return process.exitstatus, errors


class Action:
    """An action in a test script."""

    def __init__(self, type_, data, *, timeout=0):
        """Initialize this action.

        :sig: (ActionType, str, Optional[int]) -> None
        :param type_: Expect or send.
        :param data: What to expect or send.
        :param timeout: Timeout duration, in seconds.
        """
        self.type_ = type_  # sig: ActionType
        """Type of this action, expect or send."""

        self.data = data if data != "_EOF_" else pexpect.EOF  # sig: str
        """Data description of this action, what to expect or send."""

        self.timeout = timeout  # sig: int
        """Timeout duration of this action. 0 means no timeout."""

    def as_tuple(self):
        """Get this action as a tuple.

        :sig: () -> Tuple[str, str, int]
        :return: Action type, data, and timeout.
        """
        return (
            self.type_.value[0],
            self.data if self.data != pexpect.EOF else "_EOF_",
            self.timeout,
        )


def get_comment_value(node, *, name, field):
    """Get the value of a comment field.

    :sig: (SpecNode, str, str) -> str
    :param node: Node to get the comment from.
    :param name: Name of setting in the node.
    :param field: Name of comment field.
    :return: Value of comment field.
    """
    try:
        comment = node.ca.items[name][2].value[1:].strip()  # remove the leading hash
    except KeyError:
        comment = None
    if comment is not None:
        delim = field + ":"
        if comment.startswith(delim):
            return comment[len(delim) :].strip()
    return None


def make_parser(prog):
    """Build a parser for command-line arguments.

    :param prog: Name of program.
    """
    parser = ArgumentParser(prog=prog)
    parser.add_argument("--version", action="version", version="%(prog)s 1.0")

    parser.add_argument("spec", help="test specifications file")
    parser.add_argument(
        "-d", "--directory", help="change to directory before doing anything"
    )
    parser.add_argument(
        "--validate", action="store_true", help="don't run tests, just validate spec"
    )
    parser.add_argument("--quiet", action="store_true", help="disable most messages")
    parser.add_argument("--log", action="store_true", help="create a log file")
    parser.add_argument(
        "--debug", action="store_true", help="enable debugging messages"
    )
    return parser


def setup_logging(*, debug, log):
    """Set up logging levels and handlers.

    :sig: (bool, bool) -> None
    :param debug: Whether to activate debugging.
    :param log: Whether to activate logging.
    """
    _logger.setLevel(logging.DEBUG if debug else logging.INFO)

    # stream handler for console messages
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.DEBUG if debug else logging.INFO)
    _logger.addHandler(stream_handler)

    if log:
        # force debug mode
        _logger.setLevel(logging.DEBUG)

        # file handler for logging messages
        file_handler = logging.FileHandler("log.txt")
        file_handler.setLevel(logging.DEBUG)
        _logger.addHandler(file_handler)


def main(argv=None):
    """Entry point of the utility.

    :sig: (Optional[List[str]]) -> None
    :param argv: Command line arguments.
    """
    argv = argv if argv is not None else sys.argv
    parser = make_parser(prog="calico")
    arguments = parser.parse_args(argv[1:])

    try:
        spec_filename = os.path.abspath(arguments.spec)
        with open(spec_filename) as f:
            content = f.read()

        if arguments.directory is not None:
            os.chdir(arguments.directory)

        setup_logging(debug=arguments.debug, log=arguments.log)

        suite = Suite(content)

        if not arguments.validate:
            report = suite.run(quiet=arguments.quiet)
            scored = report["points"]
            print(f"Grade: {scored} / {suite.points}")
    except Exception as e:
        print(e, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

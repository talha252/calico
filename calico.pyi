# THIS FILE IS AUTOMATICALLY GENERATED, DO NOT EDIT MANUALLY.

from typing import Any, List, Mapping, Optional, Tuple, Union

from collections import OrderedDict
from enum import Enum

import ruamel.yaml.comments

ConfigNode = ruamel.yaml.comments.CommentedMap


class Direction(Enum): ...

class Evaluation:
    cases = ...   # type: OrderedDict
    points = ...  # type: int

    def __init__(self) -> None: ...

    def add_case(self, case: TestCase) -> None: ...

class TestCase:
    name = ...     # type: str
    command = ...  # type: str
    actions = ...  # type: List[Action]
    timeout = ...  # type: Optional[int]
    returns = ...  # type: int
    points = ...   # type: Optional[int]
    blocker = ...  # type: bool
    visible = ...  # type: bool

    def __init__(
            self,
            name: str,
            *,
            command: str,
            timeout: Optional[int] = ...,
            returns: Optional[int] = ...,
            points: Optional[int] = ...,
            blocker: Optional[bool] = ...,
            visible: Optional[bool] = ...
    ) -> None: ...

    def add_action(self, action: Action) -> None: ...

class Action:
    direction = ...  # type: Direction
    data = ...       # type: str
    timeout = ...    # type: int

    def __init__(
            self,
            direction: Direction,
            data: str,
            *,
            timeout: Optional[int] = ...
    ) -> None: ...

    def as_tuple(self) -> Tuple[str, str, Optional[int]]: ...

def get_comment_value(node: ConfigNode, name: str, field: str) -> str: ...

def parse_spec(source: str) -> Evaluation: ...

def run_script(
        command: str,
        script: List[Tuple[str, str, Optional[int]]]
) -> Tuple[int, List[str]]: ...

def run_test(
        test: Mapping[str, Any],
        *,
        jailed: Optional[bool] = ...
) -> Mapping[str, Union[str, List[str]]]: ...

def run_spec(
        tests: Mapping[str, Any],
        *,
        quiet: bool = ...
) -> Mapping[str, Any]: ...

def setup_logging(*, debug: bool, log: bool) -> None: ...

def main(argv: Optional[List[str]] = ...) -> None: ...

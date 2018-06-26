# THIS FILE IS AUTOMATICALLY GENERATED, DO NOT EDIT MANUALLY.

from typing import Any, List, Mapping, Optional, Tuple, Union

from collections import OrderedDict
from enum import Enum


class ActionType(Enum): ...

class Action:
    type_ = ...    # type: ActionType
    data = ...     # type: str
    timeout = ...  # type: Optional[int]

    def __init__(
            self,
            type_: ActionType,
            data: str,
            *,
            timeout: Optional[int] = ...
    ) -> None: ...

def run_script(
        command: str,
        script: List[Action],
        *,
        defs: Optional[Mapping] = ...
) -> Tuple[int, List[str]]: ...

class TestCase:
    name = ...     # type: str
    command = ...  # type: str
    script = ...   # type: List[Action]
    timeout = ...  # type: Optional[int]
    exits = ...    # type: Optional[int]
    points = ...   # type: Optional[Union[int, float]]
    blocker = ...  # type: bool
    visible = ...  # type: bool

    def __init__(
            self,
            name: str,
            *,
            command: str,
            timeout: Optional[int] = ...,
            exits: Optional[int] = ...,
            points: Optional[Union[int, float]] = ...,
            blocker: Optional[bool] = ...,
            visible: Optional[bool] = ...
    ) -> None: ...

    def add_action(self, action: Action) -> None: ...

    def run(
            self,
            *,
            defs: Optional[Mapping] = ...,
            jailed: Optional[bool] = ...
    ) -> Mapping[str, Union[str, List[str]]]: ...

class Calico(OrderedDict):
    points = ...  # type: Union[int, float]

    def __init__(self) -> None: ...

    def add_case(self, case: TestCase) -> None: ...

    def run(self, *, quiet: Optional[bool] = ...) -> Mapping[str, Any]: ...

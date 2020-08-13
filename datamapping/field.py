from dataclasses import dataclass, field, InitVar

import inspect
import logging
from functools import partial
from typing import Any, Text, Callable, List

logger = logging.getLogger("datamapping")

__all__ = [
    'map_to',
    'Ignore',
    'FieldMapping',
    'MapTo',
    'Preserve',
    'TBD'
]


def map_to(field=None, converter=lambda value, key: value):
    return FieldMapping(field, converter=converter)


@dataclass
class FieldMapping(object):
    target: Any = field(default=None)
    converter: Callable = field(default=None)
    path: Text = field(default=None)
    context: object = field(default=None)
    target_kwargs: InitVar[dict] = field(default=None)

    _path_split: Text = field(init=False, default=None)
    _tokenized_path: List[Text] = field(init=False, default=None)
    _name: Text = field(init=False, default="")

    @property
    def name(self):
        return self._name

    def __post_init__(self, target_kwargs=None):
        from datamapping import SourceMapping
        # special case a to support a cleaner interface for embedded mappings.
        if isinstance(self.converter, type) and issubclass(self.converter, SourceMapping):
            self.converter: SourceMapping = self.converter(root=self.path)
            self._configure_converter_args(self.converter.map_item)
        elif self.converter is not None:
            self._configure_converter_args(self.converter)
        self.configure_target(target_kwargs=target_kwargs)

    def configure_target(self, force=False, target_kwargs=None):
        if target_kwargs is not None:
            self._name = self.target.__name__
            self.target = partial(self.target, **target_kwargs)
        try:
            self.context = self.target.owner or self.context
        except AttributeError as ex:
            pass

        if callable(self.target) and not force:
            try:
                self._name = self.target.__name__
            except AttributeError:
                ...
            return

        target = self.target
        try:
            target = target.name
        except Exception:
            try:
                target = target.fset.__name__
            except AttributeError:
                pass

        if isinstance(target, str):
            self.target = lambda item, value: setattr(item, target, value)
            self._name = self.target
        else:
            path = self.path
            addendum = ""
            if path is None and target is None:
                calframe = inspect.getouterframes(inspect.currentframe(), 2)[3]
                code = calframe.code_context[-1]
                d = code.split("=")
                path = d[0].lstrip().rstrip()
                target = "=".join(d[1:]).split(",")[0].split("(")[1].lstrip().rstrip()
                obj = target.split('.')[0].lstrip().rstrip()
                addendum = f"Check and make sure {obj} is mappable. " \
                           f"Usually this happens when @maps(to={obj}) is used"
            msg = f"'{path}' could not be mapped. {target} is not callable. {addendum}"
            raise AttributeError(msg)

    @property
    def tokenized_path(self):
        if self._tokenized_path is None or self.path != self._path_split:
            self._tokenized_path = self.path.split(".")
            self._path_split = self.path
        return self._tokenized_path

    def update_item(self, item, value):
        # value = self.convert(value)
        try:
            self.target(item, value)
        except TypeError as ex:
            logger.debug(ex)
            self.target(value)

        return item

    def convert(self, value):
        if self.converter:
            kwargs = {self.converter_arg_map["value"]: value}
            if self.converter_arg_map["key"]:
                kwargs[self.converter_arg_map["key"]] = self.path
            converter = self.converter
            from datamapping import SourceMapping
            if isinstance(converter, SourceMapping):
                if converter.path is None:
                    converter.path = self.path
                converter = converter.map_item
            try:
                value = converter(**kwargs)
            except TypeError:
                value = converter(*kwargs.values())
        return value

    def _configure_converter_args(self, converter):
        converter_args = inspect.signature(converter).parameters
        self.converter_arg_map = {"value": None, "key": None}
        if "value" in converter_args:
            self.converter_arg_map['value'] = "value"
        if "key" in converter_args:
            self.converter_arg_map["key"] = "key"
        if self.converter_arg_map["value"] is None:
            converter_args = list(converter_args.values())
            value = converter_args.pop(0)
            if value.name == 'self':
                raise NotImplementedError("Methods intended to be instance bound can not be converters")
            self.converter_arg_map["value"] = value.name


@dataclass
class Preserve(FieldMapping):

    def __post_init__(self, target_kwargs):
        if self.target is not None:
            super().__post_init__(target_kwargs)

    def __set_name__(self, owner, name):
        if self.path is None:
            self.path = name
        if self.target is None:
            self.target = self.path
            self.configure_target()


@dataclass
class Ignore(FieldMapping):
    target: Callable = field(default=lambda: "")

    def update_item(self, item, value):
        return None


Pass = Ignore


@dataclass
class EmbeddedValues(FieldMapping):
    """There are instances where there might be embedded dictionaries but the resulting mapping
    may not follow the same structure. When the values are important but the structure is not a EmbeddedValues
    can be used to map the deeper part of the structure. Ignore could be used but the syntax (and the name) imply that
    the referenced sub tree is entirely ignored. EmbeddedValues is a special case of Ignore that will effectively
    take a mapping (or any sort of value converter) and run the conversion but the output will be ignored.

    """

    def __post_init__(self, target_kwargs):
        """

        :return:
        """
        self.converter = self.target
        self.target = lambda: None
        super().__post_init__(target_kwargs)


class MapTo(Preserve): ...


class TBD(Preserve):
    pass


class Unknown(Preserve):
    pass

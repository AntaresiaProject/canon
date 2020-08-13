from dataclasses import field, dataclass

import json
import logging
from datetime import datetime as DateTime
from typing import List, Type, TypeVar, Text, Any, get_origin, get_args

from datamapping.exceptions import MappingError
from datamapping.mappable import mappable
from ._helpers.generics import is_generic_type, get_bound, get_parameters, get_generic_type
from .field import FieldMapping, Ignore

logger = logging.getLogger("datamapping")
_mapping_registry = {}

__all__ = [
    "locate",
    "maps",
    "SourceMapping",
    "ListMapper"
]


class _Empty(object): ...


def ascls(obj):
    if isinstance(obj, type):
        return obj
    else:
        return type(obj)


def locate(mapped_source):
    source = ascls(mapped_source)
    try:
        return _mapping_registry[source]
    except KeyError:
        for k, mapping in _mapping_registry.items():
            if issubclass(source, k):
                # Cache the result so looping isn't repeated
                _mapping_registry[source] = mapping
                return mapping
    raise NotImplementedError(f"Mapping for {mapped_source} not found")


def maps(to: Type = None, ):
    """ A declarative decorator to help specify the relationship a mapping has between Data collections and
    Data sources.

    :param target_cls:
    :param source_system:
    :param dialect:
    :return:
    """
    data_collection = mappable(to)

    def wrapper(mapping_cls):
        global _mapping_registry

        if data_collection:
            mapping_cls.target_collection = data_collection
        else:
            mapping_cls.target_collection = None
        return mapping_cls

    return wrapper


class MappingType(type):
    def __new__(cls, name, bases, members):
        # Note that we replace the classdict with a regular
        # dict before passing it to the superclass, so that we
        # don't continue to record member names after the class
        # has been created.

        result = type.__new__(cls, name, bases, dict(members))
        fields = {}
        for k, v in members.items():
            if isinstance(v, FieldMapping):
                cls.add_field_mapping(v, k, fields)
            if isinstance(v, list):
                for map in v:
                    if isinstance(map, FieldMapping):
                        cls.add_field_mapping(map, k, fields)

        result._field_mappings = fields
        return dataclass(result)

    @staticmethod
    def add_field_mapping(mapping, key, fields):
        if mapping.path is None:
            mapping.path = key
        heading = mapping.tokenized_path[0]
        fields.setdefault(heading, [])
        fields[heading].append(mapping)


T_item = TypeVar("T_item")


@dataclass
class AnnotatedValue(object):
    value: Any

    def __setattr__(self, key, value):
        if key != "value":
            key = "@" + key.lstrip("@")
        super().__setattr__(key, value)


class SourceMapping(object, metaclass=MappingType):
    target_collection: Type = field(init=False, default=None)
    _item_cache: dict = field(init=False, default_factory=dict)
    _parent: 'SourceMapping' = field(init=False, default=None)
    mapping_item: object = field(init=False, default=None)
    root: Text = field(default=None)
    should_annotate: bool = field(default=False)

    def create_data_item(self, raw_data=None):
        """While the mapping definition is generally the bulk of the mapping sometimes decisions need made on other
        side of the mapping. In these cases create_data_item and mapping_complete are the 2 intesection points.
        In some cases the Mapping may be to a generic object like Employee but based off some data, or combination of
        data,  the object created, and thus mapped into, might be a FTE or a Contractor. In these cases create_data_item
        can be overridden to provide logic .

        :param raw_data:
        :return:
        """
        if self.target_collection:
            return self.target_collection()
        else:
            try:
                return self._parent.mapping_item
            except AttributeError:
                raise MappingError("data factory can only be None on embedded mappings. ")

    @property
    def path(self):
        if self._parent:
            prefix = self._parent.path
            if len(prefix):
                prefix += "."
            path = f"{prefix}{self.root}"
        else:
            path = self.root or ""
        return path

    @property
    def annotate(self):
        if self._parent:
            return self._parent.annotate
        else:
            return self.should_annotate

    @property
    def store_unmapped(self) -> bool:
        """As a row is mapped any key/heading that is not mapped will be stored or discarded based off the value
        returned by this.

        :return: list of unicode
        """
        return True

    def unmapped_data(self, values):
        if self.store_unmapped:
            return values
        else:
            return {}

    @classmethod
    def get_mappings(cls, heading: Text) -> List[FieldMapping]:

        return cls._field_mappings.get(heading, cls._field_mappings.get(heading.lower(), []))

    def mapping_complete(self, item=None):
        """In some cases a field cannot be cleaned when it is set, generally if the value is dependent on some other
        value in the activity. In these cases they should be set/fixed in this method.

        :param item: A newly created, not yet saved :class:`.StudentActivity`.
        :type item: :class:`~data_wrangler.activity.StudentActivity`
        """
        return item

    @classmethod
    def each(cls, item):
        try:
            item.save()
        except Exception as original_ex:
            logger.exception(original_ex)
            logger.error(item.__class__.__name__)
            raise

    # ignored = IgnoreProperty

    @staticmethod
    def Ignore():
        return lambda self, doc, key, value: ''

    @staticmethod
    def MapTo(field=None, converter=lambda value, key: value, path=None):
        pass

    def map_item(self, raw_data, headings=None):

        self.initialize_cache()

        if isinstance(raw_data, (list, tuple)):
            raw_data = zip(headings or [], raw_data)
        else:
            raw_data = raw_data.items()
        unmapped_data = {}
        for header, value in raw_data:
            if not isinstance(value, (int, float, DateTime, str, dict, list)):
                try:
                    # CSV wants it all encoded into UTF 8 so we must decode out of UTF8
                    value = value.decode("utf-8")

                    # We live in a windows world and lots of things are not in any sort of useful thing try this if UTF fails.
                    value = value.decode("Windows-1252")
                except Exception as ex:
                    try:
                        value = str(value)
                    except Exception as ex2:
                        raise ex2 from ex

            field_mappings = self.get_mappings(header)
            if field_mappings is None or len(field_mappings) == 0:
                unmapped_data[header] = value
            else:
                for field_mapping in field_mappings:
                    self.map_field(field_mapping, value, header)
        for k, v in self.unmapped_data(unmapped_data).items():
            setattr(self.mapping_item, k, v)
        self.mapping_complete(item=self.mapping_item)
        return self.mapping_item

    def add_parent(self, parent):
        self._parent = parent

    def initialize_cache(self):
        try:
            if self.target_collection:
                self.mapping_item = self.create_data_item()
            else:
                try:
                    self.mapping_item = self._parent.mapping_item
                except AttributeError:
                    raise MappingError("data factory can only be None on embedded mappings. ")
            try:
                self._parent._item_cache[type(self.mapping_item)] = self.mapping_item
            except AttributeError:
                pass

        except Exception:
            logger.error(f"{type(self).__name__} failed to create item {self.target_collection}")
            raise

    def get_item(self, item_cls=None, strict=True):
        if strict:
            test = lambda obj, cls: ascls(obj) == cls
        else:
            test = self.instanceof
        if item_cls is None or test(self.mapping_item, item_cls):
            return self.mapping_item
        for k, item in self._item_cache.items():
            if test(k, item_cls):
                return item
        if self._parent is not None:
            item = self._parent.get_item(item_cls, strict=True)
            if item is None:
                item = self._parent.get_item(item_cls, strict=False)
            return item

        return _Empty

    def map_field(self, field_mapping, value, header):
        for node in field_mapping.tokenized_path[1:]:
            try:
                value = value[node]
            except KeyError:
                logger.warning(f"Node '{node}' not found on {header}. Nodes found: {','.join(value.keys())}")
            except TypeError:
                logger.info(f"{value} can  ot be sliced by {node}")
                raise
        field_converter = field_mapping.converter
        is_mapping = isinstance(field_converter, SourceMapping)
        if is_mapping:
            prefix = self.path
            if len(prefix):
                prefix += "."
            field_converter.root = f"{prefix}{header}"
            field_converter.add_parent(self)
        try:

            value = field_mapping.convert(value)
        except Exception as ex:
            msg = f"Error while converting '{header}' to the mappable value using {field_converter}.\n" \
                  f"{json.dumps(value, indent=' ')} """
            raise MappingError(msg) from ex
        self._item_cache[type(value)] = value
        item = self.get_item(field_mapping.context)
        try:
            if not isinstance(field_converter, ListMapper):
                value = [value]
            for idx, v in enumerate(value):
                if not isinstance(field_mapping, Ignore):
                    field_mapping.update_item(item, self.annotated(v, field_mapping, field_converter))
        except (Exception, TypeError) as ex:
            raise MappingError(f"Error when calling '{field_mapping.name}' on '{item}' with '{value}'") from ex

    @staticmethod
    def instanceof(obj, kls):
        if not is_generic_type(kls):
            return isinstance(obj, kls)

        obj_tp = get_generic_type(obj)
        templates = list(get_bound(t) or t.__constraints__ for t in get_parameters(get_origin(kls)))

        try:
            if issubclass(type(obj), get_origin(kls)):
                for bound, obj_sub_tp in zip(templates, get_args(obj_tp)):

                    if not issubclass(obj_sub_tp, bound):
                        return False
                return True
        except TypeError as ex:
            raise ex

    def annotated(self, v, field_mapping, field_converter):
        if self.annotate and isinstance(v, (str, int, DateTime, float)):
            v = AnnotatedValue(v)
            prefix = self.root
            if len(prefix):
                prefix += "."
            v.path = f"{prefix}{field_mapping.path}"

            if field_converter is not None and not isinstance(field_converter, SourceMapping):
                v.MethodExecuted = field_converter.__name__
                v.MethodDocstring = (field_converter.__doc__ or "").lstrip().rstrip().split("\n")
        return v


class IgnoreEntry(Exception):
    pass


class ListMapper(SourceMapping):
    """In some special cases when dealing with unstructured data a List might need to be mapped not as a list but
    as individual items. This mapper is for those scenarios.

    """

    def handle_non_list(self, data, headings):
        logger.warning(f"List Mapping provided but the value provided is not a list {data}")
        return super().map_item(data, headings)

    def map_item(self, raw_data, headings=None):
        if not isinstance(raw_data, list):
            self.handle_non_list(raw_data, headings)
        for idx, item in enumerate(raw_data):
            try:
                value = super().map_item(item, headings)
            except IgnoreEntry:
                continue
            else:
                yield value

from dataclasses import is_dataclass, fields

from ._helpers.generics import get_origin


class MappingInfo(object):
    def __init__(self, owner, name, val_type):
        self.owner = owner
        self.name = name
        self.type = val_type

    def __getattr__(self, item):
        return getattr(self.type, item)


class MappableDecoration(object):
    """Collections that are decorated with dataclass behave a bit funky when referencing the class, like we do in
       mappings. This decorator (or just callable) "fixes" a dataclass's class reference to enable Mapping to function
       correctly.

       :param cls:
       :return:
       """

    def __init__(self):
        self._mappable_list = []

    def __call__(self, cls):
        o_cls = get_origin(cls) or cls
        if o_cls not in self._mappable_list and is_dataclass(o_cls):
            self.make_mappable(o_cls)
            self._mappable_list.append(o_cls)
        return cls

    def is_mappable(self, kls, set=None):
        if set is not None:
            if set:
                self._mappable_list.append(kls)
            else:
                self._mappable_list.remove(kls)
        return kls in self._mappable_list

    def make_mappable(self, cls):
        for field in fields(cls):
            name = field.name
            try:
                val_type = field.type
            except AttributeError:
                val_type = type(field)
            # always favor the annotation directly on the class
            val_type = cls.__annotations__.get(name, val_type)
            mappable(val_type)
            try:
                name = field.name
            except AttributeError:
                pass
            setattr(cls, name, MappingInfo(cls, name, val_type))


mappable = MappableDecoration()

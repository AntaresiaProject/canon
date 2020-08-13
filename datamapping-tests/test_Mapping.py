from dataclasses import field, dataclass, make_dataclass
from typing import Text, List
from unittest import TestCase

from datamapping.mappable import mappable
from datamapping import FieldMapping, MapTo, Ignore, TBD
from datamapping import SourceMapping


@mappable
@dataclass
class RootData(object):
    id: Text = field(default=None)
    verb_id: Text = field(default=None)
    somethings_deep: List[object] = field(default_factory=list)

    def add_something(self, something):
        self.somethings_deep.append(something)


@mappable
@dataclass
class Deeper(object):
    info: Text = field(default=None)


simple_row = dict(verb_id="TestRow",
                  special_case=dict(
                      a_string="MyString",
                      a_phrase="Doesn't Matter now does it?",
                      an_id="MyImportantID"
                  ))


class TestFieldMapping(TestCase):
    def test_set_name(self):
        class MyMapping(SourceMapping):
            f = FieldMapping("jinga")
            g = MapTo()
            h = FieldMapping("fsddf")

        mapping = MyMapping()
        assert len(mapping.get_mappings("f")) == 1

    def test_single_dot_path(self):
        class BasicMapping(SourceMapping):
            verb_id = MapTo()
            special_case = FieldMapping(RootData.id, path="special_case.an_id")

        mapping = BasicMapping()
        assert len(mapping.get_mappings("special_case")) == 1

    def test_dot_paths(self):
        class BasicMapping(SourceMapping):
            verb_id = MapTo()
            special_case_an_id = FieldMapping(RootData.id, path="special_case.an_id")
            special_case_string = FieldMapping("some_string", path="special_case.a_string")

        mapping = BasicMapping()
        field_mapping = mapping.get_mappings("special_case")
        assert len(field_mapping) == 2

    def test_key_to_list_mapping(self):
        class BasicMapping(SourceMapping):
            verb_id = MapTo()
            special_case = [FieldMapping(RootData.id, path="special_case.an_id"),
                            FieldMapping("some_string", path="special_case.a_string")]

        mapping = BasicMapping()
        field_mapping = mapping.get_mappings("special_case")
        assert len(field_mapping) == 2

    def test_dot_paths_map(self):
        class BasicMapping(SourceMapping):
            target_collection = RootData
            verb_id = MapTo()
            special_case_an_id = FieldMapping(RootData.id, path="special_case.an_id")
            special_case_string = FieldMapping("some_string", path="special_case.a_string")

        mapping = BasicMapping()
        item = mapping.map_item(simple_row)
        assert isinstance(item, RootData)
        assert item.id == "MyImportantID"
        assert item.some_string == "MyString"

    def test_multiple_mappings_for_key(self):
        class BasicMapping(SourceMapping):
            target_collection = RootData

            verb_id = MapTo()
            special_case = FieldMapping(RootData.id, path="special_case.an_id")
            _1 = FieldMapping("alt_id", path="special_case.an_id")

        mapping = BasicMapping()
        item = mapping.map_item(simple_row)
        assert item.alt_id == "MyImportantID"
        assert item.id == "MyImportantID"
        # assert len(field_mapping) == 2

    def test_embedded_mapping(self):
        mappable(Deeper)
        mappable(RootData)

        class EmbeddedMapping(SourceMapping):
            target_collection = Deeper

            a_string = MapTo(Deeper.info)  # example Value: "Correct",
            a_phrase = Ignore()  # example Value: "GlobalId",
            an_id = MapTo(RootData.id)

            def mapping_complete(self, item=None):
                assert hasattr(item, "info")
                assert getattr(item, "info") == "MyString"
                assert not hasattr(item, "id")

        class BasicMapping(SourceMapping):
            target_collection = RootData

            verb_id = TBD()
            special_case = FieldMapping(RootData.add_something, EmbeddedMapping)

            def mapping_complete(self, item: RootData = None):
                assert hasattr(item, "somethings_deep")
                assert item.id == "MyImportantID"

        mapping = BasicMapping()
        item = mapping.map_item(simple_row)
        print(item)

    def test_metadataclass(self):
        class DataclassMeta(type):
            def __new__(cls, name, bases, classdict):
                # Note that we replace the classdict with a regular
                # dict before passing it to the superclass, so that we
                # don't continue to record member names after the class
                # has been created.
                fields = []
                for k, v in classdict["__annotations__"].items():
                    field = (k, v, classdict.pop(k, None))
                    fields.append(field)
                result = make_dataclass(name, fields, bases=bases, namespace=classdict, init=True,
                                        repr=True, eq=True, order=False, unsafe_hash=False,
                                        frozen=False)
                # result = type.__new__(cls, name, bases, dict(classdict))
                return result

        class Shhhhh(object, metaclass=DataclassMeta):
            f: Text
            g: int = 0
            t: Text = field(default_factory=lambda: "Gogoog")

            def bob(self):
                return "Hellloooooo"

        sh = Shhhhh(g=0, f="fsdf")
        assert sh.f == "fsdf"
        assert sh.bob() == "Hellloooooo"


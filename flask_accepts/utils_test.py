from dataclasses import dataclass
from unittest.mock import MagicMock, patch
import pytest
from marshmallow import Schema, fields as ma
from flask import Flask
from flask_restplus import Resource, Api, fields as fr

# from .utils import unpack_list, unpack_nested
import flask_accepts.utils as utils


def test_unpack_list():
    app = Flask(__name__)
    api = Api(app)
    with patch("flask_accepts.utils.unpack_list", wraps=utils.unpack_list) as mock:
        result = utils.unpack_list(ma.List(ma.Integer()), api=api)

        assert isinstance(result, fr.List)
        assert mock.call_count == 1


def test_unpack_list_of_list():
    app = Flask(__name__)
    api = Api(app)
    with patch(
        "flask_accepts.utils.unpack_list", wraps=utils.unpack_list
    ) as mock, patch.dict("flask_accepts.utils.type_map", {ma.List: mock}):

        result = utils.unpack_list(ma.List(ma.List(ma.Integer())), api=api)

        assert isinstance(result, fr.List)
        assert mock.call_count == 2


def test_unpack_nested():
    app = Flask(__name__)
    api = Api(app)

    class IntegerSchema(Schema):
        my_int: ma.Integer()

    result = utils.unpack_nested(ma.Nested(IntegerSchema), api=api)

    assert result


def test_unpack_nested_self():
    app = Flask(__name__)
    api = Api(app)

    class IntegerSchema(Schema):
        my_int = ma.Integer()
        children = ma.Nested("self", exclude=["children"])

    schema = IntegerSchema()

    result = utils.unpack_nested(schema.fields.get("children"), api=api)

    assert type(result) == fr.Nested


def test_unpack_nested_self_many():
    app = Flask(__name__)
    api = Api(app)

    class IntegerSchema(Schema):
        my_int = ma.Integer()
        children = ma.Nested("self", exclude=["children"], many=True)

    schema = IntegerSchema()

    result = utils.unpack_nested(schema.fields.get("children"), api=api)

    assert type(result) == fr.List


def test_get_default_model_name():
    from .utils import get_default_model_name

    class TestSchema(Schema):
        pass

    result = get_default_model_name(TestSchema)

    expected = "Test"
    assert result == expected


def test_get_default_model_name_works_with_multiple_schema_in_name():
    from .utils import get_default_model_name

    class TestSchemaSchema(Schema):
        pass

    result = get_default_model_name(TestSchemaSchema)

    expected = "TestSchema"
    assert result == expected


def test_get_default_model_name_that_does_not_end_in_schema():
    from .utils import get_default_model_name

    class SomeOtherName(Schema):
        pass

    result = get_default_model_name(SomeOtherName)

    expected = "SomeOtherName"
    assert result == expected


def test_get_default_model_name_default_names():
    from .utils import get_default_model_name, num_default_models

    for model_num in range(5):
        result = get_default_model_name()
        expected = f"DefaultResponseModel_{model_num + num_default_models}"
        assert result == expected


def test__check_load_dump_only_on_dump():
    @dataclass
    class FakeField:
        load_only: bool
        dump_only: bool

    assert not utils._check_load_dump_only(
        FakeField(load_only=True, dump_only=False), "dump"
    )
    assert utils._check_load_dump_only(
        FakeField(load_only=False, dump_only=True), "dump"
    )


def test__check_load_dump_only_on_load():
    @dataclass
    class FakeField:
        load_only: bool
        dump_only: bool

    assert utils._check_load_dump_only(
        FakeField(load_only=True, dump_only=False), "load"
    )
    assert not utils._check_load_dump_only(
        FakeField(load_only=False, dump_only=True), "load"
    )


def test__check_load_dump_only_raises_on_invalid_operation():
    @dataclass
    class FakeField:
        load_only: bool
        dump_only: bool

    with pytest.raises(ValueError):
        utils._check_load_dump_only(
            FakeField(load_only=True, dump_only=False), "not an operation"
        )


def test__ma_field_to_fr_field_converts_required_param_if_present():
    @dataclass
    class FakeFieldWithRequired(ma.Field):
        required: bool

    fr_field_dict = utils._ma_field_to_fr_field(FakeFieldWithRequired(required=True))
    assert fr_field_dict["required"] is True

    @dataclass
    class FakeFieldNoRequired(ma.Field):
        pass

    fr_field_dict = utils._ma_field_to_fr_field(FakeFieldNoRequired())
    assert "required" not in fr_field_dict


def test__ma_field_to_fr_field_converts_missing_param_to_default_if_present():
    @dataclass
    class FakeFieldWithMissing(ma.Field):
        missing: bool

    fr_field_dict = utils._ma_field_to_fr_field(FakeFieldWithMissing(missing=True))
    assert fr_field_dict["default"] is True

    @dataclass
    class FakeFieldNoMissing(ma.Field):
        pass

    fr_field_dict = utils._ma_field_to_fr_field(FakeFieldNoMissing())
    assert "default" not in fr_field_dict


def test__ma_field_to_fr_field_converts_metadata_param_to_description_if_present():
    @dataclass
    class FakeFieldWithDescription(ma.Field):
        metadata: dict

    expected_description = "test"

    fr_field_dict = utils._ma_field_to_fr_field(
        FakeFieldWithDescription(metadata={"description": expected_description})
    )
    assert fr_field_dict["description"] == expected_description

    @dataclass
    class FakeFieldNoMetaData(ma.Field):
        pass

    fr_field_dict = utils._ma_field_to_fr_field(FakeFieldNoMetaData())
    assert "description" not in fr_field_dict

    @dataclass
    class FakeFieldNoDescription(ma.Field):
        metadata: dict

    fr_field_dict = utils._ma_field_to_fr_field(FakeFieldNoDescription(metadata={}))
    assert "description" not in fr_field_dict


def test__ma_field_to_fr_field_converts_default_to_example_if_present():
    @dataclass
    class FakeFieldWithDefault(ma.Field):
        default: str

    expected_example_value = "test"

    fr_field_dict = utils._ma_field_to_fr_field(
        FakeFieldWithDefault(default=expected_example_value)
    )
    assert fr_field_dict["example"] == expected_example_value

    @dataclass
    class FakeFieldNoDefault(ma.Field):
        pass

    fr_field_dict = utils._ma_field_to_fr_field(FakeFieldNoDefault())
    assert "example" not in fr_field_dict


def test__ma_field_to_fr_field_returns_empty_dict_for_no_params_present_in_ma_field():
    @dataclass
    class FakeFieldWithNoParams(ma.Field):
        pass

    fr_field_dict = utils._ma_field_to_fr_field(FakeFieldWithNoParams())
    assert not fr_field_dict


def test_make_type_mapper_works_with_required():
    from flask_accepts.utils import make_type_mapper

    app = Flask(__name__)
    api = Api(app)

    mapper = make_type_mapper(fr.Raw)
    result = mapper(ma.Raw(required=True), api=api, model_name='test_model_name', operation='load')
    assert result.required

def test_make_type_mapper_produces_nonrequired_param_by_default():
    from flask_accepts.utils import make_type_mapper

    app = Flask(__name__)
    api = Api(app)

    mapper = make_type_mapper(fr.Raw)
    result = mapper(ma.Raw(), api=api, model_name='test_model_name', operation='load')
    assert not result.required


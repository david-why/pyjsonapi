from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    Dict,
    ForwardRef,
    List,
    Literal,
    Optional,
    Self,
    cast,
    get_args,
    get_origin,
    get_type_hints,
)

from pydantic import BaseModel, GetCoreSchemaHandler
from pydantic_core import CoreSchema, PydanticUndefined

from pyjsonapi.relationship import RelationshipBase, RelationshipDef, ToManyRelationship
from pyjsonapi.utils import find_included

if TYPE_CHECKING:
    from pyjsonapi.session import Session

__all__ = ['Model']


class Model(BaseModel):
    _default_include: ClassVar[set[str]]

    __jsonapi_model_marker__: ClassVar[Literal[True]] = True

    __jsonapi_type__: ClassVar[str]
    __jsonapi_endpoint__: ClassVar[str]

    __jsonapi_relationships__: ClassVar[Dict[str, RelationshipDef]]
    __jsonapi_hasrefs__: ClassVar[bool]

    id: str
    meta: dict[str, Any]

    def __init_subclass__(
        cls, *, type: Optional[str] = None, endpoint: Optional[str] = None
    ):
        if not hasattr(cls, '__jsonapi_type__'):
            cls.__jsonapi_type__ = type or cls.__name__
        if not hasattr(cls, '__jsonapi_endpoint__'):
            cls.__jsonapi_endpoint__ = endpoint or cls.__jsonapi_type__

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source: type, handler: GetCoreSchemaHandler
    ) -> CoreSchema:
        cls.__jsonapi_relationships__ = {}
        cls.__jsonapi_hasrefs__ = False
        # hack so that the "default values" are removed before Pydantic
        # generates the schema
        cls._default_include = set()
        for field, info in cls.model_fields.items():
            annotation = info.annotation
            origin = get_origin(annotation)
            if isinstance(origin, type) and issubclass(origin, RelationshipBase):
                definition = info.default
                info.default = PydanticUndefined
                rel_type = get_args(annotation)[0]
                if isinstance(rel_type, str):
                    cls.__jsonapi_hasrefs__ = True
                elif isinstance(rel_type, ForwardRef):
                    cls.__jsonapi_hasrefs__ = True
                    rel_type = rel_type.__forward_arg__
                elif not issubclass(rel_type, Model):
                    raise TypeError(f'Invalid relationship type: {annotation}')
                if not isinstance(definition, RelationshipDef):
                    definition = RelationshipDef(field, rel_type)
                else:
                    definition.type = rel_type
                if definition.default_include:
                    cls._default_include.add(field)
                if issubclass(origin, ToManyRelationship):
                    definition.to_many = True
                cls.__jsonapi_relationships__[field] = definition
                setattr(cls, field, definition)
        return handler(source)

    @classmethod
    def _resolve_refs(cls) -> bool:
        success = True
        for field, reldef in cls.__jsonapi_relationships__.items():
            if not isinstance(reldef.type, str):
                continue
            rel_type = get_args(get_type_hints(cls)[field])[0]
            if not issubclass(rel_type, Model):
                success = False
            else:
                reldef.type = rel_type
        return success

    @classmethod
    def _ensure_resolve_refs(cls):
        if cls.__jsonapi_hasrefs__:
            if not cls._resolve_refs():
                raise TypeError('Failed to resolve relationship references')

    @classmethod
    def _from_data(
        cls,
        data: Dict[str, Any],
        session: 'Session',
        *,
        included: Optional[List[Dict[str, Any]]] = None,
    ) -> Self:
        cls._ensure_resolve_refs()
        model_data = {
            'id': data['id'],
            'meta': data.get('meta', {}),
            **data['attributes'],
        }
        for field, rel_def in cls.__jsonapi_relationships__.items():
            rel_type = cast(Model, rel_def.type)
            if field in data['relationships'] and included:
                reldata = data['relationships'][field]['data']
                if isinstance(reldata, list):
                    items = find_included(
                        included, *((item['type'], item['id']) for item in reldata)
                    )
                    models = []
                    for item in items:
                        models.append(
                            rel_type._from_data(item, session, included=included)
                        )
                else:
                    item = find_included(included, (reldata['type'], reldata['id']))[0]
                    models = rel_type._from_data(item, session, included=included)
                model_data[field] = {
                    'data': models,
                    'to_many': isinstance(reldata, list),
                    'session': session,
                    'rel_def': rel_def,
                    'self_type': cls,
                    'self_id': data['id'],
                    'type': 'reldata',
                }
            else:
                model_data[field] = {
                    'data': data['id'],
                    'to_many': rel_def.to_many,
                    'session': session,
                    'rel_def': rel_def,
                    'self_type': cls,
                    'self_id': data['id'],
                    'type': 'self',
                }
        return cls.model_validate(model_data)

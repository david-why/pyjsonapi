from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    Generic,
    List,
    Optional,
    Type,
    TypeVar,
    Union,
)
import warnings

from pydantic import GetCoreSchemaHandler
from pydantic_core import core_schema

if TYPE_CHECKING:
    from pyjsonapi.model import Model
    from pyjsonapi.session import Session

ModelT = TypeVar('ModelT', bound='Model')


class RelationshipBase(Generic[ModelT]):
    def __init__(
        self,
        value: Any,
        self_type: Type['Model'],
        self_id: str,
        rel_def: 'RelationshipDef',
        session: 'Session',
    ):
        self._value = value
        self._self_type = self_type
        self._self_id = self_id
        self._rel_def = rel_def
        self._session = session

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source: type, handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        return core_schema.no_info_plain_validator_function(
            cls._validate,
            serialization=core_schema.plain_serializer_function_ser_schema(
                cls._serialize, info_arg=False
            ),
        )

    @staticmethod
    def _validate(value):
        if isinstance(value, dict):
            args = (
                value['data'],
                value['self_type'],
                value['self_id'],
                value['rel_def'],
                value['session'],
            )
            if value['type'] == 'reldata':
                if value.get('to_many'):
                    return _ToManyRel(*args)
                return _ToOneRel(*args)
            if value.get('to_many'):
                return _ToManyRelSelf(*args)
            return _ToOneRelSelf(*args)
        assert False, 'invalid relationship value'

    @staticmethod
    def _serialize(value):
        return value._value


class ToOneRelationship(RelationshipBase[ModelT]):
    @property
    def item(self) -> ModelT:
        return self.fetch_item()

    def fetch_item(
        self,
        *,
        include: Optional[Union[str, List[str]]] = None,
        with_meta: Optional[Union[str, List[str]]] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> ModelT:
        raise NotImplementedError


class ToManyRelationship(RelationshipBase[ModelT]):
    @property
    def items(self) -> List[ModelT]:
        return self.fetch_items()

    def fetch_items(
        self,
        *,
        include: Optional[Union[str, List[str]]] = None,
        with_meta: Optional[Union[str, List[str]]] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> List[ModelT]:
        raise NotImplementedError


class Relationship(ToOneRelationship[ModelT], ToManyRelationship[ModelT]):
    def __class_getitem__(cls, item: Type[ModelT]) -> Type['Relationship[ModelT]']:
        warnings.warn(
            'Relationship[T] is deprecated, use ToOneRelationship[T] or ToManyRelationship[T]',
            DeprecationWarning,
            stacklevel=2,
        )
        return super().__class_getitem__(item)  # type: ignore


class _ToOneRel(ToOneRelationship[ModelT]):
    def fetch_item(self, **kwargs) -> ModelT:
        if kwargs:
            return _ToOneRelSelf(
                self._self_id,
                self._self_type,
                self._self_id,
                self._rel_def,
                self._session,
            ).fetch_item(**kwargs)
        return self._value


class _ToOneRelSelf(ToOneRelationship[ModelT]):
    def fetch_item(
        self,
        *,
        include: Optional[Union[str, List[str]]] = None,
        with_meta: Optional[Union[str, List[str]]] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> ModelT:
        return self._session.fetch_related_one(
            self._self_type,
            self._value,
            self._rel_def.name,
            include=include,
            with_meta=with_meta,
            params=params,
        )


class _ToManyRel(ToManyRelationship[ModelT]):
    def fetch_items(self, **kwargs) -> List[ModelT]:
        if kwargs:
            return _ToManyRelSelf(
                self._self_id,
                self._self_type,
                self._self_id,
                self._rel_def,
                self._session,
            ).fetch_items(**kwargs)
        return self._value


class _ToManyRelSelf(ToManyRelationship[ModelT]):
    def fetch_items(
        self,
        *,
        include: Optional[Union[str, List[str]]] = None,
        with_meta: Optional[Union[str, List[str]]] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> List[ModelT]:
        return self._session.fetch_related_many(
            self._self_type,
            self._value,
            self._rel_def.name,
            include=include,
            with_meta=with_meta,
            params=params,
        )


class RelationshipDef:
    def __init__(
        self,
        name: str,
        type: Optional[Union[str, Type['Model']]] = None,
        to_many: bool = False,
        default_include: bool = False,
    ) -> None:
        self.name = name
        self.type = type
        self.to_many = to_many
        self.default_include = default_include


def make_relationship(*, to_many: bool = False, default_include: bool = False) -> Any:
    return RelationshipDef(
        to_many=to_many,
        default_include=default_include,
    )  # type: ignore

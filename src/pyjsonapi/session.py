from typing import TYPE_CHECKING, Any, Dict, List, Optional, Type, TypeVar, Union

import requests

if TYPE_CHECKING:
    from pyjsonapi.model import Model
    from pyjsonapi.relationship import RelationshipBase

ModelT = TypeVar('ModelT', bound='Model')


class Session:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.session = requests.Session()

    @staticmethod
    def _parse_include(
        include: Optional[Union[str, List[str]]] = None,
        *,
        type: Optional[Type['Model']] = None,
    ) -> List[str]:
        if include is None:
            include = []
        elif isinstance(include, str):
            include = [include]
        if type is not None:
            for field in type._default_include:
                if field not in include:
                    include.append(field)
        return include

    @staticmethod
    def _parse_params(
        include: Optional[Union[str, List[str]]] = None,
        *,
        type: Optional[Type['Model']] = None,
        with_meta: Optional[Union[str, List[str]]] = None,
        params: Optional[Dict[str, str]] = None,
    ) -> Dict[str, str]:
        include = Session._parse_include(include, type=type)
        real_params = {}
        if include:
            real_params['include'] = ','.join(include)
        if isinstance(with_meta, str):
            with_meta = [with_meta]
        if with_meta:
            real_params['with_meta'] = ','.join(with_meta)
        if params:
            real_params.update(params)
        return real_params

    def fetch(
        self,
        type: Type[ModelT],
        id: str,
        *,
        include: Optional[Union[str, List[str]]] = None,
        with_meta: Optional[Union[str, List[str]]] = None,
        params: Optional[Dict[str, str]] = None,
    ) -> ModelT:
        url = f'{self.base_url}/{type.__jsonapi_endpoint__}/{id}'
        real_params = self._parse_params(
            include, type=type, with_meta=with_meta, params=params
        )
        resp = self.session.get(url, params=real_params)
        resp.raise_for_status()
        json = resp.json()
        data = json['data']
        return type._from_data(data, self, included=json.get('included'))

    def fetch_all(
        self,
        type: Type[ModelT],
        *,
        include: Optional[Union[str, List[str]]] = None,
        with_meta: Optional[Union[str, List[str]]] = None,
        params: Optional[Dict[str, str]] = None,
    ) -> List[ModelT]:
        url = f'{self.base_url}/{type.__jsonapi_endpoint__}'
        real_params = self._parse_params(
            include, type=type, with_meta=with_meta, params=params
        )
        resp = self.session.get(url, params=real_params)
        resp.raise_for_status()
        json = resp.json()
        data = json['data']
        included = json.get('included')
        return [type._from_data(item, self, included=included) for item in data]

    def fetch_related(
        self,
        type: Type[ModelT],
        id: str,
        # actual type of relationship is str | RelationshipDef
        relationship: 'Union[str, RelationshipBase[Any]]',
        *,
        include: Optional[Union[str, List[str]]] = None,
        with_meta: Optional[Union[str, List[str]]] = None,
        params: Optional[Dict[str, str]] = None,
    ) -> Any:
        if isinstance(relationship, str):
            rel_name = relationship
        else:
            rel_name = relationship.name  # type: ignore
        url = f'{self.base_url}/{type.__jsonapi_endpoint__}/{id}/{rel_name}'
        real_params = self._parse_params(
            include, type=type, with_meta=with_meta, params=params
        )
        resp = self.session.get(url, params=real_params)
        resp.raise_for_status()
        json = resp.json()
        data = json['data']
        included = json.get('included')
        rel_type = getattr(type, rel_name).type
        if isinstance(data, list):
            return [rel_type._from_data(item, self, included=included) for item in data]
        return rel_type._from_data(data, self, included=included)

    def fetch_related_one(
        self,
        type: Type[ModelT],
        id: str,
        relationship: 'Union[str, RelationshipBase[Any]]',
        *,
        include: Optional[Union[str, List[str]]] = None,
        with_meta: Optional[Union[str, List[str]]] = None,
        params: Optional[Dict[str, str]] = None,
    ) -> Any:
        return self.fetch_related(
            type, id, relationship, include=include, params=params, with_meta=with_meta
        )

    def fetch_related_many(
        self,
        type: Type[ModelT],
        id: str,
        relationship: 'Union[str, RelationshipBase[Any]]',
        *,
        include: Optional[Union[str, List[str]]] = None,
        with_meta: Optional[Union[str, List[str]]] = None,
        params: Optional[Dict[str, str]] = None,
    ) -> List[Any]:
        return self.fetch_related(
            type, id, relationship, include=include, params=params, with_meta=with_meta
        )

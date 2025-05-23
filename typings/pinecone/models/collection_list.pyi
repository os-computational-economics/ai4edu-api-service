"""This type stub file was generated by pyright."""

from pinecone.core.openapi.control.models import CollectionList as OpenAPICollectionList

class CollectionList:
    """A list of collections."""

    def __init__(self, collection_list: OpenAPICollectionList) -> None: ...
    def names(self):  # -> list[Any]:
        ...
    def __getitem__(self, key): ...
    def __len__(self):  # -> int:
        ...
    def __iter__(self): ...
    def __str__(self) -> str: ...
    def __repr__(self):  # -> str:
        ...
    def __getattr__(self, attr):  # -> Any:
        ...

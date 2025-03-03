from typing import Dict, Any, List, Union
from pydantic import BaseModel, Field, field_validator
from app.models.di_proof import DataIntegrityProof
from config import settings


class BaseModel(BaseModel):
    def model_dump(self, **kwargs) -> Dict[str, Any]:
        return super().model_dump(by_alias=True, exclude_none=True, **kwargs)


class ResourceMetadata(BaseModel):
    resourceId: str = Field(None)
    resourceType: str = Field(None)
    resourceName: str = Field(None)
    resourceCollectionId: str = Field(None)


class RelatedLink(BaseModel):
    id: str = Field()
    type: str = Field()
    timestamp: int = Field(None)
    digestMultibase: str = Field(None)


class AttestedResource(BaseModel):
    context: List[str] = Field(
        alias="@context",
        default=[
            "https://w3id.org/security/data-integrity/v2",
            f"https://{settings.DOMAIN}/attested-resource/v1",
        ],
    )
    type: List[str] = Field(default=["AttestedResource"])
    id: str = Field()
    content: dict = Field()
    metadata: ResourceMetadata = Field(None)
    links: List[RelatedLink] = Field(None)
    proof: Union[DataIntegrityProof, List[DataIntegrityProof]] = Field(None)

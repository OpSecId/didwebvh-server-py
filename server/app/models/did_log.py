"""DID Log models."""

from typing import Any, Dict, List, Union

from pydantic import BaseModel, Field

from config import settings

from .di_proof import DataIntegrityProof
from .did_document import DidDocument


class BaseModel(BaseModel):
    """Base model for all models in the application."""

    def model_dump(self, **kwargs) -> Dict[str, Any]:
        """Dump the model to a dictionary."""
        return super().model_dump(by_alias=True, **kwargs)


class Witness(BaseModel):
    """Witness model."""

    id: str = Field()


class WitnessParam(BaseModel):
    """WitnessParam model."""

    threshold: int = Field()
    witnesses: List[Witness] = Field()


class WitnessProof(BaseModel):
    """WitnessProof model."""

    versionId: str = Field()
    proof: List[DataIntegrityProof] = Field()


# class InitialLogParameters(BaseModel):
#     """InitialLogParameters model."""

#     method: str = Field(f"did:webvh:{settings.WEBVH_VERSION}")
#     scid: str = Field()
#     updateKeys: List[str] = Field()
#     prerotation: bool = Field(default=False)
#     portable: bool = Field(default=False)
#     deactivated: bool = Field(False)
#     nextKeyHashes: List[str] = Field(None)


class LogParameters(BaseModel):
    """LogParameters model."""

    method: str = Field(None) # This property MUST appear in the first DID log entry.
    scid: str = Field(None) # This property MUST appear in the first DID log entry.
    updateKeys: List[str] = Field(None) # his property MUST appear in the first DID log entry
    portable: bool = Field()
    prerotation: bool = Field()
    nextKeyHashes: List[str] = Field()
    witness: Union[WitnessParam, None] = Field()
    deactivated: bool = Field(None)
    ttl: bool = Field(None)


class InitialLogParameters(BaseModel):
    """InitialLogParameters model."""

    method: str = Field() # This property MUST appear in the first DID log entry.
    scid: str = Field() # This property MUST appear in the first DID log entry.
    updateKeys: List[str] = Field()


class InitialLogEntry(BaseModel):
    """InitialLogEntry model."""

    versionId: str = Field()
    versionTime: str = Field()
    parameters: LogParameters = Field()
    state: dict = Field()
    proof: Union[DataIntegrityProof, List[DataIntegrityProof]] = Field(None)


class LogEntry(BaseModel):
    """LogEntry model."""

    versionId: str = Field()
    versionTime: str = Field()
    parameters: LogParameters = Field()
    state: DidDocument = Field()
    proof: Union[DataIntegrityProof, List[DataIntegrityProof]] = Field(None)

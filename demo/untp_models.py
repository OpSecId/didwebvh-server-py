"""
UNTP (UN Transparency Protocol) Pydantic Models
Version 0.6.0

Official Specification: https://spec-untp-fbb45f.opensource.unicc.org/
"""

from typing import List, Optional, Literal, Dict, Any, Union
from pydantic import BaseModel, Field, HttpUrl
from datetime import datetime


# ============================================================================
# UNTP Version Index
# ============================================================================

UNTP_VERSIONS = {
    "0.6.0": {
        "status": "pilot",
        "release_date": "2024-12",
        "contexts": {
            "dcc": "https://test.uncefact.org/vocabulary/untp/dcc/0.6.0/",
            "dia": "https://test.uncefact.org/vocabulary/untp/dia/0.6.0/",
            "dpp": "https://test.uncefact.org/vocabulary/untp/dpp/0.6.0/",
            "dte": "https://test.uncefact.org/vocabulary/untp/dte/0.6.0/",
            "dfr": "https://test.uncefact.org/vocabulary/untp/dfr/0.6.0/",
        },
        "schemas": {
            "dcc": "https://test.uncefact.org/vocabulary/untp/dcc/untp-dcc-schema-0.6.0.json",
            "dia": "https://test.uncefact.org/vocabulary/untp/dia/untp-dia-schema-0.6.0.json",
            "dpp": "https://test.uncefact.org/vocabulary/untp/dpp/untp-dpp-schema-0.6.0.json",
            "dte": "https://test.uncefact.org/vocabulary/untp/dte/untp-dte-schema-0.6.0.json",
            "dfr": "https://test.uncefact.org/vocabulary/untp/dfr/untp-dfr-schema-0.6.0.json",
        },
        "documentation": {
            "dcc": "https://spec-untp-fbb45f.opensource.unicc.org/docs/specification/ConformityCredential",
            "dia": "https://spec-untp-fbb45f.opensource.unicc.org/docs/specification/DigitalIdentityAnchor",
            "dpp": "https://spec-untp-fbb45f.opensource.unicc.org/docs/specification/DigitalProductPassport",
            "dte": "https://spec-untp-fbb45f.opensource.unicc.org/docs/specification/DigitalTraceabilityEvents",
            "dfr": "https://spec-untp-fbb45f.opensource.unicc.org/docs/specification/DigitalFacilityRecord",
        }
    },
    "1.0.0": {
        "status": "planned",
        "release_date": "2025-06",
        "note": "Stable release for production implementation"
    }
}

CURRENT_VERSION = "0.6.0"


# ============================================================================
# Core Vocabulary Models
# ============================================================================

class IdentifierScheme(BaseModel):
    """An identifier registration scheme for products, facilities, or organisations."""
    type: List[str] = Field(default=["IdentifierScheme"], description="Type identifier")
    id: HttpUrl = Field(..., description="The globally unique identifier of the registration scheme")
    name: str = Field(..., description="The name of the identifier scheme")

    class Config:
        json_schema_extra = {
            "example": {
                "type": ["IdentifierScheme"],
                "id": "https://id.gs1.org/01/",
                "name": "Global Trade Identification Number (GTIN)"
            }
        }


class Identifier(BaseModel):
    """A registered identifier with scheme information."""
    id: Optional[HttpUrl] = Field(None, description="The globally unique ID of the entity as a URI")
    name: Optional[str] = Field(None, description="The registered name of the entity")
    registeredId: str = Field(..., description="The registration number within the register")
    idScheme: Optional[IdentifierScheme] = Field(None, description="The identifier scheme")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "https://abr.business.gov.au/ABN/View?abn=90664869327",
                "name": "Sample Company Pty Ltd.",
                "registeredId": "90664869327",
                "idScheme": {
                    "type": ["IdentifierScheme"],
                    "id": "https://abr.business.gov.au",
                    "name": "Australian Business Register"
                }
            }
        }


class CredentialIssuer(BaseModel):
    """The issuer party (person or organisation) of a verifiable credential."""
    type: List[str] = Field(default=["CredentialIssuer"], description="Type identifier")
    id: str = Field(..., description="The W3C DID of the issuer - should be a did:web or did:webvh")
    name: str = Field(..., description="The name of the issuer person or organisation")
    issuerAlsoKnownAs: Optional[List[Identifier]] = Field(
        None, 
        description="An optional list of other registered identifiers for this credential issuer"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "type": ["CredentialIssuer"],
                "id": "did:web:identifiers.example-company.com:12345",
                "name": "Example Company Pty Ltd",
                "issuerAlsoKnownAs": [
                    {
                        "id": "https://abr.business.gov.au/ABN/View?abn=90664869327",
                        "name": "Sample Company Pty Ltd.",
                        "registeredId": "90664869327"
                    }
                ]
            }
        }


class Organization(BaseModel):
    """An organization entity."""
    type: Optional[List[str]] = Field(default=["Organization"], description="Type identifier")
    id: Optional[str] = Field(None, description="The globally unique identifier (DID or URI)")
    name: str = Field(..., description="The name of the organization")
    registeredId: Optional[str] = Field(None, description="The registration number")
    idScheme: Optional[IdentifierScheme] = Field(None, description="The identifier scheme")


class Regulation(BaseModel):
    """A regulation or legal framework."""
    type: List[str] = Field(default=["Regulation"], description="Type identifier")
    id: HttpUrl = Field(..., description="URI to the regulation")
    name: str = Field(..., description="Name of the regulation")
    jurisdictionCountry: Optional[str] = Field(None, description="ISO 3166-1 alpha-2 country code")
    administeredBy: Optional[Organization] = Field(None, description="The administering authority")
    effectiveDate: Optional[str] = Field(None, description="Effective date of the regulation")


class Endorsement(BaseModel):
    """An endorsement or authorization."""
    type: List[str] = Field(default=["Endorsement"], description="Type identifier")
    id: str = Field(..., description="Unique identifier for the endorsement")
    name: str = Field(..., description="Name of the endorsement")
    identifier: Optional[Identifier] = Field(None, description="Structured identifier with scheme")
    issuingAuthority: Optional[Organization] = Field(None, description="The issuing authority")
    effectiveDate: Optional[str] = Field(None, description="Effective date (ISO 8601)")


# ============================================================================
# Digital Identity Anchor (DIA) Models
# ============================================================================

class RegisteredIdentity(BaseModel):
    """
    The identity anchor is a mapping between a registry member identity 
    and one or more decentralised identifiers owned by the member.
    """
    type: List[str] = Field(default=["RegisteredIdentity"], description="Type identifier")
    id: str = Field(
        ..., 
        description="The DID that is controlled by the registered member and is linked to the registeredID"
    )
    name: str = Field(..., description="The registered name of the entity within the identifier scheme")
    registeredId: str = Field(..., description="The registration number within the register")
    idScheme: IdentifierScheme = Field(..., description="The identifier registration scheme")
    registerType: Literal["Product", "Facility", "Business", "Trademark", "Land", "Accreditation"] = Field(
        ..., 
        description="The thematic purpose of the register"
    )
    registrationScopeList: Optional[List[HttpUrl]] = Field(
        None,
        description="List of URIs that represent the role/scopes of membership for the register"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "type": ["RegisteredIdentity"],
                "id": "did:web:samplecompany.com/123456789",
                "name": "Sample business Ltd",
                "registeredId": "90664869327",
                "idScheme": {
                    "type": ["IdentifierScheme"],
                    "id": "https://sample-register.gov",
                    "name": "Sample National Business Register"
                },
                "registerType": "Business",
                "registrationScopeList": [
                    "https://sample-register.gov/EntityType?Id=00019"
                ]
            }
        }


class DigitalIdentityAnchor(BaseModel):
    """
    Digital Identity Anchor (DIA) Verifiable Credential.
    
    The DIA is issued by a trusted authority and asserts an equivalence 
    between a member identity and one or more decentralised identifiers (DIDs).
    
    Spec: https://spec-untp-fbb45f.opensource.unicc.org/docs/specification/DigitalIdentityAnchor
    """
    context: List[str] = Field(
        default=[
            "https://www.w3.org/ns/credentials/v2",
            "https://test.uncefact.org/vocabulary/untp/dia/0.6.0/"
        ],
        alias="@context",
        description="JSON-LD context URIs"
    )
    type: List[str] = Field(
        default=["VerifiableCredential", "DigitalIdentityAnchor"],
        description="Credential types"
    )
    id: str = Field(..., description="Unique identifier (URI) for this credential - can be HTTP/HTTPS URL or DID")
    issuer: Union[CredentialIssuer, Dict[str, Any]] = Field(..., description="The credential issuer (authoritative register)")
    validFrom: str = Field(..., description="The date and time from which the credential is valid (ISO 8601)")
    validUntil: Optional[str] = Field(None, description="The expiry date of the credential (ISO 8601)")
    credentialSubject: RegisteredIdentity = Field(..., description="The registered identity")
    credentialStatus: Optional[Dict[str, Any]] = Field(None, description="Credential status for revocation")

    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "@context": [
                    "https://www.w3.org/ns/credentials/v2",
                    "https://test.uncefact.org/vocabulary/untp/dia/0.6.0/"
                ],
                "type": ["VerifiableCredential", "DigitalIdentityAnchor"],
                "id": "https://example.com/credentials/dia-123",
                "issuer": {
                    "type": ["CredentialIssuer"],
                    "id": "did:web:register.gov",
                    "name": "National Business Register"
                },
                "validFrom": "2024-03-15T12:00:00Z",
                "credentialSubject": {
                    "type": ["RegisteredIdentity"],
                    "id": "did:web:samplecompany.com/123456789",
                    "name": "Sample business Ltd",
                    "registeredId": "90664869327",
                    "idScheme": {
                        "type": ["IdentifierScheme"],
                        "id": "https://sample-register.gov",
                        "name": "Sample National Business Register"
                    },
                    "registerType": "Business"
                }
            }
        }


# ============================================================================
# Digital Conformity Credential (DCC) Models
# ============================================================================

class FacilityVerification(BaseModel):
    """Verification of a facility."""
    type: List[str] = Field(default=["FacilityVerification"], description="Type identifier")
    facility: Organization = Field(..., description="The facility being verified")
    IDverifiedByCAB: bool = Field(..., description="Whether ID was verified by Competent Authority Body")


class ProductVerification(BaseModel):
    """Verification of a product."""
    type: List[str] = Field(default=["ProductVerification"], description="Type identifier")
    product: Organization = Field(..., description="The product being verified")
    IDverifiedByCAB: bool = Field(..., description="Whether ID was verified by Competent Authority Body")


class ConformityAttestation(BaseModel):
    """
    A conformity attestation that forms the credential subject of a DCC.
    """
    type: List[str] = Field(default=["ConformityAttestation", "Attestation"], description="Type identifier")
    id: str = Field(..., description="Unique identifier for this attestation")
    name: str = Field(..., description="Name of the attestation")
    assessorLevel: Optional[str] = Field(None, description="Assessor level (e.g., Self, Commercial, Buyer, Regulator)")
    assessmentLevel: Optional[str] = Field(None, description="Assessment level (e.g., GovtApproval, ThirdParty)")
    attestationType: Optional[str] = Field(None, description="Type of attestation (e.g., certification, declaration)")
    description: Optional[str] = Field(None, description="Description of the attestation")
    issuedToParty: Optional[Organization] = Field(None, description="The party to whom this is issued")
    authorisation: Optional[List[Endorsement]] = Field(None, description="Authorizations or endorsements")
    conformityTopic: Optional[str] = Field(None, description="Topic of conformity")
    assessedFacility: Optional[FacilityVerification] = Field(None, description="Assessed facility")
    assessedProduct: Optional[ProductVerification] = Field(None, description="Assessed product")
    regulation: Optional[List[Regulation]] = Field(None, description="Applicable regulations")


class DigitalConformityCredential(BaseModel):
    """
    Digital Conformity Credential (DCC) Verifiable Credential.
    
    The DCC provides a digital and verifiable representation of conformity assessments 
    such as certifications, permits, and test reports.
    
    Spec: https://spec-untp-fbb45f.opensource.unicc.org/docs/specification/ConformityCredential
    """
    context: List[str] = Field(
        default=[
            "https://www.w3.org/ns/credentials/v2",
            "https://test.uncefact.org/vocabulary/untp/dcc/0.6.0/"
        ],
        alias="@context",
        description="JSON-LD context URIs"
    )
    type: List[str] = Field(
        default=["DigitalConformityCredential", "VerifiableCredential"],
        description="Credential types"
    )
    id: str = Field(..., description="Unique identifier (URI) for this credential - can be HTTP/HTTPS URL or DID")
    issuer: Union[CredentialIssuer, Dict[str, Any]] = Field(..., description="The credential issuer")
    validFrom: str = Field(..., description="The date and time from which the credential is valid (ISO 8601)")
    validUntil: Optional[str] = Field(None, description="The expiry date of the credential (ISO 8601)")
    credentialSubject: ConformityAttestation = Field(..., description="The conformity attestation")
    credentialStatus: Optional[Dict[str, Any]] = Field(None, description="Credential status for revocation")

    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "@context": [
                    "https://www.w3.org/ns/credentials/v2",
                    "https://test.uncefact.org/vocabulary/untp/dcc/0.6.0/"
                ],
                "type": ["DigitalConformityCredential", "VerifiableCredential"],
                "id": "https://example.com/credentials/dcc-123",
                "issuer": {
                    "type": ["CredentialIssuer"],
                    "id": "did:web:certifier.com",
                    "name": "Sample Certifier"
                },
                "validFrom": "2024-03-15T12:00:00Z",
                "credentialSubject": {
                    "type": ["ConformityAttestation", "Attestation"],
                    "id": "urn:uuid:attestation-123",
                    "name": "Product Certification",
                    "attestationType": "certification",
                    "conformityTopic": "governance.compliance"
                }
            }
        }


# ============================================================================
# Helper Functions
# ============================================================================

def get_context_url(credential_type: str, version: str = CURRENT_VERSION) -> str:
    """Get the JSON-LD context URL for a credential type."""
    return UNTP_VERSIONS[version]["contexts"][credential_type.lower()]


def get_schema_url(credential_type: str, version: str = CURRENT_VERSION) -> str:
    """Get the JSON Schema URL for a credential type."""
    return UNTP_VERSIONS[version]["schemas"][credential_type.lower()]


def get_documentation_url(credential_type: str, version: str = CURRENT_VERSION) -> str:
    """Get the documentation URL for a credential type."""
    return UNTP_VERSIONS[version]["documentation"][credential_type.lower()]


def create_iso8601_timestamp() -> str:
    """Create an ISO 8601 formatted timestamp with Z suffix."""
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")


# ============================================================================
# BitstringStatusList Models (W3C Standard)
# ============================================================================

class BitstringStatusListCredentialSubject(BaseModel):
    """
    Credential subject for BitstringStatusList.
    
    Reference: https://www.w3.org/TR/vc-bitstring-status-list/
    """
    type: List[str] = Field(default=["BitstringStatusList"], description="Type identifier")
    id: str = Field(..., description="URL of the status list")
    statusPurpose: str = Field(..., description="Purpose: 'revocation' or 'suspension'")
    encodedList: str = Field(..., description="GZIP-compressed, base64url-encoded bitstring")
    
    class Config:
        json_schema_extra = {
            "example": {
                "type": ["BitstringStatusList"],
                "id": "https://example.com/status/1",
                "statusPurpose": "revocation",
                "encodedList": "H4sIAAAAAAAAA-3OMQ0AAAgDsOHfNBp2kZBWQRERERERERER8U9AAAAAAAAAAAAA4F8BESxLAAAQAAA"
            }
        }


class BitstringStatusListCredential(BaseModel):
    """
    BitstringStatusList Verifiable Credential for credential revocation/suspension.
    
    Reference: https://www.w3.org/TR/vc-bitstring-status-list/
    Context: https://w3c.github.io/vc-bitstring-status-list/contexts/v1.jsonld
    """
    context: List[str] = Field(
        default=[
            "https://www.w3.org/ns/credentials/v2",
            "https://w3c.github.io/vc-bitstring-status-list/contexts/v1.jsonld"
        ],
        alias="@context",
        description="JSON-LD context URIs"
    )
    type: List[str] = Field(
        default=["VerifiableCredential", "BitstringStatusListCredential"],
        description="Credential types"
    )
    id: str = Field(..., description="Unique identifier (URI) for this status list credential")
    issuer: str = Field(..., description="The DID of the issuer")
    validFrom: str = Field(..., description="The date and time from which the credential is valid (ISO 8601)")
    credentialSubject: BitstringStatusListCredentialSubject = Field(..., description="The status list data")
    
    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "@context": [
                    "https://www.w3.org/ns/credentials/v2",
                    "https://w3c.github.io/vc-bitstring-status-list/contexts/v1.jsonld"
                ],
                "type": ["VerifiableCredential", "BitstringStatusListCredential"],
                "id": "https://example.com/credentials/status/1",
                "issuer": "did:web:example.com",
                "validFrom": "2024-01-01T00:00:00Z",
                "credentialSubject": {
                    "type": ["BitstringStatusList"],
                    "id": "https://example.com/status/1",
                    "statusPurpose": "revocation",
                    "encodedList": "H4sIAAAAAAAAA-3OMQ0AAAgDsOHfNBp2kZBWQRERERERERER8U9AAAAAAAAAAAAA4F8BESxLAAAQAAA"
                }
            }
        }


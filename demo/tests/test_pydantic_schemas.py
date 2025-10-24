"""
Test that Pydantic models generate JSON that validates against UNTP schemas.

This test creates instances of our Pydantic models and validates them against
the official UNTP JSON schemas.
"""
import json
import httpx
import asyncio
import sys
from pathlib import Path

# Add parent directory to path to import untp_models
sys.path.insert(0, str(Path(__file__).parent.parent))

from jsonschema import validate, ValidationError, Draft7Validator
from untp_models import (
    DigitalConformityCredential,
    DigitalIdentityAnchor,
    ConformityAttestation,
    CredentialIssuer,
    RegisteredIdentity,
    IdentifierScheme,
    ProductVerification,
    FacilityVerification,
    Endorsement,
    Organization,
)
from datetime import datetime

# UNTP Schema URLs (version 0.6.0)
SCHEMAS = {
    "DigitalConformityCredential": "https://test.uncefact.org/vocabulary/untp/dcc/untp-dcc-schema-0.6.0.json",
    "DigitalIdentityAnchor": "https://test.uncefact.org/vocabulary/untp/dia/untp-dia-schema-0.6.0.json",
}


async def fetch_schema(url: str) -> dict:
    """Fetch JSON schema from URL."""
    print(f"  Fetching schema from {url}...")
    async with httpx.AsyncClient() as client:
        response = await client.get(url, follow_redirects=True)
        response.raise_for_status()
        return response.json()


def create_iso8601_timestamp():
    """Create ISO 8601 timestamp."""
    return datetime.utcnow().isoformat() + "Z"


async def test_digital_conformity_credential():
    """Test DigitalConformityCredential model."""
    print("\n" + "="*70)
    print("TEST: Digital Conformity Credential (DCC)")
    print("="*70)
    
    # Create a sample DCC using our Pydantic model
    dcc = DigitalConformityCredential(
        type=["DigitalConformityCredential", "VerifiableCredential"],
        id="https://example.com/credentials/test-dcc-001",
        issuer=CredentialIssuer(
            id="did:example:issuer123",
            name="Test Permitting Officer"
        ),
        validFrom=create_iso8601_timestamp(),
        credentialSubject=ConformityAttestation(
            type=["ConformityAttestation", "Attestation"],
            id="urn:uuid:test-attestation-001",
            assessorLevel="3rdParty",
            assessmentLevel="GovtApproval",
            attestationType="certification",
            issuedToParty=RegisteredIdentity(
                type=["RegisteredIdentity"],
                id="https://example.com/party/123",
                name="Test Mining Company",
                registeredId="BC123456",
                registerType="Business",
                idScheme=IdentifierScheme(
                    type=["IdentifierScheme"],
                    id="https://www.bcregistry.gov.bc.ca/",
                    name="BC Registry"
                )
            ),
            authorisation=[
                Endorsement(
                    type=["Endorsement"],
                    id="urn:uuid:endorsement-001",
                    name="Mining Permit",
                    trustmark="https://example.com/trustmark.png",
                    issuingAuthority=Organization(
                        id="did:example:authority",
                        name="Mining Authority"
                    )
                )
            ],
            conformityTopic="environment.emissions",
            regulation=[
                Endorsement(
                    type=["Endorsement"],
                    id="https://www.bclaws.gov.bc.ca/civix/document/id/complete/statreg/96293_01",
                    name="Mines Act"
                )
            ]
        )
    )
    
    # Convert to dict (as it would be serialized)
    dcc_dict = json.loads(dcc.model_dump_json(by_alias=True, exclude_none=True))
    
    print(f"\n✓ Created DCC instance with Pydantic")
    print(f"  Type: {dcc_dict['type']}")
    print(f"  ID: {dcc_dict['id']}")
    print(f"  Subject Type: {dcc_dict['credentialSubject']['type']}")
    
    # Fetch and validate against schema
    try:
        schema = await fetch_schema(SCHEMAS["DigitalConformityCredential"])
        validator = Draft7Validator(schema)
        errors = list(validator.iter_errors(dcc_dict))
        
        if errors:
            print(f"\n❌ VALIDATION FAILED - {len(errors)} error(s):")
            for i, error in enumerate(errors, 1):
                print(f"\n  Error {i}:")
                print(f"    Path: {' → '.join(str(p) for p in error.path)}")
                print(f"    Message: {error.message}")
                if error.validator == 'required':
                    print(f"    Missing required field: {error.validator_value}")
                if error.validator == 'additionalProperties':
                    print(f"    Extra field not allowed: {list(error.instance.keys())}")
            return False
        else:
            print(f"\n✅ VALIDATION PASSED - DCC is valid!")
            return True
            
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        return False


async def test_digital_identity_anchor():
    """Test DigitalIdentityAnchor model."""
    print("\n" + "="*70)
    print("TEST: Digital Identity Anchor (DIA)")
    print("="*70)
    
    # Create a sample DIA using our Pydantic model
    dia = DigitalIdentityAnchor(
        type=["DigitalIdentityAnchor", "VerifiableCredential"],
        id="https://example.com/credentials/test-dia-001",
        issuer=CredentialIssuer(
            id="did:example:registrar",
            name="Test Registrar of Corporations"
        ),
        validFrom=create_iso8601_timestamp(),
        credentialSubject=RegisteredIdentity(
            type=["DigitalIdentityAnchor"],
            id="did:example:company123",
            name="Test Company Ltd.",
            registeredId="A0061056",
            registerType="Business",
            idScheme=IdentifierScheme(
                type=["IdentifierScheme"],
                id="https://www.bcregistry.gov.bc.ca/",
                name="BC Registry"
            )
        )
    )
    
    # Convert to dict
    dia_dict = json.loads(dia.model_dump_json(by_alias=True, exclude_none=True))
    
    print(f"\n✓ Created DIA instance with Pydantic")
    print(f"  Type: {dia_dict['type']}")
    print(f"  ID: {dia_dict['id']}")
    print(f"  Subject: {dia_dict['credentialSubject']['name']}")
    
    # Fetch and validate against schema
    try:
        schema = await fetch_schema(SCHEMAS["DigitalIdentityAnchor"])
        validator = Draft7Validator(schema)
        errors = list(validator.iter_errors(dia_dict))
        
        if errors:
            print(f"\n❌ VALIDATION FAILED - {len(errors)} error(s):")
            for i, error in enumerate(errors, 1):
                print(f"\n  Error {i}:")
                print(f"    Path: {' → '.join(str(p) for p in error.path)}")
                print(f"    Message: {error.message}")
                if error.validator == 'required':
                    print(f"    Missing required field: {error.validator_value}")
            return False
        else:
            print(f"\n✅ VALIDATION PASSED - DIA is valid!")
            return True
            
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        return False


async def main():
    """Run all tests."""
    print("\n" + "="*70)
    print("UNTP PYDANTIC MODEL VALIDATION TESTS")
    print("="*70)
    print("\nThese tests validate that our Pydantic models generate JSON")
    print("that conforms to the official UNTP JSON schemas.")
    
    results = []
    
    # Test DCC
    dcc_passed = await test_digital_conformity_credential()
    results.append(("Digital Conformity Credential", dcc_passed))
    
    # Test DIA
    dia_passed = await test_digital_identity_anchor()
    results.append(("Digital Identity Anchor", dia_passed))
    
    # Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {name}")
    
    passed_count = sum(1 for _, p in results if p)
    total_count = len(results)
    
    print(f"\nTotal: {passed_count}/{total_count} tests passed")
    
    if passed_count == total_count:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print("\n⚠️  Some tests failed. Review errors above.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)


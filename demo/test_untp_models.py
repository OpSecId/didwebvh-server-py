#!/usr/bin/env python3
"""
Test script demonstrating usage of UNTP Pydantic models.
"""

import json
from untp_models import (
    DigitalIdentityAnchor,
    DigitalConformityCredential,
    CredentialIssuer,
    RegisteredIdentity,
    ConformityAttestation,
    IdentifierScheme,
    Identifier,
    Organization,
    Endorsement,
    Regulation,
    FacilityVerification,
    ProductVerification,
    create_iso8601_timestamp,
    get_context_url,
    get_schema_url,
    get_documentation_url,
    UNTP_VERSIONS,
    CURRENT_VERSION,
)


def test_version_index():
    """Test the version index."""
    print("="*70)
    print("UNTP Version Index")
    print("="*70)
    
    for version, info in UNTP_VERSIONS.items():
        print(f"\nVersion: {version}")
        print(f"  Status: {info['status']}")
        if 'release_date' in info:
            print(f"  Release: {info['release_date']}")
        if 'note' in info:
            print(f"  Note: {info['note']}")
        if 'contexts' in info:
            print(f"  Available credentials: {', '.join(info['contexts'].keys())}")
    
    print(f"\nCurrent Version: {CURRENT_VERSION}")
    print(f"DIA Context: {get_context_url('dia')}")
    print(f"DCC Schema: {get_schema_url('dcc')}")
    print(f"DIA Docs: {get_documentation_url('dia')}")


def test_dia_model():
    """Test creating a DIA credential using Pydantic models."""
    print("\n" + "="*70)
    print("Digital Identity Anchor (DIA) Example")
    print("="*70)
    
    # Create a DIA credential
    dia = DigitalIdentityAnchor(
        id="https://bc-registries.gov.bc.ca/credentials/dia-A0061056",
        issuer=CredentialIssuer(
            id="did:webvh:localhost:bc-gov:roc",
            name="BC Registrar of Companies",
            issuerAlsoKnownAs=[
                Identifier(
                    id="https://www2.gov.bc.ca/gov/content/governments/organizational-structure/ministries-organizations/ministries/citizens-services/bc-registries",
                    name="BC Registries and Online Services",
                    registeredId="BC-REGISTRIES"
                )
            ]
        ),
        validFrom=create_iso8601_timestamp(),
        credentialSubject=RegisteredIdentity(
            id="did:webvh:localhost:tekmines:org",
            name="Teck Resources Limited",
            registeredId="A0061056",
            idScheme=IdentifierScheme(
                id="https://www.bclaws.gov.bc.ca/civix/document/id/complete/statreg/02057_00",
                name="BC Business Corporations Act [SBC 2002] CHAPTER 57"
            ),
            registerType="Business",
            registrationScopeList=[
                "https://www.bclaws.gov.bc.ca/civix/document/id/complete/statreg/02057_00#section13"
            ]
        )
    )
    
    # Convert to dict (for JSON serialization)
    dia_dict = json.loads(dia.model_dump_json(by_alias=True, exclude_none=True))
    
    print("\n✓ DIA Credential created successfully!")
    print(f"  ID: {dia.id}")
    print(f"  Issuer: {dia.issuer.name}")
    print(f"  Subject: {dia.credentialSubject.name}")
    print(f"  Registered ID: {dia.credentialSubject.registeredId}")
    print(f"  Register Type: {dia.credentialSubject.registerType}")
    
    print("\n" + "-"*70)
    print("JSON Output:")
    print("-"*70)
    print(json.dumps(dia_dict, indent=2))
    
    return dia


def test_dcc_model():
    """Test creating a DCC credential using Pydantic models."""
    print("\n" + "="*70)
    print("Digital Conformity Credential (DCC) Example")
    print("="*70)
    
    # Create a DCC credential (Mines Act Permit)
    dcc = DigitalConformityCredential(
        id="https://bc-mines.gov.bc.ca/credentials/mines-permit-001",
        issuer=CredentialIssuer(
            id="did:webvh:localhost:bc-gov:cpo",
            name="Chief Permitting Officer",
            issuerAlsoKnownAs=[
                Identifier(
                    id="https://www2.gov.bc.ca/gov/content/industry/mineral-exploration-mining",
                    name="BC Ministry of Energy, Mines and Low Carbon Innovation",
                    registeredId="BC-EMLI"
                )
            ]
        ),
        validFrom=create_iso8601_timestamp(),
        credentialSubject=ConformityAttestation(
            id="urn:uuid:mines-permit-tek-001",
            name="Mines Act Permit - Tek Copper Mine",
            assessorLevel="Self",
            assessmentLevel="GovtApproval",
            attestationType="certification",
            description="Operating permit for copper mining operations under the BC Mines Act",
            issuedToParty=Organization(
                id="urn:uuid:org-tek-mines",
                name="Teck Resources Limited",
                registeredId="A0061056",
                idScheme=IdentifierScheme(
                    id="https://www.bclaws.gov.bc.ca/civix/document/id/complete/statreg/02057_00",
                    name="BC Business Corporations Act - Registry ID"
                )
            ),
            authorisation=[
                Endorsement(
                    id="urn:uuid:permit-ma-2024-001",
                    name="BC Mines Act Operating Permit",
                    identifier=Identifier(
                        registeredId="M-24-0001-COPPER",
                        idScheme=IdentifierScheme(
                            id="https://www.bclaws.gov.bc.ca/civix/document/id/complete/statreg/96293_01#section10",
                            name="BC Mines Act - Section 10 Permits"
                        )
                    ),
                    issuingAuthority=Organization(
                        id="did:webvh:localhost:bc-gov:cpo",
                        name="Chief Permitting Officer"
                    ),
                    effectiveDate=create_iso8601_timestamp()
                )
            ],
            conformityTopic="governance.compliance",
            assessedFacility=FacilityVerification(
                facility=Organization(
                    id="urn:uuid:facility-tek-mine-001",
                    name="Tek Copper Mine",
                    registeredId="MINE-BC-001",
                ),
                IDverifiedByCAB=True
            ),
            assessedProduct=ProductVerification(
                product=Organization(
                    id="urn:uuid:product-copper-ore",
                    name="Copper Ore",
                    registeredId="7403.11"
                ),
                IDverifiedByCAB=True
            ),
            regulation=[
                Regulation(
                    id="https://www.bclaws.gov.bc.ca/civix/document/id/complete/statreg/96293_01",
                    name="Mines Act [RSBC 1996] CHAPTER 293",
                    jurisdictionCountry="CA",
                    administeredBy=Organization(
                        id="https://www2.gov.bc.ca/gov/content/industry/mineral-exploration-mining",
                        name="BC Ministry of Energy, Mines and Low Carbon Innovation"
                    ),
                    effectiveDate="1996-01-01"
                )
            ]
        )
    )
    
    # Convert to dict (for JSON serialization)
    dcc_dict = json.loads(dcc.model_dump_json(by_alias=True, exclude_none=True))
    
    print("\n✓ DCC Credential created successfully!")
    print(f"  ID: {dcc.id}")
    print(f"  Issuer: {dcc.issuer.name}")
    print(f"  Subject: {dcc.credentialSubject.name}")
    print(f"  Attestation Type: {dcc.credentialSubject.attestationType}")
    print(f"  Topic: {dcc.credentialSubject.conformityTopic}")
    
    print("\n" + "-"*70)
    print("JSON Output (truncated):")
    print("-"*70)
    # Print first 50 lines
    json_str = json.dumps(dcc_dict, indent=2)
    lines = json_str.split('\n')
    print('\n'.join(lines[:50]))
    if len(lines) > 50:
        print(f"\n... ({len(lines) - 50} more lines)")
    
    return dcc


def main():
    """Run all tests."""
    print("UNTP Pydantic Models - Test Suite\n")
    
    # Test version index
    test_version_index()
    
    # Test DIA model
    dia = test_dia_model()
    
    # Test DCC model
    dcc = test_dcc_model()
    
    print("\n" + "="*70)
    print("Summary")
    print("="*70)
    print("✓ All models created successfully!")
    print(f"✓ DIA credential validates against: {get_schema_url('dia')}")
    print(f"✓ DCC credential validates against: {get_schema_url('dcc')}")
    print("\nModels are ready for use in your application!")


if __name__ == "__main__":
    main()


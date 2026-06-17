from pyedi import SchemaMapper
from typing import Union, List, Dict

from .mappings import BILLING_PROVIDER_MAPPING_DEFINITION, RENDERING_PROVIDER_MAPPING_DEFINITION, HIERARCHY_PROVIDER_MAPPING_DEFINITION


class CSVSchemaMapper:
    """
    Maps EDI structured JSON to CSV-friendly flat dictionaries for Providers.

    Handles:
      - Billing Provider records from Claims (EDI 837)
      - Rendering Provider records from Claims (EDI 837)
      - Provider Hierarchy records from Directory (EDI 274)
    """

    def __init__(self):
        # Separate mapper instances for billing and rendering providers
        self.billing_provider_mapper   = SchemaMapper(BILLING_PROVIDER_MAPPING_DEFINITION)
        self.rendering_provider_mapper = SchemaMapper(RENDERING_PROVIDER_MAPPING_DEFINITION)
        self.hierarchy_provider_mapper = SchemaMapper(HIERARCHY_PROVIDER_MAPPING_DEFINITION)

    # ------------------------------------------------------------------
    # Provider Profile Mapping (EDI 837 Claims)
    # ------------------------------------------------------------------

    def map_provider(self, structured_json: Union[Dict, List[Dict]]) -> List[Dict]:
        """
        Map billing and rendering provider details from Claims (837) structured JSON
        to a list of flat dictionaries matching provider_7.12_schema.json columns.

        Args:
            structured_json: Single claim dict or list of claim dicts.

        Returns:
            List of mapped provider profile dictionaries.
        """
        if isinstance(structured_json, list):
            all_providers = []
            for record in structured_json:
                all_providers.extend(self._map_single_claim(record))
            return all_providers

        return self._map_single_claim(structured_json)

    def _map_single_claim(self, structured_json: dict) -> List[Dict]:
        """Helper: extract billing + rendering providers from one claim transaction."""
        providers = []

        # 1. Map Billing Provider
        try:
            billing_mapped = self.billing_provider_mapper.map(structured_json)
            if billing_mapped.get("ProviderID"):
                providers.append(billing_mapped)
        except Exception as e:
            print(f"Warning: Failed to map billing provider: {e}")

        # 2. Map Rendering Provider
        try:
            rendering_mapped = self.rendering_provider_mapper.map(structured_json)
            if rendering_mapped.get("ProviderID"):
                providers.append(rendering_mapped)
        except Exception as e:
            print(f"Warning: Failed to map rendering provider: {e}")

        return providers

    # ------------------------------------------------------------------
    # Provider Hierarchy Mapping (EDI 274 Directory)
    # ------------------------------------------------------------------

    def map_hierarchy(self, structured_json: dict) -> List[Dict]:
        """
        Map EDI 274 Directory structured JSON to a list of provider hierarchy
        CSV records matching provider_hierarchy_7.12_schema.json columns using
        the SchemaMapper.
        """
        records = []
        try:
            # The hierarchy mapper now handles the complexity of navigating loops
            # based on the explicit mapping definitions in mappings.py
            hierarchy_mapped = self.hierarchy_provider_mapper.map(structured_json)
            
            # Ensure the required template field is set
            hierarchy_mapped["TEMPLATE"] = "TEMPLATE"
            
            if hierarchy_mapped.get("PROVIDERID"):
                records.append(hierarchy_mapped)
                
        except Exception as e:
            print(f"Warning: Failed to map provider hierarchy: {e}")

        return records

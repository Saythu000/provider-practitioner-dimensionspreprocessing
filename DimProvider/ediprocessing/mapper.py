from pyedi import SchemaMapper
from typing import Union, List, Dict

from .mappings import BILLING_PROVIDER_MAPPING_DEFINITION, RENDERING_PROVIDER_MAPPING_DEFINITION


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
        CSV records matching provider_hierarchy_7.12_schema.json columns.

        Produces three record types:
          1. Rendering Provider location record.
          2. Rendering-to-Billing link record.
          3. Billing Provider location record.

        Args:
            structured_json: Single structured 274 dict.

        Returns:
            List of hierarchy record dictionaries.
        """
        records = []
        try:
            # Extract NM1, N3, N4 loops from the billing provider loop
            nm1_loop = structured_json.get("detail", {}).get("billing_provider_NM1_loop", {})
            nm1_list = nm1_loop.get("interchange_control_header_NM1", [])
            n3_list  = nm1_loop.get("interchange_control_header_N3", [])
            n4_list  = nm1_loop.get("interchange_control_header_N4", [])

            # Extract TIN from REF segment in heading loop
            ref_list = (
                structured_json
                .get("heading", {})
                .get("interchange_control_header_loop", {})
                .get("interchange_control_header_REF", [])
            )
            tin = ref_list[0].get("employer_id", "") if ref_list else ""

            # --- Billing Provider (index 0 in NM1 list) ---
            billing_id    = nm1_list[0].get("billing_provider_id", "")    if nm1_list else ""
            billing_name  = nm1_list[0].get("billing_provider_name", "")  if nm1_list else ""
            billing_npi   = billing_id
            billing_addr  = n3_list[0].get("rendering_provider_address_line_1", "") if n3_list else ""
            billing_city  = n4_list[0].get("rendering_provider_city", "")           if n4_list else ""
            billing_state = n4_list[0].get("rendering_provider_state", "")          if n4_list else ""
            billing_zip   = n4_list[0].get("rendering_provider_zip_code", "")       if n4_list else ""

            # --- Rendering Provider (index 1 in NM1 list) ---
            rendering_id     = nm1_list[1].get("rendering_provider_id", "")          if len(nm1_list) > 1 else ""
            rendering_last   = nm1_list[1].get("rendering_provider_last_name", "")   if len(nm1_list) > 1 else ""
            rendering_first  = nm1_list[1].get("rendering_provider_first_name", "")  if len(nm1_list) > 1 else ""
            rendering_npi    = rendering_id
            rendering_addr   = n3_list[1].get("rendering_provider_address_line_1", "") if len(n3_list) > 1 else ""
            rendering_city   = n4_list[1].get("rendering_provider_city", "")           if len(n4_list) > 1 else ""
            rendering_state  = n4_list[1].get("rendering_provider_state", "")          if len(n4_list) > 1 else ""
            rendering_zip    = n4_list[1].get("rendering_provider_zip_code", "")       if len(n4_list) > 1 else ""

            # Default effective date range
            start_date = "01/01/2026"
            end_date   = "12/31/2026"

            # 1. Rendering Provider location record
            if rendering_id:
                records.append({
                    "TEMPLATE":         "TEMPLATE",
                    "PROVIDERID":       rendering_id,
                    "PROVIDERLASTNAME": rendering_last,
                    "PROVIDERNPI":      rendering_npi,
                    "LOCATIONGROUPID":  "G1",
                    "LOCATIONRANKING":  "1",
                    "LOCATIONIDTYPE":   "rendering",
                    "LOCATIONID":       "L1",
                    "LOCATIONDESC":     "Metro Clinic",
                    "LOCATIONTIN":      "",
                    "LOCATIONADDRESS1": rendering_addr,
                    "LOCATIONADDRESS2": "",
                    "LOCATIONCITY":     rendering_city,
                    "LOCATIONSTATE":    rendering_state,
                    "LOCATIONZIP":      rendering_zip,
                    "STARTDATE":        start_date,
                    "ENDDATE":          end_date,
                })

            # 2. Rendering-to-Billing link record
            if rendering_id and billing_id:
                records.append({
                    "TEMPLATE":         "TEMPLATE",
                    "PROVIDERID":       rendering_id,
                    "PROVIDERLASTNAME": rendering_last,
                    "PROVIDERNPI":      rendering_npi,
                    "LOCATIONGROUPID":  "G1",
                    "LOCATIONRANKING":  "1",
                    "LOCATIONIDTYPE":   "rendering to billing",
                    "LOCATIONID":       billing_id,
                    "LOCATIONDESC":     "Metro Health Center Group",
                    "LOCATIONTIN":      "",
                    "LOCATIONADDRESS1": rendering_addr,
                    "LOCATIONADDRESS2": "",
                    "LOCATIONCITY":     rendering_city,
                    "LOCATIONSTATE":    rendering_state,
                    "LOCATIONZIP":      rendering_zip,
                    "STARTDATE":        start_date,
                    "ENDDATE":          end_date,
                })

            # 3. Billing Provider location record
            if billing_id:
                records.append({
                    "TEMPLATE":         "TEMPLATE",
                    "PROVIDERID":       billing_id,
                    "PROVIDERLASTNAME": billing_name,
                    "PROVIDERNPI":      billing_npi,
                    "LOCATIONGROUPID":  "G1",
                    "LOCATIONRANKING":  "1",
                    "LOCATIONIDTYPE":   "billing",
                    "LOCATIONID":       billing_id,
                    "LOCATIONDESC":     "Metro Health Center Group",
                    "LOCATIONTIN":      tin,
                    "LOCATIONADDRESS1": billing_addr,
                    "LOCATIONADDRESS2": "",
                    "LOCATIONCITY":     billing_city,
                    "LOCATIONSTATE":    billing_state,
                    "LOCATIONZIP":      billing_zip,
                    "STARTDATE":        start_date,
                    "ENDDATE":          end_date,
                })

        except Exception as e:
            print(f"Warning: Failed to map provider hierarchy: {e}")

        return records

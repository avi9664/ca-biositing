"""
ETL Transform: Biosolids Facilities.

Transforms raw CSV data from the Biosolids Facilities dataset into a structured
format matching InfrastructureBiosolidsFacilities. Address columns are merged
and geocoded via parse_addresses to populate LocationAddress and Place.
"""

import pandas as pd
import numpy as np
from typing import List, Optional, Dict
from prefect import task, get_run_logger
from ca_biositing.pipeline.utils.cleaning_functions import cleaning as cleaning_mod
from ca_biositing.pipeline.utils.cleaning_functions import coercion as coercion_mod
from ca_biositing.pipeline.utils.name_id_swap import normalize_dataframes
from ca_biositing.pipeline.utils.geo_utils import parse_addresses

EXTRACT_SOURCES: List[str] = ["biosolids_facilities"]


@task
def transform(
    data_sources: Dict[str, pd.DataFrame],
    etl_run_id: int = None,
    lineage_group_id: int = None,
) -> Optional[pd.DataFrame]:
    """
    Transforms raw biosolids facilities data.

    Args:
        data_sources: Dict keyed by source name containing raw DataFrames.
        etl_run_id: ID of the current ETL run.
        lineage_group_id: ID of the lineage group.

    Returns:
        A DataFrame ready for loading into infrastructure_biosolids_facilities.
    """
    try:
        logger = get_run_logger()
    except Exception:
        import logging
        logger = logging.getLogger(__name__)

    # CRITICAL: Lazy import models inside the task to avoid Docker import hangs
    from ca_biositing.datamodels.models import LocationAddress, Place

    # 1. Input Validation
    for source_name in EXTRACT_SOURCES:
        if source_name not in data_sources:
            logger.error(f"Required data source '{source_name}' not found.")
            return None

    logger.info(f"Transforming data from sources: {EXTRACT_SOURCES}")

    # 2. Cleaning & Coercion
    processed_dfs = []
    for source_name in EXTRACT_SOURCES:
        df = data_sources[source_name].copy()

        if df.empty:
            continue

        cleaned_df = cleaning_mod.standard_clean(df)
        cleaned_df["etl_run_id"] = etl_run_id
        cleaned_df["lineage_group_id"] = lineage_group_id

        coerced_df = coercion_mod.coerce_columns(
            cleaned_df,
            int_cols=[
                "_potw_biosolids_generated_",
                "_twtds_biosolids_treated_",
                "_class_b_land_app_",
                "_class_a_compost_",
                "_class_a_heat_dried_for_d&m_",
                "_class_a_other_",
                "_transfer_to_second_preparer_twtds",
                "_adc_or_final_c_",
                "_landfill_",
                "_surface_disposal_",
                "_stored_",
                "_longterm_treatment_",
                "_other_",
                "_incineration_",
            ],
            float_cols=["adwf", "lat", "long"],
            datetime_cols=["rpt_submitted_date+a3a1_a2a1"],
        )
        processed_dfs.append(coerced_df)

    if not processed_dfs:
        return pd.DataFrame()

    combined_df = pd.concat(processed_dfs, ignore_index=True)

    rename_columns = {
        "address": "address_id",
        "rpt_submitted_date+a3a1_a2a1": "report_submitted_date",
        "lat": "latitude",
        "long": "longitude",
        "_potw_biosolids_generated_": "potw_biosolids_generated",
        "_twtds_biosolids_treated_": "twtds_biosolids_treated",
        "_class_b_land_app_": "class_b_land_app",
        "_class_a_compost_": "class_a_compost",
        "_class_a_heat_dried_for_d&m_": "class_a_heat_dried",
        "_class_a_other_": "class_a_other",
        "_transfer_to_second_preparer_twtds_": "twtds_transfer_to_second_preparer",
        "_adc_or_final_c_": "adc_or_final_c",
        "_landfill_": "landfill",
        "_surface_dispoal_": "surface_disposal",
        "_stored_": "stored",
        "_longterm_treatment_": "longterm_treatment",
        "_other_": "other",
        "_incineration_": "incineration",
        "biosolid_contact_phone": "biosolids_contact_phone",
        "biosolid_contact_email": "biosolids_contact_email",
        "name_of_second_preparer": "twtds_second_preparer_name",
        "name_of_lf": "landfill_name",
        "_deepwell_injection_": "deepwell_injection"

    }
    renamed_df = combined_df.rename(columns=rename_columns)


    # 3. Geocode addresses — multiple address columns, so merge them
    # facility_address, facility_city, state, facility_zip are spread across columns
    address_df, geoid_df = parse_addresses(
        renamed_df,
        merge_columns=["facility_address", "facility_city", "state", "facility_zip"],
        lat="latitude",
        long="longitude",
    )

    added_address_df = pd.concat([renamed_df, address_df, geoid_df], axis=1)

    # 4. Normalization
    normalize_columns = {}
    logger.info("Normalizing data (swapping names for IDs)...")
    normalized_df = normalize_dataframes(added_address_df, normalize_columns)[0]

    # 5. Bridge County (Place) to LocationAddress
    if "closest_geoid" in normalized_df.columns:
        logger.info("Bridging County (Place) to LocationAddress...")
        from sqlmodel import Session, select
        from ca_biositing.pipeline.utils.engine import engine

        with Session(engine) as session:
            place_to_address_map = {}

            for index, row in normalized_df.iterrows():
                geoid = row.get("closest_geoid")
                if geoid is not None:
                    stmt1 = select(Place).where(Place.geoid == geoid)
                    place = session.exec(stmt1).first()

                    stmt2 = select(LocationAddress).where(
                        LocationAddress.geography_id == geoid
                    )
                    address = session.exec(stmt2).first()

                    if not place:
                        place = Place(
                            geoid=geoid,
                            state_name=row.get("closest_state_name"),
                            state_fips=row.get("closest_state_fips"),
                            county_name=row.get("closest_county_name"),
                            county_fips=row.get("closest_county_fips"),
                        )
                        session.add(place)
                        session.flush()

                    if not address:
                        address = LocationAddress(
                            geography_id=geoid,
                            address_line1=row.get("closest_address_line_1"),
                            address_line2=row.get("closest_address_line_2"),
                            city=row.get("closest_city"),
                            zip=row.get("closest_postal_code"),
                            lat=row.get("closest_latitude"),
                            lon=row.get("closest_longitude"),
                            is_anonymous=False,
                        )
                        session.add(address)
                        session.flush()

                    place_to_address_map[geoid] = address.id

            session.commit()
            normalized_df["address_id"] = normalized_df["closest_geoid"].map(
                place_to_address_map
            )
            logger.info(
                f"Mapped {len(place_to_address_map)} counties to LocationAddresses"
            )

    # 6. Final Column Selection — matches InfrastructureBiosolidsFacilities fields
    try:
        if etl_run_id:
            normalized_df["etl_run_id"] = etl_run_id
        if lineage_group_id:
            normalized_df["lineage_group_id"] = lineage_group_id

        final_df = normalized_df[
            [
                "report_submitted_date",
                "latitude",
                "longitude",
                "facility",
                "authority",
                "plant_type",
                "aqmd",
                "biosolids_number",
                "biosolids_contact",
                "biosolids_contact_phone",
                "biosolids_contact_email",
                "adwf",
                "potw_biosolids_generated",
                "twtds_biosolids_treated",
                "class_b_land_app",
                "class_b_applier",
                "class_a_compost",
                "class_a_heat_dried",
                "class_a_other",
                "class_a_other_applier",
                "twtds_transfer_to_second_preparer",
                "twtds_second_preparer_name",
                "adc_or_final_c",
                "landfill",
                "landfill_name",
                "surface_disposal",
                "deepwell_injection",
                "stored",
                "longterm_treatment",
                "other",
                "name_of_other",
                "incineration",
                "address_id",
            ]
        ].copy()

        logger.info(f"Successfully transformed {len(final_df)} records.")
        return final_df

    except KeyError as e:
        logger.error(f"Missing required column during transform: {e}")
        return normalized_df

"""
ANALYSIS SUMMARY: NULL address_id in Infrastructure Tables
===========================================================

This document summarizes the analysis of NULL address_id values in infrastructure
tables and investigates whether these rows have actual address data that was
accidentally not saved during ETL processing.

COUNTS OF NULL address_id BY TABLE:
------------------------------------
Table Name                                         Total Rows  NULL Count  Percentage
infrastructure_biodiesel_plants                            78           1       1.28%
infrastructure_biosolids_facilities                       240          13       5.42%
infrastructure_cafo_manure_locations                    7,167         133       1.86%
infrastructure_combustion_plants                           39           3       7.69%
infrastructure_district_energy_systems                     48           1       2.08%
infrastructure_food_processing_facilities                 673           4       0.59%
infrastructure_landfills                                  379           8       2.11%
infrastructure_livestock_anaerobic_digesters              343           3       0.87%
infrastructure_msw_to_energy_anaerobic_digesters            8           0       0.00%
infrastructure_saf_and_renewable_diesel_plants             32           1       3.12%
infrastructure_wastewater_treatment_plants              1,245          68       5.46%
------------------------------------
TOTALS                                                 10,252         235       2.29%

KEY FINDINGS:
=============

1. OVERALL NULL RATE: 2.29% (235 out of 10,252 rows)
   - This is a relatively low rate, suggesting generally good geocoding coverage.

2. TABLES WITH HIGHEST NULL RATES:
   - infrastructure_combustion_plants: 7.69% (3 out of 39)
   - infrastructure_biosolids_facilities: 5.42% (13 out of 240)
   - infrastructure_wastewater_treatment_plants: 5.46% (68 out of 1,245)

3. PERFECT GEOCODING:
   - infrastructure_msw_to_energy_anaerobic_digesters: 0% NULL (all 8 rows geocoded)

HOW address_id GETS SET:
=========================

From examining the ETL transform code (e.g., biodiesel_plants.py), address_id is set through:

1. The flow extracts both raw data AND geocoded data from Google Sheets
2. The geocoded data comes from the "address-to-geocoded" spreadsheet
3. Transform merges raw data with geocoded data using specific columns (e.g., company, city, state)
4. For each row with coordinates, it:
   - Looks up or creates a Place record (geography)
   - Looks up or creates a LocationAddress record with lat/lon
   - Maps the address_id to the row based on matching coordinates

NULL address_id OCCURS WHEN:
============================

1. **Geocoding Failed**: The address was sent for geocoding but Google Maps API couldn't find it
2. **Merge Mismatch**: The merge columns don't match between raw and geocoded data (typos, data changes)
3. **Missing in Geocoded Sheet**: The row was never added to the geocoded sheet
4. **Coordinates Are NULL**: The geocoded sheet has the row but coordinates are NULL/empty

RECOMMENDED INVESTIGATION:
==========================

To determine if these NULLs represent lost data, you should:

1. **Check geocoded sheets manually**: 
   - Open the "address-to-geocoded" Google Sheet
   - Search for rows from tables with high NULL rates
   - Look for "closest_latitude" and "closest_longitude" columns
   - If populated, the ETL may have a merge key mismatch

2. **Examine raw data**:
   - Check if NULL address_id rows have address information in other columns
   - (city, state, latitude, longitude fields in the infrastructure tables themselves)

3. **Review ETL logs**:
   - Check Prefect logs for geocoding errors
   - Look for merge warnings during transform step

4. **Test case**: Pick one NULL row and:
   - Find it in the geocoded sheet
   - Check if coordinates exist there
   - If yes, verify the merge columns match
   - If no, the geocoding genuinely failed

NEXT STEPS:
===========

Based on initial findings showing 235 NULL address_ids (2.29%):

A. **If these are genuine geocoding failures**:
   - Acceptable data quality - some addresses cannot be geocoded
   - Document as known limitation

B. **If geocoded data exists but wasn't merged**:
   - This is a bug in the ETL logic
   - Fix: Update merge keys or improve matching logic
   - Re-run affected ETL pipelines

C. **If geocoding never attempted**:
   - Add missing rows to geocoded sheet
   - Re-run geocoding
   - Re-run ETL

CONCLUSION:
===========

The analysis shows that 235 infrastructure facility records (2.29%) lack address_id values.
To determine if this represents lost data that should be recovered, manual inspection of
the "address-to-geocoded" Google Sheet is required. The ETL code structure is sound - 
it properly handles geocoded data when available. The question is whether the geocoded
data exists but failed to merge, or if geocoding genuinely failed for these addresses.

"""

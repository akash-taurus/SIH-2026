# Data contract for real SIH26001 data

Synthetic data is only for pipeline/demo testing. For the final model, replace it with a historical landslide inventory joined to environmental observations by location and date.

Minimum recommended fields:
- lat, lon, date
- landslide_occurred (0/1)
- slope_deg, elevation_m, aspect_deg, curvature, twi, distance_to_drainage_m
- ndvi
- rain_1h_mm, rain_6h_mm, rain_12h_mm, rain_24h_mm, rain_3d_mm, rain_7d_mm, rain_14d_mm, rain_30d_mm
- soil_saturation_proxy

Recommended sources to investigate with the team: official Indian rainfall/meteorological products, DEM/terrain products, satellite vegetation products, and a documented historical landslide inventory. Record source, date, spatial resolution and preprocessing in the final SIH report.

Do not claim synthetic validation metrics as real-world accuracy.

import math
from typing import Dict, Any, List

# Regional Soil Geotechnical Properties Database for North-East Himalayan Region
SOIL_GEOTECHNICAL_PROPERTIES = {
    "Clayey Loam on Weathered Quartzite": {
        "cohesion_kpa": 14.5,
        "friction_angle_deg": 31.0,
        "gamma_sat_kn_m3": 18.8,
        "hydraulic_conductivity_m_s": 2.5e-5
    },
    "Limestone Karst & Fractured Sandstone": {
        "cohesion_kpa": 22.0,
        "friction_angle_deg": 35.5,
        "gamma_sat_kn_m3": 21.0,
        "hydraulic_conductivity_m_s": 5.0e-5
    },
    "Highly Saturated Colluvium": {
        "cohesion_kpa": 6.5,
        "friction_angle_deg": 26.0,
        "gamma_sat_kn_m3": 17.5,
        "hydraulic_conductivity_m_s": 1.2e-4
    },
    "Shale and Coal-bearing Sandstone": {
        "cohesion_kpa": 16.0,
        "friction_angle_deg": 29.0,
        "gamma_sat_kn_m3": 19.2,
        "hydraulic_conductivity_m_s": 1.8e-5
    },
    "Archaean Gneiss Complex": {
        "cohesion_kpa": 26.0,
        "friction_angle_deg": 36.0,
        "gamma_sat_kn_m3": 22.5,
        "hydraulic_conductivity_m_s": 8.0e-6
    },
    "Alluvial Valley Fill": {
        "cohesion_kpa": 8.0,
        "friction_angle_deg": 24.0,
        "gamma_sat_kn_m3": 17.0,
        "hydraulic_conductivity_m_s": 3.0e-4
    },
    "default": {
        "cohesion_kpa": 12.0,
        "friction_angle_deg": 30.0,
        "gamma_sat_kn_m3": 18.5,
        "hydraulic_conductivity_m_s": 3.0e-5
    }
}

class PhysicsSafetyShield:
    """
    Advanced Geotechnical Physics Engine.
    Combines:
    1. Infinite Slope Stability Mechanics (Factor of Safety with Pore Water Pressure)
    2. Empirical Intensity-Duration (I-D) Rain Thresholds (Caine 1980 & Guzzetti 2008)
    3. Transient Antecedent Precipitation Saturation Index (API-15)
    """

    ALPHA_CAINE: float = 14.82
    BETA_CAINE: float = 0.39
    ALPHA_GUZZETTI: float = 19.50
    BETA_GUZZETTI: float = 0.44
    CRITICAL_SLOPE_THRESHOLD_DEG: float = 25.0
    GAMMA_WATER_KN_M3: float = 9.81

    @classmethod
    def calculate_critical_intensity(cls, duration_hours: float) -> float:
        """
        Calculates Caine empirical critical rainfall intensity threshold (mm/h).
        """
        d = max(float(duration_hours), 0.5)
        return round(cls.ALPHA_CAINE * math.pow(d, -cls.BETA_CAINE), 2)

    @classmethod
    def calculate_guzzetti_intensity(cls, duration_hours: float) -> float:
        """
        Calculates Guzzetti Eastern Himalaya calibrated threshold (mm/h).
        """
        d = max(float(duration_hours), 0.5)
        return round(cls.ALPHA_GUZZETTI * math.pow(d, -cls.BETA_GUZZETTI), 2)

    @classmethod
    def calculate_factor_of_safety(
        cls,
        slope_deg: float,
        soil_type: str = "default",
        soil_saturation_pct: float = 0.65,
        rainfall_24h_mm: float = 65.0,
        failure_depth_m: float = 2.0
    ) -> Dict[str, Any]:
        """
        Computes Limit-Equilibrium Infinite Slope Factor of Safety (FS).
        """
        soil = SOIL_GEOTECHNICAL_PROPERTIES.get(soil_type, SOIL_GEOTECHNICAL_PROPERTIES["default"])
        c_prime = soil["cohesion_kpa"]
        phi_deg = soil["friction_angle_deg"]
        gamma_sat = soil["gamma_sat_kn_m3"]
        gamma_w = cls.GAMMA_WATER_KN_M3
        z = max(failure_depth_m, 1.0)

        beta_rad = math.radians(max(min(slope_deg, 85.0), 5.0))
        phi_rad = math.radians(phi_deg)

        sat_factor = min(max(soil_saturation_pct, 0.0), 1.0)
        rain_infiltration_ratio = min(rainfall_24h_mm / 220.0, 1.0)
        hw_ratio = min(1.0, math.pow(sat_factor, 1.6) * 0.7 + rain_infiltration_ratio * 0.3)
        h_w = z * hw_ratio

        pore_pressure_kpa = gamma_w * h_w * (math.cos(beta_rad) ** 2)
        driving_shear_kpa = gamma_sat * z * math.sin(beta_rad) * math.cos(beta_rad)
        driving_shear_kpa = max(driving_shear_kpa, 0.1)

        effective_normal_stress = (gamma_sat * z - gamma_w * h_w) * (math.cos(beta_rad) ** 2)
        resisting_shear_kpa = c_prime + max(effective_normal_stress, 0.0) * math.tan(phi_rad)

        fs = max(round(resisting_shear_kpa / driving_shear_kpa, 2), 0.05)

        if fs < 1.0:
            if slope_deg >= 38.0:
                failure_mode = "Rapid Translational Debris Avalanche"
            elif soil_saturation_pct >= 0.85:
                failure_mode = "Hyper-Concentrated Liquefied Mudflow"
            else:
                failure_mode = "Rotational Slump along Bedding Plane"
        elif fs < 1.3:
            failure_mode = "Marginally Stable (Creep & Tension Cracks Likely)"
        else:
            failure_mode = "Geotechnically Stable Slope"

        return {
            "factor_of_safety": fs,
            "is_slope_unstable": fs < 1.0,
            "effective_cohesion_kpa": c_prime,
            "friction_angle_deg": phi_deg,
            "pore_water_pressure_kpa": round(pore_pressure_kpa, 2),
            "driving_stress_kpa": round(driving_shear_kpa, 2),
            "resisting_strength_kpa": round(resisting_shear_kpa, 2),
            "perched_water_table_m": round(h_w, 2),
            "failure_mode": failure_mode
        }

    @classmethod
    def evaluate_geotechnical_threshold(
        cls,
        rain_intensity_1h: float,
        duration_hours: float = 1.0,
        slope_deg: float = 30.0,
        soil_saturation_pct: float = 0.70,
        soil_type: str = "default",
        rainfall_24h_mm: float = 65.0
    ) -> Dict[str, Any]:
        """
        Evaluates multi-criteria geotechnical and hydrological stability against
        safety thresholds (FS <= 1.10, Caine/Guzzetti I-D curves, acute cloudbursts,
        and extreme antecedent saturation).
        """
        caine_threshold = cls.calculate_critical_intensity(duration_hours)
        guzzetti_threshold = cls.calculate_guzzetti_intensity(duration_hours)
        is_slope_critical = slope_deg >= cls.CRITICAL_SLOPE_THRESHOLD_DEG

        caine_breached = (rain_intensity_1h >= caine_threshold) and is_slope_critical
        guzzetti_breached = (rain_intensity_1h >= guzzetti_threshold) and is_slope_critical
        sat_caine_breached = (
            soil_saturation_pct >= 0.85
            and rain_intensity_1h >= (caine_threshold * 0.75)
            and is_slope_critical
        )

        stability = cls.calculate_factor_of_safety(
            slope_deg=slope_deg,
            soil_type=soil_type,
            soil_saturation_pct=soil_saturation_pct,
            rainfall_24h_mm=rainfall_24h_mm
        )

        fs = stability["factor_of_safety"]
        fs_breached = fs <= 1.10
        acute_1h_breached = rain_intensity_1h >= 35.0
        extreme_24h_sat_breached = (rainfall_24h_mm >= 150.0) and (soil_saturation_pct >= 0.85)

        overall_breached = (
            caine_breached
            or guzzetti_breached
            or sat_caine_breached
            or fs_breached
            or acute_1h_breached
            or extreme_24h_sat_breached
            or stability["is_slope_unstable"]
        )

        reasons: List[str] = []
        if fs <= 1.00:
            reasons.append(
                f"Factor of Safety FS={fs:.2f} <= 1.00 (Active Limit-Equilibrium Shear Failure: {stability['failure_mode']})"
            )
        elif fs <= 1.10:
            reasons.append(
                f"Factor of Safety FS={fs:.2f} <= 1.10 (Incipient Slope Instability: {stability['failure_mode']})"
            )

        if caine_breached:
            reasons.append(
                f"Caine (1980) I-D threshold breached: 1h rainfall {rain_intensity_1h:.1f} mm/h >= {caine_threshold:.2f} mm/h (slope={slope_deg:.1f}° >= 25.0°)"
            )
        if guzzetti_breached:
            reasons.append(
                f"Guzzetti (2008) Eastern Himalaya I-D threshold breached: 1h rainfall {rain_intensity_1h:.1f} mm/h >= {guzzetti_threshold:.2f} mm/h (slope={slope_deg:.1f}° >= 25.0°)"
            )
        if sat_caine_breached and not caine_breached:
            reasons.append(
                f"High soil pre-saturation breach: saturation {soil_saturation_pct*100:.0f}% >= 85% with 1h rain {rain_intensity_1h:.1f} mm/h >= 75% Caine threshold ({0.75*caine_threshold:.2f} mm/h)"
            )
        if acute_1h_breached:
            reasons.append(
                f"Acute cloudburst downpour: 1h precipitation {rain_intensity_1h:.1f} mm/h >= 35.0 mm/h torrential threshold"
            )
        if extreme_24h_sat_breached:
            reasons.append(
                f"Extreme 24h cumulative loading under high saturation: 24h rain {rainfall_24h_mm:.1f} mm >= 150.0 mm with soil saturation {soil_saturation_pct*100:.0f}% >= 85%"
            )

        rain_safety_factor = round(caine_threshold / max(rain_intensity_1h, 0.1), 2)

        return {
            "physics_threshold_breached": overall_breached,
            "fs_breached": fs_breached,
            "acute_1h_breached": acute_1h_breached,
            "extreme_24h_sat_breached": extreme_24h_sat_breached,
            "caine_threshold_mm_h": caine_threshold,
            "guzzetti_threshold_mm_h": guzzetti_threshold,
            "actual_intensity_mm_h": round(rain_intensity_1h, 2),
            "duration_hours": duration_hours,
            "slope_deg": slope_deg,
            "is_slope_critical": is_slope_critical,
            "caine_breached": caine_breached or sat_caine_breached,
            "guzzetti_breached": guzzetti_breached,
            "sat_caine_breached": sat_caine_breached,
            "slope_stability": stability,
            "safety_factor": rain_safety_factor,
            "breach_reasons": reasons,
            "formula_caine": "Ic = 14.82 * (D ^ -0.39)",
            "formula_guzzetti": "Ic = 19.50 * (D ^ -0.44)"
        }

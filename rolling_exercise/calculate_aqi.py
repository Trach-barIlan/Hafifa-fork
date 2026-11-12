def calculate_aqi(pm25, no2, co2):
    pm25_breakpoints = [
        (0, 12, 0, 50),
        (12.1, 35.4, 51, 100),
        (35.5, 55.4, 101, 150),
        (55.5, 150.4, 151, 200),
        (150.5, 250.4, 201, 300),
        (250.5, 500.4, 301, 500),
    ]

    no2_breakpoints = [
        (0, 53, 0, 50),
        (54, 100, 51, 100),
        (101, 360, 101, 150),
        (361, 649, 151, 200),
        (650, 1249, 201, 300),
        (1250, 2049, 301, 500),
    ]

    co2_breakpoints = [
        (0, 5, 0, 50),
        (5.1, 15, 51, 100),
        (15.1, 30, 101, 150),
        (30.1, 60, 151, 200),
        (60.1, 100, 201, 300),
        (100.1, 200, 301, 500),
    ]

    def calculate_sub_index(value, breakpoints):
        for lower, upper, aqi_lower, aqi_upper in breakpoints:
            if lower <= value <= upper:
                return aqi_lower + (value - lower) * (aqi_upper - aqi_lower) / (upper - lower)
        return 500

    pm25_aqi = calculate_sub_index(pm25, pm25_breakpoints)
    no2_aqi = calculate_sub_index(no2, no2_breakpoints)
    co2_aqi = calculate_sub_index(co2, co2_breakpoints)

    overall_aqi = max(min(pm25_aqi, 500), 0, min(no2_aqi, 500), 0, min(co2_aqi, 500), 0)

    aqi_thresholds = [
        (50, "Good"),
        (100, "Moderate"),
        (150, "Unhealthy for Sensitive Groups"),
        (200, "Unhealthy"),
        (300, "Very Unhealthy"),
        (500, "Hazardous")
    ]

    aqi_level = next(
        (level for threshold, level in aqi_thresholds if overall_aqi <= threshold),
        "Hazardous",
    )

    return overall_aqi, aqi_level

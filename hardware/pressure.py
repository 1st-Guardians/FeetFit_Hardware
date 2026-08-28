from errors import HardwareMeasurementError


def measure_pressure():

    try:

        # ==========================================
        # TODO
        # ADS1115 + CD74HC4067 실제 코드
        # ==========================================

        left = [
            92.2, 1.0, 605.4, 8.6,
            29.3, 8430.6, 7289.3, 34.5,
            4151.6, 14356.8, 272.2, 15257.0
        ]

        right = [
            546.9, 752.2, 683.4, 101.4,
            33.0, 1982.6, 3446.1, 64.3,
            6026.4, 16111.5, 11520.5, 13116.1
        ]


        if len(left) != 12:
            raise ValueError(
                f"left count={len(left)}"
            )

        if len(right) != 12:
            raise ValueError(
                f"right count={len(right)}"
            )


        return {
            "left": left,
            "right": right
        }


    except Exception as e:

        raise HardwareMeasurementError(
            reason="PRESSURE_SENSOR_ERROR",
            message=(
                "압력 측정에 실패했습니다. "
                "다시 시도해주세요."
            ),
            detail=str(e)
        )

import numpy as np
from typing import List, Any

from .utils import compute_theta_gamma, beam_pattern_from_gamma, tvg_gain


def _get_attr(obj, candidates, default=np.nan):
    """Helper function to get attribute from object with multiple candidate names"""
    for name in candidates:
        if hasattr(obj, name):
            return getattr(obj, name)

    return default


def process_channel(
    xtf_ping: Any,
    altitude: float,
    roll: float,
    install_angle: float,
    tvg_k: float,
    tvg_alpha: float,
    use_tvg: bool,
    apply_water_mask: bool,
    normalize_gain: bool,
    is_right: bool
):
    """
    Process Channel for an XTF ping

    Args:
        xtf_ping: XTF ping object
        yaw_offset: Yaw offset to apply in degrees
        altitude: Altitude of sonar installation
        roll: Roll angle of sonar installation
        install_angle: Sonar installation angle in degrees
        tvg_k: TVG power parameter
        tvg_alpha: TVG attenuation coefficient
        use_tvg: Whether to apply TVG correction
        apply_water_mask: Whether to mask water column
        normalize_gain: Whether to normalize gain factors
        is_right: Whether this is the right channel or not (left otherwise)

    Returns:
        Log corrected intensity
    """
    ch = int(is_right)

    chan = xtf_ping.ping_chan_headers[ch]
    smax = float(_get_attr(chan, ["SlantRange"], default=100.0))
    Ns = int(_get_attr(chan, ["NumSamples"], default=len(xtf_ping.data[ch])))
    k = np.arange(1, Ns + 1, dtype=np.float64)

    rng = smax * k / float(Ns)
    if not is_right:
        rng = np.flip(rng)  # left side is typically reversed

    theta, gamma = compute_theta_gamma(rng.reshape(1, -1), np.array([altitude]))
    lambert = 1.0 / np.clip(np.cos(theta), 1e-6, None)
    Phi = beam_pattern_from_gamma(
        gamma,
        roll_deg=np.array([roll]),
        phi0_deg=install_angle,
        is_right=is_right
    )

    gain = lambert / Phi
    if use_tvg:
        gain *= tvg_gain(rng.reshape(1, -1), k=tvg_k, alpha=tvg_alpha)

    if normalize_gain:
        gain /= np.max(gain)

    if apply_water_mask:
        gain[0, rng <= altitude] = 0.0

    I_raw = xtf_ping.data[ch].astype(np.float64) / 16384.0
    I_corrected = I_raw * gain[0]
    I_log = np.log1p(I_corrected * 16384.0)
    I_log[I_log < 0] = 0

    return I_log


def modify_pings_with_correction(
    xtf_pings: List[Any],
    yaw_offset: float=0.0,
    install_angle: float=30.0,
    tvg_k: float=2.0,
    tvg_alpha: float=0.1,
    use_tvg: bool=False,
    apply_water_mask: bool=True,
    normalize_gain: bool=True
):
    """
    Modify XTF pings with advanced intensity correction.
    
    Args:
        xtf_pings: List of XTF ping objects
        yaw_offset: Yaw offset to apply in degrees (default: 0.0)
        install_angle: Sonar installation angle in degrees (default: 30.0)
        tvg_k: TVG power parameter (default: 2.0)
        tvg_alpha: TVG attenuation coefficient (default: 0.1)
        use_tvg: Whether to apply TVG correction (default: False)
        apply_water_mask: Whether to mask water column (default: True)
        normalize_gain: Whether to normalize gain factors (default: True)
    
    Returns:
        list: Modified ping objects
    """
    pings = []

    min_val, max_val = np.inf, -np.inf
    for i in range(len(xtf_pings)):
        xtf_pings[i].SensorHeading += yaw_offset

        altitude = float(_get_attr(
            xtf_pings[i],
            ["SensorPrimaryAltitude", "SensorAltitude", "Altitude"], 
            default=np.nan
        ))

        roll = float(_get_attr(
            xtf_pings[i],
            ["SensorPrimaryRoll", "SensorRoll", "Roll", "MRURoll"],
            default=0.0
        ))

        I_left_log = process_channel(
            xtf_pings[i],
            altitude,
            roll,
            install_angle,
            tvg_k,
            tvg_alpha,
            use_tvg,
            apply_water_mask,
            normalize_gain,
            False
        )

        I_right_log = process_channel(
            xtf_pings[i],
            altitude,
            roll,
            install_angle,
            tvg_k,
            tvg_alpha,
            use_tvg,
            apply_water_mask,
            normalize_gain,
            True
        )

        min_val = min(min_val, np.min(I_left_log), np.min(I_right_log))
        max_val = max(max_val, np.max(I_left_log), np.max(I_right_log))

        xtf_pings[i].data[0] = I_left_log
        xtf_pings[i].data[1] = I_right_log

        pings.append(xtf_pings[i])

    for i in range(len(pings)):
        pings[i].data[0] = (65535.0 * (pings[i].data[0] - min_val) / (max_val - min_val)).astype(np.uint16)
        pings[i].data[1] = (65535.0 * (pings[i].data[1] - min_val) / (max_val - min_val)).astype(np.uint16)

    return pings

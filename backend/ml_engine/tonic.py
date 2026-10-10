"""
Dynamic tonic (Sa) estimation.

The 23-bin Shruti table in :mod:`ml_engine.shruti_mapping` is anchored to a
fixed reference (``REFERENCE_FREQ`` = C4 = 261.626 Hz).  Real recitations, how-
ever, are sung at whatever pitch the reciter finds comfortable, so the whole
microtonal grid must be transposed to the performance's own tonic before any
pitch can be named.  This module estimates that tonic from a pYIN pitch track
using the histogram-peak method standard in Indian-classical tonic detection:
the most sustained pitch class of a monophonic melodic line is the tonic.
"""

import numpy as np

from .shruti_mapping import REFERENCE_FREQ

_OCTAVE_CENTS = 1200.0


def tonic_hz_from_cents(tonic_cents):
    """Reference frequency shifted by ``tonic_cents`` (see :func:`estimate_tonic_cents`)."""
    return float(REFERENCE_FREQ * 2.0 ** (tonic_cents / _OCTAVE_CENTS))


def estimate_tonic_cents(f0, voiced_flag=None, bin_width_cents=10.0,
                         smooth_bins=2, min_voiced_frames=20,
                         peak_exclusion_bins=4, min_confidence=0.50):
    """
    Estimate the tonic (Sa) of a monophonic pitch track as a signed cents offset
    from ``REFERENCE_FREQ`` (C4).

    Frequencies are folded into a single octave, accumulated into a circular
    histogram, smoothed, and the dominant peak is taken as the tonic.

    Confidence is the *prominence* of that peak relative to the next-highest
    peak outside a small exclusion window::

        confidence = (peak - runner_up) / peak

    A drone-like or chant-like line that dwells on the tonic yields a dominant
    peak (confidence → 1).  An equal-weight scalar passage, in which no pitch
    class dominates, yields a nearly flat histogram (confidence → 0) and is
    reported as ambiguous so the caller keeps the C4 reference rather than
    transposing on a guess.

    Parameters
    ----------
    f0 : ndarray
        Fundamental-frequency track in Hz (NaN for unvoiced frames).
    voiced_flag : ndarray of bool, optional
        Voiced-frame mask aligned with ``f0``.  When given, unvoiced frames are
        discarded.
    bin_width_cents : float
        Histogram resolution in cents.
    smooth_bins : int
        Gaussian smoothing kernel half-width, in bins.
    min_voiced_frames : int
        Minimum number of usable voiced frames required to attempt estimation.
    peak_exclusion_bins : int
        Half-width (in bins) of the exclusion window around the peak within
        which the runner-up peak is not counted (prevents the peak's own skirt
        from being mistaken for the runner-up).
    min_confidence : float
        Below this peak-prominence the estimate is treated as ambiguous and
        ``(0.0, confidence)`` is returned so the caller keeps the C4 reference.

    Returns
    -------
    (tonic_cents, confidence)
        tonic_cents : float in [-600, 600) — cents offset to add to the
            reference so that ``REFERENCE_FREQ * 2**(tonic_cents/1200)`` is the
            estimated tonic in Hz.
        confidence : float in [0, 1] — peak prominence (see above).
    """
    f0 = np.asarray(f0, dtype=np.float64)
    if f0.size == 0:
        return 0.0, 0.0

    if voiced_flag is not None:
        vf = np.asarray(voiced_flag, dtype=bool)
        n = min(f0.size, vf.size)
        if n:
            f0 = f0[:n][vf[:n]]

    f0 = f0[np.isfinite(f0) & (f0 > 0.0)]
    if f0.size < min_voiced_frames:
        return 0.0, 0.0

    cents = _OCTAVE_CENTS * np.log2(f0 / REFERENCE_FREQ)
    pitch_class = np.mod(cents, _OCTAVE_CENTS)

    n_bins = int(round(_OCTAVE_CENTS / bin_width_cents))
    hist, edges = np.histogram(
        pitch_class, bins=n_bins, range=(0.0, _OCTAVE_CENTS),
    )
    hist = hist.astype(np.float64)

    if smooth_bins > 0:
        k = int(smooth_bins)
        idx = np.arange(-3 * k, 3 * k + 1)
        kernel = np.exp(-0.5 * (idx / k) ** 2)
        kernel /= kernel.sum()
        padded = np.concatenate([hist, hist, hist])
        hist = np.convolve(padded, kernel, mode='same')[n_bins:2 * n_bins]

    total = float(hist.sum())
    if total <= 0.0:
        return 0.0, 0.0

    peak_bin = int(np.argmax(hist))
    peak_height = float(hist[peak_bin])

    outside = np.ones(n_bins, dtype=bool)
    for d in range(-peak_exclusion_bins, peak_exclusion_bins + 1):
        outside[(peak_bin + d) % n_bins] = False
    runner_up = float(hist[outside].max()) if outside.any() else 0.0

    confidence = (peak_height - runner_up) / peak_height \
        if peak_height > 0.0 else 0.0

    if confidence < min_confidence:
        return 0.0, confidence

    peak_center = edges[peak_bin] + bin_width_cents / 2.0
    tonic_cents = ((peak_center + _OCTAVE_CENTS / 2) % _OCTAVE_CENTS) \
                  - _OCTAVE_CENTS / 2
    return float(tonic_cents), confidence

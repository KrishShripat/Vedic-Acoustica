"""Vedic Acoustica ML engine.

``PIPELINE_VERSION`` is stamped into every ``analysis_metadata`` blob written by
``api.tasks.process_audio_task`` so stale results (produced by an older
algorithm) can be detected and re-analysed via ``manage.py reanalyze``.

Bump this string whenever a change to the feature/PCP/clustering/Ghana/raga
stages would alter stored results.
"""

PIPELINE_VERSION = 'r4-2026-09-22'

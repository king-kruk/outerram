"""Known-good upstream revisions used by OuterRAM 0.3 bootstrap.

Pins make installations reproducible. Users can opt into upstream HEAD with
`outerram bootstrap --latest` when testing new model support.

Transition lock snapshot: 2026-08-24.
"""

MLX_LM_REF = "cc8521569694a3240b52c98acffd100d59b4c755"
MLX_LM_VERSION = "0.32.0"
MLX_MIN_VERSION = "0.32.1"
MLX_MIN_MACOS_VERSION = "14.0"

MLX_FLASH_REF = "f01b6f15affc054e143c1426ef2c3cc500cdbea8"
MLX_FLASH_VERSION = "0.4.0"

STREAMLX_REF = "146507b59293058b3a1cecc43f47947b25012297"
STREAMLX_VERSION = "0.1.0"

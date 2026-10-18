#!/usr/bin/env bash
set -euo pipefail
out_dir="${1:-$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)}"
mkdir -p "$out_dir"
/home/ferna/digital_twin_asset_forge/bin/IfcConvert \
  --no-progress --fail-on-error --log-format json \
  --log-file "$out_dir/conversion.json" \
  /home/ferna/digital_twin_asset_forge/assets/P71_TS_M05_IFC4.ifc \
  "$out_dir/P71_TS_M05_IFC4.stp" \
  > "$out_dir/conversion.stdout.log" 2>&1

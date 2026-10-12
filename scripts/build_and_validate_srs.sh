#!/usr/bin/env bash
# Convert compact geosite/geoip .dat → sing-box rule-set (.srs), then validate.
# Approach mirrors SagerNet/sing-geosite (geosite → headless rule → srs.Write),
# but uses geoview + sing-box CLI already in this repo's CI.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

GEOSITE_DAT="${GEOSITE_DAT:-dist/geosite-compact.dat}"
GEOIP_DAT="${GEOIP_DAT:-dist/geoip-compact.dat}"
OUT_DIR="${OUT_DIR:-dist/srs}"
WORK_DIR="${WORK_DIR:-work/srs}"
# Rule-set version 1: domain / domain_suffix / ip_cidr — compatible with sing-box 1.8+.
# geoview may emit version 3; we normalize before compile.
RULESET_VERSION="${RULESET_VERSION:-1}"

need() { command -v "$1" >/dev/null 2>&1 || { echo "missing tool: $1" >&2; exit 1; }; }
need geoview
need sing-box
need python3

[[ -f "$GEOSITE_DAT" ]] || { echo "missing $GEOSITE_DAT" >&2; exit 1; }
[[ -f "$GEOIP_DAT" ]] || { echo "missing $GEOIP_DAT" >&2; exit 1; }

mkdir -p "$OUT_DIR" "$WORK_DIR"

convert_one() {
  local type="$1" list="$2" out_stem="$3"
  local json_raw="$WORK_DIR/${out_stem}.raw.json"
  local json_v="$WORK_DIR/${out_stem}.json"
  local srs_out="$OUT_DIR/${out_stem}.srs"

  echo "convert ${type}:${list} → ${srs_out}"
  geoview \
    -type "$type" \
    -action convert \
    -input "$( [[ "$type" == geosite ]] && echo "$GEOSITE_DAT" || echo "$GEOIP_DAT" )" \
    -list "$list" \
    -output "$json_raw" \
    -format json \
    -strict=false

  python3 - "$json_raw" "$json_v" "$RULESET_VERSION" <<'PY'
import json, sys
src, dst, ver = sys.argv[1], sys.argv[2], int(sys.argv[3])
data = json.load(open(src, encoding="utf-8"))
data["version"] = ver
if not data.get("rules"):
    raise SystemExit(f"empty rules in {src}")
json.dump(data, open(dst, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
print(f"  version={ver} rules={len(data['rules'])}")
PY

  sing-box rule-set compile "$json_v" -o "$srs_out"
  # Round-trip: binary must decompile
  sing-box rule-set decompile "$srs_out" -o "$WORK_DIR/${out_stem}.decompiled.json" >/dev/null
}

convert_one geosite category-ru geosite-category-ru
convert_one geosite private geosite-private
convert_one geosite category-ads geosite-category-ads
convert_one geoip ru geoip-ru
convert_one geoip private geoip-private

echo "validate matches (source JSON; sing-box match defaults to source format)"
must_match() {
  local file="$1" value="$2"
  local out
  out="$(sing-box rule-set match "$file" "$value" 2>&1 || true)"
  if [[ "$out" != match* ]]; then
    echo "FAIL: expected match for $value in $file; got: $out" >&2
    exit 1
  fi
  echo "  OK match $value"
}
must_not_match() {
  local file="$1" value="$2"
  local out
  out="$(sing-box rule-set match "$file" "$value" 2>&1 || true)"
  if [[ "$out" == match* ]]; then
    echo "FAIL: expected NO match for $value in $file; got: $out" >&2
    exit 1
  fi
  echo "  OK no-match $value"
}

GEOSITE_JSON="$WORK_DIR/geosite-category-ru.json"
GEOIP_JSON="$WORK_DIR/geoip-ru.json"

# Covered by domain_suffix "ru" after polishList (same as Xray geosite:category-ru)
must_match "$GEOSITE_JSON" "nalog.ru"
must_match "$GEOSITE_JSON" "gosuslugi.ru"
must_match "$GEOSITE_JSON" "www.gosuslugi.ru"
must_match "$GEOSITE_JSON" "yandex.ru"
must_not_match "$GEOSITE_JSON" "google.com"
must_not_match "$GEOSITE_JSON" "example.com"

# First RU CIDR host from compiled list
RU_SAMPLE_IP="$(python3 - "$GEOIP_JSON" <<'PY'
import json, sys
from ipaddress import ip_network
cidrs = json.load(open(sys.argv[1], encoding="utf-8"))["rules"][0]["ip_cidr"]
net = ip_network(cidrs[0], strict=False)
# pick a usable host address inside the network
hosts = list(net.hosts())
print(str(hosts[0] if hosts else net.network_address))
PY
)"
must_match "$GEOIP_JSON" "$RU_SAMPLE_IP"
must_not_match "$GEOIP_JSON" "8.8.8.8"
must_not_match "$GEOIP_JSON" "1.1.1.1"

# Minimal config: load both binary .srs
CFG="$WORK_DIR/sing-box-check.json"
cat > "$CFG" <<EOF
{
  "log": { "level": "warn" },
  "inbounds": [
    {
      "type": "mixed",
      "tag": "mixed-in",
      "listen": "127.0.0.1",
      "listen_port": 18081
    }
  ],
  "outbounds": [
    { "type": "direct", "tag": "direct" },
    { "type": "block", "tag": "block" }
  ],
  "route": {
    "rule_set": [
      {
        "type": "local",
        "tag": "geosite-category-ru",
        "format": "binary",
        "path": "${OUT_DIR}/geosite-category-ru.srs"
      },
      {
        "type": "local",
        "tag": "geoip-ru",
        "format": "binary",
        "path": "${OUT_DIR}/geoip-ru.srs"
      },
      {
        "type": "local",
        "tag": "geosite-private",
        "format": "binary",
        "path": "${OUT_DIR}/geosite-private.srs"
      },
      {
        "type": "local",
        "tag": "geoip-private",
        "format": "binary",
        "path": "${OUT_DIR}/geoip-private.srs"
      }
    ],
    "rules": [
      { "rule_set": "geosite-private", "outbound": "direct" },
      { "rule_set": "geoip-private", "outbound": "direct" },
      { "rule_set": "geosite-category-ru", "outbound": "direct" },
      { "rule_set": "geoip-ru", "outbound": "direct" }
    ],
    "final": "direct"
  }
}
EOF

# Paths in config are relative to cwd (= ROOT)
sing-box check -c "$CFG"
echo "sing-box check: OK"

ls -la "$OUT_DIR"
echo "SRS build + validation complete."

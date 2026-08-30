#!/usr/bin/env bash
#
# Diagnose the two network failures that account for most lost time on this project:
# DDS binding to a virtual interface, and a discovery server that is configured but
# not reachable.
#
# Run on any machine after sourcing its config/env file.

set -uo pipefail

fail=0
note() { printf '  %s\n' "$*"; }
ok()   { printf 'ok    %s\n' "$*"; }
bad()  { printf 'FAIL  %s\n' "$*"; fail=1; }

echo "environment"
for var in ROS_DOMAIN_ID RMW_IMPLEMENTATION FASTRTPS_DEFAULT_PROFILES_FILE ROS_DISCOVERY_SERVER; do
  if [[ -n "${!var:-}" ]]; then ok "${var}=${!var}"; else bad "${var} is not set"; fi
done

if [[ -n "${ROS_SUPER_CLIENT:-}" ]]; then
  ok "ROS_SUPER_CLIENT=${ROS_SUPER_CLIENT}"
else
  note "ROS_SUPER_CLIENT is not set. Required on operator machines or CLI tools"
  note "will report a partial graph. Not needed on the robot."
fi

echo
echo "transport profile"
profile="${FASTRTPS_DEFAULT_PROFILES_FILE:-}"
if [[ -r "${profile}" ]]; then
  ok "profile readable at ${profile}"
  if grep -q 'interfaceWhiteList' "${profile}"; then
    ok "interface whitelist present"
    grep -o '<address>[^<]*</address>' "${profile}" | sed 's/.*>\(.*\)<.*/  whitelisted: \1/'
  else
    bad "no interface whitelist: DDS will enumerate every interface, TUN devices included"
  fi
  grep -q '<type>SHM</type>' "${profile}" \
    && ok "shared memory transport declared" \
    || bad "no SHM transport: onboard traffic will not use shared memory"
else
  bad "profile not readable at '${profile}'"
fi

echo
echo "interfaces"
ip -o -4 addr show | awk '{printf "  %-12s %s\n", $2, $4}'
if ip -o link show type tun 2>/dev/null | grep -q .; then
  note "TUN devices present. The whitelist above must not include their addresses."
fi

echo
echo "discovery server"
if [[ -n "${ROS_DISCOVERY_SERVER:-}" ]]; then
  host="${ROS_DISCOVERY_SERVER%%:*}"
  port="${ROS_DISCOVERY_SERVER##*:}"
  if timeout 2 bash -c "</dev/tcp/${host}/${port}" 2>/dev/null; then
    ok "reachable at ${host}:${port}"
  else
    # The server speaks UDP; a refused TCP probe is expected and only tells us the
    # host is up. Treat an unreachable host as the real failure.
    ping -c1 -W2 "${host}" >/dev/null 2>&1 \
      && note "host ${host} responds to ping, TCP probe refused as expected for UDP" \
      || bad "host ${host} is unreachable"
  fi
fi

echo
[[ "${fail}" -eq 0 ]] && echo "all checks passed" || echo "problems found, see FAIL lines above"
exit "${fail}"

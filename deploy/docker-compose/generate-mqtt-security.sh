#!/bin/sh

set -eu

SECURITY_DIR="/security"

if \
  [ -f "${SECURITY_DIR}/ca.crt" ] && \
  [ -f "${SECURITY_DIR}/server.crt" ] && \
  [ -f "${SECURITY_DIR}/server.key" ] && \
  [ -f "${SECURITY_DIR}/passwords" ]; then
    echo "MQTT test security material already exists"
    exit 0
fi

: "${MQTT_RUNTIME_USERNAME:?MQTT_RUNTIME_USERNAME is required}"
: "${MQTT_RUNTIME_PASSWORD:?MQTT_RUNTIME_PASSWORD is required}"
: "${MQTT_SIMULATOR_USERNAME:?MQTT_SIMULATOR_USERNAME is required}"
: "${MQTT_SIMULATOR_PASSWORD:?MQTT_SIMULATOR_PASSWORD is required}"

mkdir -p "${SECURITY_DIR}"

openssl genrsa \
  -out "${SECURITY_DIR}/ca.key" \
  2048

openssl req \
  -x509 \
  -new \
  -key "${SECURITY_DIR}/ca.key" \
  -sha256 \
  -days 1 \
  -out "${SECURITY_DIR}/ca.crt" \
  -subj "/CN=EdgePulse Compose Test CA"

openssl genrsa \
  -out "${SECURITY_DIR}/server.key" \
  2048

openssl req \
  -new \
  -key "${SECURITY_DIR}/server.key" \
  -out "${SECURITY_DIR}/server.csr" \
  -subj "/CN=mqtt"

cat >"${SECURITY_DIR}/server.ext" <<'EOF'
subjectAltName=DNS:mqtt,DNS:localhost,IP:127.0.0.1
extendedKeyUsage=serverAuth
keyUsage=digitalSignature,keyEncipherment
EOF

openssl x509 \
  -req \
  -in "${SECURITY_DIR}/server.csr" \
  -CA "${SECURITY_DIR}/ca.crt" \
  -CAkey "${SECURITY_DIR}/ca.key" \
  -CAcreateserial \
  -out "${SECURITY_DIR}/server.crt" \
  -days 1 \
  -sha256 \
  -extfile "${SECURITY_DIR}/server.ext"

mosquitto_passwd \
  -b \
  -c \
  "${SECURITY_DIR}/passwords" \
  "${MQTT_RUNTIME_USERNAME}" \
  "${MQTT_RUNTIME_PASSWORD}"

mosquitto_passwd \
  -b \
  "${SECURITY_DIR}/passwords" \
  "${MQTT_SIMULATOR_USERNAME}" \
  "${MQTT_SIMULATOR_PASSWORD}"

rm -f \
  "${SECURITY_DIR}/ca.key" \
  "${SECURITY_DIR}/ca.srl" \
  "${SECURITY_DIR}/server.csr" \
  "${SECURITY_DIR}/server.ext"

chown 1883:1883 \
  "${SECURITY_DIR}/server.key" \
  "${SECURITY_DIR}/server.crt" \
  "${SECURITY_DIR}/passwords"

chmod 600 \
  "${SECURITY_DIR}/server.key" \
  "${SECURITY_DIR}/passwords"

chmod 644 \
  "${SECURITY_DIR}/server.crt" \
  "${SECURITY_DIR}/ca.crt"

echo "MQTT test security material generated"

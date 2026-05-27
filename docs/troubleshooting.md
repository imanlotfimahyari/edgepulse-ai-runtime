# Troubleshooting

## MQTT messages are not consumed

If MQTT simulators print successful publish messages but the runtime does not update MQTT metrics, check whether another Mosquitto broker is already running locally.

Check port `1883`:

```bash
sudo ss -ltnp | grep ':1883' || true
```

If a local Mosquitto service is running, stop it:

```bash
sudo systemctl stop mosquitto || true
sudo pkill mosquitto || true
```

Then restart Docker Compose:

```bash
docker compose -f deploy/docker-compose/docker-compose.yaml down --remove-orphans
docker compose -f deploy/docker-compose/docker-compose.yaml up --build
```

## Verify the Docker MQTT broker directly

Subscribe inside the Mosquitto container:

```bash
docker exec -it edgepulse-mqtt mosquitto_sub -t '#' -v
```

Publish a test message from WSL:

```bash
mosquitto_pub \
  -h 127.0.0.1 \
  -p 1883 \
  -t 'edge/devices/vibration/telemetry' \
  -m '{"device_id":"wsl-test","device_type":"vibration_sensor","payload_type":"vibration","features":[1.0,1.1,0.9],"metadata":{"generated_anomaly":true}}'
```

The subscriber should show the message, and the runtime should process it.

## Check runtime MQTT metrics

```bash
curl -s http://localhost:8080/metrics | grep edgepulse_mqtt_messages_total
curl -s http://localhost:8080/metrics | grep 'ingestion="mqtt"'
curl -s http://localhost:8080/metrics | grep edgepulse_device_messages_total
```

Expected result: metrics should include all MQTT device types that published telemetry.

## Docker cannot pull Mosquitto

If Docker cannot pull `eclipse-mosquitto:2`, check Docker Desktop network, DNS, and proxy settings.

Then retry:

```bash
docker pull eclipse-mosquitto:2
```

## Mosquitto config mount error

If Docker reports that it cannot mount `mosquitto.conf`, verify that the config path is a file, not a directory:

```bash
ls -la deploy/docker-compose
file deploy/docker-compose/mosquitto.conf || true
```

If it is a directory, recreate it as a file:

```bash
rm -rf deploy/docker-compose/mosquitto.conf

cat > deploy/docker-compose/mosquitto.conf <<'MOSQUITTO_EOF'
listener 1883 0.0.0.0
allow_anonymous true
MOSQUITTO_EOF
```

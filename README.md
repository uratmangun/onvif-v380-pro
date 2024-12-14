# ONVIF PTZ Camera Control Commands and RTSP Web viewer

This document provides a comprehensive list of ONVIF PTZ (Pan-Tilt-Zoom) commands for camera control. All commands use the base URL `http://<your camera ip>:8899/onvif/ptz_service` with basic authentication.

## Setup and Configuration for RTSP Web Viewer

This setup allows you to view your RTSP stream on a web interface.

### Environment Variables
Create a `.env` file based on the provided `.env.example`:
```bash
cp .env.example .env
```

Edit the `.env` file with your camera details:
```
ONVIF_USERNAME=
ONVIF_PASSWORD=
ONVIF_IP=
```

### Docker Setup
1. Build the Docker image:
```bash
docker-compose build
```

2. Run the container:
```bash
docker-compose up -d
```

The RTSP web viewer will be available at `http://localhost:8083`

## Basic Authentication
All commands require basic authentication with the following credentials:
- Username: `username`
- Password: `password`

## Common Parameters
- `ProfileToken`: PROFILE_000 (used in all PTZ commands)
- Velocity values range: -1.0 to 1.0
  - Slow movement: ±0.2
  - Medium movement: ±0.5
  - Fast movement: ±0.8
  - Maximum speed: ±1.0

## PTZ Commands

### 1. Continuous Move
Moves the camera continuously in a specified direction until stopped.

#### Move Left
```bash
curl -v -u username:password \
-H "Content-Type: application/soap+xml" \
-H "Charset: utf-8" \
-d '<?xml version="1.0" encoding="utf-8"?>
<s:Envelope xmlns:s="http://www.w3.org/2003/05/soap-envelope">
  <s:Body xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema">
    <ContinuousMove xmlns="http://www.onvif.org/ver20/ptz/wsdl">
      <ProfileToken>PROFILE_000</ProfileToken>
      <Velocity>
        <PanTilt xmlns="http://www.onvif.org/ver10/schema" x="-0.5" y="0" space="http://www.onvif.org/ver10/tptz/PanTiltSpaces/VelocityGenericSpace"/>
      </Velocity>
    </ContinuousMove>
  </s:Body>
</s:Envelope>' \
http://<your camera ip>:8899/onvif/ptz_service
```

#### Move Right
```bash
# Same as Move Left but with x="0.5"
```

#### Move Up
```bash
# Same as Move Left but with x="0" y="0.5"
```

#### Move Down
```bash
# Same as Move Left but with x="0" y="-0.5"
```

#### Diagonal Movement
```bash
# Combine x and y values for diagonal movement
# Example: Up-Right: x="0.5" y="0.5"
# Example: Down-Left: x="-0.5" y="-0.5"
```

### 2. Stop Movement
Stops any ongoing PTZ movement.

```bash
curl -v -u username:password \
-H "Content-Type: application/soap+xml" \
-H "Charset: utf-8" \
-d '<?xml version="1.0" encoding="utf-8"?>
<s:Envelope xmlns:s="http://www.w3.org/2003/05/soap-envelope">
  <s:Body xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema">
    <Stop xmlns="http://www.onvif.org/ver20/ptz/wsdl">
      <ProfileToken>PROFILE_000</ProfileToken>
      <PanTilt>true</PanTilt>
      <Zoom>true</Zoom>
    </Stop>
  </s:Body>
</s:Envelope>' \
http://<your camera ip>:8899/onvif/ptz_service
```

### 3. Absolute Move
Moves the camera to a specific absolute position.

```bash
curl -v -u username:password \
-H "Content-Type: application/soap+xml" \
-H "Charset: utf-8" \
-d '<?xml version="1.0" encoding="utf-8"?>
<s:Envelope xmlns:s="http://www.w3.org/2003/05/soap-envelope">
  <s:Body xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema">
    <AbsoluteMove xmlns="http://www.onvif.org/ver20/ptz/wsdl">
      <ProfileToken>PROFILE_000</ProfileToken>
      <Position>
        <PanTilt xmlns="http://www.onvif.org/ver10/schema" x="0.5" y="0.5" space="http://www.onvif.org/ver10/tptz/PanTiltSpaces/PositionGenericSpace"/>
      </Position>
    </AbsoluteMove>
  </s:Body>
</s:Envelope>' \
http://<your camera ip>:8899/onvif/ptz_service
```

### 4. Relative Move
Moves the camera relative to its current position.

```bash
curl -v -u username:password \
-H "Content-Type: application/soap+xml" \
-H "Charset: utf-8" \
-d '<?xml version="1.0" encoding="utf-8"?>
<s:Envelope xmlns:s="http://www.w3.org/2003/05/soap-envelope">
  <s:Body xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema">
    <RelativeMove xmlns="http://www.onvif.org/ver20/ptz/wsdl">
      <ProfileToken>PROFILE_000</ProfileToken>
      <Translation>
        <PanTilt xmlns="http://www.onvif.org/ver10/schema" x="0.1" y="0.1" space="http://www.onvif.org/ver10/tptz/PanTiltSpaces/TranslationGenericSpace"/>
      </Translation>
    </RelativeMove>
  </s:Body>
</s:Envelope>' \
http://<your camera ip>:8899/onvif/ptz_service
```

### 5. Get PTZ Status
Retrieves the current status of the PTZ camera.

```bash
curl -v -u username:password \
-H "Content-Type: application/soap+xml" \
-H "Charset: utf-8" \
-d '<?xml version="1.0" encoding="utf-8"?>
<s:Envelope xmlns:s="http://www.w3.org/2003/05/soap-envelope">
  <s:Body xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema">
    <GetStatus xmlns="http://www.onvif.org/ver20/ptz/wsdl">
      <ProfileToken>PROFILE_000</ProfileToken>
    </GetStatus>
  </s:Body>
</s:Envelope>' \
http://<your camera ip>:8899/onvif/ptz_service
```

### 6. Set/Get Presets
#### Set Preset
```bash
curl -v -u username:password \
-H "Content-Type: application/soap+xml" \
-H "Charset: utf-8" \
-d '<?xml version="1.0" encoding="utf-8"?>
<s:Envelope xmlns:s="http://www.w3.org/2003/05/soap-envelope">
  <s:Body xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema">
    <SetPreset xmlns="http://www.onvif.org/ver20/ptz/wsdl">
      <ProfileToken>PROFILE_000</ProfileToken>
      <PresetName>Preset1</PresetName>
    </SetPreset>
  </s:Body>
</s:Envelope>' \
http://<your camera ip>:8899/onvif/ptz_service
```

#### Get Presets
```bash
curl -v -u username:password \
-H "Content-Type: application/soap+xml" \
-H "Charset: utf-8" \
-d '<?xml version="1.0" encoding="utf-8"?>
<s:Envelope xmlns:s="http://www.w3.org/2003/05/soap-envelope">
  <s:Body xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema">
    <GetPresets xmlns="http://www.onvif.org/ver20/ptz/wsdl">
      <ProfileToken>PROFILE_000</ProfileToken>
    </GetPresets>
  </s:Body>
</s:Envelope>' \
http://<your camera ip>:8899/onvif/ptz_service
```

#### Go To Preset
```bash
curl -v -u username:password \
-H "Content-Type: application/soap+xml" \
-H "Charset: utf-8" \
-d '<?xml version="1.0" encoding="utf-8"?>
<s:Envelope xmlns:s="http://www.w3.org/2003/05/soap-envelope">
  <s:Body xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema">
    <GotoPreset xmlns="http://www.onvif.org/ver20/ptz/wsdl">
      <ProfileToken>PROFILE_000</ProfileToken>
      <PresetToken>1</PresetToken>
    </GotoPreset>
  </s:Body>
</s:Envelope>' \
http://<your camera ip>:8899/onvif/ptz_service
```

## Notes
- All velocity and position values are between -1.0 and 1.0
- The camera may have specific limitations on movement ranges
- Some commands may not be supported by all camera models
- Always stop ongoing movements before starting new ones
- Use appropriate speed values based on your needs (slower for precise movements, faster for quick positioning)

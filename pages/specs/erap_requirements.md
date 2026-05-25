---
type: spec
id: SPEC-ERAP
title: "ERAP Integration — Complete Technical Specification"
tags: [spec, erap, integration, gost, smartbridge, soap]
date: 2026-04-06
related: [SYS-ERAP, cameras, smartbridge, koap_speed_fines]
source: raw/asylbek-apr6/ (6 Apr 2026 — Asylbek docs via Telegram)
last_updated: 2026-04-06
source_count: 1
status: reviewed
---
# ERAP Integration — Complete Technical Specification

**Source:** Asylbek docs (6 Apr 2026) — violation receiver schema, SmartBridge requirements, ШЭП/EDS specs, sample XML
**Service Key:** `erap_violation_receiver`
**Owner:** Комитет по правовой статистике и специальным учетам Генеральной прокуратуры РК
**System:** ИС ЕРАП (Единый реестр административных производств)

## 1. Service Overview

- **Protocol:** SOAP (synchronous)
- **Transport:** HTTPS
- **Security:** WS-Security with ЭЦП (XML Signature)
- **Namespace:** `http://esb.sergek.kz/cxf/violation`
- **Response namespace:** `http://otgroup.kz/`
- **Service key:** `erap_violation_receiver`
- **Flow:** Our Server → ВШЭП Gateway → ИС ЕРАП

## 2. Request Fields (Параметры запроса)

| Field | Description | Example | Required |
|-------|-------------|---------|----------|
| serviceId | Service UUID | c30c35ec-19e8-4703-997f-d5318636dac4 | Yes |
| clientId | Client UUID (our system) | 57aced76-9452-4484-8755-5f2d8a265a1d | Yes |
| messageId | Unique message ID | 104084560 | Yes |
| sendAt | Send timestamp | 2023-03-27T04:45:09 | Yes |
| source | Sender system ID | 59 | Yes |
| Signature | Transport EDS signature | (base64) | Yes |
| plate_number | License plate (ГРНЗ) | 489AAC02 | Yes |
| plateNumberType | Plate type | military, civilian, diplomatic | No |
| event_time | Violation timestamp | 2023-03-27T08:54:11 | Yes |
| violation_code | Violation type | speed_limit, bus_lane | Yes |
| speed | Recorded speed (km/h) | 80 | Yes |
| delta_speed | Measurement error (km/h) | 2 | Yes |
| speed_limit | Speed limit (km/h) | 60 | Yes |
| road_lane | Lane number | 2 | Yes |
| location_id | Location identifier | ALMLU234 | Yes |
| location_title | Location name (RU) | Алатауский район, ЛУ 234... | Yes |
| location_title_kaz | Location name (KZ) | Алатау ауданы... | Yes |
| district_code | District code | 197512 | Yes |
| latitude | GPS latitude | 43.2319 | Yes |
| longitude | GPS longitude | 76.77981 | Yes |
| device_number | Device/camera ID | ALMLU234 | Yes |
| certificate_number | Metrology certificate # | RK-06-02-210314 | Yes |
| certificate_issue_date | Cert issue date | 2021-07-20T00:00:00 | Yes |
| certificate_expire_date | Cert expiry date | 2023-07-20T00:00:00 | Yes |
| direction_travel | Travel direction code | 6 | No |
| direction_street | Street direction (RU) | от ул. Ашимова в сторону ул. Алатау | No |
| direction_street_kaz | Street direction (KZ) | Әшімов көшесі арқылы... | No |
| lp_shape | Plate shape type | 2 | No |
| **plate_frame** | **Plate crop photo (base64 JPG)** | /9j/4AAQ... | **Yes** |
| **car_frame** | **Vehicle photo (base64 JPG)** | /9j/4AAQ... | **Yes** |
| **frame** | **Violation photo (base64 JPG)** | /9j/4AAQ... | **Yes** |
| **fix_frame** | **Overview photo (base64 JPG)** | /9j/4AAQ... | **Yes** |
| clean_frame | Additional overview (base64 JPG) | /9j/4AAQ... | No |
| **video_frame** | **Overview video (base64 MP4)** | AAAAI... | **Yes** |
| ptz_frame | Additional PTZ video (base64 MP4) | ... | No |
| observe_video_frame | Observation video (base64) | ... | No |

## 3. Response Fields (Параметры ответа)

| Field | Description | Example |
|-------|-------------|---------|
| Return | Success flag | 1 |
| faultcode | Error code (if error) | 123 |
| faultstring | Error description | ... |

**SmartBridge envelope codes:**
- SCSS001 = Success
- SCSE002 = Business data error (see faultstring)
- SCSE003 = Unhandled exception

## 4. SOAP Envelope Structure

```xml
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
  xmlns:ns1="http://esb.sergek.kz/cxf/violation"
  xmlns:otg="http://otgroup.kz/">
  <soapenv:Header/>
  <soapenv:Body>
    <data xsi:type="ns1:onEvent">
      <ns1:violation>
        <ns1:service_id>...</ns1:service_id>
        <ns1:client_id>...</ns1:client_id>
        <!-- ... all fields from table above ... -->
        <ns1:plate_frame>
          <ns1:content>(base64 encoded JPG)</ns1:content>
          <ns1:ext>jpg</ns1:ext>
        </ns1:plate_frame>
        <ns1:video_frame>
          <ns1:content>(base64 encoded MP4)</ns1:content>
          <ns1:ext>mp4</ns1:ext>
        </ns1:video_frame>
      </ns1:violation>
    </data>
  </soapenv:Body>
</soapenv:Envelope>
```

## 5. Performance Requirements (SmartBridge SLA)

| Metric | Requirement |
|--------|------------|
| Max response time | 30 seconds |
| Avg response time | 10 seconds |
| Peak load | 2000 requests/hour |
| Nominal load | 360 requests/hour |
| Availability | 365/7/24 |
| Recovery time | 3 hours |

## 6. EDS/ЭЦП Requirements

### Algorithm Standards
- **Signature:** ГОСТ 34.311-95
- **Keys:** ГОСТ 34.310-2004
- **Format:** XML Signature (W3C) / XAdES (ETSI TS 101 903 V1.2.2)

### Validation Rules
1. Certificate must be issued by НУЦ РК (NCA of RK)
2. Check IIN/BIN of sender matches certificate
3. Check NotBefore / NotAfter (Astana timezone)
4. Build full chain to trusted root CA
5. Check revocation via OCSP (НУЦ РК service)
6. Fallback: Base CRL + Delta CRL if OCSP unavailable
7. Check KeyUsage: "Digital Signature" + "Non-repudiation" for signing
8. WS-Security envelope for transport signature

### Application
- Sign every request with organization EDS (not personal)
- Transport signature in `<Signature>` field
- ВШЭП verifies signature before forwarding to ЕРАП

## 7. Logging Requirements

### Mandatory Fields
- Date/time (DD:MM:YYYY, HH:MM:SS)
- Source service name
- User account/ID
- Client IP
- Operation start/end time
- Event level: Alerts, Critical, Errors, Warning, Notifications, Informational, Debug
- Event category
- Event description

### Retention
- **Minimum 3 years** total retention
- **Minimum 3 months** online access
- UTF-8 encoding
- Key-value pairs format
- Unique transaction IDs throughout pipeline
- SIEM integration via syslog (RFC 5424)

## 8. Violation Types Supported

From VMS analytics requirements:
- `speed_limit` — Speed violation (radar)
- `bus_lane` — Bus lane driving
- `red_light` — Red light running
- `stop_line` — Stop line crossing on red
- `road_signs` — Road sign/marking violations

## 9. Blockers & Dependencies

| Item | Status | Owner |
|------|--------|-------|
| SmartBridge registration + OID | PENDING | Asylbek/Aidana |
| ECP certificate (OID → ECP → KalkanCrypt) | PENDING | Aidana → Roza |
| 109 APK metrology certificates expired | EXPIRED since Dec 2024 | Must renew |
| SmartBridge test env application | Apply via sb.egov.kz Monday | Asylbek |

## See also
- [[erap|ERAP Pipeline Technical]]
- [[cameras|Camera Network]]
- [[smartbridge-concept|SmartBridge]]
- [[koap_speed_fines|KoAP Speed Fines]]
- [[erap-concept|GOST Crypto]]

# Chiller Operations Manual — Chiller-03 (M126)

**Document type:** Operations Manual  
**Asset type:** chiller  
**Asset ID:** Chiller-03, M126

## 1. Overview

Chiller-03 (M126) is a water-cooled centrifugal chiller serving the building chilled-water (CHW) loop. Normal operation is monitored through OPC UA tags including CHW supply/return temperatures, condenser water (CW) supply/return temperatures, percent RLA load, primary header flows, cooling tower control signals, and outdoor wet-bulb temperature.

## 2. Normal Operating Ranges

| Parameter | Normal Range | Unit | Notes |
|-----------|--------------|------|-------|
| CHW Supply | 42–46 | °F | At setpoint under steady load |
| CHW Return | 52–58 | °F | Depends on building load |
| CHW Delta-T | 10–14 | °F | CHW_Return minus CHW_Supply |
| CW Supply | 80–90 | °F | Elevated in high wet-bulb conditions |
| CW Return | 90–100 | °F | Typically 8–12 °F above CW supply |
| CW Delta-T | 8–12 | °F | CW_Return minus CW_Supply |
| RLA_Avg | 20–85 | % | Below 5% indicates OFF state |
| PH1_FLOW + PH2_FLOW | 1,600–2,200 | gal/min combined | Verify both headers |
| CW Approach to Wet Bulb | 6–12 | °F | CW_Supply minus WET_BULB |

## 3. Condenser Water Performance

Condenser heat rejection depends on cooling tower operation and condenser water flow. A healthy system maintains stable CW delta-T and approach temperature relative to wet bulb.

**Warning signs:**
- CW approach to wet bulb rising above 14 °F for sustained periods
- CW delta-T below 6 °F at moderate-to-high RLA
- CW supply temperature rising while wet bulb is stable

**Likely causes:**
1. Reduced condenser water flow (partially closed valve, pump issue, strainer blockage)
2. Cooling tower fill media fouling or reduced airflow
3. Tower fan or VFD tracking problem (compare FEEDBACK vs SIGNAL)
4. Non-condensables or refrigerant charge issue (requires specialist)

## 4. Chilled Water Performance

CHW delta-T below 8 °F at high load may indicate low flow, bypass leakage, or control instability. CHW return temperature rising above setpoint band while RLA is high suggests the chiller cannot meet load.

## 5. Load and Electrical Balance

Monitor RLA_L1, RLA_L2, RLA_L3 for phase imbalance. RLA spread above 15% between phases at steady load warrants investigation. Compare phase currents (CURRENT_L1, CURRENT_L2, CURRENT_L3) against RLA readings.

## 6. Operator Response to Elevated Anomaly Score

When the LOF anomaly detection model flags Chiller-03:

1. Confirm chiller is in STEADY STATE (RLA_Avg > 5%, not in startup transient).
2. Review latest CHW and CW delta-T against baseline.
3. Check CW approach to wet bulb and total condenser flow (PH1_FLOW + PH2_FLOW).
4. Inspect cooling tower FEEDBACK vs SIGNAL tracking error.
5. Escalate to maintenance if condenser-side indicators are abnormal before adjusting setpoints.

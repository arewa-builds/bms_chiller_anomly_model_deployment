# Cooling Tower Troubleshooting Guide

**Document type:** Troubleshooting Guide  
**Asset type:** cooling_tower  
**Related asset:** Chiller-03 condenser loop

## 1. Purpose

This guide covers diagnosis of cooling tower and condenser water loop problems that affect chiller efficiency and may trigger anomaly alerts on Chiller-03.

## 2. Key Sensors

| Tag | Description |
|-----|-------------|
| CW_Supply | Condenser water leaving the tower (°F) |
| CW_Return | Condenser water entering the tower (°F) |
| WET_BULB | Outdoor wet-bulb temperature (°F) |
| FEEDBACK | Tower fan/VFD actual position (%) |
| SIGNAL | Tower fan/VFD commanded position (%) |
| PH1_FLOW | Primary header flow 1 (gal/min) |
| PH2_FLOW | Primary header flow 2 (gal/min) |

## 3. Approach Temperature Diagnostics

**CW approach to wet bulb** = CW_Supply − WET_BULB

| Approach (°F) | Interpretation |
|---------------|----------------|
| 6–10 | Normal |
| 10–14 | Monitor — possible degradation |
| > 14 | Investigate — tower or flow problem likely |

An elevated approach with normal wet bulb usually points to tower performance or condenser flow restriction, not ambient conditions alone.

## 4. Tower Tracking Error

**Tower tracking error** = FEEDBACK − SIGNAL

| Condition | Action |
|-----------|--------|
| \|error\| < 5% | Normal tracking |
| \|error\| 5–15% | Check VFD, linkage, or controller tuning |
| SIGNAL > 50% and error < −10% | Tower non-response flag — fan may not be responding to command |

Inspect mechanical linkage, VFD faults, and basin water level before adjusting control setpoints.

## 5. Condenser Flow Problems

**Total flow** = PH1_FLOW + PH2_FLOW

**Flow imbalance** = |PH1_FLOW − PH2_FLOW|

High flow imbalance percentage (> 15%) suggests a partially closed isolation valve, air binding, or pump cavitation on one header.

**Investigation steps:**
1. Verify isolation valve positions on PH1 and PH2.
2. Check pump suction strainers and differential pressure.
3. Compare flow readings against historical baseline at similar RLA.
4. Inspect for air in the loop at high points.

## 6. Common Failure Patterns

### Pattern A: Elevated approach, normal flow
- Fouled tower fill or scale on heat transfer surfaces
- Reduced airflow (fan belt, motor, debris on intake)
- Inadequate water distribution over fill

### Pattern B: Elevated approach, reduced flow
- Partially closed valve
- Pump performance degradation
- Strainer or pipe blockage

### Pattern C: Low CW delta-T at high load
- Excessive condenser flow (over-pumping) or sensor calibration issue
- Verify CW_Return and CW_Supply sensor calibration

## 7. Recommended Investigation Sequence

1. Record current CW_Supply, CW_Return, WET_BULB, and compute approach.
2. Verify PH1_FLOW and PH2_FLOW against expected range for current RLA.
3. Compare FEEDBACK to SIGNAL — note tracking error magnitude.
4. Visually inspect tower basin level, fan operation, and fill condition.
5. Review maintenance history for recent chemical treatment or cleaning.

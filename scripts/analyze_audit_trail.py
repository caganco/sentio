"""Analyze backtest audit trail for macro gate conditions."""
import csv
import sys
from pathlib import Path
from collections import defaultdict
from statistics import median, stdev


def analyze_audit_trail(csv_path: str) -> None:
    """Analyze audit trail CSV for macro gate statistics."""
    csv_file = Path(csv_path)
    if not csv_file.exists():
        print(f"ERROR: {csv_path} not found")
        return

    # Load data
    rows = []
    with open(csv_file, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)

    if not rows:
        print("No audit trail data found")
        return

    print(f"\n{'='*70}")
    print(f"  AUDIT TRAIL ANALYSIS — {csv_path}")
    print(f"{'='*70}\n")

    # Extract numeric columns
    macro_scores = []
    vix_levels = []
    usdtry_changes = []
    entry_gates = []
    signals = []

    for row in rows:
        # Macro score
        try:
            macro_score = float(row.get("macro_score", ""))
            macro_scores.append(macro_score)
        except ValueError:
            pass

        # VIX level
        try:
            vix = float(row.get("vix_level", ""))
            if vix is not None:
                vix_levels.append(vix)
        except (ValueError, TypeError):
            pass

        # USDTRY 1d change
        try:
            usdtry = float(row.get("USDTRY_1d_change", ""))
            if usdtry is not None:
                usdtry_changes.append(usdtry)
        except (ValueError, TypeError):
            pass

        # Entry gated flag
        entry_gates.append(row.get("entry_gated", "False").lower() == "true")

        # Signal
        signals.append(row.get("signal", "HOLD"))

    # === MACRO SCORE ANALYSIS ===
    print("1. MACRO SCORE STATISTICS")
    print("-" * 70)
    if macro_scores:
        macro_min = min(macro_scores)
        macro_max = max(macro_scores)
        macro_med = median(macro_scores)
        macro_mean = sum(macro_scores) / len(macro_scores)
        print(f"   Count:         {len(macro_scores)}")
        print(f"   Min:           {macro_min:.2f}")
        print(f"   Max:           {macro_max:.2f}")
        print(f"   Median:        {macro_med:.2f}")
        print(f"   Mean:          {macro_mean:.2f}")

        # Count near-gate threshold (45)
        near_gate_macro = [x for x in macro_scores if 40.0 <= x < 50.0]
        print(f"   Near gate (40-50): {len(near_gate_macro)} days ({len(near_gate_macro)/len(macro_scores)*100:.1f}%)")

        # Below proposed threshold (50)
        below_50 = [x for x in macro_scores if x < 50.0]
        print(f"   Below 50 (proposed gate): {len(below_50)} days ({len(below_50)/len(macro_scores)*100:.1f}%)")
    else:
        print("   No macro_score data found")

    # === VIX ANALYSIS ===
    print("\n2. VIX LEVEL STATISTICS")
    print("-" * 70)
    if vix_levels:
        vix_min = min(vix_levels)
        vix_max = max(vix_levels)
        vix_med = median(vix_levels)
        vix_mean = sum(vix_levels) / len(vix_levels)
        print(f"   Count:         {len(vix_levels)}")
        print(f"   Min:           {vix_min:.2f}")
        print(f"   Max:           {vix_max:.2f}")
        print(f"   Median:        {vix_med:.2f}")
        print(f"   Mean:          {vix_mean:.2f}")

        # Count near-gate threshold (30)
        near_gate_vix = [x for x in vix_levels if 25.0 <= x < 35.0]
        print(f"   Near gate (25-35): {len(near_gate_vix)} days ({len(near_gate_vix)/len(vix_levels)*100:.1f}%)")

        # Above 30 (current gate)
        above_30 = [x for x in vix_levels if x > 30.0]
        print(f"   Above 30 (current gate): {len(above_30)} days ({len(above_30)/len(vix_levels)*100:.1f}%)")

        # Above 28 (proposed gate)
        above_28 = [x for x in vix_levels if x > 28.0]
        print(f"   Above 28 (proposed gate): {len(above_28)} days ({len(above_28)/len(vix_levels)*100:.1f}%)")
    else:
        print(f"   No vix_level data found (KEY ISSUE: vix_level not in macro_data?)")
        print(f"   Non-null vix entries in CSV: {sum(1 for row in rows if row.get('vix_level'))}")

    # === USDTRY ANALYSIS ===
    print("\n3. USDTRY 1D CHANGE STATISTICS")
    print("-" * 70)
    if usdtry_changes:
        usdtry_min = min(usdtry_changes)
        usdtry_max = max(usdtry_changes)
        usdtry_med = median(usdtry_changes)
        usdtry_mean = sum(usdtry_changes) / len(usdtry_changes)
        print(f"   Count:         {len(usdtry_changes)}")
        print(f"   Min (outflow):  {usdtry_min:.4f} ({usdtry_min*100:.2f}%)")
        print(f"   Max (inflow):   {usdtry_max:.4f} ({usdtry_max*100:.2f}%)")
        print(f"   Median:        {usdtry_med:.4f} ({usdtry_med*100:.2f}%)")
        print(f"   Mean:          {usdtry_mean:.4f} ({usdtry_mean*100:.2f}%)")

        # Positive spikes (TRY outflow)
        positive_changes = [x for x in usdtry_changes if x > 0]
        print(f"   Positive days (TRY outflow): {len(positive_changes)} ({len(positive_changes)/len(usdtry_changes)*100:.1f}%)")

        if positive_changes:
            print(f"   Max positive spike: {max(positive_changes):.4f} ({max(positive_changes)*100:.2f}%)")

        # Above 2% gate
        above_2pct = [x for x in usdtry_changes if x > 0.02]
        print(f"   Above 2% (current gate): {len(above_2pct)} days ({len(above_2pct)/len(usdtry_changes)*100:.1f}%)")

        # Above 1.5% (proposed gate)
        above_1_5pct = [x for x in usdtry_changes if x > 0.015]
        print(f"   Above 1.5% (proposed gate): {len(above_1_5pct)} days ({len(above_1_5pct)/len(usdtry_changes)*100:.1f}%)")
    else:
        print(f"   No USDTRY_1d_change data found (KEY ISSUE: USDTRY_1d_change not in macro_data?)")
        print(f"   Non-null USDTRY entries in CSV: {sum(1 for row in rows if row.get('USDTRY_1d_change'))}")

    # === ENTRY GATE STATUS ===
    print("\n4. ENTRY GATE FIRING STATUS")
    print("-" * 70)
    gated_entries = sum(entry_gates)
    total_entries = len(entry_gates)
    print(f"   Total audit entries: {total_entries}")
    print(f"   Gated entries (blocked): {gated_entries}")
    print(f"   Gated ratio: {gated_entries/total_entries*100:.2f}%")

    if gated_entries == 0:
        print("\n   ⚠️ NO GATES TRIGGERED — Thresholds too loose or macro data missing")

    # === SIGNAL DISTRIBUTION ===
    print("\n5. SIGNAL DISTRIBUTION")
    print("-" * 70)
    signal_counts = defaultdict(int)
    for sig in signals:
        signal_counts[sig] += 1

    for sig, count in sorted(signal_counts.items()):
        print(f"   {sig:15} {count:5} ({count/len(signals)*100:.1f}%)")

    # === DATA QUALITY CHECK ===
    print("\n6. DATA QUALITY CHECK")
    print("-" * 70)
    rows_with_vix = sum(1 for row in rows if row.get("vix_level"))
    rows_with_usdtry = sum(1 for row in rows if row.get("USDTRY_1d_change"))
    rows_with_macro = sum(1 for row in rows if row.get("macro_score"))

    print(f"   Rows with macro_score:       {rows_with_macro:4} / {len(rows):4} ({rows_with_macro/len(rows)*100:.1f}%)")
    print(f"   Rows with vix_level:         {rows_with_vix:4} / {len(rows):4} ({rows_with_vix/len(rows)*100:.1f}%)")
    print(f"   Rows with USDTRY_1d_change:  {rows_with_usdtry:4} / {len(rows):4} ({rows_with_usdtry/len(rows)*100:.1f}%)")

    if rows_with_vix < len(rows) * 0.5:
        print(f"\n   🔴 BUG: vix_level missing in >50% of rows — macro_data.get('vix_level') returning None?")
    if rows_with_usdtry < len(rows) * 0.5:
        print(f"\n   🔴 BUG: USDTRY_1d_change missing in >50% of rows — macro_data.get('USDTRY_1d_change') returning None?")

    print(f"\n{'='*70}\n")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python analyze_audit_trail.py <csv_path>")
        sys.exit(1)

    analyze_audit_trail(sys.argv[1])

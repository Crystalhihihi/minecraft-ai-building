# Stair orientation rules (楼梯朝向规则)

Ground truth from hand-built reference pieces (E6, 2026-07-31; full record in
the project repo at docs/research/stair-orientations.md). **Derive
facing/half/shape from geometry — never hand-pick states per block.**

Legend: `^v<>` = facing N/S/E/W (facing = the stair's high/back side; steps
descend the opposite way). `i/o` = shape inner/outer corner. `T` = half=top
(upside-down). `=` = slab.

## 1. facing / half basics

- facing = uphill direction (the tall back side). For roof slopes: every
  stair row's facing points AT the ridge.
- half=bottom: normal (walking surface, roof slope). half=top: upside-down
  (under-eave detail, arch soffit, ceiling trim).

## 2. Corner rule (围合结构转角铁律)

For any closed frame (eaves ring, parapet, crown molding): corners MUST be
corner shapes — butting two straight runs leaves gaps or bulges.

- **backs outward (steps down into the center) → inner corners**:
```
<i ^  ^i
<  .  >
vi v  vi
```
- **backs inward (steps down outward) → outer corners**:
```
vo v  vo
>  .  <
>o ^  <o
```
- Long straight runs: same facing all along; close the two ends with inner
  corners (top/bottom rows in the left example).

## 3. Smooth risers without slab filler (光滑上升梯段)

Alternate a normal stair (tread) with an upside-down stair (riser/soffit);
each level +1y. Two mirror variants:

```
y=-59: >  <T  .        y=-59: .  >T  <
y=-58: .  >  <T        y=-58: >T <   .
y=-57: .  .   >        y=-57: <  .   .
```

## 4. Stacked trim (墙裙/檐下收边)

Same column, two levels: bottom stair + top stair. Face them toward each
other (`< >` over `<T >T`) or same direction (`v` over `vT`).

## 5. Machine-checkable rules (validators)

- Every corner of a closed stair frame must have a corner shape
  (inner_*/outer_*), never "straight".
- Every stair row of a roof slope shares one facing, pointing at the ridge.
- half (bottom/top) must match the design layer; slab type likewise.

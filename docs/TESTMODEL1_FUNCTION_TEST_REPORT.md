# TestModel1 JMAG Function Test Report

## Outcome

- Source project: `C:\JMAG_Models\TestModel1.jproj` (loaded only; not saved).
- Test copy: `C:\JMAG_Models\TestModel1_function_test_20260715_steps12\TestModel1_steps12.jproj`.
- Model / study / case: `1220_RXModel` / `kVA` / `1`.
- Step relation: `Step = Div / Div_Period * 1.5 + 1`.
- Before: `Div=60.0`, 90.0 intervals, 91 points.
- After: `Div=8`, 12 intervals, 13 points.
- JMAG load, mutation, solve and export time reported by the script: 22.72 s.

`Step` was not overwritten with a literal. The existing dependency was preserved: `Div=60 -> 8`, while `Div_Period=1` and the Step expression remain unchanged.

## Selected solver results

The user did not name individual response quantities, so the script exported the complete case-value table and the complete Step result tables. The following common motor metrics are highlighted from that complete export:

| Result | Value |
| --- | ---: |
| `Average_Torque` | 80.4374891023 |
| `Vline` | 877.843355641 |
| `Irms` | 111; 111 (duplicate JMAG columns) |
| `CuLoss_eff` | 2580.79957892; 2580.79957892 (duplicate JMAG columns) |
| `PM_Loss` | 0; 50 (duplicate JMAG columns) |
| `IronLoss_Syoke` | 564.225398954; 564.225398954 (duplicate JMAG columns) |
| `IronLoss_Steeth` | 1485.19547396; 1485.19547396 (duplicate JMAG columns) |
| `IronLoss_Rotor` | 28.1076829727; 28.1076829727 (duplicate JMAG columns) |
| `Losstotal` | 5523.9414848 |
| `Slot_Fill_Factor` | 0.570182362167; Area_Conductor*Conductor_Layer/Area_Slot (duplicate JMAG columns) |

## Parameter inventory and purpose analysis

Purposes are engineering interpretations based on parameter names and expressions. Blank JMAG descriptions mean these interpretations are not authoritative model documentation.

| # | Type | Parameter | Before | After | Expression | Recorded purpose |
| ---: | --- | --- | --- | --- | --- | --- |
| 0 | Real | `CAD parameters: PMangle2@Variables` | 120 | 120 |  | CAD input synchronized to the corresponding geometry variable. Second magnet segment angle; controls rotor PM geometry. |
| 1 | Real | `CAD parameters: Rri@Variables` | 30 | 30 |  | CAD input synchronized to the corresponding geometry variable. Rotor inner radius CAD variable. |
| 2 | Real | `CAD parameters: Rso@Variables` | 116.5 | 116.5 |  | CAD input synchronized to the corresponding geometry variable. Stator outer radius. |
| 3 | Real | `CAD parameters: airgap@Variables` | 0.8 | 0.8 |  | CAD input synchronized to the corresponding geometry variable. Mechanical air-gap length. |
| 4 | Real | `CAD parameters: arcangle1@Variables` | 14 | 14 |  | CAD input synchronized to the corresponding geometry variable. First rotor/magnet arc angle. |
| 5 | Real | `CAD parameters: arcangle2@Variables` | 25 | 25 |  | CAD input synchronized to the corresponding geometry variable. Second rotor/magnet arc angle. |
| 6 | Real | `CAD parameters: d1@Variables` | 0.4 | 0.4 |  | CAD input synchronized to the corresponding geometry variable. Local rotor/magnet geometry offset d1. |
| 7 | Real | `CAD parameters: d2@Variables` | 0.4 | 0.4 |  | CAD input synchronized to the corresponding geometry variable. Local rotor/magnet geometry offset d2. |
| 8 | Real | `CAD parameters: d3@Variables` | 0.4 | 0.4 |  | CAD input synchronized to the corresponding geometry variable. Local rotor/magnet geometry offset d3. |
| 9 | Real | `CAD parameters: d4@Variables` | 0.4 | 0.4 |  | CAD input synchronized to the corresponding geometry variable. Local rotor/magnet geometry offset d4. |
| 10 | Real | `CAD parameters: dPM1@Variables` | 2.8 | 2.8 |  | CAD input synchronized to the corresponding geometry variable. First permanent-magnet thickness parameter. |
| 11 | Real | `CAD parameters: dPM2@Variables` | 2.8 | 2.8 |  | CAD input synchronized to the corresponding geometry variable. Second permanent-magnet thickness parameter. |
| 12 | Real | `CAD parameters: dair@Variables` | 0.05 | 0.05 |  | CAD input synchronized to the corresponding geometry variable. Local air-region clearance in the rotor geometry. |
| 13 | Real | `CAD parameters: dbridge11@Variables` | 0.7 | 0.7 |  | CAD input synchronized to the corresponding geometry variable. Rotor bridge thickness for bridge 1-1. |
| 14 | Real | `CAD parameters: dbridge12@Variables` | 0.7 | 0.7 |  | CAD input synchronized to the corresponding geometry variable. Rotor bridge thickness for bridge 1-2. |
| 15 | Real | `CAD parameters: dbridge21@Variables` | 0.8 | 0.8 |  | CAD input synchronized to the corresponding geometry variable. Rotor bridge thickness for bridge 2-1. |
| 16 | Real | `CAD parameters: dbridge22@Variables` | 0.8 | 0.8 |  | CAD input synchronized to the corresponding geometry variable. Rotor bridge thickness for bridge 2-2. |
| 17 | Real | `CAD parameters: dbridge23@Variables` | 0.8 | 0.8 |  | CAD input synchronized to the corresponding geometry variable. Rotor bridge thickness for bridge 2-3. |
| 18 | Real | `CAD parameters: dslot@Variables` | 4 | 4 |  | CAD input synchronized to the corresponding geometry variable. Rotor/stator slot local width or clearance parameter. |
| 19 | Real | `CAD parameters: dso@Variables` | 0.5 | 0.5 |  | CAD input synchronized to the corresponding geometry variable. Slot-opening width parameter. |
| 20 | Real | `CAD parameters: dyoke@Variables` | 19 | 19 |  | CAD input synchronized to the corresponding geometry variable. Stator yoke radial thickness. |
| 21 | Real | `CAD parameters: hcore1@Variables` | 6 | 6 |  | CAD input synchronized to the corresponding geometry variable. First rotor core height parameter. |
| 22 | Real | `CAD parameters: hcore2@Variables` | 8 | 8 |  | CAD input synchronized to the corresponding geometry variable. Second rotor core height parameter. |
| 23 | Real | `CAD parameters: hslot@Variables` | 16 | 16 |  | CAD input synchronized to the corresponding geometry variable. Stator slot height. |
| 24 | Real | `CAD parameters: hso@Variables` | 1 | 1 |  | CAD input synchronized to the corresponding geometry variable. Stator slot-opening height. |
| 25 | Real | `CAD parameters: hwedge@Variables` | 1.2 | 1.2 |  | CAD input synchronized to the corresponding geometry variable. Slot-wedge height. |
| 26 | Real | `CAD parameters: lPM1@Variables` | 6 | 6 |  | CAD input synchronized to the corresponding geometry variable. First permanent-magnet length parameter. |
| 27 | Real | `CAD parameters: lPM21@Variables` | 5 | 5 |  | CAD input synchronized to the corresponding geometry variable. Second PM section length, segment 1. |
| 28 | Real | `CAD parameters: lPM22@Variables` | 6.5 | 6.5 |  | CAD input synchronized to the corresponding geometry variable. Second PM section length, segment 2. |
| 29 | Real | `CAD parameters: lPMslot21@Variables` | 8 | 8 |  | CAD input synchronized to the corresponding geometry variable. Second PM-slot length, segment 1. |
| 30 | Real | `CAD parameters: lPMslot22@Variables` | 16 | 16 |  | CAD input synchronized to the corresponding geometry variable. Second PM-slot length, segment 2. |
| 31 | Real | `CAD parameters: lbridge11@Variables` | 2.5 | 2.5 |  | CAD input synchronized to the corresponding geometry variable. Rotor bridge length for bridge 1-1. |
| 32 | Real | `CAD parameters: lbridge12@Variables` | 2.4 | 2.4 |  | CAD input synchronized to the corresponding geometry variable. Rotor bridge length for bridge 1-2. |
| 33 | Real | `CAD parameters: lbridge21@Variables` | 2.7 | 2.7 |  | CAD input synchronized to the corresponding geometry variable. Rotor bridge length for bridge 2-1. |
| 34 | Real | `CAD parameters: lbridge22@Variables` | 1.1 | 1.1 |  | CAD input synchronized to the corresponding geometry variable. Rotor bridge length for bridge 2-2. |
| 35 | Real | `CAD parameters: lbridge23@Variables` | 2.8 | 2.8 |  | CAD input synchronized to the corresponding geometry variable. Rotor bridge length for bridge 2-3. |
| 36 | Real | `CAD parameters: r0@Variables` | 0.5 | 0.5 |  | CAD input synchronized to the corresponding geometry variable. Local geometry fillet radius r0. |
| 37 | Real | `CAD parameters: r1@Variables` | 0.2 | 0.2 |  | CAD input synchronized to the corresponding geometry variable. Local geometry fillet radius r1. |
| 38 | Equation | `Equation parameters: Rso` | 116.5 | 116.5 | `116.5` | Stator outer radius. |
| 39 | Equation | `Equation parameters: Ri` | 30 | 30 | `30` | Rotor inner radius used by the parametric geometry. |
| 40 | Equation | `Equation parameters: d1` | 0.4 | 0.4 | `0.4` | Local rotor/magnet geometry offset d1. |
| 41 | Equation | `Equation parameters: d2` | 0.4 | 0.4 | `0.4` | Local rotor/magnet geometry offset d2. |
| 42 | Equation | `Equation parameters: d3` | 0.4 | 0.4 | `0.4` | Local rotor/magnet geometry offset d3. |
| 43 | Equation | `Equation parameters: d4` | 0.4 | 0.4 | `0.4` | Local rotor/magnet geometry offset d4. |
| 44 | Equation | `Equation parameters: dair` | 0.05 | 0.05 | `0.05` | Local air-region clearance in the rotor geometry. |
| 45 | Equation | `Equation parameters: dbridge11` | 0.7 | 0.7 | `0.7` | Rotor bridge thickness for bridge 1-1. |
| 46 | Equation | `Equation parameters: dPM2` | 2.8 | 2.8 | `2.8` | Second permanent-magnet thickness parameter. |
| 47 | Equation | `Equation parameters: dbridge21` | 0.8 | 0.8 | `0.8` | Rotor bridge thickness for bridge 2-1. |
| 48 | Equation | `Equation parameters: dbridge12` | 0.7 | 0.7 | `0.7` | Rotor bridge thickness for bridge 1-2. |
| 49 | Equation | `Equation parameters: dbridge22` | 0.8 | 0.8 | `0.8` | Rotor bridge thickness for bridge 2-2. |
| 50 | Equation | `Equation parameters: dbridge23` | 0.8 | 0.8 | `0.8` | Rotor bridge thickness for bridge 2-3. |
| 51 | Equation | `Equation parameters: dso` | 0.5 | 0.5 | `0.5` | Slot-opening width parameter. |
| 52 | Equation | `Equation parameters: hcore1` | 6 | 6 | `6` | First rotor core height parameter. |
| 53 | Equation | `Equation parameters: hcore2` | 8 | 8 | `8` | Second rotor core height parameter. |
| 54 | Equation | `Equation parameters: hso` | 1 | 1 | `1` | Stator slot-opening height. |
| 55 | Equation | `Equation parameters: hwedge` | 1.2 | 1.2 | `1.2` | Slot-wedge height. |
| 56 | Equation | `Equation parameters: lPMslot21` | 8 | 8 | `8` | Second PM-slot length, segment 1. |
| 57 | Equation | `Equation parameters: lbridge12` | 2.4 | 2.4 | `2.4` | Rotor bridge length for bridge 1-2. |
| 58 | Equation | `Equation parameters: lbridge11` | 2.5 | 2.5 | `2.5` | Rotor bridge length for bridge 1-1. |
| 59 | Equation | `Equation parameters: lbridge21` | 2.7 | 2.7 | `2.7` | Rotor bridge length for bridge 2-1. |
| 60 | Equation | `Equation parameters: lbridge22` | 1.1 | 1.1 | `1.1` | Rotor bridge length for bridge 2-2. |
| 61 | Equation | `Equation parameters: lbridge23` | 2.8 | 2.8 | `2.8` | Rotor bridge length for bridge 2-3. |
| 62 | Equation | `Equation parameters: r0` | 0.5 | 0.5 | `0.5` | Local geometry fillet radius r0. |
| 63 | Equation | `Equation parameters: r1` | 0.2 | 0.2 | `0.2` | Local geometry fillet radius r1. |
| 64 | Real | `Study Properties: ModelThickness` | 160 | 160 |  | 2-D model extrusion/stack thickness used by the study. |
| 65 | Flag | `Study Properties: Step` | 91 | 13 |  | Total transient sample points; derived as intervals plus the initial point. |
| 66 | Flag | `Study Properties: StepDivision` | 60 | 8 |  | Study step-division setting linked to the Div equation. |
| 67 | Real | `CS1 (3PhaseCurrentSource): PhaseU` | 71.5 | 71.5 |  | Phase-U angle applied to the three-phase current source. |
| 68 | Equation | `Equation parameters: lPMslot22` | 16 | 16 | `16` | Second PM-slot length, segment 2. |
| 69 | Equation | `Equation parameters: Vline_limit` | 1046.96 | 1046.96 | `1046.96` | Maximum allowed line voltage for operating-point checks. |
| 70 | Equation | `Equation parameters: Initial_Position` | 2.5*360/54-180/12 | 2.5*360/54-180/12 | `2.5*360/54-180/12` | Initial rotor position derived from slot/pole geometry. |
| 71 | Real | `roate (RotationMotion2D): InitialRotationAngle` | 1.6666666666666679 | 1.6666666666666679 |  | Initial mechanical rotor angle applied to the motion condition. |
| 72 | Equation | `Equation parameters: J_limit` | 40 | 40 | `40` | Current-density limit used to derive the allowable RMS current. |
| 73 | Equation | `Equation parameters: ab` | 2 | 2 | `2` | Number of parallel winding branches. |
| 74 | Equation | `Equation parameters: fre` | speed*Poles/2/60 | speed*Poles/2/60 | `speed*Poles/2/60` | Electrical frequency derived from speed and pole count. |
| 75 | Equation | `Equation parameters: Poles` | 12 | 12 | `12` | Pole count used by the electrical-frequency expression. |
| 76 | Equation | `Equation parameters: Phase_Advance` | 71.5 | 71.5 | `71.5` | Current phase-advance angle. |
| 77 | Equation | `Equation parameters: Copper_Resistivity` | 2.34218e-8 | 2.34218e-8 | `2.34218e-8` | Copper resistivity assigned to the electromagnetic model. |
| 78 | Equation | `Equation parameters: Conductor_Layer` | 8 | 8 | `8` | Number of conductor layers used by the slot-fill expression. |
| 79 | Equation | `Equation parameters: speed` | 18000 | 18000 | `18000` | Mechanical rotor speed in r/min. |
| 80 | Equation | `Equation parameters: Magnet_Conductivity` | 62500000 | 62500000 | `62500000` | Electrical conductivity assigned to the permanent magnets. |
| 81 | Equation | `Equation parameters: dPM1` | 2.8 | 2.8 | `2.8` | First permanent-magnet thickness parameter. |
| 82 | Equation | `Equation parameters: dslot` | 4 | 4 | `4` | Rotor/stator slot local width or clearance parameter. |
| 83 | Equation | `Equation parameters: dyoke` | 19 | 19 | `19` | Stator yoke radial thickness. |
| 84 | Equation | `Equation parameters: hslot` | 16 | 16 | `16` | Stator slot height. |
| 85 | Equation | `Equation parameters: airgap` | 0.8 | 0.8 | `0.8` | Mechanical air-gap length. |
| 86 | Equation | `Equation parameters: arcangle2` | 25 | 25 | `25` | Second rotor/magnet arc angle. |
| 87 | Equation | `Equation parameters: arcangle1` | 14 | 14 | `14` | First rotor/magnet arc angle. |
| 88 | Equation | `Equation parameters: PMangle2` | 120 | 120 | `120` | Second magnet segment angle; controls rotor PM geometry. |
| 89 | Equation | `Equation parameters: lPM1` | 6 | 6 | `6` | First permanent-magnet length parameter. |
| 90 | Equation | `Equation parameters: lPM22` | 6.5 | 6.5 | `6.5` | Second PM section length, segment 2. |
| 91 | Equation | `Equation parameters: lPM21` | 5 | 5 | `5` | Second PM section length, segment 1. |
| 92 | Equation | `Equation parameters: CoilEnd` | 0 | 0 | `0` | End-winding modeling/control flag. |
| 93 | Equation | `Equation parameters: Torque_Required` | 400 | 400 | `400` | Target torque used by the operating-point/optimization setup. |
| 94 | Equation | `Equation parameters: Stack_Length` | 160 | 160 | `160` | Active axial stack length used in loss and mass calculations. |
| 95 | Equation | `Equation parameters: poles` | 12 | 12 | `12` | Pole count used by geometric end-winding expressions. |
| 96 | Equation | `Equation parameters: Conductor_Layers` | 8 | 8 | `8` | Conductor-layer count used in copper-loss calculations. |
| 97 | Equation | `Equation parameters: Slot_Number` | 54 | 54 | `54` | Stator slot count. |
| 98 | Equation | `Equation parameters: Tem_Magnets` | 80 | 80 | `80` | Magnet operating temperature. |
| 99 | Equation | `Equation parameters: Tem_End_Winding` | 100 | 100 | `100` | End-winding conductor temperature. |
| 100 | Equation | `Equation parameters: DC_Copper_Lossef` | Irms*Irms/ab/ab/Area_Conductor*Slot_Number*Conductor_Layers*Stack_Length*Curesistivity_Eff*1000 | Irms*Irms/ab/ab/Area_Conductor*Slot_Number*Conductor_Layers*Stack_Length*Curesistivity_Eff*1000 | `Irms*Irms/ab/ab/Area_Conductor*Slot_Number*Conductor_Layers*Stack_Length*Curesistivity_Eff*1000` | Calculated active-length DC copper loss. |
| 101 | Equation | `Equation parameters: End_Winding_Length` | 10+(Rso-dyoke-hslot/2-d1+d3)*2*pi/poles*sqrt(2) | 10+(Rso-dyoke-hslot/2-d1+d3)*2*pi/poles*sqrt(2) | `10+(Rso-dyoke-hslot/2-d1+d3)*2*pi/poles*sqrt(2)` | Estimated end-winding conductor length. |
| 102 | Equation | `Equation parameters: DC_Copper_Lossend` | Irms*Irms/ab/ab/Area_Conductor*Slot_Number*Conductor_Layers*End_Winding_Length*Curesistivity_End*1000 | Irms*Irms/ab/ab/Area_Conductor*Slot_Number*Conductor_Layers*End_Winding_Length*Curesistivity_End*1000 | `Irms*Irms/ab/ab/Area_Conductor*Slot_Number*Conductor_Layers*End_Winding_Length*Curesistivity_End*1000` | Calculated end-winding DC copper loss. |
| 103 | Equation | `Equation parameters: End_Winding_Height` | 5+(Rso-dyoke-hslot/2-d1+d3)*pi/poles | 5+(Rso-dyoke-hslot/2-d1+d3)*pi/poles | `5+(Rso-dyoke-hslot/2-d1+d3)*pi/poles` | Estimated axial/radial end-winding envelope height. |
| 104 | Equation | `Equation parameters: Cu_Tem_Cof` | 0.0039 | 0.0039 | `0.0039` | Copper temperature coefficient of resistivity. |
| 105 | Equation | `Equation parameters: Magnet_Tem_Cof` | -0.002 | -0.002 | `-0.002` | Magnet temperature coefficient used by project calculations. |
| 106 | Equation | `Equation parameters: Rsi` | Rso-dyoke-hslot-hso-hwedge | Rso-dyoke-hslot-hso-hwedge | `Rso-dyoke-hslot-hso-hwedge` | Derived stator inner radius. |
| 107 | Equation | `Equation parameters: Area_Slot` | ((Rso*Rso-Rsi*Rsi)*pi/6-Area_StatorIron)/9-hso*dso | ((Rso*Rso-Rsi*Rsi)*pi/6-Area_StatorIron)/9-hso*dso | `((Rso*Rso-Rsi*Rsi)*pi/6-Area_StatorIron)/9-hso*dso` | Derived usable slot area. |
| 108 | Equation | `Equation parameters: Slot_Fill_Factor` | Area_Conductor*Conductor_Layer/Area_Slot | Area_Conductor*Conductor_Layer/Area_Slot | `Area_Conductor*Conductor_Layer/Area_Slot` | Conductor area divided by usable slot area. |
| 109 | Equation | `Equation parameters: Irms_limit` | J_limit*Area_Conductor*ab | J_limit*Area_Conductor*ab | `J_limit*Area_Conductor*ab` | Allowable RMS current derived from current density, conductor area and branches. |
| 110 | Equation | `Equation parameters: ProcessNo` | 3 | 3 | `3` | Project workflow/optimization process selector. |
| 111 | Equation | `Equation parameters: margin_ratio` | 1.05 | 1.05 | `1.05` | Engineering margin multiplier used by project constraints. |
| 112 | Equation | `Equation parameters: Phase0` | 48.1 | 48.1 | `48.1` | Baseline/reference current phase angle. |
| 113 | Equation | `Equation parameters: Irms` | 111 | 111 | `111` | Applied RMS phase current. |
| 114 | Equation | `Equation parameters: kVA_Ratio` | 2.1323 | 2.1323 | `2.1323` | Project apparent-power scaling or constraint ratio. |
| 115 | Equation | `Equation parameters: kVA_Cost` | 260.43 | 260.43 | `260.43` | Project cost/objective contribution associated with kVA. |
| 116 | Equation | `Equation parameters: objT` | 67.87 | 67.87 | `67.87` | Project optimization objective value/target variable. |
| 117 | Equation | `Equation parameters: IRange0` | 0 | 0 | `0` | Lower/current-range control value for the project workflow. |
| 118 | Equation | `Equation parameters: IRange1` | 0 | 0 | `0` | Upper/secondary current-range control value for the project workflow. |
| 119 | Equation | `Equation parameters: mesh_ratio` | 1 | 1 | `1` | Global mesh-density scaling factor. |
| 120 | Equation | `Equation parameters: Div_Period` | 1 | 1 | `1` | Number of modeled periods used in transient step derivation. |
| 121 | Equation | `Equation parameters: Step` | Div/Div_Period*1.5+1 | Div/Div_Period*1.5+1 |  | Total transient sample points; derived as intervals plus the initial point. |
| 122 | Equation | `Equation parameters: Div` | 60 | 8 | `60` | Base transient divisions; changed from 60 to 8 for this test. |
| 123 | Equation | `Equation parameters: Curesistivity_Eff` | 1.7852e-08*(1+(Tem_Eff_Winding-20)*Cu_Tem_Cof) | 1.7852e-08*(1+(Tem_Eff_Winding-20)*Cu_Tem_Cof) | `1.7852e-08*(1+(Tem_Eff_Winding-20)*Cu_Tem_Cof)` | Temperature-adjusted copper resistivity for active conductors. |
| 124 | Equation | `Equation parameters: Curesistivity_End` | 1.7852e-08*(1+(Tem_End_Winding-20)*Cu_Tem_Cof) | 1.7852e-08*(1+(Tem_End_Winding-20)*Cu_Tem_Cof) | `1.7852e-08*(1+(Tem_End_Winding-20)*Cu_Tem_Cof)` | Temperature-adjusted copper resistivity for end windings. |
| 125 | Equation | `Equation parameters: Tem_Eff_Winding` | 100 | 100 | `100` | Active-winding conductor temperature. |

## What should become reusable functions

| Operation | Recommendation | Reason / boundary |
| --- | --- | --- |
| Load a project and save a protected copy | Candidate: `load_project_copy` | Reusable safety boundary; source/target paths must remain caller configuration. |
| Enumerate every Design Table parameter and Equation metadata | Candidate: `inventory_design_table` | Real TestModel1 evidence exists, including graceful handling of an Equation wrapper that cannot be materialized. |
| Set one or several equation parameters | Reuse `set_parameter` / `set_parameters` | Existing library API succeeded against real JMAG 25.1 with `Div`. |
| Apply CAD parameters and run selected cases | Extend/review `run_cases` or add explicit orchestration | `ApplyAllCasesCadParameters` is Help-verified and was required before this run; result deletion must remain explicit. |
| Read named response values | Reuse/extend `get_value` / `get_values` | Result names and cases remain caller configuration. |
| Export Design Table | Candidate: `export_design_table` | Thin Help-verified wrapper with output-path validation. |
| Export response value table | Candidate: `export_case_values` | General operation, distinct from selecting named responses. |
| Export full result tables | Candidate with explicit axis policy | `Step`, `Time`, `Angle`, or `Distance` must be selected by the caller. |
| Convert 90 intervals to `Div=8` | Do not generalize as a JMAG function | It depends on TestModel1's project equation `Step = Div / Div_Period * 1.5 + 1`. |
| Parameter-purpose text in this report | Do not encode as API behavior | It is engineering interpretation and belongs in model documentation/configuration. |

No candidate should be promoted automatically. `inventory_design_table` has real-project evidence from TestModel1, while project loading, export policies and run orchestration still need isolated tests before catalog publication.

## JMAG 25.1 Help evidence

- `Designer/classApplication.html`: `Load` anchor `af72d1bec02cac3c005fe554aa258b8d9`; `SaveAs` anchor `aec8db8d7e6949bc5a777e5f8e2e505aa`.
- `Designer/classDesignTable.html`: `NumParameters`, `ParameterName`, `ParameterTypeName`, `GetValue`, `SetValue`, and `Export`.
- `Designer/classParametricEquation.html`: `GetName`, `GetDisplayName`, `GetDescription`, `GetExpression`, and zero-based `GetValue`.
- `Designer/classStudy.html`: `ApplyAllCasesCadParameters`, `Run`, `GetResponseData`, `ExportCaseValueData`, and `GetResultTable`.
- `Designer/classResultTable.html`: `WriteAllCaseTables(filename, type)`.

## Produced evidence

- `design_table_before.csv` and `design_table_after.csv`: complete case parameter tables.
- `case_values.csv`: complete response value table.
- `result_tables.csv`: complete Step-axis result tables (260 CSV lines).
- `run_report.json`: machine-readable before/after inventory and run metadata.
- `TestModel1_steps12.jproj` plus `.jfiles`: saved runnable test copy and result files.
